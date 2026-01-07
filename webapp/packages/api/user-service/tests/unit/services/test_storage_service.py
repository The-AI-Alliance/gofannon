"""Unit tests for storage services."""
from __future__ import annotations

import io
from unittest.mock import Mock

import pytest

from services import storage_service


pytestmark = pytest.mark.unit


def test_s3_storage_upload_and_url(monkeypatch):
    uploaded = {}

    class FakeClient:
        def upload_fileobj(self, file_obj, bucket, file_name):
            uploaded["bucket"] = bucket
            uploaded["file_name"] = file_name
            uploaded["content"] = file_obj.read()

    monkeypatch.setattr(storage_service.boto3, "client", lambda *args, **kwargs: FakeClient())
    monkeypatch.setattr(storage_service.settings, "S3_ENDPOINT_URL", "http://s3")
    monkeypatch.setattr(storage_service.settings, "S3_BUCKET_NAME", "bucket")
    monkeypatch.setattr(storage_service.settings, "AWS_ACCESS_KEY_ID", "key")
    monkeypatch.setattr(storage_service.settings, "AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setattr(storage_service.settings, "AWS_DEFAULT_REGION", "us-east-1")

    service = storage_service.S3StorageService()
    payload = io.BytesIO(b"hello")

    service.upload("file.txt", payload)

    assert uploaded == {"bucket": "bucket", "file_name": "file.txt", "content": b"hello"}
    assert service.get_public_url("file.txt") == "http://s3/bucket/file.txt"


def test_gcs_storage_upload_and_url(monkeypatch):
    uploaded = {}

    class FakeBlob:
        def __init__(self, name):
            self.name = name

        def upload_from_file(self, file_obj):
            uploaded["name"] = self.name
            uploaded["content"] = file_obj.read()

    class FakeBucket:
        def __init__(self, name):
            self.name = name

        def blob(self, name):
            return FakeBlob(name)

    class FakeClient:
        def bucket(self, name):
            return FakeBucket(name)

    monkeypatch.setattr(storage_service.storage, "Client", lambda: FakeClient())
    monkeypatch.setattr(storage_service.settings, "S3_BUCKET_NAME", "gcs-bucket")

    service = storage_service.GCSStorageService()
    payload = io.BytesIO(b"hello-gcs")

    service.upload("file.txt", payload)

    assert uploaded == {"name": "file.txt", "content": b"hello-gcs"}
    assert service.get_public_url("file.txt") == "https://storage.googleapis.com/gcs-bucket/file.txt"
