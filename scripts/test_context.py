#!/usr/bin/env python3
"""
Roxane OS - Test Context Manager
Script pour tester le gestionnaire de contexte optimisé
"""

import asyncio
import sys
import time
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

import yaml
from loguru import logger
from core.database import DatabaseManager
from core.cache import RedisCacheManager
from core.nlp.context_manager import ContextManager
from core.interfaces import Message


async def test_context_performance():
    """Teste les performances du gestionnaire de contexte"""
    try:
        # Charger la configuration
        config_path = Path(__file__).parent.parent / "config" / "system.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info("🚀 Test du gestionnaire de contexte...")
        
        # Initialiser la base de données
        db_manager = DatabaseManager(config['database']['postgres'])
        db_success = await db_manager.initialize()
        
        if not db_success:
            logger.error("❌ Échec de l'initialisation de la base de données")
            return False
        
        # Initialiser Redis
        redis_manager = RedisCacheManager(config['database']['redis'])
        redis_success = await redis_manager.initialize()
        
        if not redis_success:
            logger.warning("⚠️ Redis non disponible, utilisation sans cache")
            redis_manager = None
        
        # Initialiser le gestionnaire de contexte
        context_manager = ContextManager(
            db_manager=db_manager,
            redis_client=redis_manager.client if redis_manager else None,
            config=config['context']
        )
        
        # Test de performance
        user_id = "test_user_123"
        
        # Test 1: Création de contexte
        logger.info("📝 Test 1: Création de contexte...")
        start_time = time.time()
        
        context = await context_manager.get_context(user_id)
        creation_time = time.time() - start_time
        
        logger.info(f"✅ Contexte créé en {creation_time:.3f}s")
        logger.info(f"📊 Contexte: {len(context.history)} messages, session: {context.session_id}")
        
        # Test 2: Mise à jour de contexte
        logger.info("📝 Test 2: Mise à jour de contexte...")
        start_time = time.time()
        
        user_message = Message(
            content="Bonjour Roxane, comment ça va ?",
            role="user",
            timestamp=None,
            metadata={"test": True}
        )
        
        assistant_response = Message(
            content="Bonjour ! Je vais très bien, merci de demander. Comment puis-je vous aider ?",
            role="assistant",
            timestamp=None,
            metadata={"confidence": 0.95}
        )
        
        await context_manager.update_context(user_id, user_message, assistant_response)
        update_time = time.time() - start_time
        
        logger.info(f"✅ Contexte mis à jour en {update_time:.3f}s")
        
        # Test 3: Récupération de contexte (cache)
        logger.info("📝 Test 3: Récupération de contexte (cache)...")
        start_time = time.time()
        
        cached_context = await context_manager.get_context(user_id)
        cache_time = time.time() - start_time
        
        logger.info(f"✅ Contexte récupéré du cache en {cache_time:.3f}s")
        logger.info(f"📊 Contexte en cache: {len(cached_context.history)} messages")
        
        # Test 4: Performance avec plusieurs utilisateurs
        logger.info("📝 Test 4: Performance avec plusieurs utilisateurs...")
        start_time = time.time()
        
        tasks = []
        for i in range(10):
            user_id_test = f"test_user_{i}"
            task = context_manager.get_context(user_id_test)
            tasks.append(task)
        
        contexts = await asyncio.gather(*tasks)
        multi_user_time = time.time() - start_time
        
        logger.info(f"✅ {len(contexts)} contextes créés en {multi_user_time:.3f}s")
        logger.info(f"📊 Temps moyen par contexte: {multi_user_time/len(contexts):.3f}s")
        
        # Test 5: Statistiques
        logger.info("📝 Test 5: Statistiques...")
        stats = context_manager.get_stats()
        
        logger.info("📊 Statistiques du gestionnaire de contexte:")
        for key, value in stats.items():
            if key != 'stats':
                logger.info(f"  {key}: {value}")
        
        if 'stats' in stats:
            logger.info("📊 Statistiques détaillées:")
            for key, value in stats['stats'].items():
                logger.info(f"  {key}: {value}")
        
        # Test 6: Nettoyage
        logger.info("📝 Test 6: Nettoyage...")
        start_time = time.time()
        
        await context_manager.clear_context(user_id)
        cleanup_time = time.time() - start_time
        
        logger.info(f"✅ Contexte nettoyé en {cleanup_time:.3f}s")
        
        # Statistiques finales
        final_stats = context_manager.get_stats()
        logger.info("📊 Statistiques finales:")
        for key, value in final_stats.items():
            if key != 'stats':
                logger.info(f"  {key}: {value}")
        
        # Nettoyage
        await context_manager.cleanup()
        await db_manager.cleanup()
        if redis_manager:
            await redis_manager.cleanup()
        
        logger.success("✅ Test du gestionnaire de contexte terminé avec succès")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du test: {e}")
        return False


async def main():
    """Fonction principale"""
    success = await test_context_performance()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
