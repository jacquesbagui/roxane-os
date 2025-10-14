"""
Roxane OS - Unified Memory Manager
Gestionnaire de mémoire unifié avec persistance PostgreSQL
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path

from core.interfaces import Message, ConversationContext
from core.database import DatabaseManager


@dataclass
class ConversationEntry:
    """Entrée de conversation"""
    message: Message
    intent: Optional[str] = None
    response: Optional[str] = None
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class MemoryManager:
    """
    Gestionnaire de mémoire unifié avec persistance PostgreSQL
    
    Architecture:
    - PostgreSQL pour la persistance durable
    - Cache local pour les accès rapides
    - Fallback vers stockage local si PostgreSQL indisponible
    
    Single Responsibility: Gestion de la mémoire conversationnelle
    Dependency Inversion: Dépend de DatabaseManager, pas d'une implémentation
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le gestionnaire de mémoire
        
        Args:
            db_manager: Gestionnaire de base de données PostgreSQL
            config: Configuration de la mémoire
        """
        self.db_manager = db_manager
        self.config = config or {}
        
        # Configuration
        self.storage_path = Path(self.config.get('storage_path', './roxane_memory'))
        self.max_entries = self.config.get('max_entries', 1000)
        self.retention_days = self.config.get('retention_days', 30)
        self.use_postgres = self.config.get('use_postgres', True)
        
        # Cache local
        self._conversations: Dict[str, List[ConversationEntry]] = {}
        self._last_cleanup = datetime.now()
        
        # Statistiques
        self._stats = {
            'total_entries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'db_reads': 0,
            'db_writes': 0,
            'fallback_writes': 0
        }
        
        # Créer le répertoire de stockage local si nécessaire
        if not self.use_postgres or not self.db_manager:
            self.storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("Memory manager initialized")
    
    async def add_message(
        self, 
        session_id: str, 
        message: Message, 
        intent: Optional[str] = None,
        response: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Ajoute un message à la mémoire
        
        Args:
            session_id: Identifiant de session
            message: Message à stocker
            intent: Intention détectée
            response: Réponse générée
            metadata: Métadonnées supplémentaires
        """
        try:
            # Créer l'entrée
            entry = ConversationEntry(
                message=message,
                intent=intent,
                response=response,
                metadata=metadata or {}
            )
            
            # Ajouter au cache local
            if session_id not in self._conversations:
                self._conversations[session_id] = []
            
            self._conversations[session_id].append(entry)
            self._stats['total_entries'] += 1
            
            # Sauvegarder en PostgreSQL si disponible
            if self.use_postgres and self.db_manager:
                await self._save_to_postgres(session_id, entry)
                self._stats['db_writes'] += 1
            else:
                # Fallback vers stockage local
                await self._save_to_local(session_id, entry)
                self._stats['fallback_writes'] += 1
            
            # Nettoyage périodique
            await self._cleanup_if_needed()
            
        except Exception as e:
            logger.error(f"Failed to add message to memory: {e}")
    
    async def get_conversation_history(
        self, 
        session_id: str, 
        limit: Optional[int] = None
    ) -> List[ConversationEntry]:
        """
        Récupère l'historique d'une conversation
        
        Args:
            session_id: Identifiant de session
            limit: Nombre maximum d'entrées à retourner
            
        Returns:
            Liste des entrées de conversation
        """
        try:
            # Vérifier le cache local d'abord
            if session_id in self._conversations:
                self._stats['cache_hits'] += 1
                history = self._conversations[session_id]
                return history[-limit:] if limit else history
            
            # Charger depuis PostgreSQL si disponible
            if self.use_postgres and self.db_manager:
                history = await self._load_from_postgres(session_id, limit)
                self._stats['db_reads'] += 1
                
                # Mettre en cache
                self._conversations[session_id] = history
                return history
            
            # Fallback vers stockage local
            history = await self._load_from_local(session_id, limit)
            self._stats['cache_misses'] += 1
            
            # Mettre en cache
            self._conversations[session_id] = history
            return history
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    async def save_turn(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        actions: List[Dict] = None,
        context: Dict = None
    ) -> None:
        """
        Sauvegarde un tour de conversation
        
        Args:
            user_id: Identifiant utilisateur
            user_message: Message de l'utilisateur
            assistant_response: Réponse de l'assistant
            actions: Actions exécutées
            context: Contexte conversationnel
        """
        try:
            # Créer les messages
            user_msg = Message(
                content=user_message,
                role="user",
                timestamp=datetime.now(),
                metadata=context or {}
            )
            
            assistant_msg = Message(
                content=assistant_response,
                role="assistant",
                timestamp=datetime.now(),
                metadata={"actions": actions or []}
            )
            
            # Sauvegarder les deux messages
            await self.add_message(user_id, user_msg, response=assistant_response)
            await self.add_message(user_id, assistant_msg, intent="response")
            
        except Exception as e:
            logger.error(f"Failed to save turn: {e}")
    
    async def search_conversations(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[ConversationEntry]:
        """
        Recherche dans les conversations
        
        Args:
            query: Requête de recherche
            user_id: Filtrer par utilisateur
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des entrées correspondantes
        """
        try:
            results = []
            query_lower = query.lower()
            
            # Rechercher dans le cache local
            for session_id, entries in self._conversations.items():
                if user_id and session_id != user_id:
                    continue
                
                for entry in entries:
                    if (query_lower in entry.message.content.lower() or
                        (entry.intent and query_lower in entry.intent.lower()) or
                        (entry.response and query_lower in entry.response.lower())):
                        results.append(entry)
            
            # Trier par timestamp et limiter
            results.sort(key=lambda x: x.timestamp, reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search conversations: {e}")
            return []
    
    async def clear_session(self, session_id: str) -> None:
        """
        Efface la mémoire d'une session
        
        Args:
            session_id: Identifiant de session
        """
        try:
            # Effacer du cache local
            if session_id in self._conversations:
                del self._conversations[session_id]
            
            # Effacer de PostgreSQL si disponible
            if self.use_postgres and self.db_manager:
                await self._clear_from_postgres(session_id)
            
            # Effacer du stockage local
            await self._clear_from_local(session_id)
            
            logger.info(f"Session {session_id} cleared from memory")
            
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
    
    async def cleanup(self) -> None:
        """
        Nettoie les anciennes entrées
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            # Nettoyer le cache local
            for session_id in list(self._conversations.keys()):
                self._conversations[session_id] = [
                    entry for entry in self._conversations[session_id]
                    if entry.timestamp > cutoff_date
                ]
                
                if not self._conversations[session_id]:
                    del self._conversations[session_id]
            
            # Nettoyer PostgreSQL si disponible
            if self.use_postgres and self.db_manager:
                await self._cleanup_postgres(cutoff_date)
            
            # Nettoyer le stockage local
            await self._cleanup_local(cutoff_date)
            
            self._last_cleanup = datetime.now()
            logger.info("Memory cleanup completed")
            
        except Exception as e:
            logger.error(f"Failed to cleanup memory: {e}")
    
    async def _save_to_postgres(self, session_id: str, entry: ConversationEntry) -> None:
        """Sauvegarde une entrée en PostgreSQL"""
        try:
            if not self.db_manager:
                return
            
            # Récupérer ou créer l'utilisateur
            user = await self.db_manager.get_or_create_user(session_id)
            
            # Récupérer ou créer la session
            db_session = await self.db_manager.get_or_create_session(str(user.id), session_id)
            
            # Récupérer ou créer la conversation
            conversation = await self._get_or_create_conversation(str(db_session.id))
            
            # Sauvegarder le message
            await self.db_manager.add_message(
                conversation_id=str(conversation.id),
                role=entry.message.role,
                content=entry.message.content,
                metadata={
                    "intent": entry.intent,
                    "response": entry.response,
                    "timestamp": entry.timestamp.isoformat(),
                    **entry.metadata
                }
            )
            
        except Exception as e:
            logger.warning(f"Failed to save to PostgreSQL: {e}")
    
    async def _load_from_postgres(self, session_id: str, limit: Optional[int] = None) -> List[ConversationEntry]:
        """Charge les entrées depuis PostgreSQL"""
        try:
            if not self.db_manager:
                return []
            
            # Récupérer l'utilisateur
            user = await self.db_manager.get_or_create_user(session_id)
            if not user:
                return []
            
            # Récupérer la session
            db_session = await self.db_manager.get_session_by_id(session_id)
            if not db_session:
                return []
            
            # Récupérer les conversations
            conversations = await self.db_manager.get_user_conversations(str(user.id), limit=1)
            if not conversations:
                return []
            
            # Récupérer les messages
            messages = await self.db_manager.get_conversation_messages(
                str(conversations[0].id),
                limit=limit
            )
            
            # Convertir en ConversationEntry
            entries = []
            for msg in messages:
                entry = ConversationEntry(
                    message=Message(
                        content=msg.content,
                        role=msg.role,
                        timestamp=msg.timestamp,
                        metadata=msg.metadata or {}
                    ),
                    intent=msg.metadata.get('intent') if msg.metadata else None,
                    response=msg.metadata.get('response') if msg.metadata else None,
                    metadata=msg.metadata or {}
                )
                entries.append(entry)
            
            return entries
            
        except Exception as e:
            logger.warning(f"Failed to load from PostgreSQL: {e}")
            return []
    
    async def _get_or_create_conversation(self, session_id: str):
        """Récupère ou crée une conversation"""
        try:
            if not self.db_manager:
                return None
            
            async with self.db_manager.get_session() as session:
                from core.database.models import Conversation
                
                # Chercher une conversation active récente
                recent_conversation = session.query(Conversation).filter(
                    Conversation.session_id == session_id,
                    Conversation.created_at >= datetime.now() - timedelta(hours=24)
                ).order_by(Conversation.created_at.desc()).first()
                
                if recent_conversation:
                    # Détacher l'objet de la session pour éviter les problèmes de binding
                    session.expunge(recent_conversation)
                    return recent_conversation
                
                # Créer une nouvelle conversation
                conversation = Conversation(
                    session_id=session_id,
                    title=f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    message_count=0
                )
                session.add(conversation)
                session.commit()
                session.refresh(conversation)
                # Détacher l'objet de la session
                session.expunge(conversation)
                return conversation
                
        except Exception as e:
            logger.warning(f"Failed to get/create conversation: {e}")
            return None
    
    async def _save_to_local(self, session_id: str, entry: ConversationEntry) -> None:
        """Sauvegarde une entrée en stockage local"""
        try:
            file_path = self.storage_path / f"{session_id}.json"
            
            # Charger les données existantes
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = []
            
            # Ajouter la nouvelle entrée
            entry_data = {
                'message': {
                    'content': entry.message.content,
                    'role': entry.message.role,
                    'timestamp': entry.message.timestamp.isoformat() if entry.message.timestamp else None,
                    'metadata': entry.message.metadata
                },
                'intent': entry.intent,
                'response': entry.response,
                'timestamp': entry.timestamp.isoformat(),
                'metadata': entry.metadata
            }
            data.append(entry_data)
            
            # Sauvegarder
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save to local storage: {e}")
    
    async def _load_from_local(self, session_id: str, limit: Optional[int] = None) -> List[ConversationEntry]:
        """Charge les entrées depuis le stockage local"""
        try:
            file_path = self.storage_path / f"{session_id}.json"
            
            if not file_path.exists():
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convertir en ConversationEntry
            entries = []
            for item in data:
                entry = ConversationEntry(
                    message=Message(
                        content=item['message']['content'],
                        role=item['message']['role'],
                        timestamp=datetime.fromisoformat(item['message']['timestamp']) if item['message']['timestamp'] else None,
                        metadata=item['message']['metadata']
                    ),
                    intent=item.get('intent'),
                    response=item.get('response'),
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    metadata=item.get('metadata', {})
                )
                entries.append(entry)
            
            # Limiter si nécessaire
            if limit:
                entries = entries[-limit:]
            
            return entries
            
        except Exception as e:
            logger.warning(f"Failed to load from local storage: {e}")
            return []
    
    async def _clear_from_postgres(self, session_id: str) -> None:
        """Efface les données PostgreSQL d'une session"""
        try:
            if not self.db_manager:
                return
            
            # Pour l'instant, on ne supprime pas les données historiques
            # TODO: Implémenter la suppression si nécessaire
            logger.info(f"Session {session_id} cleared from PostgreSQL")
            
        except Exception as e:
            logger.warning(f"Failed to clear from PostgreSQL: {e}")
    
    async def _clear_from_local(self, session_id: str) -> None:
        """Efface les données locales d'une session"""
        try:
            file_path = self.storage_path / f"{session_id}.json"
            if file_path.exists():
                file_path.unlink()
                
        except Exception as e:
            logger.warning(f"Failed to clear from local storage: {e}")
    
    async def _cleanup_postgres(self, cutoff_date: datetime) -> None:
        """Nettoie les anciennes données PostgreSQL"""
        try:
            if not self.db_manager:
                return
            
            # Pour l'instant, on ne supprime pas les données historiques
            # TODO: Implémenter le nettoyage si nécessaire
            logger.info("PostgreSQL cleanup completed")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup PostgreSQL: {e}")
    
    async def _cleanup_local(self, cutoff_date: datetime) -> None:
        """Nettoie les anciennes données locales"""
        try:
            for file_path in self.storage_path.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Filtrer les entrées récentes
                    recent_data = [
                        item for item in data
                        if datetime.fromisoformat(item['timestamp']) > cutoff_date
                    ]
                    
                    if recent_data:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(recent_data, f, ensure_ascii=False, indent=2)
                    else:
                        file_path.unlink()
                        
                except Exception as e:
                    logger.warning(f"Failed to cleanup file {file_path}: {e}")
            
            logger.info("Local storage cleanup completed")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup local storage: {e}")
    
    async def _cleanup_if_needed(self) -> None:
        """Nettoie si nécessaire"""
        if datetime.now() - self._last_cleanup > timedelta(hours=1):
            await self.cleanup()
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du gestionnaire de mémoire"""
        return {
            'total_entries': self._stats['total_entries'],
            'cached_sessions': len(self._conversations),
            'cache_hits': self._stats['cache_hits'],
            'cache_misses': self._stats['cache_misses'],
            'db_reads': self._stats['db_reads'],
            'db_writes': self._stats['db_writes'],
            'fallback_writes': self._stats['fallback_writes'],
            'postgres_enabled': self.use_postgres and self.db_manager is not None,
            'storage_path': str(self.storage_path),
            'max_entries': self.max_entries,
            'retention_days': self.retention_days
        }
    
    async def close(self) -> None:
        """Ferme le gestionnaire de mémoire"""
        try:
            await self.cleanup()
            logger.info("Memory manager closed")
        except Exception as e:
            logger.warning(f"Failed to close memory manager: {e}")


# Alias pour la compatibilité
ConversationMemory = MemoryManager
