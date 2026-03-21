from __future__ import annotations

import hashlib
import io
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.config import settings
from app.core.logger import logger


class StorageManager:
    def __init__(self):
        self.base_dir = Path(settings.STORAGE_BASE_PATH).expanduser().resolve()
        self._s3_client = None
        self._bucket_checked = False
        self._ensure_directories()

    @property
    def is_s3(self) -> bool:
        return settings.STORAGE_BACKEND == "s3"

    def _ensure_directories(self) -> None:
        for subdir in ["papers", "slides", "notes", "searches", "books", "datasets", "artifacts"]:
            (self.base_dir / subdir).mkdir(parents=True, exist_ok=True)

    def _sanitize_path(self, path: Path) -> Path:
        resolved = path.resolve()
        try:
            resolved.relative_to(self.base_dir)
        except ValueError as exc:
            raise ValueError(f"Path {path} está fuera de base directory") from exc
        return resolved

    def _sanitize_relative_key(self, key: str) -> str:
        candidate = Path(key)
        if candidate.is_absolute():
            raise ValueError("Storage key must be relative")
        normalized = str(candidate).replace("\\", "/").lstrip("/")
        if not normalized or normalized.startswith("../") or "/../" in normalized:
            raise ValueError("Invalid storage key")
        return normalized

    def _calculate_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def validate_pdf(self, data: bytes) -> bool:
        if not data.startswith(b"%PDF-"):
            return False
        if b"%%EOF" not in data[-2048:]:
            return False
        return True

    def validate_pptx(self, data: bytes) -> bool:
        if not data.startswith(b"PK\x03\x04"):
            return False
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = set(z.namelist())
                if "[Content_Types].xml" not in names:
                    return False
                return any(name.startswith("ppt/") for name in names)
        except Exception:
            return False

    def _sanitize_filename(self, filename: str) -> str:
        clean = "".join(c for c in filename if c.isalnum() or c in (" ", "-", "_", "."))
        clean = clean.strip().replace("..", ".")
        return clean or "artifact"

    def _s3(self):
        if self._s3_client is None:
            import boto3
            from botocore.config import Config as BotoConfig

            self._s3_client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
                config=BotoConfig(s3={"addressing_style": "path" if settings.S3_FORCE_PATH_STYLE else "auto"}),
            )
        return self._s3_client

    def ensure_bucket(self) -> None:
        if not self.is_s3 or self._bucket_checked:
            return
        client = self._s3()
        try:
            client.head_bucket(Bucket=settings.S3_BUCKET)
        except Exception:
            if not settings.S3_AUTO_CREATE_BUCKET:
                raise
            client.create_bucket(Bucket=settings.S3_BUCKET)
        self._bucket_checked = True

    def _save_locally(self, *, relative_path: str, data: bytes) -> Dict[str, Any]:
        file_path = self._sanitize_path(self.base_dir / relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        return {
            "file_path": str(file_path.relative_to(self.base_dir)),
            "size_kb": len(data) // 1024,
            "content_hash": self._calculate_hash(data),
        }

    def _save_s3(self, *, relative_path: str, data: bytes) -> Dict[str, Any]:
        key = self._sanitize_relative_key(relative_path)
        self.ensure_bucket()
        self._s3().put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=data,
            ContentLength=len(data),
        )
        return {
            "file_path": key,
            "size_kb": len(data) // 1024,
            "content_hash": self._calculate_hash(data),
        }

    def _persist_bytes(self, *, relative_path: str, data: bytes) -> Dict[str, Any]:
        if self.is_s3:
            return self._save_s3(relative_path=relative_path, data=data)
        return self._save_locally(relative_path=relative_path, data=data)

    def _build_relative_path(self, *, subdir: str, filename: str, project_id: UUID | None = None) -> str:
        safe_filename = self._sanitize_filename(filename)
        path = Path(subdir)
        if project_id is not None:
            path /= str(project_id)
        return str(path / safe_filename)

    def _save_bytes(self, *, subdir: str, filename: str, data: bytes, project_id: UUID | None = None) -> Dict[str, Any]:
        relative_path = self._build_relative_path(subdir=subdir, filename=filename, project_id=project_id)
        saved = self._persist_bytes(relative_path=relative_path, data=data)
        saved["filename"] = self._sanitize_filename(filename)
        return saved

    async def save_paper_bytes(
        self,
        *,
        data: bytes,
        project_id: UUID,
        suggested_filename: str | None = None,
    ) -> Dict:
        if not self.validate_pdf(data):
            raise ValueError("Archivo no es un PDF válido")

        year = datetime.now().year
        base_name = suggested_filename or f"{project_id}_{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}.pdf"
        safe_name = self._sanitize_filename(base_name)
        if not safe_name.lower().endswith(".pdf"):
            safe_name += ".pdf"
        relative_path = str(Path("papers") / str(project_id) / str(year) / safe_name)
        saved = self._persist_bytes(relative_path=relative_path, data=data)
        saved["filename"] = safe_name
        return saved

    async def save_paper(self, file: UploadFile, project_id: UUID) -> Dict:
        content = await file.read()
        return await self.save_paper_bytes(data=content, project_id=project_id, suggested_filename=file.filename or None)

    async def save_presentation(self, content: bytes, filename: str, project_id: UUID) -> Dict:
        if not self.validate_pptx(content):
            raise ValueError("Archivo no es un PPTX válido")
        saved = self._save_bytes(subdir="slides", filename=filename, data=content, project_id=project_id)
        return {
            "filename": saved["filename"],
            "file_path": saved["file_path"],
            "size_kb": saved["size_kb"],
        }

    async def save_dataset_bytes(self, *, data: bytes, filename: str, project_id: UUID) -> Dict[str, Any]:
        return self._save_bytes(subdir="datasets", filename=filename, data=data, project_id=project_id)

    async def save_artifact_bytes(self, *, data: bytes, filename: str, project_id: UUID) -> Dict[str, Any]:
        return self._save_bytes(subdir="artifacts", filename=filename, data=data, project_id=project_id)

    async def save_text_artifact(self, *, text: str, filename: str, project_id: UUID) -> Dict[str, Any]:
        return await self.save_artifact_bytes(data=text.encode("utf-8"), filename=filename, project_id=project_id)

    def read_bytes(self, file_path: str) -> bytes:
        if self.is_s3:
            key = self._sanitize_relative_key(file_path)
            self.ensure_bucket()
            response = self._s3().get_object(Bucket=settings.S3_BUCKET, Key=key)
            return response["Body"].read()
        full_path = self._sanitize_path(self.base_dir / file_path)
        return full_path.read_bytes()

    def delete_file(self, file_path: str) -> bool:
        if self.is_s3:
            key = self._sanitize_relative_key(file_path)
            self.ensure_bucket()
            self._s3().delete_object(Bucket=settings.S3_BUCKET, Key=key)
            return True
        full_path = self._sanitize_path(self.base_dir / file_path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    def get_file_info(self, file_path: str) -> Dict:
        if self.is_s3:
            key = self._sanitize_relative_key(file_path)
            self.ensure_bucket()
            response = self._s3().head_object(Bucket=settings.S3_BUCKET, Key=key)
            return {
                "size_bytes": int(response["ContentLength"]),
                "created": response.get("LastModified"),
                "modified": response.get("LastModified"),
                "exists": True,
            }
        full_path = self._sanitize_path(self.base_dir / file_path)
        if not full_path.exists():
            raise FileNotFoundError(f"Archivo {file_path} no existe")
        stat = full_path.stat()
        return {
            "size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "exists": True,
        }

    def safe_abs_path(self, relative_path: str) -> Path:
        """Resolve *relative_path* to an absolute path inside base_dir.

        Raises HTTPException 400 on path traversal or S3 backend (callers that
        need a local filesystem path must guard against S3 themselves).

        This is the single canonical implementation — routers should call this
        instead of defining their own ``_safe_abs_path`` helpers.
        """
        from fastapi import HTTPException  # local import to avoid circular

        if self.is_s3:
            raise HTTPException(status_code=400, detail="S3-backed files do not have a local path")
        full_path = (self.base_dir / relative_path).resolve()
        try:
            full_path.relative_to(self.base_dir)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid file path")
        return full_path

    @contextmanager
    def local_path(self, file_path: str, *, suffix: str | None = None) -> Iterator[Path]:
        if self.is_s3:
            data = self.read_bytes(file_path)
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or Path(file_path).suffix or "") as tmp:
                tmp.write(data)
                tmp_path = Path(tmp.name)
            try:
                yield tmp_path
            finally:
                tmp_path.unlink(missing_ok=True)
            return

        full_path = self._sanitize_path(self.base_dir / file_path)
        yield full_path


storage_manager = StorageManager()
