#!/usr/bin/env python3
"""
Roxane OS - Test Open Source Providers
Script pour tester les providers de recherche open source uniquement
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
from core.modules.simple_web_search import SimpleWebSearchModule


async def test_open_source_providers():
    """Teste les providers de recherche open source"""
    try:
        # Charger la configuration
        config_path = Path(__file__).parent.parent / "config" / "system.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info("🚀 Test des providers de recherche open source...")
        
        # Initialiser Redis
        redis_manager = RedisCacheManager(config['database']['redis'])
        redis_success = await redis_manager.initialize()
        
        if not redis_success:
            logger.warning("⚠️ Redis non disponible, utilisation sans cache")
            redis_manager = None
        
        # Initialiser le module de recherche web simple
        web_search_module = SimpleWebSearchModule(
            config={
                'max_results': 3,
                'timeout': 15,
                'cache_ttl': 1800
            },
            redis_cache=redis_manager
        )
        
        # Initialiser le module
        init_success = await web_search_module.initialize()
        if not init_success:
            logger.error("❌ Échec de l'initialisation du module")
            return False
        
        # Test 1: Lister les providers disponibles
        logger.info("📝 Test 1: Providers disponibles...")
        
        providers_result = await web_search_module.execute('list_providers', {})
        
        if providers_result.success:
            logger.info("✅ Providers listés avec succès")
            providers = providers_result.data['providers']
            logger.info(f"📊 Nombre de providers: {len(providers)}")
            
            for provider in providers:
                logger.info(f"  🔍 {provider['name']}: {provider['description']}")
                logger.info(f"     Open Source: {provider['open_source']}")
                logger.info(f"     API Key Required: {provider['api_key_required']}")
                logger.info(f"     Privacy Focused: {provider['privacy_focused']}")
                logger.info(f"     Weight: {provider['weight']}")
        else:
            logger.error(f"❌ Échec de la liste des providers: {providers_result.error}")
        
        # Test 2: Recherche avec chaque provider
        query = "intelligence artificielle open source"
        
        logger.info("📝 Test 2: Recherche avec chaque provider...")
        
        for provider in web_search_module.search_providers:
            logger.info(f"🔍 Test avec {provider['name']}...")
            start_time = time.time()
            
            try:
                # Recherche avec le provider spécifique
                results = await web_search_module._search_with_provider(provider, query, 2)
                
                search_time = time.time() - start_time
                
                if results:
                    logger.info(f"✅ {provider['name']} réussi en {search_time:.3f}s")
                    logger.info(f"📊 Résultats: {len(results)} trouvés")
                    
                    for i, result in enumerate(results, 1):
                        logger.info(f"  {i}. {result.title}")
                        logger.info(f"     URL: {result.url}")
                        logger.info(f"     Score: {result.relevance_score:.2f}")
                        logger.info(f"     Source: {result.source}")
                else:
                    logger.warning(f"⚠️ {provider['name']} n'a retourné aucun résultat")
                    
            except Exception as e:
                logger.error(f"❌ {provider['name']} échoué: {e}")
        
        # Test 3: Recherche avec fallback automatique
        logger.info("📝 Test 3: Recherche avec fallback automatique...")
        start_time = time.time()
        
        search_result = await web_search_module.execute('search', {
            'query': query,
            'max_results': 3
        })
        
        search_time = time.time() - start_time
        
        if search_result.success:
            logger.info(f"✅ Recherche avec fallback réussie en {search_time:.3f}s")
            logger.info(f"📊 Résultats: {len(search_result.data['results'])} trouvés")
            logger.info(f"🔍 Providers utilisés: {search_result.data['engines_used']}")
            
            # Afficher les résultats
            for i, result in enumerate(search_result.data['results'], 1):
                logger.info(f"  {i}. {result['title']}")
                logger.info(f"     URL: {result['url']}")
                logger.info(f"     Score: {result['relevance_score']:.2f}")
                logger.info(f"     Source: {result['source']}")
                logger.info(f"     Snippet: {result['snippet'][:100]}...")
        else:
            logger.error(f"❌ Recherche avec fallback échouée: {search_result.error}")
        
        # Test 4: Performance avec plusieurs requêtes
        logger.info("📝 Test 4: Performance avec plusieurs requêtes...")
        start_time = time.time()
        
        queries = [
            "machine learning open source",
            "deep learning frameworks",
            "neural networks python"
        ]
        
        tasks = []
        for query_test in queries:
            task = web_search_module.execute('search', {
                'query': query_test,
                'max_results': 2
            })
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        multi_query_time = time.time() - start_time
        
        successful_searches = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        logger.info(f"✅ {len(queries)} requêtes en {multi_query_time:.3f}s")
        logger.info(f"📊 Succès: {successful_searches}/{len(queries)}")
        logger.info(f"📊 Temps moyen par requête: {multi_query_time/len(queries):.3f}s")
        
        # Test 5: Statistiques
        logger.info("📝 Test 5: Statistiques...")
        stats = web_search_module.get_stats()
        
        logger.info("📊 Statistiques du module de recherche web open source:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        # Test 6: Informations du module
        logger.info("📝 Test 6: Informations du module...")
        info = web_search_module.get_info()
        
        logger.info("📊 Informations du module:")
        for key, value in info.items():
            if key != 'stats':
                logger.info(f"  {key}: {value}")
        
        # Nettoyage
        await web_search_module.cleanup()
        if redis_manager:
            await redis_manager.cleanup()
        
        logger.success("✅ Test des providers de recherche open source terminé avec succès")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du test: {e}")
        return False


async def main():
    """Fonction principale"""
    success = await test_open_source_providers()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
