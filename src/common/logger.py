"""
로깅 설정

loguru를 사용한 애플리케이션 로거 설정
"""

import sys
from loguru import logger


def setup_logger(log_level: str = "INFO") -> None:
    """로거를 초기화하고 포맷을 설정

    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
    """
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(sys.stderr, format=log_format, level=log_level)
    logger.add(
        "logs/app.log",
        format=log_format,
        level=log_level,
        rotation="10 MB",
        retention="7 days",
    )
