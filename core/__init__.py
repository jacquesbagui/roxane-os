"""
Roxane OS - Core Package
API publique du core engine
"""

# Public API
from core.factory import create_roxane_engine, RoxaneFactory
from core.engine import RoxaneEngine
from core.interfaces import (
    # Data classes
    Message,
    Intent,
    Action,
    ActionResult,
    ConversationContext,
    ModelResponse,
    
    # Interfaces
    ILanguageModel,
    IIntentClassifier,
    IContextManager,
    IActionModule,
    IMemoryStore,
    IResponseGenerator,
    IPermissionChecker,
    
    # Exceptions
    RoxaneException,
    ModelException,
    ActionException,
    PermissionException,
    ContextException,
)

# Version
__version__ = "1.0.0"

# Exports
__all__ = [
    # Factory (usage principal)
    "create_roxane_engine",
    "RoxaneFactory",
    
    # Core
    "RoxaneEngine",
    
    # Data classes
    "Message",
    "Intent",
    "Action",
    "ActionResult",
    "ConversationContext",
    "ModelResponse",
    
    # Interfaces (pour extensibilité)
    "ILanguageModel",
    "IIntentClassifier",
    "IContextManager",
    "IActionModule",
    "IMemoryStore",
    "IResponseGenerator",
    "IPermissionChecker",
    
    # Exceptions
    "RoxaneException",
    "ModelException",
    "ActionException",
    "PermissionException",
    "ContextException",
]