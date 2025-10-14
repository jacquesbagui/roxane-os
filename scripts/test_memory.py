#!/usr/bin/env python3
"""
Roxane OS - Test Memory Manager
Script pour tester le gestionnaire de mémoire unifié
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
from core.memory import MemoryManager
from core.interfaces import Message


async def test_memory_performance():
    """Teste les performances du gestionnaire de mémoire"""
    try:
        # Charger la configuration
        config_path = Path(__file__).parent.parent / "config" / "system.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info("🚀 Test du gestionnaire de mémoire unifié...")
        
        # Initialiser la base de données
        db_manager = DatabaseManager(config['database']['postgres'])
        db_success = await db_manager.initialize()
        
        if not db_success:
            logger.error("❌ Échec de l'initialisation de la base de données")
            return False
        
        # Initialiser le gestionnaire de mémoire
        memory_manager = MemoryManager(
            db_manager=db_manager,
            config=config['memory']
        )
        
        # Test de performance
        session_id = "test_session_123"
        
        # Test 1: Ajout de messages
        logger.info("📝 Test 1: Ajout de messages...")
        start_time = time.time()
        
        user_message = Message(
            content="Bonjour Roxane, comment ça va ?",
            role="user",
            timestamp=None,
            metadata={"test": True}
        )
        
        await memory_manager.add_message(
            session_id=session_id,
            message=user_message,
            intent="greeting",
            response="Bonjour ! Je vais très bien, merci de demander.",
            metadata={"confidence": 0.95}
        )
        
        add_time = time.time() - start_time
        logger.info(f"✅ Message ajouté en {add_time:.3f}s")
        
        # Test 2: Récupération de l'historique
        logger.info("📝 Test 2: Récupération de l'historique...")
        start_time = time.time()
        
        history = await memory_manager.get_conversation_history(session_id)
        get_time = time.time() - start_time
        
        logger.info(f"✅ Historique récupéré en {get_time:.3f}s")
        logger.info(f"📊 Historique: {len(history)} entrées")
        
        # Test 3: Sauvegarde d'un tour complet
        logger.info("📝 Test 3: Sauvegarde d'un tour complet...")
        start_time = time.time()
        
        await memory_manager.save_turn(
            user_id=session_id,
            user_message="Quelle est la météo aujourd'hui ?",
            assistant_response="Je ne peux pas accéder à la météo en temps réel, mais je peux vous aider à la rechercher.",
            actions=[{"type": "web_search", "query": "météo"}],
            context={"intent": "weather_query"}
        )
        
        save_time = time.time() - start_time
        logger.info(f"✅ Tour sauvegardé en {save_time:.3f}s")
        
        # Test 4: Recherche dans les conversations
        logger.info("📝 Test 4: Recherche dans les conversations...")
        start_time = time.time()
        
        results = await memory_manager.search_conversations("météo", session_id)
        search_time = time.time() - start_time
        
        logger.info(f"✅ Recherche effectuée en {search_time:.3f}s")
        logger.info(f"📊 Résultats: {len(results)} entrées trouvées")
        
        # Test 5: Performance avec plusieurs sessions
        logger.info("📝 Test 5: Performance avec plusieurs sessions...")
        start_time = time.time()
        
        tasks = []
        for i in range(10):
            session_id_test = f"test_session_{i}"
            message = Message(
                content=f"Message de test {i}",
                role="user",
                timestamp=None,
                metadata={"test": True}
            )
            task = memory_manager.add_message(session_id_test, message)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        multi_session_time = time.time() - start_time
        
        logger.info(f"✅ {len(tasks)} messages ajoutés en {multi_session_time:.3f}s")
        logger.info(f"📊 Temps moyen par message: {multi_session_time/len(tasks):.3f}s")
        
        # Test 6: Statistiques
        logger.info("📝 Test 6: Statistiques...")
        stats = memory_manager.get_stats()
        
        logger.info("📊 Statistiques du gestionnaire de mémoire:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        # Test 7: Nettoyage
        logger.info("📝 Test 7: Nettoyage...")
        start_time = time.time()
        
        await memory_manager.clear_session(session_id)
        cleanup_time = time.time() - start_time
        
        logger.info(f"✅ Session nettoyée en {cleanup_time:.3f}s")
        
        # Nettoyage final
        await memory_manager.close()
        await db_manager.cleanup()
        
        logger.success("✅ Test du gestionnaire de mémoire terminé avec succès")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du test: {e}")
        return False


async def main():
    """Fonction principale"""
    success = await test_memory_performance()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
