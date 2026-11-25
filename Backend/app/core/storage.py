"""Where uploaded files (profile photos) are kept: a local folder or an AWS S3 bucket.

STORAGE_BACKEND=local: files go in MEDIA_DIR and are served by the API at /media/<key>.
STORAGE_BACKEND=s3: files go in S3_BUCKET; the URL is a presigned link that lasts 1 hour,
so the bucket can stay private.
"""

from pathlib import Path

from app.config import settings

MEDIA_URL_PATH = "/media"
S3_URL_SECONDS = 3600


def _s3_client():
    import boto3

    return boto3.client(
        "s3",
        region_name=settings.s3_region or None,
        endpoint_url=settings.s3_endpoint_url or None,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )


def _local_path(key: str) -> Path:
    return Path(settings.media_dir) / key


def save(key: str, data: bytes, content_type: str) -> None:
    if settings.storage_backend == "s3":
        _s3_client().put_object(
            Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type
        )
    else:
        path = _local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def delete(key: str) -> None:
    if settings.storage_backend == "s3":
        _s3_client().delete_object(Bucket=settings.s3_bucket, Key=key)
    else:
        _local_path(key).unlink(missing_ok=True)


def url(key: str | None) -> str | None:
    if key is None:
        return None
    if settings.storage_backend == "s3":
        return _s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=S3_URL_SECONDS,
        )
    return f"{MEDIA_URL_PATH}/{key}"
