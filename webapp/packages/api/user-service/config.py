import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "local")
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")
    
    # S3/MinIO Settings
    S3_ENDPOINT_URL: str | None = os.getenv("S3_ENDPOINT_URL")
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_DEFAULT_REGION: str | None = os.getenv("AWS_DEFAULT_REGION")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "local-bucket")


settings = Settings()