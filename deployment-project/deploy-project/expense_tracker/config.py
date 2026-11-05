"""Configuration comes from environment variables (12-factor style); no secrets in code."""
import os


class Config:
    ENV = os.getenv("APP_ENV", "development")          # development | staging | production
    DB_PATH = os.getenv("DB_PATH", "expenses.db")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    API_KEY = os.getenv("API_KEY", "")                  # required for write requests when set
    VERSION = os.getenv("APP_VERSION", "1.0.0")
