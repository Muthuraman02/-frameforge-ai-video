import logging
import re
import sys


class SecretRedactingFilter(logging.Filter):
    """Redacts API keys, bearer tokens, and database passwords from logs."""

    PATTERNS = [
        (re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), r"\1[REDACTED]"),
        (re.compile(r"(api[_-]?key\s*[=:]\s*)['\"]?[^\s'\"]+['\"]?", re.IGNORECASE), r"\1[REDACTED]"),
        (re.compile(r"(://[^:\s]+:)[^@\s]+(@)"), r"\1[REDACTED]\2"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern, replacement in self.PATTERNS:
                msg = pattern.sub(replacement, msg)
            record.msg = msg
        return True


def setup_logging(level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.addFilter(SecretRedactingFilter())
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(SecretRedactingFilter())

    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.addHandler(handler)
