# This file makes the app directory a Python package 

from .core.config import settings, config_manager
from .routers import files, config

__all__ = ['settings', 'config_manager', 'files', 'config'] 