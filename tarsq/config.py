from pydantic_settings import BaseSettings, SettingsConfigDict


class TarsqSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None

    # model_config = {"env_prefix": "TARSQ_"}


settings = TarsqSettings()
