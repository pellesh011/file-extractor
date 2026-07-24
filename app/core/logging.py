import sys

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=log_format,
        serialize=(settings.log_format == "structured"),
    )

    logger.add(
        "logs/file_extractor_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format=log_format,
        rotation="1 day",
        retention="30 days",
        serialize=False,
    )
