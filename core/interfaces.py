"""
Roxane OS - Core Interfaces
Définition des interfaces (contrats) pour respecter le principe SOLID
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# DATA CLASSES (Value Objects)
# ============================================================================

@dataclass(frozen=True)
class Message:
    """Message utilisateur ou assistant"""
    content: str
    role: str  # 'user' | 'assistant' | 'system'
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.role not in ['user', 'assistant', 'system']:
            raise ValueError(f"Invalid role: {self.role}")


@dataclass(frozen=True)
class Intent:
    """Intention détectée"""
    name: str
    confidence: float
    entities: Dict[str, Any]
    
    def __post_init__(self):
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")


@dataclass(frozen=True)
class Action:
    """Action à exécuter"""
    type: str
    parameters: Dict[str, Any]
    require_confirmation: bool = False


@dataclass
class ActionResult:
    """Résultat d'une action"""
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class ConversationContext:
    """Contexte d'une conversation"""
    user_id: str
    session_id: str
    history: List[Message]
    metadata: Dict[str, Any]


@dataclass
class ModelResponse:
    """Réponse d'un modèle"""
    text: str
    confidence: float
    tokens_used: int
    latency: float


# ============================================================================
# INTERFACES (Abstract Base Classes)
# ============================================================================

class ILanguageModel(ABC):
    """Interface pour les modèles de langage (LLM)"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs
    ) -> ModelResponse:
        """Génère une réponse à partir d'un prompt"""
        pass
    
    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Génère un embedding vectoriel pour un texte"""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Retourne les informations sur le modèle"""
        pass


class IIntentClassifier(ABC):
    """Interface pour la classification d'intentions"""
    
    @abstractmethod
    async def classify(
        self,
        message: str,
        context: Optional[ConversationContext] = None
    ) -> Intent:
        """Classifie l'intention d'un message"""
        pass


class IEntityExtractor(ABC):
    """Interface pour l'extraction d'entités"""
    
    @abstractmethod
    async def extract(
        self,
        text: str,
        intent: Intent
    ) -> Dict[str, Any]:
        """Extrait les entités d'un texte"""
        pass


class IContextManager(ABC):
    """Interface pour la gestion du contexte conversationnel"""
    
    @abstractmethod
    async def get_context(self, user_id: str) -> ConversationContext:
        """Récupère le contexte d'un utilisateur"""
        pass
    
    @abstractmethod
    async def update_context(
        self,
        user_id: str,
        message: Message,
        response: Message
    ) -> None:
        """Met à jour le contexte avec un nouvel échange"""
        pass
    
    @abstractmethod
    async def clear_context(self, user_id: str) -> None:
        """Efface le contexte d'un utilisateur"""
        pass


class IActionModule(ABC):
    """Interface pour les modules d'action"""
    
    @abstractmethod
    async def execute(
        self,
        action: Action,
        context: ConversationContext
    ) -> ActionResult:
        """Exécute une action"""
        pass
    
    @abstractmethod
    def can_handle(self, action: Action) -> bool:
        """Vérifie si le module peut gérer cette action"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Retourne le nom du module"""
        pass


class IMemoryStore(ABC):
    """Interface pour le stockage en mémoire"""
    
    @abstractmethod
    async def save_conversation(
        self,
        user_id: str,
        message: Message,
        response: Message,
        actions: List[ActionResult]
    ) -> None:
        """Sauvegarde un tour de conversation"""
        pass
    
    @abstractmethod
    async def search_similar(
        self,
        query: str,
        limit: int = 10
    ) -> List[Message]:
        """Recherche des messages similaires"""
        pass
    
    @abstractmethod
    async def get_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Message]:
        """Récupère l'historique de conversation"""
        pass


class IAudioProcessor(ABC):
    """Interface pour le traitement audio"""
    
    @abstractmethod
    async def transcribe(self, audio_data: bytes) -> str:
        """Convertit audio en texte (Speech-to-Text)"""
        pass
    
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Convertit texte en audio (Text-to-Speech)"""
        pass
    
    @abstractmethod
    async def detect_voice_activity(self, audio_data: bytes) -> bool:
        """Détecte la présence de voix (Voice Activity Detection)"""
        pass


class IResponseGenerator(ABC):
    """Interface pour la génération de réponses"""
    
    @abstractmethod
    async def generate_response(
        self,
        message: Message,
        intent: Intent,
        actions_results: List[ActionResult],
        context: ConversationContext
    ) -> ModelResponse:
        """Génère une réponse naturelle"""
        pass


class IPermissionChecker(ABC):
    """Interface pour la vérification des permissions"""
    
    @abstractmethod
    async def check_permission(
        self,
        action: Action,
        user_id: str
    ) -> bool:
        """Vérifie si l'utilisateur a la permission"""
        pass
    
    @abstractmethod
    async def require_confirmation(self, action: Action) -> bool:
        """Vérifie si l'action nécessite une confirmation"""
        pass


# ============================================================================
# EXCEPTIONS
# ============================================================================

class RoxaneException(Exception):
    """Exception de base pour Roxane"""
    pass


class ModelException(RoxaneException):
    """Exception liée aux modèles"""
    pass


class ActionException(RoxaneException):
    """Exception liée aux actions"""
    pass


class PermissionException(RoxaneException):
    """Exception liée aux permissions"""
    pass


class ContextException(RoxaneException):
    """Exception liée au contexte"""
    pass


# ============================================================================
# MODULE INTERFACE
# ============================================================================

class IModule(ABC):
    """Interface pour les modules fonctionnels"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialise le module"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Nettoie les ressources du module"""
        pass
    
    @abstractmethod
    async def execute(self, action_type: str, parameters: Dict[str, Any]) -> ActionResult:
        """Exécute une action du module"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Retourne les capacités du module"""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Retourne les informations du module"""
        pass