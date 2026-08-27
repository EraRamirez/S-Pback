from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "saas_pymes"
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 24 * 30
    port: int = 8787


settings = Settings()
