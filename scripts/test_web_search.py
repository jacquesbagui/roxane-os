#!/usr/bin/env python3
"""
Roxane OS - Test Robust Web Search Module
Script pour tester le module de recherche web robuste
"""

import asyncio
import sys
import time
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

import yaml
from loguru import logger
from core.cache import RedisCacheManager
from core.modules.robust_web_search import RobustWebSearchModule


async def test_web_search_performance():
    """Teste les performances du module de recherche web robuste"""
    try:
        # Charger la configuration
        config_path = Path(__file__).parent.parent / "config" / "system.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info("🚀 Test du module de recherche web robuste...")
        
        # Initialiser Redis
        redis_manager = RedisCacheManager(config['database']['redis'])
        redis_success = await redis_manager.initialize()
        
        if not redis_success:
            logger.warning("⚠️ Redis non disponible, utilisation sans cache")
            redis_manager = None
        
        # Initialiser le module de recherche web
        web_search_module = RobustWebSearchModule(
            config=config['web_search'],
            redis_cache=redis_manager
        )
        
        # Initialiser le module
        init_success = await web_search_module.initialize()
        if not init_success:
            logger.error("❌ Échec de l'initialisation du module")
            return False
        
        # Test de performance
        query = "intelligence artificielle 2024"
        
        # Test 1: Recherche simple
        logger.info("📝 Test 1: Recherche simple...")
        start_time = time.time()
        
        result = await web_search_module.execute('search', {
            'query': query,
            'max_results': 5
        })
        
        search_time = time.time() - start_time
        
        if result.success:
            logger.info(f"✅ Recherche effectuée en {search_time:.3f}s")
            logger.info(f"📊 Résultats: {len(result.data['results'])} trouvés")
            logger.info(f"🔍 Sources: {result.data.get('engines_used', [])}")
        else:
            logger.error(f"❌ Recherche échouée: {result.error}")
        
        # Test 2: Recherche multi-moteurs
        logger.info("📝 Test 2: Recherche multi-moteurs...")
        start_time = time.time()
        
        result = await web_search_module.execute('multi_search', {
            'query': query,
            'max_results': 3
        })
        
        multi_search_time = time.time() - start_time
        
        if result.success:
            logger.info(f"✅ Recherche multi-moteurs en {multi_search_time:.3f}s")
            logger.info(f"📊 Résultats: {len(result.data['results'])} trouvés")
            logger.info(f"🔍 Sources totales: {result.data.get('total_sources', 0)}")
            logger.info(f"📝 Synthèse: {result.data.get('synthesis', '')[:200]}...")
        else:
            logger.error(f"❌ Recherche multi-moteurs échouée: {result.error}")
        
        # Test 3: Extraction de contenu
        if result.success and result.data['results']:
            logger.info("📝 Test 3: Extraction de contenu...")
            start_time = time.time()
            
            first_result = result.data['results'][0]
            extract_result = await web_search_module.execute('extract', {
                'url': first_result['url']
            })
            
            extract_time = time.time() - start_time
            
            if extract_result.success:
                logger.info(f"✅ Contenu extrait en {extract_time:.3f}s")
                logger.info(f"📊 Longueur: {extract_result.data['content_length']} caractères")
                logger.info(f"📝 Titre: {extract_result.data['metadata']['title']}")
                logger.info(f"🔗 Liens importants: {len(extract_result.data['important_links'])}")
            else:
                logger.error(f"❌ Extraction échouée: {extract_result.error}")
        
        # Test 4: Résumé de contenu
        if 'extract_result' in locals() and extract_result.success:
            logger.info("📝 Test 4: Résumé de contenu...")
            start_time = time.time()
            
            summarize_result = await web_search_module.execute('summarize', {
                'content': extract_result.data['content'],
                'max_length': 300
            })
            
            summarize_time = time.time() - start_time
            
            if summarize_result.success:
                logger.info(f"✅ Contenu résumé en {summarize_time:.3f}s")
                logger.info(f"📊 Compression: {summarize_result.data['compression_ratio']:.2%}")
                logger.info(f"📝 Résumé: {summarize_result.data['summary'][:200]}...")
            else:
                logger.error(f"❌ Résumé échoué: {summarize_result.error}")
        
        # Test 5: Performance avec plusieurs requêtes
        logger.info("📝 Test 5: Performance avec plusieurs requêtes...")
        start_time = time.time()
        
        queries = [
            "machine learning",
            "deep learning",
            "neural networks",
            "computer vision",
            "natural language processing"
        ]
        
        tasks = []
        for query_test in queries:
            task = web_search_module.execute('search', {
                'query': query_test,
                'max_results': 3
            })
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        multi_query_time = time.time() - start_time
        
        successful_searches = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        logger.info(f"✅ {len(queries)} requêtes en {multi_query_time:.3f}s")
        logger.info(f"📊 Succès: {successful_searches}/{len(queries)}")
        logger.info(f"📊 Temps moyen par requête: {multi_query_time/len(queries):.3f}s")
        
        # Test 6: Statistiques
        logger.info("📝 Test 6: Statistiques...")
        stats = web_search_module.get_stats()
        
        logger.info("📊 Statistiques du module de recherche web:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        # Test 7: Informations du module
        logger.info("📝 Test 7: Informations du module...")
        info = web_search_module.get_info()
        
        logger.info("📊 Informations du module:")
        for key, value in info.items():
            if key != 'stats':
                logger.info(f"  {key}: {value}")
        
        # Nettoyage
        await web_search_module.cleanup()
        if redis_manager:
            await redis_manager.cleanup()
        
        logger.success("✅ Test du module de recherche web robuste terminé avec succès")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du test: {e}")
        return False


async def main():
    """Fonction principale"""
    success = await test_web_search_performance()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
