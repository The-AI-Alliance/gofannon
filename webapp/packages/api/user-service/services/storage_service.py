import boto3
from botocore.client import Config
from ..config import settings

class StorageService:
    def upload(self, file_name: str, file_obj):
        raise NotImplementedError

    def get_public_url(self, file_name: str) -> str:
        raise NotImplementedError

class S3StorageService(StorageService):
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name=settings.AWS_DEFAULT_REGION,
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    def upload(self, file_name: str, file_obj):
        self.s3_client.upload_fileobj(file_obj, self.bucket_name, file_name)
        print(f"Uploaded {file_name} to {self.bucket_name}")

    def get_public_url(self, file_name: str) -> str:
        # Note: This requires the object to have public-read ACL
        return f"{settings.S3_ENDPOINT_URL}/{self.bucket_name}/{file_name}"

class LocalDiskStorageService(StorageService):
    def upload(self, file_name: str, file_obj):
        # Implementation for saving to local disk
        pass

# --- Service Factory ---
def get_storage_service() -> StorageService:
    if settings.STORAGE_PROVIDER == "s3":
        return S3StorageService()
    elif settings.STORAGE_PROVIDER == "local":
        return LocalDiskStorageService()
    else:
        raise ValueError(f"Unknown storage provider: {settings.STORAGE_PROVIDER}")