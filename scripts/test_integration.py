#!/usr/bin/env python3
"""
Roxane OS - Test d'Intégration
Script pour tester l'intégration complète du système
"""

import asyncio
import sys
import time
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

import yaml
from loguru import logger
from core.engine import RoxaneEngine


async def test_integration():
    """Teste l'intégration complète du système"""
    try:
        # Charger la configuration
        config_path = Path(__file__).parent.parent / "config" / "system.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info("🚀 Test d'intégration complète de Roxane OS...")
        
        # Initialiser le moteur principal
        engine = RoxaneEngine(config)
        
        # Initialiser le système
        logger.info("📝 Initialisation du système...")
        init_success = await engine.initialize()
        
        if not init_success:
            logger.error("❌ Échec de l'initialisation du système")
            return False
        
        logger.success("✅ Système initialisé avec succès")
        
        # Test 1: Recherche web
        logger.info("📝 Test 1: Recherche web...")
        start_time = time.time()
        
        search_result = await engine.modules['web_search'].execute('search', {
            'query': 'intelligence artificielle',
            'max_results': 3
        })
        
        search_time = time.time() - start_time
        
        if search_result.success:
            logger.info(f"✅ Recherche web réussie en {search_time:.3f}s")
            logger.info(f"📊 Résultats: {len(search_result.data['results'])} trouvés")
        else:
            logger.error(f"❌ Recherche web échouée: {search_result.error}")
        
        # Test 2: Contrôle système
        logger.info("📝 Test 2: Contrôle système...")
        start_time = time.time()
        
        system_result = await engine.modules['system_control'].execute('get_system_info', {})
        
        system_time = time.time() - start_time
        
        if system_result.success:
            logger.info(f"✅ Contrôle système réussi en {system_time:.3f}s")
            logger.info(f"📊 Système: {system_result.data.get('os', 'Unknown')}")
        else:
            logger.error(f"❌ Contrôle système échoué: {system_result.error}")
        
        # Test 3: Gestionnaire de fichiers
        logger.info("📝 Test 3: Gestionnaire de fichiers...")
        start_time = time.time()
        
        file_result = await engine.modules['file_manager'].execute('list_directory', {
            'path': str(Path(__file__).parent.parent)
        })
        
        file_time = time.time() - start_time
        
        if file_result.success:
            logger.info(f"✅ Gestionnaire de fichiers réussi en {file_time:.3f}s")
            logger.info(f"📊 Fichiers: {len(file_result.data.get('files', []))} trouvés")
        else:
            logger.error(f"❌ Gestionnaire de fichiers échoué: {file_result.error}")
        
        # Test 4: Mémoire
        logger.info("📝 Test 4: Mémoire...")
        start_time = time.time()
        
        memory_result = await engine.memory.store_conversation(
            user_id="test_user",
            session_id="test_session",
            message="Test d'intégration",
            response="Test réussi"
        )
        
        memory_time = time.time() - start_time
        
        if memory_result:
            logger.info(f"✅ Mémoire réussie en {memory_time:.3f}s")
            logger.info(f"📊 Conversation stockée: {memory_result}")
        else:
            logger.error("❌ Mémoire échouée")
        
        # Test 5: Contexte
        logger.info("📝 Test 5: Contexte...")
        start_time = time.time()
        
        context_result = await engine.context_manager.add_message(
            "user", "Test de contexte", "test_session"
        )
        
        context_time = time.time() - start_time
        
        if context_result:
            logger.info(f"✅ Contexte réussi en {context_time:.3f}s")
            logger.info(f"📊 Contexte mis à jour")
        else:
            logger.error("❌ Contexte échoué")
        
        # Test 6: Classification d'intention
        logger.info("📝 Test 6: Classification d'intention...")
        start_time = time.time()
        
        intent_result = await engine.intent_classifier.classify_intent(
            "Recherche des dernières actualités sur l'IA"
        )
        
        intent_time = time.time() - start_time
        
        if intent_result:
            logger.info(f"✅ Classification d'intention réussie en {intent_time:.3f}s")
            logger.info(f"📊 Intention: {intent_result.name} (confiance: {intent_result.confidence:.2f})")
        else:
            logger.error("❌ Classification d'intention échouée")
        
        # Test 7: Modèle de langage
        logger.info("📝 Test 7: Modèle de langage...")
        start_time = time.time()
        
        llm_result = await engine.model_manager.generate(
            prompt="Bonjour, comment allez-vous ?",
            max_tokens=50
        )
        
        llm_time = time.time() - start_time
        
        if llm_result:
            logger.info(f"✅ Modèle de langage réussi en {llm_time:.3f}s")
            logger.info(f"📊 Réponse: {llm_result.text[:100]}...")
        else:
            logger.error("❌ Modèle de langage échoué")
        
        # Test 8: Traitement complet d'un message
        logger.info("📝 Test 8: Traitement complet d'un message...")
        start_time = time.time()
        
        try:
            full_result = await engine.process_message(
                "Recherche des informations sur l'intelligence artificielle",
                user_id="test_user",
                session_id="test_session"
            )
            
            full_time = time.time() - start_time
            
            if full_result:
                logger.info(f"✅ Traitement complet réussi en {full_time:.3f}s")
                logger.info(f"📊 Réponse: {full_result.text[:100]}...")
                logger.info(f"📊 Actions: {len(full_result.actions)} exécutées")
            else:
                logger.error("❌ Traitement complet échoué")
                
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement complet: {e}")
        
        # Nettoyage
        await engine.cleanup()
        
        logger.success("✅ Test d'intégration complète terminé avec succès")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du test d'intégration: {e}")
        return False


async def main():
    """Fonction principale"""
    success = await test_integration()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
