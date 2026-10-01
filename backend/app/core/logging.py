import json
import logging
import sys
from datetime import UTC, datetime


def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)


class JsonLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _write(self, level: int, event: str, **fields) -> None:
        record = {"timestamp": datetime.now(UTC).isoformat(), "level": logging.getLevelName(level).lower(), "event": event, **fields}
        self.logger.log(level, json.dumps(record, ensure_ascii=False, default=str))

    def info(self, event: str, **fields) -> None:
        self._write(logging.INFO, event, **fields)

    def warning(self, event: str, **fields) -> None:
        self._write(logging.WARNING, event, **fields)

    def error(self, event: str, **fields) -> None:
        self._write(logging.ERROR, event, **fields)


def get_logger(name: str = "pakistan_legal_assistant") -> JsonLogger:
    return JsonLogger(name)
