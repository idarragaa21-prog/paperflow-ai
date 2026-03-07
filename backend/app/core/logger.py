from __future__ import annotations

import sys

from loguru import logger

from app.config import settings

# Remove default handler
logger.remove()

# Console
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.ENV == "development" else "INFO",
)

# File (rotación diaria)
logger.add(
    "logs/paperflow_ai_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
)
