import logging
import sys

from core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    level = logging.DEBUG if settings.node_env == "development" else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)


logger = logging.getLogger("millennio")
