"""
Roxane OS - Modules Package
Modules fonctionnels pour les différentes capacités de Roxane
"""

from .simple_web_search import SimpleWebSearchModule
from .system_control import SystemControlModule
from .file_manager import FileManagerModule

__all__ = [
    'SimpleWebSearchModule',
    'SystemControlModule', 
    'FileManagerModule'
]
