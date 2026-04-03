from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.core.storage import StorageManager
import pytest

class FakeBody:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data

class FakeS3:
    def __init__(self):
        self.objects = {}
        self.created_bucket = None
        self.raise_on_put = False

    def head_bucket(self, Bucket):
        if self.created_bucket != Bucket:
            raise Exception("missing bucket")

    def create_bucket(self, Bucket):
        self.created_bucket = Bucket

    def put_object(self, Bucket, Key, Body, ContentLength):
        if self.raise_on_put:
            raise Exception("Upload failed")
        self.objects[(Bucket, Key)] = bytes(Body)

    def get_object(self, Bucket, Key):
        return {"Body": FakeBody(self.objects[(Bucket, Key)])}

    def head_object(self, Bucket, Key):
        return {"ContentLength": len(self.objects[(Bucket, Key)]), "LastModified": None}

    def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)

def test_storage_manager_can_roundtrip_s3(monkeypatch, tmp_path):
    original_backend = settings.STORAGE_BACKEND
    settings.STORAGE_BACKEND = "s3"
    try:
        fake_s3 = FakeS3()
        manager = StorageManager()
        manager.base_dir = tmp_path.resolve()
        monkeypatch.setattr(manager, "_s3", lambda: fake_s3)

        saved = manager._persist_bytes(relative_path="papers/test.pdf", data=b"hello")
        assert saved["file_path"] == "papers/test.pdf"
        assert manager.read_bytes("papers/test.pdf") == b"hello"
        assert manager.get_file_info("papers/test.pdf")["exists"] is True
        with manager.local_path("papers/test.pdf", suffix=".pdf") as local_path:
            assert Path(local_path).read_bytes() == b"hello"
    finally:
        settings.STORAGE_BACKEND = original_backend

def test_s3_upload_exception_handled(monkeypatch, tmp_path):
    original_backend = settings.STORAGE_BACKEND
    settings.STORAGE_BACKEND = "s3"
    try:
        fake_s3 = FakeS3()
        fake_s3.raise_on_put = True

        manager = StorageManager()
        manager.base_dir = tmp_path.resolve()

        manager._s3_client = fake_s3
        manager._bucket_checked = True

        with pytest.raises(RuntimeError, match="Storage upload failed: Upload failed"):
            manager._save_s3(relative_path="papers/fail.pdf", data=b"fail")

    finally:
        settings.STORAGE_BACKEND = original_backend
