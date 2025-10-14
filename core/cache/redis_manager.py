"""
Roxane OS - Redis Cache Manager
Gestionnaire de cache Redis pour les performances
"""

import asyncio
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from loguru import logger
import redis.asyncio as redis
import json


class RedisCacheManager:
    """
    Gestionnaire de cache Redis optimisé
    
    Single Responsibility: Gère le cache Redis pour les performances
    Dependency Inversion: Dépend de redis.asyncio, pas d'une implémentation
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialise le gestionnaire de cache Redis
        
        Args:
            config: Configuration Redis
        """
        self.config = config or {}
        self.host = self.config.get('host', 'localhost')
        self.port = self.config.get('port', 6379)
        self.db = self.config.get('db', 0)
        self.password = self.config.get('password')
        self.max_connections = self.config.get('max_connections', 20)
        
        self.client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        
        # Configuration des TTL par défaut
        self.default_ttl = self.config.get('default_ttl', 3600)  # 1 heure
        self.context_ttl = self.config.get('context_ttl', 1800)  # 30 minutes
        self.session_ttl = self.config.get('session_ttl', 7200)   # 2 heures
        
        # Statistiques
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
        
        logger.info("Redis cache manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialise la connexion Redis
        
        Returns:
            True si l'initialisation réussit
        """
        try:
            # Créer le pool de connexions
            self._connection_pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Créer le client Redis
            self.client = redis.Redis(connection_pool=self._connection_pool)
            
            # Tester la connexion
            await self.client.ping()
            
            logger.success("✅ Redis connection established")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis: {e}")
            self.client = None
            return False
    
    async def is_available(self) -> bool:
        """Vérifie si Redis est disponible"""
        try:
            if not self.client:
                return False
            await self.client.ping()
            return True
        except Exception:
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Récupère une valeur du cache
        
        Args:
            key: Clé du cache
            
        Returns:
            Valeur du cache ou None
        """
        try:
            if not self.client:
                return None
            
            data = await self.client.get(key)
            if data is None:
                self._stats['misses'] += 1
                return None
            
            # Désérialiser les données JSON
            try:
                value = json.loads(data)
                self._stats['hits'] += 1
                return value
            except json.JSONDecodeError:
                # Si ce n'est pas du JSON, retourner la valeur brute
                self._stats['hits'] += 1
                return data.decode('utf-8')
                
        except Exception as e:
            logger.warning(f"Redis get error for key {key}: {e}")
            self._stats['errors'] += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Met une valeur en cache
        
        Args:
            key: Clé du cache
            value: Valeur à mettre en cache
            ttl: Time to live en secondes
            
        Returns:
            True si la mise en cache réussit
        """
        try:
            if not self.client:
                return False
            
            # Sérialiser les données
            if isinstance(value, (dict, list)):
                data = json.dumps(value)
            else:
                data = str(value)
            
            # Utiliser le TTL par défaut si non spécifié
            if ttl is None:
                ttl = self.default_ttl
            
            await self.client.setex(key, ttl, data)
            self._stats['sets'] += 1
            return True
            
        except Exception as e:
            logger.warning(f"Redis set error for key {key}: {e}")
            self._stats['errors'] += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Supprime une valeur du cache
        
        Args:
            key: Clé du cache
            
        Returns:
            True si la suppression réussit
        """
        try:
            if not self.client:
                return False
            
            result = await self.client.delete(key)
            self._stats['deletes'] += 1
            return result > 0
            
        except Exception as e:
            logger.warning(f"Redis delete error for key {key}: {e}")
            self._stats['errors'] += 1
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Vérifie si une clé existe dans le cache
        
        Args:
            key: Clé du cache
            
        Returns:
            True si la clé existe
        """
        try:
            if not self.client:
                return False
            
            return await self.client.exists(key) > 0
            
        except Exception as e:
            logger.warning(f"Redis exists error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Définit l'expiration d'une clé
        
        Args:
            key: Clé du cache
            ttl: Time to live en secondes
            
        Returns:
            True si l'expiration est définie
        """
        try:
            if not self.client:
                return False
            
            return await self.client.expire(key, ttl)
            
        except Exception as e:
            logger.warning(f"Redis expire error for key {key}: {e}")
            return False
    
    async def get_multiple(self, keys: List[str]) -> Dict[str, Any]:
        """
        Récupère plusieurs valeurs du cache
        
        Args:
            keys: Liste des clés
            
        Returns:
            Dictionnaire des valeurs trouvées
        """
        try:
            if not self.client or not keys:
                return {}
            
            values = await self.client.mget(keys)
            result = {}
            
            for i, key in enumerate(keys):
                if values[i] is not None:
                    try:
                        result[key] = json.loads(values[i])
                    except json.JSONDecodeError:
                        result[key] = values[i].decode('utf-8')
                    self._stats['hits'] += 1
                else:
                    self._stats['misses'] += 1
            
            return result
            
        except Exception as e:
            logger.warning(f"Redis mget error: {e}")
            self._stats['errors'] += 1
            return {}
    
    async def set_multiple(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Met plusieurs valeurs en cache
        
        Args:
            data: Dictionnaire des données à mettre en cache
            ttl: Time to live en secondes
            
        Returns:
            True si la mise en cache réussit
        """
        try:
            if not self.client or not data:
                return False
            
            # Sérialiser les données
            serialized_data = {}
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    serialized_data[key] = json.dumps(value)
                else:
                    serialized_data[key] = str(value)
            
            # Utiliser le TTL par défaut si non spécifié
            if ttl is None:
                ttl = self.default_ttl
            
            # Mettre en cache avec pipeline pour les performances
            pipe = self.client.pipeline()
            for key, value in serialized_data.items():
                pipe.setex(key, ttl, value)
            
            await pipe.execute()
            self._stats['sets'] += len(data)
            return True
            
        except Exception as e:
            logger.warning(f"Redis mset error: {e}")
            self._stats['errors'] += 1
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Supprime toutes les clés correspondant à un motif
        
        Args:
            pattern: Motif des clés à supprimer
            
        Returns:
            Nombre de clés supprimées
        """
        try:
            if not self.client:
                return 0
            
            keys = await self.client.keys(pattern)
            if not keys:
                return 0
            
            deleted = await self.client.delete(*keys)
            self._stats['deletes'] += deleted
            return deleted
            
        except Exception as e:
            logger.warning(f"Redis clear pattern error: {e}")
            self._stats['errors'] += 1
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du cache
        
        Returns:
            Dictionnaire des statistiques
        """
        try:
            if not self.client:
                return self._stats
            
            # Statistiques Redis
            info = await self.client.info('memory')
            redis_stats = {
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'maxmemory': info.get('maxmemory', 0),
                'maxmemory_human': info.get('maxmemory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0)
            }
            
            # Calculer le taux de réussite
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'redis_stats': redis_stats,
                'cache_stats': self._stats,
                'hit_rate': f"{hit_rate:.1f}%",
                'available': await self.is_available(),
                'connection_pool_size': self.max_connections
            }
            
        except Exception as e:
            logger.warning(f"Failed to get Redis stats: {e}")
            return self._stats
    
    async def cleanup(self) -> None:
        """Nettoie les ressources"""
        try:
            if self.client:
                await self.client.close()
            if self._connection_pool:
                await self._connection_pool.disconnect()
            logger.info("Redis cache manager cleaned up")
        except Exception as e:
            logger.warning(f"Failed to cleanup Redis manager: {e}")
    
    def __del__(self):
        """Destructeur pour nettoyer les ressources"""
        try:
            if self.client:
                asyncio.create_task(self.client.close())
        except Exception:
            pass
