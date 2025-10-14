"""
Roxane OS - LLM-based Intent Classifier
Classificateur d'intentions utilisant un modèle de langage
"""

import json
import re
from typing import Dict, Optional, List, Any
from loguru import logger

from core.interfaces import IIntentClassifier, Intent, ConversationContext


class LLMIntentClassifier(IIntentClassifier):
    """
    Classificateur d'intentions basé sur un LLM
    
    Utilise un modèle de langage pour classifier les intentions de manière plus flexible
    et intelligente que les règles codées en dur
    """
    
    # Intentions supportées avec descriptions
    SUPPORTED_INTENTS = {
        'web_search': {
            'description': 'Recherche d\'informations sur internet',
            'examples': [
                'Recherche des informations sur Python',
                'Trouve des restaurants près de chez moi',
                'Qu\'est-ce que l\'intelligence artificielle ?'
            ]
        },
        'system_command': {
            'description': 'Contrôle du système d\'exploitation',
            'examples': [
                'Ouvre le terminal',
                'Ferme toutes les applications',
                'Redémarre l\'ordinateur'
            ]
        },
        'file_operation': {
            'description': 'Gestion des fichiers et dossiers',
            'examples': [
                'Crée un dossier appelé projet',
                'Supprime le fichier test.txt',
                'Liste tous les fichiers du bureau'
            ]
        },
        'question': {
            'description': 'Question générale nécessitant une réponse',
            'examples': [
                'Comment fonctionne Python ?',
                'Pourquoi le ciel est bleu ?',
                'Quelle est la capitale de la France ?'
            ]
        },
        'greeting': {
            'description': 'Salutation ou accueil',
            'examples': [
                'Bonjour Roxane',
                'Salut !',
                'Hello'
            ]
        },
        'chitchat': {
            'description': 'Conversation informelle',
            'examples': [
                'Merci beaucoup',
                'C\'est super !',
                'D\'accord'
            ]
        },
        'audio_control': {
            'description': 'Contrôle audio (enregistrement, lecture)',
            'examples': [
                'Enregistre ma voix',
                'Lis ce texte à voix haute',
                'Arrête la lecture'
            ]
        },
        'unknown': {
            'description': 'Intention non reconnue',
            'examples': []
        }
    }
    
    def __init__(self, language_model):
        """
        Initialise le classificateur LLM
        
        Args:
            language_model: Modèle de langage pour la classification
        """
        self.language_model = language_model
        logger.info("LLM Intent classifier initialized")
    
    async def classify(
        self, 
        message: str, 
        context: Optional[ConversationContext] = None
    ) -> Intent:
        """
        Classifie l'intention d'un message
        
        Args:
            message: Message à classifier
            context: Contexte conversationnel
            
        Returns:
            Intent avec l'intention détectée
        """
        try:
            # Construire le prompt de classification
            prompt = self._build_classification_prompt(message, context)
            
            # Générer la classification avec le LLM
            response = await self.language_model.generate(
                prompt=prompt,
                max_tokens=200,
                temperature=0.1,  # Faible température pour plus de cohérence
                stop_tokens=['User:', 'Roxane:', '\n\n']
            )
            
            # Parser la réponse
            intent_result = self._parse_classification_response(response.text)
            
            return Intent(
                name=intent_result['intent'],
                confidence=intent_result['confidence'],
                entities=intent_result['entities']
            )
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            # Fallback vers une classification basique
            return self._fallback_classification(message)
    
    def _build_classification_prompt(
        self, 
        message: str, 
        context: Optional[ConversationContext] = None
    ) -> str:
        """Construit le prompt pour la classification"""
        
        # Description des intentions
        intents_desc = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.SUPPORTED_INTENTS.items()
            if name != 'unknown'
        ])
        
        # Contexte conversationnel
        context_str = ""
        if context and context.history:
            recent_messages = context.history[-3:]  # 3 derniers messages
            context_str = "\nContexte récent:\n"
            for msg in recent_messages:
                role = "User" if msg.role == "user" else "Roxane"
                context_str += f"{role}: {msg.content}\n"
        
        prompt = f"""Tu es un classificateur d'intentions expert. Analyse le message utilisateur et détermine son intention.

Intentions possibles:
{intents_desc}

{context_str}

Message à classifier: "{message}"

Réponds UNIQUEMENT avec un JSON valide dans ce format:
{{
    "intent": "nom_de_l_intention",
    "confidence": 0.95,
    "entities": {{
        "query": "terme de recherche si applicable",
        "command": "commande système si applicable",
        "path": "chemin fichier si applicable",
        "operation": "opération fichier si applicable"
    }},
    "reasoning": "explication courte de la classification"
}}

Réponse:"""
        
        return prompt
    
    def _parse_classification_response(self, response: str) -> Dict[str, Any]:
        """Parse la réponse de classification du LLM"""
        try:
            # Extraire le JSON de la réponse
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            json_str = json_match.group(0)
            result = json.loads(json_str)
            
            # Valider et normaliser
            intent_name = result.get('intent', 'unknown')
            if intent_name not in self.SUPPORTED_INTENTS:
                intent_name = 'unknown'
            
            confidence = float(result.get('confidence', 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp entre 0 et 1
            
            entities = result.get('entities', {})
            
            return {
                'intent': intent_name,
                'confidence': confidence,
                'entities': entities,
                'reasoning': result.get('reasoning', '')
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse classification response: {e}")
            return {
                'intent': 'unknown',
                'confidence': 0.1,
                'entities': {},
                'reasoning': f'Parse error: {e}'
            }
    
    def _fallback_classification(self, message: str) -> Intent:
        """Classification de fallback basée sur des mots-clés"""
        message_lower = message.lower()
        
        # Patterns simples pour le fallback
        if any(word in message_lower for word in ['bonjour', 'salut', 'hello', 'hey']):
            return Intent('greeting', 0.7, {})
        
        if any(word in message_lower for word in ['recherche', 'cherche', 'trouve', 'google']):
            return Intent('web_search', 0.6, {'query': message})
        
        if any(word in message_lower for word in ['ouvre', 'ferme', 'lance', 'démarre']):
            return Intent('system_command', 0.6, {'command': message})
        
        if any(word in message_lower for word in ['fichier', 'dossier', 'crée', 'supprime']):
            return Intent('file_operation', 0.6, {'operation': 'unknown'})
        
        if message_lower.endswith('?'):
            return Intent('question', 0.5, {})
        
        return Intent('unknown', 0.3, {})
    
    def get_supported_intents(self) -> List[str]:
        """Retourne la liste des intentions supportées"""
        return list(self.SUPPORTED_INTENTS.keys())
    
    def get_intent_info(self, intent_name: str) -> Optional[Dict[str, Any]]:
        """Retourne les informations d'une intention"""
        return self.SUPPORTED_INTENTS.get(intent_name)
    
    async def add_intent_example(
        self, 
        intent_name: str, 
        example: str, 
        description: Optional[str] = None
    ) -> bool:
        """
        Ajoute un exemple pour une intention (pour améliorer la classification)
        
        Args:
            intent_name: Nom de l'intention
            example: Exemple de message
            description: Description optionnelle
            
        Returns:
            True si ajouté avec succès
        """
        try:
            if intent_name not in self.SUPPORTED_INTENTS:
                # Créer une nouvelle intention
                self.SUPPORTED_INTENTS[intent_name] = {
                    'description': description or f'Intention {intent_name}',
                    'examples': []
                }
            
            if example not in self.SUPPORTED_INTENTS[intent_name]['examples']:
                self.SUPPORTED_INTENTS[intent_name]['examples'].append(example)
            
            logger.info(f"Added example for intent '{intent_name}': {example}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add intent example: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du classificateur"""
        total_examples = sum(
            len(info['examples']) 
            for info in self.SUPPORTED_INTENTS.values()
        )
        
        return {
            'supported_intents': len(self.SUPPORTED_INTENTS),
            'total_examples': total_examples,
            'intent_details': {
                name: {
                    'description': info['description'],
                    'example_count': len(info['examples'])
                }
                for name, info in self.SUPPORTED_INTENTS.items()
            }
        }
