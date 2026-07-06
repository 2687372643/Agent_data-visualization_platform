"""
应用核心配置模块

使用 pydantic-settings 从环境变量和 .env 文件读取配置，
提供全局单例 `settings`。

用法:
    from app.core.config import settings

    # 直接访问各属性
    db_url = settings.database.url
    redis_url = settings.redis.url
    model = settings.llm.model_name
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ──────────────────────────────────────────────
#  项目根目录（自动向上查找 backend/ 目录）
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


# ──────────────────────────────────────────────
#  子配置：数据库
# ──────────────────────────────────────────────
class DatabaseConfig(BaseSettings):
    """PostgreSQL 数据库连接与连接池配置。"""

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/advp",
        description="异步数据库连接串",
    )
    pool_size: int = Field(default=10, ge=1, description="连接池大小")
    max_overflow: int = Field(default=20, ge=0, description="连接池溢出上限")
    echo: bool = Field(default=False, description="是否打印 SQL 语句（调试用）")


# ──────────────────────────────────────────────
#  子配置：Redis
# ──────────────────────────────────────────────
class RedisConfig(BaseSettings):
    """Redis 缓存与任务队列配置。"""

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis 连接串",
    )
    socket_timeout: int = Field(default=5, ge=1, description="Socket 超时（秒）")
    cache_ttl: int = Field(default=300, ge=0, description="默认缓存 TTL（秒）")


# ──────────────────────────────────────────────
#  子配置：LLM / Agent
# ──────────────────────────────────────────────
class LLMConfig(BaseSettings):
    """大语言模型与 Agent 运行时配置。"""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str = Field(default="", description="LLM API Key")
    base_url: str = Field(default="", description="API 基础地址（兼容 OpenAI 格式）")
    model_name: str = Field(default="gpt-4o", description="模型名称")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="生成温度")
    max_tokens: int = Field(default=4096, ge=1, description="每次调用最大 Token 数")
    max_retries: int = Field(default=3, ge=0, description="失败最大重试次数")
    request_timeout: int = Field(default=60, ge=1, description="请求超时（秒）")


# ──────────────────────────────────────────────
#  子配置：日志
# ──────────────────────────────────────────────
class LogConfig(BaseSettings):
    """结构化日志配置。"""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    level: str = Field(default="INFO", description="日志级别 (DEBUG/INFO/WARNING/ERROR)")
    format: str = Field(
        default="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        description="日志格式字符串",
    )
    # JSON 结构化日志开关，生产环境开启
    use_json: bool = Field(default=False, description="是否输出 JSON 格式日志")


# ──────────────────────────────────────────────
#  主配置聚合
# ──────────────────────────────────────────────
class Settings(BaseSettings):
    """
    应用主配置。

    所有子配置通过嵌套模型聚合，.env 文件中用前缀区分：
      DATABASE_URL=...
      REDIS_URL=...
      LLM_API_KEY=...
      LOG_LEVEL=INFO
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # 允许嵌套模型使用各自 env_prefix
        env_nested_delimiter="__",
    )

    # ── 应用基础 ──
    app_name: str = Field(default="AI Agent Data Platform", description="应用名称")
    debug: bool = Field(default=False, description="调试模式")
    version: str = Field(default="0.1.0", description="API 版本号")

    # ── CORS ──
    cors_origins: list[str] = Field(default=["*"], description="允许的 CORS 来源")

    # ── 数据目录 ──
    upload_dir: str = Field(
        default=str(PROJECT_ROOT / "backend" / "data" / "uploads"),
        description="上传文件存储路径",
    )
    chart_dir: str = Field(
        default=str(PROJECT_ROOT / "backend" / "data" / "charts"),
        description="图表 HTML 存储路径",
    )
    export_dir: str = Field(
        default=str(PROJECT_ROOT / "backend" / "data" / "exports"),
        description="导出文件存储路径",
    )
    temp_dir: str = Field(
        default=str(PROJECT_ROOT / "backend" / "data" / "temp"),
        description="临时文件存储路径",
    )

    # ── 文件上传限制 ──
    max_upload_size_mb: int = Field(default=200, ge=1, description="单文件上传上限（MB）")
    allowed_extensions: list[str] = Field(
        default=[".csv", ".xlsx", ".xls", ".json", ".tsv", ".parquet"],
        description="允许上传的文件扩展名",
    )

    # ── 子配置 ──
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    log: LogConfig = Field(default_factory=LogConfig)

    def ensure_dirs(self) -> None:
        """确保所有数据目录存在。"""
        for dir_path in [self.upload_dir, self.chart_dir, self.export_dir, self.temp_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


# ── 全局单例 ──
settings = Settings()
