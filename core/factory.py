"""
Roxane OS - Factory Pattern
Factory pour créer et configurer tous les composants du core
"""

from typing import Dict, Any, List
from loguru import logger
import yaml
from pathlib import Path

from core.engine import RoxaneEngine
from core.nlp.language_model import LLaMAModel
from core.nlp.llm_intent_classifier import LLMIntentClassifier
from core.nlp.context_manager import ContextManager
from core.nlp.response_generator import PromptBasedResponseGenerator
from core.interfaces import IActionModule


class RoxaneFactory:
    """
    Factory pour créer une instance de Roxane Engine
    """
    
    @staticmethod
    def create_engine(config_path: str = None) -> RoxaneEngine:
        """
        Crée une instance complète de Roxane Engine
        
        Args:
            config_path: Chemin vers le fichier de config (optionnel)
            
        Returns:
            Instance configurée de RoxaneEngine
        """
        logger.info("Factory: Creating Roxane Engine...")
        
        # 1. Charger la configuration
        config = RoxaneFactory._load_config(config_path)
        
        # 2. Créer le modèle de langage
        language_model = RoxaneFactory._create_language_model(config)
        
        # 3. Créer le classificateur d'intentions
        intent_classifier = RoxaneFactory._create_intent_classifier(config)
        
        # 4. Créer le gestionnaire de contexte
        context_manager = RoxaneFactory._create_context_manager(config)
        
        # 5. Créer les modules d'action
        action_modules = RoxaneFactory._create_action_modules(config)
        
        # 6. Créer le memory store
        memory_store = RoxaneFactory._create_memory_store(config)
        
        # 7. Créer le générateur de réponses
        response_generator = RoxaneFactory._create_response_generator(
            language_model,
            config
        )
        
        # 8. Créer le vérificateur de permissions
        permission_checker = RoxaneFactory._create_permission_checker(config)
        
        # 9. Assembler le tout
        engine = RoxaneEngine(
            language_model=language_model,
            intent_classifier=intent_classifier,
            context_manager=context_manager,
            action_modules=action_modules,
            memory_store=memory_store,
            response_generator=response_generator,
            permission_checker=permission_checker
        )
        
        logger.success("✅ Factory: Roxane Engine created successfully")
        return engine
    
    @staticmethod
    def _load_config(config_path: str = None) -> Dict[str, Any]:
        """Charge la configuration depuis YAML"""
        if config_path is None:
            config_path = "/opt/roxane/config/system.yaml"
        
        path = Path(config_path)
        
        if not path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return RoxaneFactory._default_config()
        
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Configuration loaded from {config_path}")
        return config
    
    @staticmethod
    def _default_config() -> Dict[str, Any]:
        """Configuration par défaut"""
        return {
            'models': {
                'llm': {
                    'name': 'TinyLlama/TinyLlama-1.1B-Chat-v1.0',
                    'device': 'auto',
                    'quantization': '4bit'
                }
            },
            'memory': {
                'short_term_limit': 20
            },
            'permissions': {
                'level': 2,
                'require_confirmation': True
            }
        }
    
    @staticmethod
    def _create_language_model(config: Dict) -> LLaMAModel:
        """Crée le modèle de langage"""
        model_config = config.get('models', {}).get('llm', {})
        
        return LLaMAModel(
            model_name=model_config.get('name', 'TinyLlama/TinyLlama-1.1B-Chat-v1.0'),
            device=model_config.get('device', 'auto'),
            quantization=model_config.get('quantization', '4bit')
        )
    
    @staticmethod
    def _create_intent_classifier(config: Dict):
        """Crée le classificateur d'intentions"""
        # Pour l'instant, toujours rule-based
        # TODO: Ajouter option ML classifier
        return RuleBasedIntentClassifier()
    
    @staticmethod
    def _create_context_manager(config: Dict):
        """Crée le gestionnaire de contexte"""
        # Pour l'instant, retourner None car ContextManager nécessite db_manager et redis_client
        # TODO: Ajouter option persistent avec dépendances
        return None
    
    @staticmethod
    def _create_action_modules(config: Dict) -> List[IActionModule]:
        """Crée les modules d'action"""
        modules = []
        
        # TODO: Créer les vrais modules
        # Pour l'instant, liste vide (à implémenter)
        
        logger.warning("⚠️  Action modules not implemented yet")
        return modules
    
    @staticmethod
    def _create_memory_store(config: Dict):
        """Crée le memory store"""
        # TODO: Implémenter
        from core.memory.memory_store import MockMemoryStore
        return MockMemoryStore()
    
    @staticmethod
    def _create_response_generator(language_model, config: Dict):
        """Crée le générateur de réponses"""
        return PromptBasedResponseGenerator(language_model)
    
    @staticmethod
    def _create_permission_checker(config: Dict):
        """Crée le vérificateur de permissions"""
        # TODO: Implémenter
        from core.security.permission_checker import DefaultPermissionChecker
        return DefaultPermissionChecker(config)


# Fonction helper pour usage simple
def create_roxane_engine(config_path: str = None) -> RoxaneEngine:
    """
    Helper function pour créer rapidement une instance de Roxane
    
    Usage:
        from core.factory import create_roxane_engine
        engine = create_roxane_engine()
    """
    return RoxaneFactory.create_engine(config_path)