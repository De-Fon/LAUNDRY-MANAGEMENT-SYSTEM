from loguru import logger
import sys


def configure_logger() -> None:
    logger.remove()  # Remove default handler

    # Console output — clean and readable
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan> | "
               "<white>{message}</white>",
        colorize=True,
    )

    # File output — daily rotation, 30 day retention
    logger.add(
        "logs/laundry_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
        encoding="utf-8",
    )

    # Separate error file for fast debugging
    logger.add(
        "logs/errors_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}\n{exception}",
        encoding="utf-8",
    )


__all__ = ["logger", "configure_logger"]
