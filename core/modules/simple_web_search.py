"""
Roxane OS - Simple Web Search Module
Module de recherche web simple avec fallback pour la production
"""

import asyncio
import aiohttp
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger
from bs4 import BeautifulSoup
import json
import hashlib
from urllib.parse import urljoin, urlparse, quote_plus, unquote, parse_qs
import re

from core.interfaces import IModule, ActionResult
from core.cache import RedisCacheManager


@dataclass
class SearchResult:
    """Résultat de recherche simple"""
    title: str
    url: str
    snippet: str
    relevance_score: float
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SimpleWebSearchModule(IModule):
    """
    Module de recherche web simple avec providers open source uniquement
    
    Fonctionnalités:
    - Recherche DuckDuckGo HTML (open source, pas d'API key)
    - Recherche SearxNG (métamoteur open source)
    - Recherche Startpage (respect de la vie privée)
    - Cache Redis pour les performances
    - Extraction de contenu basique
    - Gestion d'erreurs simple
    - Rotation des User-Agents
    - Monitoring des performances
    - 100% open source, aucune API key requise
    """
    
    def __init__(self, config: Dict[str, Any] = None, redis_cache: Optional[RedisCacheManager] = None):
        """
        Initialise le module de recherche web simple
        
        Args:
            config: Configuration du module
            redis_cache: Gestionnaire de cache Redis
        """
        self.config = config or {}
        self.redis_cache = redis_cache
        
        # Configuration par défaut
        self.max_results = self.config.get('max_results', 5)
        self.timeout = self.config.get('timeout', 15)
        self.cache_ttl = self.config.get('cache_ttl', 1800)  # 30 minutes
        
        # Session HTTP
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Providers open source uniquement
        self.search_providers = [
            {
                'name': 'duckduckgo',
                'url': 'https://html.duckduckgo.com/html/',
                'weight': 1.0,
                'description': 'DuckDuckGo HTML (open source, respect de la vie privée)'
            },
            {
                'name': 'searxng',
                'url': 'http://localhost:8080/search',
                'weight': 0.9,
                'description': 'SearxNG métamoteur (open source, auto-hébergé)'
            },
            {
                'name': 'startpage',
                'url': 'https://www.startpage.com/sp/search',
                'weight': 0.8,
                'description': 'Startpage (respect de la vie privée)'
            },
            {
                'name': 'qwant',
                'url': 'https://www.qwant.com/',
                'weight': 0.7,
                'description': 'Qwant (moteur français, respect de la vie privée)'
            }
        ]
        
        # User-Agents pour rotation
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        
        # Statistiques
        self.stats = {
            'total_searches': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'average_response_time': 0.0
        }
        
        logger.info("Simple web search module initialized")
    
    async def initialize(self) -> bool:
        """Initialise la session HTTP"""
        try:
            user_agent = random.choice(self.user_agents)
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={'User-Agent': user_agent},
                connector=aiohttp.TCPConnector(
                    limit=50,
                    limit_per_host=10,
                    ttl_dns_cache=300,
                    use_dns_cache=True
                )
            )
            
            # Initialiser le cache Redis si disponible
            if self.redis_cache:
                await self.redis_cache.initialize()
            
            logger.success("✅ Simple web search module initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize simple web search module: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Nettoie les ressources"""
        try:
            if self.session:
                await self.session.close()
            
            if self.redis_cache:
                await self.redis_cache.cleanup()
            
            logger.info("Simple web search module cleaned up")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup web search module: {e}")
    
    async def execute(self, action_type: str, parameters: Dict[str, Any]) -> ActionResult:
        """
        Exécute une action de recherche web simple
        
        Args:
            action_type: Type d'action ('search', 'extract', 'summarize')
            parameters: Paramètres de l'action
            
        Returns:
            ActionResult avec les résultats
        """
        start_time = time.time()
        
        try:
            if action_type == 'search':
                result = await self._search_web_simple(parameters)
            elif action_type == 'extract':
                result = await self._extract_content_simple(parameters)
            elif action_type == 'summarize':
                result = await self._summarize_content_simple(parameters)
            elif action_type == 'list_providers':
                result = ActionResult(
                    success=True,
                    data={
                        'providers': self.get_providers_info(),
                        'total': len(self.search_providers),
                        'open_source_only': True
                    }
                )
            else:
                result = ActionResult(
                    success=False,
                    error=f"Unknown action type: {action_type}",
                    data={}
                )
            
            # Mettre à jour les statistiques
            response_time = time.time() - start_time
            self._update_stats(action_type, result.success, response_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Web search action failed: {e}")
            self.stats['failed_searches'] += 1
            return ActionResult(
                success=False,
                error=str(e),
                data={}
            )
    
    async def _search_web_simple(self, parameters: Dict[str, Any]) -> ActionResult:
        """Effectue une recherche web simple avec DuckDuckGo HTML"""
        query = parameters.get('query', '')
        max_results = parameters.get('max_results', self.max_results)
        
        if not query:
            return ActionResult(
                success=False,
                error="Query parameter is required",
                data={}
            )
        
        # Vérifier le cache
        cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}:{max_results}"
        if self.redis_cache:
            cached_result = await self.redis_cache.get(cache_key)
            if cached_result:
                self.stats['cache_hits'] += 1
                return ActionResult(
                    success=True,
                    data=cached_result
                )
        
        self.stats['cache_misses'] += 1
        
        try:
            # Essayer plusieurs providers open source
            results = []
            for provider in self.search_providers:
                try:
                    provider_results = await self._search_with_provider(provider, query, max_results)
                    if provider_results:
                        results.extend(provider_results)
                        break  # Utiliser le premier provider qui fonctionne
                except Exception as e:
                    logger.warning(f"Provider {provider['name']} failed: {e}")
                    continue
            
            if not results:
                return ActionResult(
                    success=False,
                    error="No results found from any provider",
                    data={}
                )
            
            # Préparer la réponse
            response_data = {
                'query': query,
                'results': [
                    {
                        'title': r.title,
                        'url': r.url,
                        'snippet': r.snippet,
                        'relevance_score': r.relevance_score,
                        'source': r.source,
                        'timestamp': r.timestamp.isoformat(),
                        'metadata': r.metadata
                    }
                    for r in results
                ],
                'count': len(results),
                'search_time': time.time() - time.time(),
                'engines_used': list(set(r.source for r in results))
            }
            
            # Mettre en cache
            if self.redis_cache:
                await self.redis_cache.set(cache_key, response_data, ttl=self.cache_ttl)
            
            return ActionResult(
                success=True,
                data=response_data
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Search failed: {e}",
                data={}
            )
    
    async def _search_with_provider(self, provider: Dict, query: str, max_results: int) -> List[SearchResult]:
        """Recherche avec un provider spécifique"""
        if provider['name'] == 'duckduckgo':
            return await self._search_duckduckgo_html(query, max_results)
        elif provider['name'] == 'searxng':
            return await self._search_searxng(query, max_results)
        elif provider['name'] == 'startpage':
            return await self._search_startpage(query, max_results)
        elif provider['name'] == 'qwant':
            return await self._search_qwant(query, max_results)
        else:
            return []
    
    async def _search_duckduckgo_html(self, query: str, max_results: int) -> List[SearchResult]:
        """Recherche DuckDuckGo via HTML (plus robuste)"""
        if not self.session:
            raise Exception("Session not initialized")
        
        # Encoder la requête pour l'URL
        encoded_query = quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            results = []
            
            # Chercher les résultats de recherche
            result_elements = soup.find_all('div', class_='result')
            
            for i, element in enumerate(result_elements[:max_results]):
                try:
                    # Extraire le titre et le lien
                    title_element = element.find('a', class_='result__a')
                    if not title_element:
                        continue
                    
                    title = title_element.get_text(strip=True)
                    url = title_element.get('href', '')
                    
                    # Décoder l'URL DuckDuckGo si nécessaire
                    decoded_url = self._decode_duckduckgo_url(url)
                    
                    # Extraire le snippet
                    snippet_element = element.find('a', class_='result__snippet')
                    snippet = snippet_element.get_text(strip=True) if snippet_element else ''
                    
                    # Calculer un score de pertinence basique
                    relevance_score = self._calculate_relevance_score(query, title, snippet)
                    
                    results.append(SearchResult(
                        title=title,
                        url=decoded_url,
                        snippet=snippet,
                        relevance_score=relevance_score,
                        source='duckduckgo',
                        metadata={'position': i + 1, 'original_url': url}
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to parse result {i}: {e}")
                    continue
            
            return results
    
    async def _search_searxng(self, query: str, max_results: int) -> List[SearchResult]:
        """Recherche SearxNG (métamoteur open source)"""
        if not self.session:
            raise Exception("Session not initialized")
        
        # Encoder la requête pour l'URL
        encoded_query = quote_plus(query)
        url = f"http://localhost:8080/search?q={encoded_query}&format=json&categories=general"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"SearxNG HTTP {response.status}")
            
            data = await response.json()
            results = []
            
            for result in data.get('results', [])[:max_results]:
                results.append(SearchResult(
                    title=result.get('title', ''),
                    url=result.get('url', ''),
                    snippet=result.get('content', ''),
                    relevance_score=float(result.get('score', 0.8)),
                    source='searxng',
                    metadata={
                        'engine': result.get('engine', ''),
                        'positions': result.get('positions', [])
                    }
                ))
            
            return results
    
    async def _search_startpage(self, query: str, max_results: int) -> List[SearchResult]:
        """Recherche Startpage (respect de la vie privée)"""
        if not self.session:
            raise Exception("Session not initialized")
        
        # Encoder la requête pour l'URL
        encoded_query = quote_plus(query)
        url = f"https://www.startpage.com/sp/search?query={encoded_query}"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Startpage HTTP {response.status}")
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            results = []
            
            # Chercher les résultats de recherche
            result_elements = soup.find_all('div', class_='w-gl__result')
            
            for i, element in enumerate(result_elements[:max_results]):
                try:
                    # Extraire le titre et le lien
                    title_element = element.find('a', class_='w-gl__result-title')
                    if not title_element:
                        continue
                    
                    title = title_element.get_text(strip=True)
                    url = title_element.get('href', '')
                    
                    # Extraire le snippet
                    snippet_element = element.find('p', class_='w-gl__description')
                    snippet = snippet_element.get_text(strip=True) if snippet_element else ''
                    
                    # Calculer un score de pertinence basique
                    relevance_score = self._calculate_relevance_score(query, title, snippet)
                    
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        relevance_score=relevance_score,
                        source='startpage',
                        metadata={'position': i + 1}
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to parse Startpage result {i}: {e}")
                    continue
            
            return results
    
    async def _search_qwant(self, query: str, max_results: int) -> List[SearchResult]:
        """Recherche Qwant (moteur français, respect de la vie privée)"""
        if not self.session:
            raise Exception("Session not initialized")
        
        # Encoder la requête pour l'URL
        encoded_query = quote_plus(query)
        url = f"https://www.qwant.com/?q={encoded_query}&t=web"
        
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Qwant HTTP {response.status}")
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            results = []
            
            # Chercher les résultats de recherche
            result_elements = soup.find_all('div', class_='result')
            
            for i, element in enumerate(result_elements[:max_results]):
                try:
                    # Extraire le titre et le lien
                    title_element = element.find('a', class_='result__title')
                    if not title_element:
                        continue
                    
                    title = title_element.get_text(strip=True)
                    url = title_element.get('href', '')
                    
                    # Extraire le snippet
                    snippet_element = element.find('p', class_='result__description')
                    snippet = snippet_element.get_text(strip=True) if snippet_element else ''
                    
                    # Calculer un score de pertinence basique
                    relevance_score = self._calculate_relevance_score(query, title, snippet)
                    
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        relevance_score=relevance_score,
                        source='qwant',
                        metadata={'position': i + 1}
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to parse Qwant result {i}: {e}")
                    continue
            
            return results
    
    def _calculate_relevance_score(self, query: str, title: str, snippet: str) -> float:
        """Calcule un score de pertinence basique"""
        query_words = set(query.lower().split())
        title_words = set(title.lower().split())
        snippet_words = set(snippet.lower().split())
        
        # Score basé sur les mots communs
        title_matches = len(query_words.intersection(title_words))
        snippet_matches = len(query_words.intersection(snippet_words))
        
        # Score normalisé (0.5 à 1.0)
        score = 0.5 + (title_matches * 0.3 + snippet_matches * 0.2) / len(query_words)
        return min(score, 1.0)
    
    def _decode_duckduckgo_url(self, url: str) -> str:
        """Décode les URLs de redirection DuckDuckGo"""
        if not url.startswith('//duckduckgo.com/l/'):
            return url
        
        try:
            # Parser l'URL pour extraire les paramètres
            parsed = urlparse(f"https:{url}")
            query_params = parse_qs(parsed.query)
            
            # Extraire l'URL cible depuis le paramètre 'uddg'
            if 'uddg' in query_params:
                target_url = unquote(query_params['uddg'][0])
                return target_url
            
            return url
        except Exception as e:
            logger.warning(f"Failed to decode DuckDuckGo URL {url}: {e}")
            return url
    
    async def _extract_content_simple(self, parameters: Dict[str, Any]) -> ActionResult:
        """Extraction de contenu simple"""
        url = parameters.get('url', '')
        
        if not url:
            return ActionResult(
                success=False,
                error="URL parameter is required",
                data={}
            )
        
        # Vérifier le cache
        cache_key = f"content:{hashlib.md5(url.encode()).hexdigest()}"
        if self.redis_cache:
            cached_content = await self.redis_cache.get(cache_key)
            if cached_content:
                return ActionResult(
                    success=True,
                    data=cached_content
                )
        
        try:
            if not self.session:
                raise Exception("Session not initialized")
            
            # S'assurer que l'URL est valide
            if not url.startswith(('http://', 'https://')):
                raise Exception(f"Invalid URL format: {url}")
            
            # Ajouter des headers pour éviter les blocages
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extraire le contenu principal
                content = self._extract_main_content_simple(soup)
                
                # Extraire les métadonnées
                metadata = {
                    'title': soup.title.string if soup.title else '',
                    'description': '',
                    'language': soup.get('lang', ''),
                    'url': url
                }
                
                # Meta description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    metadata['description'] = meta_desc.get('content', '')
                
                content_data = {
                    'url': url,
                    'metadata': metadata,
                    'content': content,
                    'content_length': len(content),
                    'extraction_time': datetime.now().isoformat()
                }
                
                # Mettre en cache
                if self.redis_cache:
                    await self.redis_cache.set(cache_key, content_data, ttl=self.cache_ttl)
                
                return ActionResult(
                    success=True,
                    data=content_data
                )
                
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Content extraction failed: {e}",
                data={}
            )
    
    def _extract_main_content_simple(self, soup: BeautifulSoup) -> str:
        """Extraction du contenu principal simple"""
        # Supprimer les éléments non pertinents
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Chercher le contenu principal
        main_selectors = [
            'main', 'article', '.content', '#content', 
            '.main-content', '.post-content', '.entry-content',
            '.text', '.body', '.article-body'
        ]
        
        for selector in main_selectors:
            elements = soup.select(selector)
            if elements:
                # Prendre l'élément avec le plus de texte
                best_element = max(elements, key=lambda el: len(el.get_text(strip=True)))
                content = best_element.get_text(strip=True, separator=' ')
                
                # Vérifier que le contenu est suffisant
                if len(content) > 100:  # Au moins 100 caractères
                    return content
        
        # Fallback: prendre tout le body
        body = soup.find('body')
        if body:
            return body.get_text(strip=True, separator=' ')
        
        return soup.get_text(strip=True, separator=' ')
    
    async def _summarize_content_simple(self, parameters: Dict[str, Any]) -> ActionResult:
        """Résumé de contenu simple"""
        content = parameters.get('content', '')
        max_length = parameters.get('max_length', 500)
        
        if not content:
            return ActionResult(
                success=False,
                error="Content parameter is required",
                data={}
            )
        
        # Résumé simple par troncature intelligente
        sentences = content.split('. ')
        summary_sentences = []
        current_length = 0
        
        for sentence in sentences:
            if current_length + len(sentence) > max_length:
                break
            summary_sentences.append(sentence)
            current_length += len(sentence) + 2
        
        summary = '. '.join(summary_sentences)
        if summary_sentences and not summary.endswith('.'):
            summary += '.'
        
        return ActionResult(
            success=True,
            data={
                'original_length': len(content),
                'summary_length': len(summary),
                'summary': summary,
                'compression_ratio': len(summary) / len(content) if content else 0,
                'method': 'intelligent_truncation'
            }
        )
    
    def _update_stats(self, action_type: str, success: bool, response_time: float):
        """Met à jour les statistiques"""
        self.stats['total_searches'] += 1
        
        if success:
            self.stats['successful_searches'] += 1
        else:
            self.stats['failed_searches'] += 1
        
        # Mettre à jour le temps de réponse moyen
        total = self.stats['successful_searches']
        if total > 0:
            self.stats['average_response_time'] = (
                (self.stats['average_response_time'] * (total - 1) + response_time) / total
            )
    
    def get_capabilities(self) -> List[str]:
        """Retourne les capacités du module"""
        return ['search', 'extract', 'summarize', 'list_providers']
    
    def get_providers_info(self) -> List[Dict[str, Any]]:
        """Retourne les informations sur les providers disponibles"""
        return [
            {
                'name': provider['name'],
                'description': provider['description'],
                'weight': provider['weight'],
                'open_source': True,
                'api_key_required': False,
                'privacy_focused': True
            }
            for provider in self.search_providers
        ]
    
    def get_info(self) -> Dict[str, Any]:
        """Retourne les informations du module"""
        return {
            'name': 'SimpleWebSearchModule',
            'version': '1.0.0',
            'description': 'Module de recherche web simple avec providers open source uniquement',
            'capabilities': self.get_capabilities(),
            'engines': [provider['name'] for provider in self.search_providers],
            'stats': self.stats,
            'config': {
                'max_results': self.max_results,
                'timeout': self.timeout,
                'cache_ttl': self.cache_ttl
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques détaillées"""
        return {
            **self.stats,
            'cache_hit_rate': (
                self.stats['cache_hits'] / (self.stats['cache_hits'] + self.stats['cache_misses']) * 100
                if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0
            ),
            'success_rate': (
                self.stats['successful_searches'] / self.stats['total_searches'] * 100
                if self.stats['total_searches'] > 0 else 0
            )
        }
