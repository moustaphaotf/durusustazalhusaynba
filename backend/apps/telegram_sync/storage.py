from __future__ import annotations

import threading
from dataclasses import dataclass

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class R2Config:
    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    endpoint_url: str
    region: str


_client_lock = threading.Lock()
_client_cache = None


def get_r2_config() -> R2Config:
    missing = []
    if not settings.R2_ACCESS_KEY_ID:
        missing.append("R2_ACCESS_KEY_ID")
    if not settings.R2_SECRET_ACCESS_KEY:
        missing.append("R2_SECRET_ACCESS_KEY")
    if not settings.R2_BUCKET_NAME:
        missing.append("R2_BUCKET_NAME")

    endpoint = settings.R2_ENDPOINT
    if not endpoint and settings.R2_ACCOUNT_ID:
        endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    if not endpoint:
        missing.append("R2_ENDPOINT or R2_ACCOUNT_ID")

    if missing:
        variables = ", ".join(missing)
        raise ImproperlyConfigured(
            f"Missing Cloudflare R2 configuration: {variables}. "
            "Set the variables in the root .env file."
        )

    return R2Config(
        account_id=settings.R2_ACCOUNT_ID,
        access_key_id=settings.R2_ACCESS_KEY_ID,
        secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        bucket_name=settings.R2_BUCKET_NAME,
        endpoint_url=endpoint,
        region=settings.R2_REGION or "auto",
    )


def get_r2_client(config: R2Config | None = None):
    global _client_cache

    r2_config = config or get_r2_config()

    with _client_lock:
        if _client_cache is None:
            _client_cache = boto3.client(
                "s3",
                endpoint_url=r2_config.endpoint_url,
                aws_access_key_id=r2_config.access_key_id,
                aws_secret_access_key=r2_config.secret_access_key,
                region_name=r2_config.region,
                config=Config(signature_version="s3v4"),
            )
    return _client_cache


def upload_file(
    local_path: str,
    key: str,
    *,
    content_type: str = "",
    config: R2Config | None = None,
) -> str:
    r2_config = config or get_r2_config()
    client = get_r2_client(r2_config)

    if content_type:
        client.upload_file(
            Filename=local_path,
            Bucket=r2_config.bucket_name,
            Key=key,
            ExtraArgs={"ContentType": content_type},
        )
    else:
        client.upload_file(
            Filename=local_path,
            Bucket=r2_config.bucket_name,
            Key=key,
        )
    return key


def object_exists(
    key: str,
    *,
    config: R2Config | None = None,
) -> bool:
    """Check whether an exact object key exists without downloading it."""
    r2_config = config or get_r2_config()
    client = get_r2_client(r2_config)
    try:
        client.head_object(Bucket=r2_config.bucket_name, Key=key)
    except ClientError as exc:
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if status_code == 404 or error_code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise
    return True


def find_existing_teaching_key(
    *,
    channel_id: int,
    message_id: int,
    known_key: str = "",
    config: R2Config | None = None,
) -> str | None:
    """Return the existing R2 key for a teaching, if any.

    The exact database key is checked first. If it is missing or stale,
    search the deterministic ``channel/message.`` prefix to recover objects
    whose extension is only known from Telegram metadata.
    """
    r2_config = config or get_r2_config()
    client = get_r2_client(r2_config)

    if known_key and object_exists(known_key, config=r2_config):
        return known_key

    prefix = f"teachings/{channel_id}/{message_id}."
    response = client.list_objects_v2(
        Bucket=r2_config.bucket_name,
        Prefix=prefix,
        MaxKeys=1,
    )
    objects = response.get("Contents") or []
    if not objects:
        return None
    return objects[0]["Key"]


def generate_presigned_url(
    key: str,
    *,
    expires_in: int = 3600,
    config: R2Config | None = None,
) -> str:
    r2_config = config or get_r2_config()
    client = get_r2_client(r2_config)

    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": r2_config.bucket_name, "Key": key},
        ExpiresIn=expires_in,
    )
