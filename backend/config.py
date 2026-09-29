from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", )

    database_url: str
    
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    #R2 obj storage
    r2_bucket_name: str
    r2_access_key_id: SecretStr | None = None
    r2_secret_access_key: SecretStr | None = None
    r2_endpoint_url: str | None = None
    r2_account_id: str
    r2_api_token: SecretStr
    r2_public_domain: str


    max_upload_size_bytes: int = 5 * 1024 * 1024

    gemini_api_key: SecretStr

    default_city_lat: float = -27.4698
    default_city_lon: float = 153.0251
    default_city_name: str = "Brisbane CBD"

    reset_token_expire_minutes: int = 60
    mail_server: str = "localhost"
    mail_port: int = 587
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    mail_from: str = "noreply@mealfinder.com"
    mail_use_tls: bool = True
    frontend_url: str = "http://localhost:8000"

settings = Settings()