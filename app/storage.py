import os
from io import BytesIO

from dotenv import load_dotenv
from minio import Minio

load_dotenv()

MINIO_BUCKET = os.environ["MINIO_BUCKET"]
MINIO_ENDPOINT = os.environ["MINIO_ENDPOINT"]
MINIO_ACCESS_KEY = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET_KEY = os.environ["MINIO_SECRET_KEY"]
MINIO_SECURE = os.environ["MINIO_SECURE"].lower() == "true"


def get_minio_client() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


def ensure_bucket() -> None:
    minio_client = get_minio_client()
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)


def upload_cv(
    object_key: str, content: bytes, content_type: str | None
) -> None:
    minio_client = get_minio_client()
    ensure_bucket()
    minio_client.put_object(
        MINIO_BUCKET,
        object_key,
        BytesIO(content),
        length=len(content),
        content_type=content_type or "application/octet-stream",
    )


def get_cv_url(object_key: str, expires_seconds: int = 900) -> str:
    from datetime import timedelta

    return get_minio_client().presigned_get_object(
        MINIO_BUCKET, object_key, expires=timedelta(seconds=expires_seconds)
    )


def download_cv(object_key: str) -> tuple[bytes, str | None]:
    minio_client = get_minio_client()
    response = minio_client.get_object(MINIO_BUCKET, object_key)
    data = response.read()
    content_type = response.headers.get("Content-Type")
    response.close()
    response.release_conn()
    return data, content_type
