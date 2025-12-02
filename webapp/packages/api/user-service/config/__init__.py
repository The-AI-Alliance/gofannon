import os
from dotenv import load_dotenv

load_dotenv()


def _get_bool_env(var_name: str, default: bool = False) -> bool:
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "local")
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")

    ADMIN_PANEL_ENABLED: bool = _get_bool_env("ADMIN_PANEL_ENABLED", False)
    ADMIN_PANEL_PASSWORD: str = os.getenv("ADMIN_PANEL_PASSWORD", "password")

    # S3/MinIO Settings
    S3_ENDPOINT_URL: str | None = os.getenv("S3_ENDPOINT_URL")
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_DEFAULT_REGION: str | None = os.getenv("AWS_DEFAULT_REGION")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "local-bucket")

    # Database Settings
    DATABASE_PROVIDER: str = os.getenv("DATABASE_PROVIDER", "memory") # Default to memory if not set
    COUCHDB_URL: str | None = os.getenv("COUCHDB_URL")
    COUCHDB_USER: str | None = os.getenv("COUCHDB_USER")
    COUCHDB_PASSWORD: str | None = os.getenv("COUCHDB_PASSWORD")
    # AWS CloudWatch Logging Settings
    CLOUDWATCH_LOG_GROUP_NAME: str | None = os.getenv("CLOUDWATCH_LOG_GROUP_NAME")
    # Google Cloud Settings
    GCP_PROJECT_ID: str | None = os.getenv("GCP_PROJECT_ID")


settings = Settings()
