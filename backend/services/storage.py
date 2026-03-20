import io
import os
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile

from config import settings

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None


def _safe_name(file_name: str) -> str:
    return file_name.replace("\\", "_").replace("/", "_")


class StorageService:
    def __init__(self):
        self.backend = settings.STORAGE_BACKEND.lower()
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.export_dir = Path(settings.EXPORT_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)

        self.s3_client = None
        if self.backend == "s3" and boto3:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
            )

    async def save_upload(self, file: UploadFile) -> Tuple[str, str]:
        ext = Path(file.filename or "").suffix
        saved_name = f"{uuid.uuid4()}{ext}"
        disk_path = self.upload_dir / saved_name
        content = await file.read()

        if self.backend == "s3" and self.s3_client and settings.S3_BUCKET:
            self.s3_client.upload_fileobj(
                io.BytesIO(content),
                settings.S3_BUCKET,
                f"uploads/{saved_name}",
                ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
            )
            uri = f"s3://{settings.S3_BUCKET}/uploads/{saved_name}"
            return saved_name, uri

        disk_path.write_bytes(content)
        return saved_name, str(disk_path.resolve())

    def save_export_bytes(self, file_name: str, payload: bytes) -> str:
        safe = _safe_name(file_name)
        target = self.export_dir / safe

        if self.backend == "s3" and self.s3_client and settings.S3_BUCKET:
            self.s3_client.upload_fileobj(
                io.BytesIO(payload),
                settings.S3_BUCKET,
                f"exports/{safe}",
                ExtraArgs={"ContentType": "application/octet-stream"},
            )
            return f"s3://{settings.S3_BUCKET}/exports/{safe}"

        target.write_bytes(payload)
        return str(target.resolve())

    def read_local_bytes(self, path: str) -> bytes:
        return Path(path).read_bytes()


storage_service = StorageService()
