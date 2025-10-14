"""
Roxane OS - Core Engine
Moteur principal orchestrant tous les modules
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger

from core.nlp.model_manager import ModelManager
from core.nlp.llm_intent_classifier import LLMIntentClassifier
from core.nlp.context_manager import ContextManager
from core.database import DatabaseManager
from core.cache import RedisCacheManager
from core.audio.manager import AudioManager
from core.modules.simple_web_search import SimpleWebSearchModule
from core.modules.system_control import SystemControlModule
from core.modules.file_manager import FileManagerModule
from core.memory import MemoryManager


@dataclass
class RoxaneResponse:
    """Réponse de Roxane"""
    text: str
    actions: List[Dict]
    confidence: float
    context: Dict


class RoxaneEngine:
    """
    Moteur principal de Roxane OS
    Orchestre tous les modules et gère le flux conversationnel
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialise le moteur Roxane
        
        Args:
            config: Configuration optionnelle
        """
        logger.info("🚀 Initializing Roxane Engine...")
        
        self.config = config or self._load_default_config()
        
        # Initialiser les composants de base
        self.model_manager = ModelManager(self.config)
        self.intent_classifier = LLMIntentClassifier(self.model_manager)
        self.audio_manager = AudioManager(self.config)
        
        # Initialiser la base de données
        self.db_manager = DatabaseManager(self.config.get('database', {}).get('postgres', {}))
        
        # Initialiser le cache Redis
        self.redis_manager = RedisCacheManager(self.config.get('cache', {}).get('redis', {}))
        
        # Initialiser le gestionnaire de contexte
        self.context_manager = ContextManager(
            db_manager=self.db_manager,
            redis_client=self.redis_manager.client,
            config=self.config.get('context', {})
        )
        
        # Modules fonctionnels
        self.modules = {
            'web_search': SimpleWebSearchModule(
                config=self.config.get('web_search', {}),
                redis_cache=self.redis_manager
            ),
            'system_control': SystemControlModule(),
            'file_manager': FileManagerModule(),
        }
        
        # Mémoire
        self.memory = MemoryManager(
            db_manager=self.db_manager,
            config=self.config.get('memory', {})
        )
        
        logger.success("✅ Roxane Engine initialized")
    
    def _load_default_config(self) -> Dict:
        """Charge la configuration par défaut"""
        return {
            'model': {
                'name': 'TinyLlama/TinyLlama-1.1B-Chat-v1.0',
                'temperature': 0.7,
                'max_tokens': 2048,
            },
            'audio': {
                'stt_model': 'whisper-large-v3',
                'tts_model': 'xtts-v2',
                'language': 'fr',
            },
            'permissions': {
                'level': 2,
                'require_confirmation': True,
            }
        }
    
    async def process_message(self, 
                             message: str, 
                             user_id: str = "default",
                             context: Optional[Dict] = None) -> RoxaneResponse:
        """
        Traite un message utilisateur
        
        Args:
            message: Message de l'utilisateur
            user_id: Identifiant utilisateur
            context: Contexte additionnel
            
        Returns:
            RoxaneResponse avec la réponse et les actions
        """
        logger.info(f"📨 Processing message: {message[:50]}...")
        
        try:
            # 1. Charger le contexte conversationnel
            conversation_context = await self.context_manager.get_context(user_id)
            
            # 2. Classifier l'intention
            intent = await self.intent_classifier.classify(message, conversation_context)
            logger.debug(f"Intent detected: {intent.name} (confidence: {intent.confidence})")
            
            # 3. Router vers le module approprié
            actions = []
            
            if intent.name == "web_search":
                search_results = await self.modules['web_search'].search(
                    message, 
                    intent.entities
                )
                actions.append({
                    'type': 'web_search',
                    'query': intent.entities.get('query', message),
                    'results': search_results
                })
            
            elif intent.name == "system_command":
                command_result = await self.modules['system_control'].execute(
                    intent.entities.get('command'),
                    require_confirmation=self.config['permissions']['require_confirmation']
                )
                actions.append({
                    'type': 'system_command',
                    'command': intent.entities.get('command'),
                    'result': command_result
                })
            
            elif intent.name == "file_operation":
                file_result = await self.modules['file_manager'].handle(
                    intent.entities.get('operation'),
                    intent.entities.get('path')
                )
                actions.append({
                    'type': 'file_operation',
                    'operation': intent.entities.get('operation'),
                    'result': file_result
                })
            
            # 4. Générer la réponse avec le LLM
            response_text = await self._generate_response(
                message=message,
                intent=intent,
                actions=actions,
                context=conversation_context
            )
            
            # 5. Sauvegarder dans la mémoire
            await self.memory.save_turn(
                user_id=user_id,
                user_message=message,
                assistant_response=response_text,
                actions=actions,
                context=conversation_context
            )
            
            # 6. Mettre à jour le contexte
            await self.context_manager.update_context(
                user_id=user_id,
                message=message,
                response=response_text
            )
            
            return RoxaneResponse(
                text=response_text,
                actions=actions,
                confidence=intent.confidence,
                context=conversation_context
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            return RoxaneResponse(
                text=f"Désolée, j'ai rencontré une erreur : {str(e)}",
                actions=[],
                confidence=0.0,
                context={}
            )
    
    async def _generate_response(self,
                                message: str,
                                intent: any,
                                actions: List[Dict],
                                context: Dict) -> str:
        """
        Génère une réponse naturelle avec le LLM
        
        Args:
            message: Message original
            intent: Intention détectée
            actions: Actions exécutées
            context: Contexte conversationnel
            
        Returns:
            Réponse en langage naturel
        """
        # Construire le prompt
        prompt = self._build_prompt(message, intent, actions, context)
        
        # Générer avec le LLM
        response = await self.model_manager.generate(
            prompt=prompt,
            temperature=self.config['model']['temperature'],
            max_tokens=self.config['model']['max_tokens']
        )
        
        return response.strip()
    
    def _build_prompt(self,
                     message: str,
                     intent: any,
                     actions: List[Dict],
                     context: Dict) -> str:
        """Construit le prompt pour le LLM"""
        
        system_prompt = """Tu es Roxane, un assistant IA personnel intelligent et serviable.
