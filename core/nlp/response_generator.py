"""
Roxane OS - Response Generator Implementation
Génère des réponses naturelles en langage humain
"""

from typing import List
from loguru import logger

from core.interfaces import (
    IResponseGenerator, ILanguageModel,
    Message, Intent, ActionResult, ConversationContext, ModelResponse
)


class PromptBasedResponseGenerator(IResponseGenerator):
    """
    Générateur de réponses basé sur des prompts
    
    Single Responsibility: Génère uniquement les réponses naturelles
    Dependency Inversion: Dépend de ILanguageModel, pas d'une implémentation
    """
    
    SYSTEM_PROMPT = """Tu es Roxane, un assistant IA personnel intelligent et serviable.
Tu réponds de manière naturelle, concise et amicale.
Tu as accès au système d'exploitation, à internet, et aux fichiers de l'utilisateur.
Utilise les résultats des actions exécutées pour formuler ta réponse."""
    
    def __init__(self, language_model: ILanguageModel):
        """
        Initialise le générateur de réponses
        
        Args:
            language_model: Modèle de langage à utiliser
        """
        self._llm = language_model
        logger.info("Response generator initialized")
    
    async def generate_response(
        self,
        message: Message,
        intent: Intent,
        actions_results: List[ActionResult],
        context: ConversationContext
    ) -> ModelResponse:
        """
        Génère une réponse naturelle
        
        Args:
            message: Message de l'utilisateur
            intent: Intention détectée
            actions_results: Résultats des actions exécutées
            context: Contexte conversationnel
            
        Returns:
            ModelResponse avec la réponse générée
        """
        # Construire le prompt
        prompt = self._build_prompt(message, intent, actions_results, context)
        
        # Générer avec le LLM
        response = await self._llm.generate(
            prompt=prompt,
            max_tokens=512,  # Réponses plus courtes
            temperature=0.7
        )
        
        return response
    
    def _build_prompt(
        self,
        message: Message,
        intent: Intent,
        actions_results: List[ActionResult],
        context: ConversationContext
    ) -> str:
        """
        Construit le prompt pour le LLM
        
        Template Method Pattern: Structure fixe, détails variables
        """
        prompt_parts = [
            self.SYSTEM_PROMPT,
            "",
            self._format_context(context),
            self._format_actions(actions_results),
            self._format_current_exchange(message, intent),
            "Roxane:"
        ]
        
        return "\n".join(part for part in prompt_parts if part)
    
    def _format_context(self, context: ConversationContext) -> str:
        """Formate le contexte conversationnel"""
        if not context.history:
            return ""
        
        # Prendre seulement les 3 derniers échanges
        recent_history = context.history[-6:]  # 3 tours = 6 messages
        
        formatted = ["Contexte de conversation:"]
        for msg in recent_history:
            role = "User" if msg.role == "user" else "Roxane"
            formatted.append(f"{role}: {msg.content}")
        
        return "\n".join(formatted)
    
    def _format_actions(self, actions_results: List[ActionResult]) -> str:
        """Formate les résultats des actions"""
        if not actions_results:
            return ""
        
        formatted = ["\nActions exécutées:"]
        
        for i, result in enumerate(actions_results, 1):
            status = "✅ Succès" if result.success else "❌ Échec"
            formatted.append(f"{i}. {status}")
            
            if result.success and result.data:
                # Résumer les données (éviter les réponses trop longues)
                data_summary = self._summarize_data(result.data)
                formatted.append(f"   Résultat: {data_summary}")
            elif result.error:
                formatted.append(f"   Erreur: {result.error}")
        
        return "\n".join(formatted)
    
    def _summarize_data(self, data: any, max_length: int = 200) -> str:
        """Résume les données pour éviter des prompts trop longs"""
        data_str = str(data)
        if len(data_str) > max_length:
            return data_str[:max_length] + "..."
        return data_str
    
    def _format_current_exchange(self, message: Message, intent: Intent) -> str:
        """Formate l'échange actuel"""
        return f"\nUser: {message.content}"


class TemplateBasedResponseGenerator(IResponseGenerator):
    """
    Générateur de réponses basé sur des templates
    
    Alternative pour des réponses simples sans LLM
    Utile pour économiser de la latence sur des intentions simples
    """
    
    TEMPLATES = {
        'greeting': [
            "Bonjour ! Comment puis-je vous aider ?",
            "Salut ! Je suis là pour vous assister.",
            "Bonjour ! Que puis-je faire pour vous aujourd'hui ?"
        ],
        'thanks': [
            "Avec plaisir ! N'hésitez pas si vous avez d'autres questions.",
            "De rien ! Je suis là pour ça.",
            "Content de pouvoir aider !"
        ],
        'goodbye': [
            "Au revoir ! À bientôt !",
            "Bye ! N'hésitez pas à revenir.",
            "À plus tard !"
        ]
    }
    
    def __init__(self, language_model: ILanguageModel):
        """
        Initialise avec un LLM en fallback
        
        Args:
            language_model: LLM pour les cas complexes
        """
        self._llm = language_model
        logger.info("Template-based response generator initialized")
    
    async def generate_response(
        self,
        message: Message,
        intent: Intent,
        actions_results: List[ActionResult],
        context: ConversationContext
    ) -> ModelResponse:
        """Génère une réponse via template ou LLM"""
        import random
        import time
        
        # Si template disponible pour cette intention
        if intent.name in self.TEMPLATES and not actions_results:
            template = random.choice(self.TEMPLATES[intent.name])
            return ModelResponse(
                text=template,
                confidence=1.0,
                tokens_used=0,
                latency=0.001
            )
        
        # Sinon, utiliser le LLM
        prompt_gen = PromptBasedResponseGenerator(self._llm)
        return await prompt_gen.generate_response(
            message, intent, actions_results, context
        )