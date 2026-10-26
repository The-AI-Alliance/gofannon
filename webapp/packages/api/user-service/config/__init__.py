import os
from dotenv import load_dotenv

load_dotenv()


def _get_bool_env(var_name: str, default: bool = False) -> bool:
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


def _load_auth_config() -> dict:
    """Load auth config from AUTH_CONFIG_PATH (YAML) if set.

    Returns a dict with keys: providers (list), site_admins (list),
    session_ttl_hours (int), workspace_refresh_minutes (int),
    legacy_firebase_enabled (bool). When no config file is present, returns
    an empty/default config that keeps Phase B disabled — pre-Phase-B
    deployments work without any auth config file.
    """
    defaults = {
        "providers": [],
        "site_admins": [],
        "session_ttl_hours": 24,
        "workspace_refresh_minutes": 15,
        "legacy_firebase_enabled": True,
    }
    path = os.getenv("AUTH_CONFIG_PATH")
    if not path or not os.path.exists(path):
        return defaults
    try:
        import yaml
        with open(path, "r") as fh:
            raw = yaml.safe_load(fh) or {}
        auth = raw.get("auth", {})
        return {**defaults, **auth}
    except Exception as e:
        print(f"Warning: failed to load AUTH_CONFIG_PATH={path}: {e}")
        return defaults


class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "local")
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")

    ADMIN_PANEL_ENABLED: bool = _get_bool_env("ADMIN_PANEL_ENABLED", False)
    ADMIN_PANEL_PASSWORD: str = os.getenv("ADMIN_PANEL_PASSWORD", "password")

    # S3/MinIO Settings
    S3_ENDPOINT_URL: str | None = os.getenv("S3_ENDPOINT_URL")
    # Renamed from AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY. Those are the
    # STANDARD AWS credential env vars, so boto3 read them before reaching
    # the EC2 instance role -- meaning any SDK call meant to use the
    # instance role silently got MinIO credentials instead. The S3_ prefix
    # says what they actually are and unshadows the instance role.
    S3_ACCESS_KEY_ID: str | None = os.getenv("S3_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY: str | None = os.getenv("S3_SECRET_ACCESS_KEY")
    # Deprecated aliases, kept so existing deployments and any code still
    # reading the old attribute names keep working. They prefer the S3_
    # environment variables and fall back to the old ones, so a deployment
    # can migrate at its own pace. Prefer S3_ACCESS_KEY_ID /
    # S3_SECRET_ACCESS_KEY in new code; these will go away in a future
    # release.
    AWS_ACCESS_KEY_ID: str | None = (
        os.getenv("S3_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
    )
    AWS_SECRET_ACCESS_KEY: str | None = (
        os.getenv("S3_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    AWS_DEFAULT_REGION: str | None = os.getenv("AWS_DEFAULT_REGION")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "local-bucket")

    # Database Settings
    DATABASE_PROVIDER: str = os.getenv("DATABASE_PROVIDER", "memory") # Default to memory if not set
    COUCHDB_URL: str | None = os.getenv("COUCHDB_URL")
    COUCHDB_USER: str | None = os.getenv("COUCHDB_USER")
    COUCHDB_PASSWORD: str | None = os.getenv("COUCHDB_PASSWORD")
    
    # DynamoDB Settings
    DYNAMODB_REGION: str | None = os.getenv("DYNAMODB_REGION")
    DYNAMODB_ENDPOINT_URL: str | None = os.getenv("DYNAMODB_ENDPOINT_URL")

    # AWS CloudWatch Logging Settings
    CLOUDWATCH_LOG_GROUP_NAME: str | None = os.getenv("CLOUDWATCH_LOG_GROUP_NAME")
    # Google Cloud Settings
    GCP_PROJECT_ID: str | None = os.getenv("GCP_PROJECT_ID")

    # Phase B: pluggable auth providers. See auth/ module and docs/PHASE_B.md.
    # Disabled by default — legacy Firebase path is the only enabled path
    # until a site operator sets AUTH_CONFIG_PATH or the APP_ENV.
    AUTH_CONFIG_PATH: str | None = os.getenv("AUTH_CONFIG_PATH")
    AUTH_CONFIG: dict = _load_auth_config()


settings = Settings()