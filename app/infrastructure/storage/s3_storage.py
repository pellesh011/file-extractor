from __future__ import annotations

from collections.abc import AsyncIterator

from aiobotocore.session import AioSession
from loguru import logger

from app.application.ports.object_storage import ObjectStorage
from app.core.config import settings


class S3Storage(ObjectStorage):
    def __init__(self) -> None:
        self._session = AioSession()
        self._bucket = settings.s3_bucket_name
        self._endpoint = settings.s3_endpoint_url

    async def upload_stream(
        self,
        stream: AsyncIterator[bytes],
        key: str,
        length: int,
    ) -> str:
        async with self._session.create_client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        ) as client:
            await client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=b"".join([chunk async for chunk in stream]),
            )
            logger.info(
                "s3_upload_completed",
                key=key,
                size=length,
                bucket=self._bucket,
            )
            return key

    async def delete(self, key: str) -> None:
        async with self._session.create_client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        ) as client:
            await client.delete_object(Bucket=self._bucket, Key=key)
            logger.info("s3_delete_completed", key=key, bucket=self._bucket)

    async def get_download_url(self, key: str, expires_in: int = 3600) -> str | None:
        async with self._session.create_client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        ) as client:
            url: str = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
