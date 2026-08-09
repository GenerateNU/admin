from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class Environment(StrEnum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def settings_config(env_prefix: str = "") -> SettingsConfigDict:
    return SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
        env_prefix=env_prefix,
    )


class BaseConfig(BaseSettings):
    model_config = settings_config()


class AppConfig(BaseConfig):
    model_config = settings_config("APP_")

    name: str = "Generate Admin"
    environment: Environment = Environment.LOCAL
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION


class DatabaseConfig(BaseConfig):
    model_config = settings_config("DATABASE_")

    url: SecretStr
    pool_size: int = 10
    max_overflow: int = 5
    echo: bool = False


class EntraConfig(BaseConfig):
    model_config = settings_config("ENTRA_")

    tenant_id: str = ""
    api_client_id: str = ""
    allowed_audiences_raw: str = Field(default="", alias="ENTRA_ALLOWED_AUDIENCES")

    @property
    def is_configured(self) -> bool:
        return bool(self.tenant_id and self.api_client_id)

    @property
    def issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"

    @property
    def jwks_uri(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"

    @property
    def allowed_audiences(self) -> list[str]:
        configured = _split_csv(self.allowed_audiences_raw)
        return configured or [self.api_client_id, f"api://{self.api_client_id}"]


class StorageConfig(BaseConfig):
    endpoint: str = Field(default="", alias="S3_ENDPOINT")
    bucket_name: str = Field(default="", alias="S3_BUCKET_NAME")
    region: str = Field(default="us-east-1", alias="AWS_REGION")
    access_key_id: SecretStr = Field(default=SecretStr(""), alias="AWS_ACCESS_KEY_ID")
    secret_access_key: SecretStr = Field(default=SecretStr(""), alias="AWS_SECRET_ACCESS_KEY")
    public_base_url: str = Field(default="", alias="S3_PUBLIC_BASE_URL")
    upload_url_ttl_seconds: int = Field(default=900, alias="S3_UPLOAD_URL_TTL_SECONDS")
    download_url_ttl_seconds: int = Field(default=3600, alias="S3_DOWNLOAD_URL_TTL_SECONDS")
    max_upload_bytes: int = Field(default=26_214_400, alias="S3_MAX_UPLOAD_BYTES")

    @property
    def is_configured(self) -> bool:
        return bool(self.bucket_name)

    def public_url_for(self, key: str) -> str:
        base = self.public_base_url or f"{self.endpoint}/{self.bucket_name}"
        return f"{base.rstrip('/')}/{key}"


class Settings(BaseConfig):
    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    entra: EntraConfig = Field(default_factory=EntraConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    cors_allowed_origins_raw: str = Field(default="", alias="CORS_ALLOWED_ORIGINS")
    redis_url: str = Field(default="", alias="REDIS_URL")

    @property
    def cors_allowed_origins(self) -> list[str]:
        return _split_csv(self.cors_allowed_origins_raw)


@lru_cache
def get_settings() -> Settings:
    return Settings()
