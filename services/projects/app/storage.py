import uuid
from typing import Any

import aioboto3
from botocore.config import Config


class MinIOStorage:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        use_ssl: bool = False,
    ) -> None:
        self._endpoint = f"{'https' if use_ssl else 'http'}://{endpoint}"
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket = bucket
        self._session = aioboto3.Session()

    def _client(self) -> Any:
        return self._session.client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            config=Config(signature_version="s3v4"),
        )

    def make_object_key(self, tenant_id: uuid.UUID, attachment_id: uuid.UUID, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        return f"{tenant_id}/{attachment_id}.{ext}" if ext else f"{tenant_id}/{attachment_id}"

    async def generate_presigned_put_url(
        self, object_key: str, content_type: str, expire_seconds: int = 300
    ) -> str:
        async with self._client() as s3:
            url: str = await s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": self._bucket, "Key": object_key, "ContentType": content_type},
                ExpiresIn=expire_seconds,
            )
        return url

    async def generate_presigned_get_url(self, object_key: str, expire_seconds: int = 3600) -> str:
        async with self._client() as s3:
            url: str = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": object_key},
                ExpiresIn=expire_seconds,
            )
        return url

    async def object_exists(self, object_key: str) -> bool:
        try:
            async with self._client() as s3:
                await s3.head_object(Bucket=self._bucket, Key=object_key)
            return True
        except Exception:
            return False

    async def delete_object(self, object_key: str) -> None:
        async with self._client() as s3:
            await s3.delete_object(Bucket=self._bucket, Key=object_key)
