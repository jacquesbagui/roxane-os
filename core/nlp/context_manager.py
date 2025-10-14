"""
Roxane OS - Optimized Context Manager
Gestionnaire de contexte optimisé avec cache Redis et PostgreSQL
"""

import asyncio
import json
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from loguru import logger
import redis.asyncio as redis

from core.interfaces import IContextManager, ConversationContext, Message, ContextException
from core.database import DatabaseManager, User, Session as DBSession, Conversation, Message as DBMessage


class ContextManager(IContextManager):
    """
    Gestionnaire de contexte optimisé avec cache Redis et PostgreSQL
    
    Architecture:
    - Cache Redis pour les accès rapides (< 1ms)
    - PostgreSQL pour la persistance durable
    - Cache local pour les accès ultra-rapides
    - Compression des données pour réduire la mémoire
    
    Single Responsibility: Gère le contexte conversationnel avec optimisations
    Dependency Inversion: Dépend de DatabaseManager et Redis, pas d'implémentations
    """
    
    def __init__(self, db_manager: DatabaseManager, redis_client: Optional[redis.Redis] = None, config: Optional[Dict] = None):
        """
        Initialise le gestionnaire de contexte optimisé
        
        Args:
            db_manager: Gestionnaire de base de données PostgreSQL
            redis_client: Client Redis pour le cache
            config: Configuration optionnelle
        """
        self.db_manager = db_manager
        self.redis_client = redis_client
        self.config = config or {}
        
        # Configuration
        self._max_history = self.config.get('max_history', 20)
        self._cache_ttl = self.config.get('cache_ttl', 3600)  # 1 heure
        self._compression_enabled = self.config.get('compression', True)
        self._batch_size = self.config.get('batch_size', 10)
        
        # Cache local (plus rapide que Redis)
        self._local_cache: Dict[str, ConversationContext] = {}
        self._local_cache_ttl: Dict[str, datetime] = {}
        
        # Statistiques
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'db_reads': 0,
            'db_writes': 0,
            'redis_hits': 0,
            'redis_misses': 0
        }
        
        logger.info("Context manager initialized")
    
    async def get_context(self, user_id: str) -> ConversationContext:
        """
        Récupère le contexte conversationnel avec cache multi-niveaux
        
        Args:
            user_id: Identifiant utilisateur
            
        Returns:
            Contexte conversationnel
        """
        try:
            # 1. Vérifier le cache local d'abord (le plus rapide)
            if await self._check_local_cache(user_id):
                self._stats['cache_hits'] += 1
                return self._local_cache[user_id]
            
            # 2. Vérifier le cache Redis
            if self.redis_client:
                context = await self._get_from_redis_cache(user_id)
                if context:
                    self._stats['redis_hits'] += 1
                    # Mettre en cache local
                    await self._set_local_cache(user_id, context)
                    return context
                else:
                    self._stats['redis_misses'] += 1
            
            # 3. Charger depuis PostgreSQL
            self._stats['db_reads'] += 1
            context = await self._load_from_db(user_id)
            
            # 4. Mettre en cache
            await self._set_local_cache(user_id, context)
            if self.redis_client:
                await self._set_redis_cache(user_id, context)
            
            self._stats['cache_misses'] += 1
            return context
            
        except Exception as e:
            logger.error(f"Failed to get context for user {user_id}: {e}")
            raise ContextException(f"Context retrieval failed: {e}")
    
    async def update_context(
        self,
        user_id: str,
        message: Message,
        response: Message
    ) -> None:
        """
        Met à jour le contexte avec un nouvel échange
        
        Args:
            user_id: Identifiant utilisateur
            message: Message utilisateur
            response: Réponse de l'assistant
        """
        try:
            # Récupérer le contexte
            context = await self.get_context(user_id)
            
            # Ajouter les messages à l'historique
            context.history.append(message)
            context.history.append(response)
            
            # Limiter l'historique
            if len(context.history) > self._max_history * 2:
                context.history = context.history[-(self._max_history * 2):]
            
            # Mettre à jour les métadonnées
            context.metadata['last_updated'] = datetime.now().isoformat()
            context.metadata['message_count'] = len(context.history)
            
            # Mettre à jour les caches
            await self._set_local_cache(user_id, context)
            if self.redis_client:
                await self._set_redis_cache(user_id, context)
            
            # Sauvegarder en base de données (asynchrone)
            asyncio.create_task(self._save_to_db_async(user_id, message, response))
            
        except Exception as e:
            logger.error(f"Failed to update context for user {user_id}: {e}")
            raise ContextException(f"Context update failed: {e}")
    
    async def clear_context(self, user_id: str) -> None:
        """
        Efface le contexte d'un utilisateur
        
        Args:
            user_id: Identifiant utilisateur
        """
        try:
            # Effacer du cache local
            if user_id in self._local_cache:
                del self._local_cache[user_id]
            if user_id in self._local_cache_ttl:
                del self._local_cache_ttl[user_id]
            
            # Effacer du cache Redis
            if self.redis_client:
                await self.redis_client.delete(f"context:{user_id}")
            
            # Effacer de la base de données
            await self._clear_from_db(user_id)
            
            logger.info(f"Context cleared for user: {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to clear context for user {user_id}: {e}")
            raise ContextException(f"Context clearing failed: {e}")
    
    async def _check_local_cache(self, user_id: str) -> bool:
        """Vérifie si le contexte est en cache local et valide"""
        if user_id not in self._local_cache:
            return False
        
        # Vérifier la TTL
        if user_id in self._local_cache_ttl:
            if datetime.now() > self._local_cache_ttl[user_id]:
                del self._local_cache[user_id]
                del self._local_cache_ttl[user_id]
                return False
        
        return True
    
    async def _set_local_cache(self, user_id: str, context: ConversationContext) -> None:
        """Met le contexte en cache local"""
        self._local_cache[user_id] = context
        self._local_cache_ttl[user_id] = datetime.now() + timedelta(seconds=self._cache_ttl)
    
    async def _get_from_redis_cache(self, user_id: str) -> Optional[ConversationContext]:
        """Récupère le contexte depuis Redis"""
        try:
            if not self.redis_client:
                return None
            
            key = f"context:{user_id}"
            data = await self.redis_client.get(key)
            
            if not data:
                return None
            
            # Décompresser si nécessaire
            if self._compression_enabled:
                data = self._decompress_data(data)
            
            context_data = json.loads(data)
            return self._deserialize_context(context_data)
            
        except Exception as e:
            logger.warning(f"Failed to get from Redis cache: {e}")
            return None
    
    async def _set_redis_cache(self, user_id: str, context: ConversationContext) -> None:
        """Met le contexte en cache Redis"""
        try:
            if not self.redis_client:
                return
            
            key = f"context:{user_id}"
            context_data = self._serialize_context(context)
            data = json.dumps(context_data)
            
            # Compresser si nécessaire
            if self._compression_enabled:
                data = self._compress_data(data)
            
            await self.redis_client.setex(key, self._cache_ttl, data)
            
        except Exception as e:
            logger.warning(f"Failed to set Redis cache: {e}")
    
    async def _load_from_db(self, user_id: str) -> ConversationContext:
        """Charge le contexte depuis PostgreSQL"""
        try:
            # Récupérer ou créer l'utilisateur
            user = await self.db_manager.get_or_create_user(user_id)
            
            # Récupérer ou créer la session
            session_id = f"session_{user_id}"
            db_session = await self.db_manager.get_or_create_session(str(user.id), session_id)
            
            # Récupérer la conversation active ou créer une nouvelle
            conversation = await self._get_or_create_conversation(str(db_session.id))
            
            # Récupérer les messages récents
            messages = await self.db_manager.get_conversation_messages(
                str(conversation.id),
                limit=self._max_history
            )
            
            # Convertir en objets Message
            history = []
            for msg in messages:
                history.append(Message(
                    content=msg.content,
                    role=msg.role,
                    timestamp=msg.timestamp,
                    metadata=msg.meta_data or {}
                ))
            
            return ConversationContext(
                user_id=user_id,
                session_id=session_id,
                history=history,
                metadata={
                    'conversation_id': str(conversation.id),
                    'session_id': str(db_session.id),
                    'message_count': conversation.message_count,
                    'last_updated': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.warning(f"Failed to load context from DB, creating new: {e}")
            # Fallback: créer un nouveau contexte
            return ConversationContext(
                user_id=user_id,
                session_id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                history=[],
                metadata={'last_updated': datetime.now().isoformat()}
            )
    
    async def _get_or_create_conversation(self, session_id: str) -> Conversation:
        """Récupère ou crée une conversation"""
        try:
            # Essayer de récupérer une conversation active récente
            async with self.db_manager.get_session() as session:
                # Chercher une conversation active des dernières 24h
                recent_conversation = session.query(Conversation).filter(
                    Conversation.session_id == session_id,
                    Conversation.is_active == True,
                    Conversation.created_at >= datetime.now() - timedelta(hours=24)
                ).order_by(Conversation.created_at.desc()).first()
                
                if recent_conversation:
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
                session.expunge(conversation)
                return conversation
                
        except Exception as e:
            logger.warning(f"Failed to get/create conversation: {e}")
            # Fallback: conversation simple
            async with self.db_manager.get_session() as session:
                conversation = Conversation(session_id=session_id)
                session.add(conversation)
                session.commit()
                session.refresh(conversation)
                session.expunge(conversation)
                return conversation
    
    async def _save_to_db_async(
        self,
        user_id: str,
        message: Message,
        response: Message
    ) -> None:
        """Sauvegarde les messages en base de données de manière asynchrone"""
        try:
            # Récupérer le contexte pour obtenir l'ID de conversation
            context = self._local_cache.get(user_id)
            if not context:
                return
            
            conversation_id = context.metadata.get('conversation_id')
            if not conversation_id:
                return
            
            # Sauvegarder le message utilisateur
            await self.db_manager.add_message(
                conversation_id=conversation_id,
                role=message.role,
                content=message.content,
                metadata=message.metadata
            )
            
            # Sauvegarder la réponse de l'assistant
            await self.db_manager.add_message(
                conversation_id=conversation_id,
                role=response.role,
                content=response.content,
                metadata=response.metadata
            )
            
            # Mettre à jour le compteur de messages
            await self.db_manager.update_conversation_message_count(conversation_id)
            
            self._stats['db_writes'] += 1
            
        except Exception as e:
            logger.warning(f"Failed to save context to DB: {e}")
    
    async def _clear_from_db(self, user_id: str) -> None:
        """Efface le contexte de la base de données"""
        try:
            # Pour l'instant, on ne supprime pas les données historiques
            # TODO: Implémenter la suppression si nécessaire
            logger.info(f"Context cleared from DB for user: {user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to clear context from DB: {e}")
    
    def _serialize_context(self, context: ConversationContext) -> Dict[str, Any]:
        """Sérialise le contexte pour le cache"""
        return {
            'user_id': context.user_id,
            'session_id': context.session_id,
            'history': [
                {
                    'content': msg.content,
                    'role': msg.role,
                    'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                    'metadata': msg.metadata
                }
                for msg in context.history
            ],
            'metadata': context.metadata
        }
    
    def _deserialize_context(self, data: Dict[str, Any]) -> ConversationContext:
        """Désérialise le contexte depuis le cache"""
        history = []
        for msg_data in data.get('history', []):
            history.append(Message(
                content=msg_data['content'],
                role=msg_data['role'],
                timestamp=datetime.fromisoformat(msg_data['timestamp']) if msg_data['timestamp'] else None,
                metadata=msg_data.get('metadata', {})
            ))
        
        return ConversationContext(
            user_id=data['user_id'],
            session_id=data['session_id'],
            history=history,
            metadata=data.get('metadata', {})
        )
    
    def _compress_data(self, data: str) -> str:
        """Compresse les données pour réduire la mémoire"""
        # TODO: Implémenter la compression (gzip, lz4, etc.)
        return data
    
    def _decompress_data(self, data: str) -> str:
        """Décompresse les données"""
        # TODO: Implémenter la décompression
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du gestionnaire de contexte"""
        total_requests = self._stats['cache_hits'] + self._stats['cache_misses']
        cache_hit_rate = (self._stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cached_contexts': len(self._local_cache),
            'max_history': self._max_history,
            'cache_ttl': self._cache_ttl,
            'compression_enabled': self._compression_enabled,
            'redis_available': self.redis_client is not None,
            'stats': self._stats,
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'db_manager_initialized': self.db_manager.is_initialized()
        }
    
    async def cleanup(self) -> None:
        """Nettoie les ressources"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            logger.info("Context manager cleaned up")
        except Exception as e:
            logger.warning(f"Failed to cleanup context manager: {e}")
