"""Dyscount API - REST API for the Dyscount task queue system."""

__version__ = "0.1.0"

from .main import create_app

__all__ = ["__version__", "create_app"]
