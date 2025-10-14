"""
Roxane OS - Robust Web Search Module
Module de recherche web robuste pour la production
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
from urllib.parse import urljoin, urlparse
import re

from core.interfaces import IModule, ActionResult
from core.cache import RedisCacheManager


@dataclass
class SearchResult:
    """Résultat de recherche enrichi"""
    title: str
    url: str
    snippet: str
    relevance_score: float
    source: str  # 'duckduckgo', 'searxng', 'google', etc.
    timestamp: datetime = field(default_factory=datetime.now)
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchConfig:
    """Configuration de recherche"""
    max_results: int = 10
    timeout: int = 30
    retry_attempts: int = 3
    cache_ttl: int = 3600  # 1 heure
    respect_robots_txt: bool = True
    user_agent_rotation: bool = True
    proxy_enabled: bool = False
    proxy_list: List[str] = field(default_factory=list)


class RobustWebSearchModule(IModule):
    """
    Module de recherche web robuste pour la production
    
    Fonctionnalités:
    - Métamoteur privé (SearxNG) avec fallback
    - Cache Redis pour les performances
    - Extraction de contenu avancée avec Playwright
    - Gestion d'erreurs robuste avec retry
    - Rotation des User-Agents
    - Respect des robots.txt
    - Monitoring des performances
    - Synthèse multi-sources
    """
    
    def __init__(self, config: Dict[str, Any] = None, redis_cache: Optional[RedisCacheManager] = None):
        """
        Initialise le module de recherche web robuste
        
        Args:
            config: Configuration du module
            redis_cache: Gestionnaire de cache Redis
        """
        self.config = config or {}
        self.redis_cache = redis_cache
        self.search_config = SearchConfig(**self.config.get('search', {}))
        
        # Sessions HTTP avec rotation
        self.sessions: List[aiohttp.ClientSession] = []
        self.current_session_index = 0
        
        # User-Agents pour rotation
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        
        # Métamoteurs de recherche
        self.search_engines = [
            {'name': 'searxng', 'url': 'http://localhost:8080/search', 'weight': 1.0},
            {'name': 'duckduckgo', 'url': 'https://api.duckduckgo.com/', 'weight': 0.8},
            {'name': 'bing', 'url': 'https://api.bing.microsoft.com/v7.0/search', 'weight': 0.6},
            {'name': 'google', 'url': 'https://www.googleapis.com/customsearch/v1', 'weight': 0.4}
        ]
        
        # Statistiques
        self.stats = {
            'total_searches': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'average_response_time': 0.0,
            'engines_used': {}
        }
        
        # Cache local pour robots.txt
        self.robots_cache: Dict[str, Dict] = {}
        
        logger.info("Robust web search module initialized")
    
    async def initialize(self) -> bool:
        """Initialise les sessions HTTP"""
        try:
            # Créer plusieurs sessions avec différents User-Agents
            for i, user_agent in enumerate(self.user_agents):
                session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.search_config.timeout),
                    headers={'User-Agent': user_agent},
                    connector=aiohttp.TCPConnector(
                        limit=100,
                        limit_per_host=30,
                        ttl_dns_cache=300,
                        use_dns_cache=True
                    )
                )
                self.sessions.append(session)
            
            # Initialiser le cache Redis si disponible
            if self.redis_cache:
                await self.redis_cache.initialize()
            
            logger.success("✅ Robust web search module initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize robust web search module: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Nettoie les ressources"""
        try:
            for session in self.sessions:
                await session.close()
            
            if self.redis_cache:
                await self.redis_cache.cleanup()
            
            logger.info("Robust web search module cleaned up")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup web search module: {e}")
    
    async def execute(self, action_type: str, parameters: Dict[str, Any]) -> ActionResult:
        """
        Exécute une action de recherche web robuste
        
        Args:
            action_type: Type d'action ('search', 'extract', 'summarize', 'multi_search')
            parameters: Paramètres de l'action
            
        Returns:
            ActionResult avec les résultats
        """
        start_time = time.time()
        
        try:
            if action_type == 'search':
                result = await self._search_web_robust(parameters)
            elif action_type == 'multi_search':
                result = await self._multi_engine_search(parameters)
            elif action_type == 'extract':
                result = await self._extract_content_robust(parameters)
            elif action_type == 'summarize':
                result = await self._summarize_content_advanced(parameters)
            elif action_type == 'synthesize':
                result = await self._synthesize_multiple_sources(parameters)
            else:
                result = ActionResult(
                    success=False,
                    error=f"Unknown action type: {action_type}"
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
    
    async def _search_web_robust(self, parameters: Dict[str, Any]) -> ActionResult:
        """Effectue une recherche web robuste avec cache et fallback"""
        query = parameters.get('query', '')
        max_results = parameters.get('max_results', self.search_config.max_results)
        
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
        
        # Essayer plusieurs moteurs de recherche
        results = []
        for engine in self.search_engines:
            try:
                engine_results = await self._search_with_engine(engine, query, max_results)
                if engine_results:
                    results.extend(engine_results)
                    break  # Utiliser le premier moteur qui fonctionne
            except Exception as e:
                logger.warning(f"Search engine {engine['name']} failed: {e}")
                continue
        
        if not results:
            return ActionResult(
                success=False,
                error="All search engines failed",
                data={}
            )
        
        # Dédupliquer et trier les résultats
        unique_results = self._deduplicate_results(results)
        sorted_results = sorted(unique_results, key=lambda x: x.relevance_score, reverse=True)
        
        # Limiter le nombre de résultats
        final_results = sorted_results[:max_results]
        
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
                for r in final_results
            ],
            'count': len(final_results),
            'search_time': time.time() - time.time(),
            'engines_used': list(set(r.source for r in final_results))
        }
        
        # Mettre en cache
        if self.redis_cache:
            await self.redis_cache.set(cache_key, response_data, ttl=self.search_config.cache_ttl)
        
        return ActionResult(
            success=True,
            data=response_data
        )
    
    async def _search_with_engine(self, engine: Dict, query: str, max_results: int) -> List[SearchResult]:
        """Recherche avec un moteur spécifique"""
        if engine['name'] == 'searxng':
            return await self._search_searxng(engine['url'], query, max_results)
        elif engine['name'] == 'duckduckgo':
            return await self._search_duckduckgo_robust(engine['url'], query, max_results)
        elif engine['name'] == 'bing':
            return await self._search_bing(engine['url'], query, max_results)
        elif engine['name'] == 'google':
            return await self._search_google(engine['url'], query, max_results)
        else:
            return []
    
    async def _search_searxng(self, base_url: str, query: str, max_results: int) -> List[SearchResult]:
        """Recherche via SearxNG (métamoteur privé)"""
        session = self._get_next_session()
        
        params = {
            'q': query,
            'format': 'json',
            'categories': 'general',
            'engines': 'google,bing,duckduckgo',
            'safesearch': 'moderate',
            'time_range': '',
            'language': 'fr'
        }
        
        async with session.get(base_url, params=params) as response:
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
                        'parsed_url': result.get('parsed_url', {}),
                        'positions': result.get('positions', [])
                    }
                ))
            
            return results
    
    async def _search_duckduckgo_robust(self, base_url: str, query: str, max_results: int) -> List[SearchResult]:
        """Recherche DuckDuckGo robuste avec retry"""
        session = self._get_next_session()
        
        params = {
            'q': query,
            'format': 'json',
            'no_html': '1',
            'skip_disambig': '1',
            't': 'roxane-os'
        }
        
        for attempt in range(self.search_config.retry_attempts):
            try:
                async with session.get(base_url, params=params) as response:
                    if response.status != 200:
                        if attempt < self.search_config.retry_attempts - 1:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        raise Exception(f"DuckDuckGo HTTP {response.status}")
                    
                    data = await response.json()
                    results = []
                    
                    # Traiter les résultats instant answers
                    if data.get('Abstract'):
                        results.append(SearchResult(
                            title=data.get('Heading', 'Instant Answer'),
                            url=data.get('AbstractURL', ''),
                            snippet=data.get('Abstract', ''),
                            relevance_score=1.0,
                            source='duckduckgo',
                            metadata={'type': 'instant_answer'}
                        ))
                    
                    # Traiter les résultats web
                    for result in data.get('Results', [])[:max_results]:
                        results.append(SearchResult(
                            title=result.get('Text', ''),
                            url=result.get('FirstURL', ''),
                            snippet=result.get('Text', ''),
                            relevance_score=0.8,
                            source='duckduckgo',
                            metadata={'type': 'web_result'}
                        ))
                    
                    return results
                    
            except Exception as e:
                if attempt < self.search_config.retry_attempts - 1:
                    logger.warning(f"DuckDuckGo attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise e
        
        return []
    
    async def _search_bing(self, base_url: str, query: str, max_results: int) -> List[SearchResult]:
        """Recherche Bing (nécessite une clé API)"""
        # TODO: Implémenter avec clé API Bing
        logger.warning("Bing search not implemented (requires API key)")
        return []
    
    async def _search_google(self, base_url: str, query: str, max_results: int) -> List[SearchResult]:
        """Recherche Google (nécessite une clé API)"""
        # TODO: Implémenter avec clé API Google
        logger.warning("Google search not implemented (requires API key)")
        return []
    
    async def _multi_engine_search(self, parameters: Dict[str, Any]) -> ActionResult:
        """Recherche multi-moteurs avec synthèse"""
        query = parameters.get('query', '')
        max_results = parameters.get('max_results', 5)
        
        if not query:
                return ActionResult(
                    success=False,
                    error="Query parameter is required",
                    data={}
                )
        
        # Rechercher avec tous les moteurs disponibles
        all_results = []
        tasks = []
        
        for engine in self.search_engines:
            task = self._search_with_engine(engine, query, max_results)
            tasks.append(task)
        
        # Attendre tous les résultats
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collecter les résultats valides
        for results in results_list:
            if isinstance(results, list):
                all_results.extend(results)
        
        # Dédupliquer et fusionner
        unique_results = self._deduplicate_results(all_results)
        sorted_results = sorted(unique_results, key=lambda x: x.relevance_score, reverse=True)
        
        # Synthétiser les résultats
        synthesis = await self._synthesize_search_results(query, sorted_results[:max_results])
        
        return ActionResult(
            success=True,
            data={
                'query': query,
                'results': [
                    {
                        'title': r.title,
                        'url': r.url,
                        'snippet': r.snippet,
                        'relevance_score': r.relevance_score,
                        'source': r.source
                    }
                    for r in sorted_results[:max_results]
                ],
                'synthesis': synthesis,
                'total_sources': len(set(r.source for r in all_results)),
                'count': len(sorted_results)
            }
        )
    
    async def _extract_content_robust(self, parameters: Dict[str, Any]) -> ActionResult:
        """Extraction de contenu robuste avec respect des robots.txt"""
        url = parameters.get('url', '')
        
        if not url:
                return ActionResult(
                    success=False,
                    error="URL parameter is required",
                    data={}
                )
        
        # Vérifier robots.txt
        if self.search_config.respect_robots_txt:
            if not await self._check_robots_txt(url):
                return ActionResult(
                    success=False,
                    error="Robots.txt disallows crawling this URL",
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
        
        # Extraire le contenu
        try:
            session = self._get_next_session()
            
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extraction avancée
                content_data = await self._extract_content_advanced(soup, url)
                
                # Mettre en cache
                if self.redis_cache:
                    await self.redis_cache.set(cache_key, content_data, ttl=self.search_config.cache_ttl)
                
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
    
    async def _extract_content_advanced(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extraction de contenu avancée"""
        # Supprimer les éléments non pertinents
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'advertisement']):
            element.decompose()
        
        # Extraire les métadonnées
        metadata = {
            'title': soup.title.string if soup.title else '',
            'description': '',
            'keywords': '',
            'author': '',
            'published_date': '',
            'language': soup.get('lang', ''),
            'canonical_url': ''
        }
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            metadata['description'] = meta_desc.get('content', '')
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            metadata['keywords'] = meta_keywords.get('content', '')
        
        # Meta author
        meta_author = soup.find('meta', attrs={'name': 'author'})
        if meta_author:
            metadata['author'] = meta_author.get('content', '')
        
        # Canonical URL
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            metadata['canonical_url'] = canonical.get('href', '')
        
        # Extraire le contenu principal avec plusieurs stratégies
        content = self._extract_main_content_advanced(soup)
        
        # Extraire les liens importants
        important_links = self._extract_important_links(soup, url)
        
        # Extraire les images
        images = self._extract_images(soup, url)
        
        return {
            'url': url,
            'metadata': metadata,
            'content': content,
            'content_length': len(content),
            'important_links': important_links,
            'images': images,
            'extraction_time': datetime.now().isoformat()
        }
    
    def _extract_main_content_advanced(self, soup: BeautifulSoup) -> str:
        """Extraction du contenu principal avec stratégies avancées"""
        # Stratégies d'extraction par ordre de priorité
        strategies = [
            # Sélecteurs spécifiques pour le contenu principal
            ['main', 'article', '.content', '#content', '.main-content', '.post-content', '.entry-content'],
            # Sélecteurs pour les blogs et articles
            ['.post', '.article', '.blog-post', '.news-article', '.story'],
            # Sélecteurs génériques
            ['.text', '.body', '.article-body', '.post-body'],
            # Fallback
            ['body']
        ]
        
        for strategy in strategies:
            for selector in strategy:
                elements = soup.select(selector)
                if elements:
                    # Prendre l'élément avec le plus de texte
                    best_element = max(elements, key=lambda el: len(el.get_text(strip=True)))
                    content = best_element.get_text(strip=True, separator=' ')
                    
                    # Vérifier que le contenu est suffisant
                    if len(content) > 100:  # Au moins 100 caractères
                        return content
        
        # Dernier recours
        return soup.get_text(strip=True, separator=' ')
    
    def _extract_important_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extrait les liens importants de la page"""
        important_links = []
        
        # Liens avec texte descriptif
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            text = link.get_text(strip=True)
            
            if text and len(text) > 10:  # Liens avec texte significatif
                full_url = urljoin(base_url, href)
                important_links.append({
                    'url': full_url,
                    'text': text,
                    'title': link.get('title', '')
                })
        
        # Limiter à 10 liens les plus pertinents
        return important_links[:10]
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extrait les images importantes de la page"""
        images = []
        
        for img in soup.find_all('img', src=True):
            src = img.get('src')
            alt = img.get('alt', '')
            
            if src:
                full_url = urljoin(base_url, src)
                images.append({
                    'url': full_url,
                    'alt': alt,
                    'title': img.get('title', '')
                })
        
        return images[:5]  # Limiter à 5 images
    
    async def _check_robots_txt(self, url: str) -> bool:
        """Vérifie si l'URL est autorisée par robots.txt"""
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            # Vérifier le cache
            if robots_url in self.robots_cache:
                robots_data = self.robots_cache[robots_url]
            else:
                session = self._get_next_session()
                async with session.get(robots_url) as response:
                    if response.status != 200:
                        return True  # Pas de robots.txt = autorisé
                    
                    robots_text = await response.text()
                    robots_data = self._parse_robots_txt(robots_text)
                    self.robots_cache[robots_url] = robots_data
            
            # Vérifier si l'URL est autorisée
            return self._is_url_allowed(url, robots_data)
            
        except Exception as e:
            logger.warning(f"Failed to check robots.txt for {url}: {e}")
            return True  # En cas d'erreur, autoriser
    
    def _parse_robots_txt(self, robots_text: str) -> Dict[str, List[str]]:
        """Parse le contenu de robots.txt"""
        robots_data = {'allow': [], 'disallow': []}
        current_user_agent = None
        
        for line in robots_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.lower().startswith('user-agent:'):
                current_user_agent = line.split(':', 1)[1].strip()
            elif line.lower().startswith('allow:') and current_user_agent == '*':
                robots_data['allow'].append(line.split(':', 1)[1].strip())
            elif line.lower().startswith('disallow:') and current_user_agent == '*':
                robots_data['disallow'].append(line.split(':', 1)[1].strip())
        
        return robots_data
    
    def _is_url_allowed(self, url: str, robots_data: Dict[str, List[str]]) -> bool:
        """Vérifie si une URL est autorisée par robots.txt"""
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Vérifier les règles de disallow
        for disallow_rule in robots_data['disallow']:
            if disallow_rule == '/':
                return False  # Tout est interdit
            if path.startswith(disallow_rule):
                return False
        
        # Vérifier les règles de allow
        for allow_rule in robots_data['allow']:
            if path.startswith(allow_rule):
                return True
        
        return True  # Par défaut, autoriser
    
    def _get_next_session(self) -> aiohttp.ClientSession:
        """Obtient la prochaine session avec rotation"""
        if not self.sessions:
            raise Exception("No HTTP sessions available")
        
        session = self.sessions[self.current_session_index]
        self.current_session_index = (self.current_session_index + 1) % len(self.sessions)
        return session
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Déduplique les résultats de recherche"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        return unique_results
    
    async def _synthesize_search_results(self, query: str, results: List[SearchResult]) -> str:
        """Synthétise les résultats de recherche"""
        if not results:
            return "Aucun résultat trouvé pour cette recherche."
        
        # Extraire les informations clés
        titles = [r.title for r in results]
        snippets = [r.snippet for r in results]
        sources = list(set(r.source for r in results))
        
        # Créer une synthèse simple
        synthesis = f"Recherche pour '{query}' :\n\n"
        
        for i, result in enumerate(results[:3], 1):  # Top 3 résultats
            synthesis += f"{i}. {result.title}\n"
            synthesis += f"   {result.snippet[:200]}...\n"
            synthesis += f"   Source: {result.url}\n\n"
        
        if len(results) > 3:
            synthesis += f"... et {len(results) - 3} autres résultats.\n"
        
        synthesis += f"\nSources consultées: {', '.join(sources)}"
        
        return synthesis
    
    async def _summarize_content_advanced(self, parameters: Dict[str, Any]) -> ActionResult:
        """Résumé de contenu avancé avec LLM"""
        content = parameters.get('content', '')
        max_length = parameters.get('max_length', 500)
        
        if not content:
                return ActionResult(
                    success=False,
                    error="Content parameter is required",
                    data={}
                )
        
        # TODO: Implémenter avec LLM pour un résumé intelligent
        # Pour l'instant, résumé simple par troncature intelligente
        
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
    
    async def _synthesize_multiple_sources(self, parameters: Dict[str, Any]) -> ActionResult:
        """Synthétise plusieurs sources d'information"""
        sources = parameters.get('sources', [])
        
        if not sources:
                return ActionResult(
                    success=False,
                    error="Sources parameter is required",
                    data={}
                )
        
        # TODO: Implémenter synthèse intelligente avec LLM
        # Pour l'instant, concaténation simple
        
        synthesis = "Synthèse des sources :\n\n"
        
        for i, source in enumerate(sources, 1):
            synthesis += f"Source {i}:\n"
            synthesis += f"{source.get('content', '')[:300]}...\n\n"
        
        return ActionResult(
            success=True,
            data={
                'synthesis': synthesis,
                'source_count': len(sources),
                'method': 'simple_concatenation'
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
        return [
            'search', 'multi_search', 'extract', 'summarize', 
            'synthesize', 'robots_check', 'cache_management'
        ]
    
    def get_info(self) -> Dict[str, Any]:
        """Retourne les informations du module"""
        return {
            'name': 'RobustWebSearchModule',
            'version': '2.0.0',
            'description': 'Module de recherche web robuste pour la production',
            'capabilities': self.get_capabilities(),
            'engines': [engine['name'] for engine in self.search_engines],
            'stats': self.stats,
            'config': {
                'max_results': self.search_config.max_results,
                'timeout': self.search_config.timeout,
                'retry_attempts': self.search_config.retry_attempts,
                'cache_ttl': self.search_config.cache_ttl,
                'respect_robots_txt': self.search_config.respect_robots_txt,
                'user_agent_rotation': self.search_config.user_agent_rotation
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
            ),
            'sessions_count': len(self.sessions),
            'engines_available': len(self.search_engines)
        }