Tu réponds en français de manière naturelle et concise.
Tu as accès au système, à internet, et aux fichiers de l'utilisateur.
Utilise les résultats des actions pour formuler ta réponse."""
        
        # Ajouter le contexte conversationnel
        context_str = ""
        if context.get('history'):
            recent = context['history'][-3:]  # 3 derniers échanges
            context_str = "\n".join([
                f"User: {h['user']}\nRoxane: {h['assistant']}"
                for h in recent
            ])
        
        # Ajouter les résultats des actions
        actions_str = ""
        if actions:
            actions_str = "\nActions exécutées:\n"
            for action in actions:
                actions_str += f"- {action['type']}: {action.get('result', 'OK')}\n"
        
        prompt = f"""{system_prompt}

Contexte de conversation:
{context_str}

{actions_str}

User: {message}
Roxane:"""
        
        return prompt
    
    async def process_voice(self, audio_data: bytes) -> RoxaneResponse:
        """
        Traite un input vocal
        
        Args:
            audio_data: Données audio brutes
            
        Returns:
            RoxaneResponse avec texte et audio
        """
        logger.info("🎤 Processing voice input...")
        
        # 1. Speech-to-Text
        text = await self.audio_manager.transcribe(audio_data)
        logger.debug(f"Transcribed: {text}")
        
        # 2. Traiter le message
        response = await self.process_message(text)
        
        # 3. Text-to-Speech
        audio_response = await self.audio_manager.synthesize(response.text)
        response.audio = audio_response
        
        return response
    
    async def shutdown(self):
        """Arrêt propre du moteur"""
        logger.info("🛑 Shutting down Roxane Engine...")
        
        await self.model_manager.shutdown()
        await self.audio_manager.shutdown()
        await self.memory.close()
        
        logger.success("✅ Roxane Engine shut down")


# Singleton global pour l'application
_engine_instance = None

def get_engine() -> RoxaneEngine:
    """Obtient l'instance globale du moteur"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RoxaneEngine()
    return _engine_instance