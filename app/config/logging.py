import logging
import sys
from app.config.settings import settings


def setup_logging():
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.logs_dir / "nyra.log", encoding="utf-8"),
    ]

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )

    # Silence verbose third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


logger = logging.getLogger("nyra")
