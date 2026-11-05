"""Entry point for the production server: gunicorn wsgi:app"""
from expense_tracker.api import app  # noqa: F401
