from __future__ import annotations

import io
import zipfile
from collections.abc import AsyncIterator

from app.application.ports.file_processor import ExtractedFile
from app.application.ports.file_processor import FileProcessor as FileProcessorInterface


class ZipProcessor(FileProcessorInterface):
    async def extract_stream(
        self, zip_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[ExtractedFile]:
        buffer = io.BytesIO()

        async for chunk in zip_stream:
            buffer.write(chunk)

        buffer.seek(0)

        with zipfile.ZipFile(buffer, mode="r") as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                content = archive.read(info.filename)
                yield ExtractedFile(
                    filename=info.filename,
                    content=content,
                    size=info.file_size,
                )
