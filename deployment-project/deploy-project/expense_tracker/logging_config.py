"""Structured one-line logs that are easy to grep and to ship to a log service."""
import logging
import sys


def setup(level: str = "INFO") -> logging.Logger:
    root = logging.getLogger()
    if not root.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter(
            "%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s"))
        root.addHandler(h)
    root.setLevel(level)
    return logging.getLogger("expense_tracker")
