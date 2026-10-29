"""Local/S3 storage adapter. Access control remains in generated_file_service."""
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from app.config import settings


@lru_cache(maxsize=1)
def s3_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        's3', endpoint_url=settings.s3_endpoint_url, region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id or None,
        aws_secret_access_key=settings.s3_secret_access_key or None,
        config=Config(connect_timeout=3, read_timeout=30, retries={'max_attempts': 2},
                      s3={'addressing_style': 'path'}),
    )


def _object_location(reference: str) -> tuple[str, str]:
    parsed = urlparse(reference)
    key = parsed.path.lstrip('/')
    prefix = settings.s3_key_prefix.strip('/') + '/'
    if parsed.scheme != 's3' or parsed.netloc != settings.s3_bucket or not key.startswith(prefix):
        raise ValueError('Artifact object is outside configured storage scope')
    return parsed.netloc, key


def put_artifact(storage_name: str, content: bytes, mime_type: str) -> str:
    if not storage_name or Path(storage_name).name != storage_name or storage_name in {'.', '..'}:
        raise ValueError('Artifact storage name must be a filename')
    if settings.artifact_storage_backend == 's3':
        if not settings.s3_bucket:
            raise ValueError('S3_BUCKET is required for object storage')
        key = settings.s3_key_prefix.strip('/') + '/' + storage_name
        s3_client().put_object(Bucket=settings.s3_bucket, Key=key, Body=content, ContentType=mime_type)
        return f's3://{settings.s3_bucket}/{key}'
    directory = Path(settings.generated_file_storage_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / storage_name
    import os
    import tempfile
    fd, temporary_name = tempfile.mkstemp(dir=directory, prefix='.upload-')
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(content)
        os.replace(temporary_name, path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    return str(path)


def local_artifact_path(reference: str) -> Path:
    path = Path(reference).resolve()
    root = Path(settings.generated_file_storage_dir).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Artifact file is outside configured storage scope')
    return path


def read_artifact(reference: str) -> bytes:
    if reference.startswith('s3://'):
        bucket, key = _object_location(reference)
        response = s3_client().get_object(Bucket=bucket, Key=key)
        body = response['Body']
        try:
            return body.read()
        finally:
            body.close()
    return local_artifact_path(reference).read_bytes()


def artifact_exists(reference: str) -> bool:
    if reference.startswith('s3://'):
        from botocore.exceptions import ClientError
        bucket, key = _object_location(reference)
        try:
            s3_client().head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as error:
            if error.response.get('Error', {}).get('Code') in {'404', 'NoSuchKey', 'NotFound'}:
                return False
            raise
    return local_artifact_path(reference).is_file()


def delete_artifact(reference: str) -> None:
    if reference.startswith('s3://'):
        bucket, key = _object_location(reference)
        s3_client().delete_object(Bucket=bucket, Key=key)
    else:
        local_artifact_path(reference).unlink(missing_ok=True)


def materialize_artifact(reference: str) -> str:
    """Supply a local path only for existing desktop/RPA attachment adapters."""
    if not reference.startswith('s3://'):
        return str(local_artifact_path(reference))
    from hashlib import sha256
    bucket, key = _object_location(reference)
    root = Path(settings.generated_file_storage_dir).resolve() / 'materialized'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / (sha256(reference.encode()).hexdigest()+Path(key).suffix)
    # Do not reuse a stale copy after the source object changes.
    content = read_artifact(reference)
    import os
    import tempfile
    fd, temporary_name = tempfile.mkstemp(dir=root, prefix='.download-')
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(content)
        os.replace(temporary_name, path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    return str(path)


def cleanup_materialized_files() -> int:
    from time import time
    root = Path(settings.generated_file_storage_dir).resolve() / 'materialized'
    if not root.is_dir():
        return 0
    cutoff = time() - settings.materialized_file_retention_hours * 3600
    deleted = 0
    for path in root.iterdir():
        if not path.is_symlink() and path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
            deleted += 1
    return deleted
