from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", )

    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    max_upload_size_bytes: int = 5 * 1024 * 1024

    gemini_api_key: SecretStr

    default_city_lat: float = -27.4698
    default_city_lon: float = 153.0251
    default_city_name: str = "Brisbane CBD"


settings = Settings()