"""配置管理模块 - 使用Pydantic Settings从环境变量读取配置"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """应用配置类 - 禁止硬编码，所有配置从环境变量读取"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # LLM配置 - 硅基流动
    siliconflow_api_key: str
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_fast_model: str = "deepseek-ai/DeepSeek-V3"
    siliconflow_strong_model: str = "Qwen/Qwen2.5-72B-Instruct"
    
    # LLM配置 - OpenAI（备选）
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    
    # ClickHouse配置
    clickhouse_host: str
    clickhouse_port: int = 8868
    clickhouse_database: str
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_pool_size: int = 5
    
    # 应用配置
    app_env: Literal["development", "production"] = "development"
    app_port: int = 8000
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    # 记忆配置
    memory_store_backend: Literal["memory", "redis", "postgres"] = "memory"
    memory_max_messages: int = 20
    
    # LangSmith追踪
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "hkex-analysis"
    
    # 性能配置
    max_concurrent_tools: int = 5
    tool_timeout: int = 30
    agent_max_iterations: int = 10
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.app_env == "production"
    
    @property
    def clickhouse_url(self) -> str:
        """ClickHouse连接URL"""
        return f"clickhouse://{self.clickhouse_user}:{self.clickhouse_password}@{self.clickhouse_host}:{self.clickhouse_port}/{self.clickhouse_database}"


# 全局配置实例 - 懒加载
_settings: Settings | None = None


def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# 便捷导出
settings = get_settings()

