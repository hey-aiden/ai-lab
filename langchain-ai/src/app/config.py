"""应用配置：统一从环境变量 / .env 读取并做类型校验。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """项目配置，字段与 .env 变量一一对应（大小写不敏感）。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key_deepseek: str
    model_deepseek: str = "deepseek-chat"
    temperature: float = 0.0
    db_url: str


settings = Settings()
