"""
Roxane OS - File Manager Module
Module de gestion avancée des fichiers et répertoires
"""

import asyncio
import os
import shutil
import mimetypes
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from loguru import logger
import json
from datetime import datetime

from core.interfaces import IModule, ActionResult


@dataclass
class FileInfo:
    """Informations sur un fichier"""
    name: str
    path: str
    size: int
    is_directory: bool
    modified: float
    mime_type: Optional[str] = None
    hash_md5: Optional[str] = None


class FileManagerModule(IModule):
    """
    Module de gestion de fichiers
    
    Single Responsibility: Gestion des fichiers et répertoires
    Open/Closed: Extensible pour différents types de fichiers
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialise le module de gestion de fichiers
        
        Args:
            config: Configuration du module
        """
        self.config = config or {}
        self.max_file_size = self.config.get('max_file_size', 100 * 1024 * 1024)  # 100MB
        self.allowed_extensions = self.config.get('allowed_extensions', [])
        self.restricted_paths = self.config.get('restricted_paths', ['/System', '/usr/bin'])
        logger.info("File manager module initialized")
    
    async def initialize(self) -> bool:
        """Initialise le module"""
        try:
            # Créer le répertoire de travail par défaut s'il n'existe pas
            work_dir = self.config.get('work_directory', './roxane_workspace')
            os.makedirs(work_dir, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize file manager module: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Nettoie les ressources"""
        pass
    
    def _is_path_allowed(self, path: str) -> bool:
        """Vérifie si le chemin est autorisé"""
        abs_path = os.path.abspath(path)
        for restricted in self.restricted_paths:
            if abs_path.startswith(os.path.abspath(restricted)):
                return False
        return True
    
    def _is_extension_allowed(self, file_path: str) -> bool:
        """Vérifie si l'extension est autorisée"""
        if not self.allowed_extensions:
            return True
        
        ext = Path(file_path).suffix.lower()
        return ext in [e.lower() for e in self.allowed_extensions]
    
    async def execute(self, action_type: str, parameters: Dict[str, Any]) -> ActionResult:
        """
        Exécute une action de gestion de fichiers
        
        Args:
            action_type: Type d'action ('list', 'read', 'write', 'copy', 'move', 'delete', 'search')
            parameters: Paramètres de l'action
            
        Returns:
            ActionResult avec les résultats
        """
        try:
            if action_type == 'list':
                return await self._list_files(parameters)
            elif action_type == 'read':
                return await self._read_file(parameters)
            elif action_type == 'write':
                return await self._write_file(parameters)
            elif action_type == 'copy':
                return await self._copy_file(parameters)
            elif action_type == 'move':
                return await self._move_file(parameters)
            elif action_type == 'delete':
                return await self._delete_file(parameters)
            elif action_type == 'search':
                return await self._search_files(parameters)
            elif action_type == 'info':
                return await self._get_file_info(parameters)
            elif action_type == 'create_dir':
                return await self._create_directory(parameters)
            else:
                return ActionResult(
                    success=False,
                    error=f"Unknown action type: {action_type}"
                )
        except Exception as e:
            logger.error(f"File manager action failed: {e}")
            return ActionResult(
                success=False,
                error=str(e)
            )
    
    async def _list_files(self, parameters: Dict[str, Any]) -> ActionResult:
        """Liste les fichiers d'un répertoire"""
        path = parameters.get('path', '.')
        recursive = parameters.get('recursive', False)
        include_hidden = parameters.get('include_hidden', False)
        limit = parameters.get('limit', 100)
        
        if not self._is_path_allowed(path):
            return ActionResult(
                success=False,
                error="Access to this path is restricted"
            )
        
        try:
            files = []
            count = 0
            
            if recursive:
                for root, dirs, filenames in os.walk(path):
                    # Filtrer les fichiers cachés si nécessaire
                    if not include_hidden:
                        filenames = [f for f in filenames if not f.startswith('.')]
                        dirs[:] = [d for d in dirs if not d.startswith('.')]
                    
                    for filename in filenames:
                        if count >= limit:
                            break
                        
                        file_path = os.path.join(root, filename)
                        try:
                            stat = os.stat(file_path)
                            files.append({
                                'name': filename,
                                'path': file_path,
                                'size': stat.st_size,
                                'is_directory': False,
                                'modified': stat.st_mtime,
                                'mime_type': mimetypes.guess_type(file_path)[0]
                            })
                            count += 1
                        except OSError:
                            continue
            else:
                try:
                    items = os.listdir(path)
                    if not include_hidden:
                        items = [item for item in items if not item.startswith('.')]
                    
                    for item in items[:limit]:
                        item_path = os.path.join(path, item)
                        try:
                            stat = os.stat(item_path)
                            files.append({
                                'name': item,
                                'path': item_path,
                                'size': stat.st_size,
                                'is_directory': os.path.isdir(item_path),
                                'modified': stat.st_mtime,
                                'mime_type': mimetypes.guess_type(item_path)[0]
                            })
                        except OSError:
                            continue
                except OSError as e:
                    return ActionResult(
                        success=False,
                        error=f"Failed to list directory: {e}"
                    )
            
            return ActionResult(
                success=True,
                data={
                    'path': path,
                    'files': files,
                    'count': len(files),
                    'recursive': recursive
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to list files: {e}"
            )
    
    async def _read_file(self, parameters: Dict[str, Any]) -> ActionResult:
        """Lit un fichier"""
        path = parameters.get('path', '')
        encoding = parameters.get('encoding', 'utf-8')
        max_size = parameters.get('max_size', self.max_file_size)
        
        if not path:
            return ActionResult(
                success=False,
                error="Path is required"
            )
        
        if not self._is_path_allowed(path):
            return ActionResult(
                success=False,
                error="Access to this path is restricted"
            )
        
        if not self._is_extension_allowed(path):
            return ActionResult(
                success=False,
                error="File extension not allowed"
            )
        
        try:
            file_size = os.path.getsize(path)
            
            if file_size > max_size:
                return ActionResult(
                    success=False,
                    error=f"File too large ({file_size} bytes). Max allowed: {max_size}"
                )
            
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return ActionResult(
                success=True,
                data={
                    'path': path,
                    'content': content,
                    'size': file_size,
                    'encoding': encoding,
                    'mime_type': mimetypes.guess_type(path)[0]
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to read file: {e}"
            )
    
    async def _write_file(self, parameters: Dict[str, Any]) -> ActionResult:
        """Écrit dans un fichier"""
        path = parameters.get('path', '')
        content = parameters.get('content', '')
        mode = parameters.get('mode', 'w')
        encoding = parameters.get('encoding', 'utf-8')
        create_dirs = parameters.get('create_dirs', True)
        
        if not path:
            return ActionResult(
                success=False,
                error="Path is required"
            )
        
        if not self._is_path_allowed(path):
            return ActionResult(
                success=False,
                error="Access to this path is restricted"
            )
        
        if not self._is_extension_allowed(path):
            return ActionResult(
                success=False,
                error="File extension not allowed"
            )
        
        try:
            # Créer les répertoires parents si nécessaire
            if create_dirs:
                os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, mode, encoding=encoding) as f:
                f.write(content)
            
            bytes_written = len(content.encode(encoding))
            
            return ActionResult(
                success=True,
                data={
                    'path': path,
                    'bytes_written': bytes_written,
                    'mode': mode,
                    'encoding': encoding
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to write file: {e}"
            )
    
    async def _copy_file(self, parameters: Dict[str, Any]) -> ActionResult:
        """Copie un fichier ou répertoire"""
        source = parameters.get('source', '')
        destination = parameters.get('destination', '')
        
        if not source or not destination:
            return ActionResult(
                success=False,
                error="Source and destination are required"
            )
        
        if not self._is_path_allowed(source) or not self._is_path_allowed(destination):
            return ActionResult(
                success=False,
                error="Access to one of the paths is restricted"
            )
        
        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(source, destination)
            
            return ActionResult(
                success=True,
                data={
                    'source': source,
                    'destination': destination,
                    'operation': 'copy'
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to copy: {e}"
            )
    
    async def _move_file(self, parameters: Dict[str, Any]) -> ActionResult:
        """Déplace un fichier ou répertoire"""
        source = parameters.get('source', '')
        destination = parameters.get('destination', '')
        
        if not source or not destination:
            return ActionResult(
                success=False,
                error="Source and destination are required"
            )
        
        if not self._is_path_allowed(source) or not self._is_path_allowed(destination):
            return ActionResult(
                success=False,
                error="Access to one of the paths is restricted"
            )
        
        try:
            shutil.move(source, destination)
            
            return ActionResult(
                success=True,
                data={
                    'source': source,
                    'destination': destination,
                    'operation': 'move'
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to move: {e}"
            )
    
    async def _delete_file(self, parameters: Dict[str, Any]) -> ActionResult:
        """Supprime un fichier ou répertoire"""
        path = parameters.get('path', '')
        recursive = parameters.get('recursive', False)
        
        if not path:
            return ActionResult(
                success=False,
                error="Path is required"
            )
        
        if not self._is_path_allowed(path):
            return ActionResult(
                success=False,
                error="Access to this path is restricted"
            )
        
        try:
            if os.path.isdir(path):
                if recursive:
                    shutil.rmtree(path)
                else:
                    os.rmdir(path)
            else:
                os.remove(path)
            
            return ActionResult(
                success=True,
                data={
                    'path': path,
                    'operation': 'delete',
                    'recursive': recursive
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to delete: {e}"
            )
    
    async def _search_files(self, parameters: Dict[str, Any]) -> ActionResult:
        """Recherche des fichiers"""
        query = parameters.get('query', '')
        path = parameters.get('path', '.')
        pattern = parameters.get('pattern', '')
        max_results = parameters.get('max_results', 50)
        
        if not query and not pattern:
            return ActionResult(
                success=False,
                error="Query or pattern is required"
            )
        
        if not self._is_path_allowed(path):
            return ActionResult(
                success=False,
                error="Access to this path is restricted"
            )
        
        try:
            results = []
            count = 0
            
            for root, dirs, filenames in os.walk(path):
                for filename in filenames:
                    if count >= max_results:
                        break
                    
                    file_path = os.path.join(root, filename)
                    
                    # Recherche par nom
                    if query and query.lower() in filename.lower():
                        results.append({
                            'name': filename,
                            'path': file_path,
                            'match_type': 'filename'
                        })
                        count += 1
                    
                    # Recherche par pattern
                    elif pattern:
                        import fnmatch
                        if fnmatch.fnmatch(filename, pattern):
                            results.append({
                                'name': filename,
                                'path': file_path,
                                'match_type': 'pattern'
                            })
                            count += 1
            
            return ActionResult(
                success=True,
                data={
                    'query': query,
                    'pattern': pattern,
                    'path': path,
                    'results': results,
                    'count': len(results)
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to search files: {e}"
            )
    
    async def _get_file_info(self, parameters: Dict[str, Any]) -> ActionResult:
        """Récupère les informations détaillées d'un fichier"""
        path = parameters.get('path', '')
        include_hash = parameters.get('include_hash', False)
        
        if not path:
            return ActionResult(
                success=False,
                error="Path is required"
            )
        
        if not self._is_path_allowed(path):
            return ActionResult(
                success=False,
                error="Access to this path is restricted"
            )
        
        try:
            if not os.path.exists(path):
                return ActionResult(
                    success=False,
                    error="File not found"
                )
            
            stat = os.stat(path)
            mime_type = mimetypes.guess_type(path)[0]
            
            file_info = {
                'name': os.path.basename(path),
                'path': path,
                'size': stat.st_size,
                'is_directory': os.path.isdir(path),
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'mime_type': mime_type,
                'permissions': oct(stat.st_mode)[-3:]
            }
            
            # Calculer le hash MD5 si demandé
            if include_hash and not os.path.isdir(path):
                try:
                    hash_md5 = hashlib.md5()
                    with open(path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_md5.update(chunk)
                    file_info['hash_md5'] = hash_md5.hexdigest()
                except Exception:
                    pass
            
            return ActionResult(
                success=True,
                data=file_info
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to get file info: {e}"
            )
    
    async def _create_directory(self, parameters: Dict[str, Any]) -> ActionResult:
        """Crée un répertoire"""
        path = parameters.get('path', '')
        parents = parameters.get('parents', True)
        
        if not path:
            return ActionResult(
                success=False,
                error="Path is required"
            )
        
        if not self._is_path_allowed(path):
            return ActionResult(
                success=False,
                error="Access to this path is restricted"
            )
        
        try:
            os.makedirs(path, exist_ok=parents)
            
            return ActionResult(
                success=True,
                data={
                    'path': path,
                    'created': True,
                    'parents': parents
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Failed to create directory: {e}"
            )
    
    def get_capabilities(self) -> List[str]:
        """Retourne les capacités du module"""
        return ['list', 'read', 'write', 'copy', 'move', 'delete', 'search', 'info', 'create_dir']
    
    def get_info(self) -> Dict[str, Any]:
        """Retourne les informations du module"""
        return {
            'name': 'FileManagerModule',
            'version': '1.0.0',
            'description': 'Module de gestion avancée des fichiers et répertoires',
            'capabilities': self.get_capabilities(),
            'max_file_size': self.max_file_size,
            'allowed_extensions': self.allowed_extensions
        }
