"""
Roxane OS - System Control Module
Module de contrôle du système d'exploitation
"""

import asyncio
import subprocess
import platform
import psutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger
import json

from core.interfaces import IModule, ActionResult


@dataclass
class SystemInfo:
    """Informations système"""
    platform: str
    cpu_count: int
    memory_total: int
    memory_available: int
    disk_usage: Dict[str, Any]
    processes_count: int


class SystemControlModule(IModule):
    """
    Module de contrôle système
    
    Single Responsibility: Contrôle du système d'exploitation
    Interface Segregation: Interface spécifique aux actions système
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialise le module de contrôle système
        
        Args:
            config: Configuration du module
        """
        self.config = config or {}
        self.allowed_commands = self.config.get('allowed_commands', [])
        self.restricted_paths = self.config.get('restricted_paths', ['/System', '/usr/bin'])
        logger.info("System control module initialized")
    
    async def initialize(self) -> bool:
        """Initialise le module"""
        try:
            # Vérifier les permissions
            if not self._check_permissions():
                logger.warning("Limited system permissions detected")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize system control module: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Nettoie les ressources"""
        pass
    
    def _check_permissions(self) -> bool:
        """Vérifie les permissions système"""
        try:
            # Test simple de commande système
            result = subprocess.run(['whoami'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    async def execute(self, action_type: str, parameters: Dict[str, Any]) -> ActionResult:
        """
        Exécute une action système
        
        Args:
            action_type: Type d'action ('info', 'process', 'file', 'network')
            parameters: Paramètres de l'action
            
        Returns:
            ActionResult avec les résultats
        """
        try:
            if action_type == 'info':
                return await self._get_system_info()
            elif action_type == 'process':
                return await self._manage_processes(parameters)
            elif action_type == 'file':
                return await self._manage_files(parameters)
            elif action_type == 'network':
                return await self._manage_network(parameters)
            else:
                return ActionResult(
                    success=False,
                    data={},
                    error=f"Unknown action type: {action_type}"
                )
        except Exception as e:
            logger.error(f"System control action failed: {e}")
            return ActionResult(
                success=False,
                data={},
                error=str(e)
            )
    
    async def _get_system_info(self) -> ActionResult:
        """Récupère les informations système"""
        try:
            # Informations système de base
            system_info = SystemInfo(
                platform=platform.platform(),
                cpu_count=psutil.cpu_count(),
                memory_total=psutil.virtual_memory().total,
                memory_available=psutil.virtual_memory().available,
                disk_usage=self._get_disk_usage(),
                processes_count=len(psutil.pids())
            )
            
            return ActionResult(
                success=True,
                data={
                    'system': {
                        'platform': system_info.platform,
                        'cpu_count': system_info.cpu_count,
                        'memory_total_gb': round(system_info.memory_total / (1024**3), 2),
                        'memory_available_gb': round(system_info.memory_available / (1024**3), 2),
                        'memory_percent': psutil.virtual_memory().percent,
                        'disk_usage': system_info.disk_usage,
                        'processes_count': system_info.processes_count
                    },
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'boot_time': psutil.boot_time()
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                data={},
                error=f"Failed to get system info: {e}"
            )
    
    def _get_disk_usage(self) -> Dict[str, Any]:
        """Récupère l'utilisation des disques"""
        try:
            disk_usage = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.mountpoint] = {
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_gb': round(usage.used / (1024**3), 2),
                        'free_gb': round(usage.free / (1024**3), 2),
                        'percent': round((usage.used / usage.total) * 100, 2)
                    }
                except PermissionError:
                    continue
            return disk_usage
        except Exception:
            return {}
    
    async def _manage_processes(self, parameters: Dict[str, Any]) -> ActionResult:
        """Gère les processus"""
        action = parameters.get('action', 'list')
        
        try:
            if action == 'list':
                return await self._list_processes(parameters)
            elif action == 'kill':
                return await self._kill_process(parameters)
            elif action == 'start':
                return await self._start_process(parameters)
            else:
                return ActionResult(
                    success=False,
                    data={},
                    error=f"Unknown process action: {action}"
                )
        except Exception as e:
            return ActionResult(
                success=False,
                data={},
                error=f"Process management failed: {e}"
            )
    
    async def _list_processes(self, parameters: Dict[str, Any]) -> ActionResult:
        """Liste les processus"""
        limit = parameters.get('limit', 20)
        filter_name = parameters.get('filter', '')
        
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    if filter_name and filter_name.lower() not in proc_info['name'].lower():
                        continue
                    
                    processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cpu_percent': proc_info['cpu_percent'],
                        'memory_percent': proc_info['memory_percent']
                    })
                    
                    if len(processes) >= limit:
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return ActionResult(
                success=True,
                data={
                    'processes': processes,
                    'count': len(processes)
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                data={},
                error=f"Failed to list processes: {e}"
            )
    
    async def _kill_process(self, parameters: Dict[str, Any]) -> ActionResult:
        """Termine un processus"""
        pid = parameters.get('pid')
        
        if not pid:
            return ActionResult(
                success=False,
                data={},
                error="PID is required"
            )
        
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            
            # Attendre la terminaison
            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                proc.kill()
            
            return ActionResult(
                success=True,
                data={'pid': pid, 'status': 'terminated'}
            )
        except psutil.NoSuchProcess:
            return ActionResult(
                success=False,
                data={},
                error=f"Process {pid} not found"
            )
        except psutil.AccessDenied:
            return ActionResult(
                success=False,
                data={},
                error=f"Access denied for process {pid}"
            )
    
    async def _start_process(self, parameters: Dict[str, Any]) -> ActionResult:
        """Démarre un processus"""
        command = parameters.get('command', '')
        
        if not command:
            return ActionResult(
                success=False,
                data={},
                error="Command is required"
            )
        
        # Vérifier si la commande est autorisée
        if self.allowed_commands and command.split()[0] not in self.allowed_commands:
            return ActionResult(
                success=False,
                data={},
                error=f"Command '{command}' not allowed"
            )
        
        try:
            # Exécuter en arrière-plan
            process = subprocess.Popen(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            return ActionResult(
                success=True,
                data={
                    'pid': process.pid,
                    'command': command,
                    'status': 'started'
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                data={},
                error=f"Failed to start process: {e}"
            )
    
    async def _manage_files(self, parameters: Dict[str, Any]) -> ActionResult:
        """Gère les fichiers"""
        action = parameters.get('action', 'list')
        
        try:
            if action == 'list':
                return await self._list_files(parameters)
            elif action == 'read':
                return await self._read_file(parameters)
            elif action == 'write':
                return await self._write_file(parameters)
            else:
                return ActionResult(
                    success=False,
                    error=f"Unknown file action: {action}"
                )
        except Exception as e:
            return ActionResult(
                success=False,
                data={},
                error=f"File management failed: {e}"
            )
    
    async def _list_files(self, parameters: Dict[str, Any]) -> ActionResult:
        """Liste les fichiers d'un répertoire"""
        path = parameters.get('path', '.')
        limit = parameters.get('limit', 50)
        
        try:
            import os
            files = []
            
            for item in os.listdir(path)[:limit]:
                item_path = os.path.join(path, item)
                try:
                    stat = os.stat(item_path)
                    files.append({
                        'name': item,
                        'path': item_path,
                        'size': stat.st_size,
                        'is_directory': os.path.isdir(item_path),
                        'modified': stat.st_mtime
                    })
                except OSError:
                    continue
            
            return ActionResult(
                success=True,
                data={
                    'path': path,
                    'files': files,
                    'count': len(files)
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                data={},
                error=f"Failed to list files: {e}"
            )
    
    async def _read_file(self, parameters: Dict[str, Any]) -> ActionResult:
        """Lit un fichier"""
        path = parameters.get('path', '')
        max_size = parameters.get('max_size', 1024 * 1024)  # 1MB par défaut
        
        if not path:
            return ActionResult(
                success=False,
                data={},
                error="Path is required"
            )
        
        try:
            import os
            file_size = os.path.getsize(path)
            
            if file_size > max_size:
                return ActionResult(
                    success=False,
                    error=f"File too large ({file_size} bytes). Max allowed: {max_size}"
                )
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return ActionResult(
                success=True,
                data={
                    'path': path,
                    'content': content,
                    'size': file_size
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                data={},
                error=f"Failed to read file: {e}"
            )
    
    async def _write_file(self, parameters: Dict[str, Any]) -> ActionResult:
        """Écrit dans un fichier"""
        path = parameters.get('path', '')
        content = parameters.get('content', '')
        mode = parameters.get('mode', 'w')
        
        if not path:
            return ActionResult(
                success=False,
                data={},
                error="Path is required"
            )
        
        try:
            with open(path, mode, encoding='utf-8') as f:
                f.write(content)
            
            return ActionResult(
                success=True,
                data={
                    'path': path,
                    'bytes_written': len(content.encode('utf-8'))
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                data={},
                error=f"Failed to write file: {e}"
            )
    
    async def _manage_network(self, parameters: Dict[str, Any]) -> ActionResult:
        """Gère les connexions réseau"""
        action = parameters.get('action', 'info')
        
        try:
            if action == 'info':
                return await self._get_network_info()
            elif action == 'connections':
                return await self._list_connections()
            else:
                return ActionResult(
                    success=False,
                    error=f"Unknown network action: {action}"
                )
        except Exception as e:
            return ActionResult(
                success=False,
                data={},
                error=f"Network management failed: {e}"
            )
    
    async def _get_network_info(self) -> ActionResult:
        """Récupère les informations réseau"""
        try:
            # Interfaces réseau
            interfaces = {}
            for interface, addrs in psutil.net_if_addrs().items():
                interfaces[interface] = []
                for addr in addrs:
                    interfaces[interface].append({
                        'family': str(addr.family),
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    })
            
            # Statistiques réseau
            stats = psutil.net_io_counters(pernic=True)
            
            return ActionResult(
                success=True,
                data={
                    'interfaces': interfaces,
                    'stats': {k: {
                        'bytes_sent': v.bytes_sent,
                        'bytes_recv': v.bytes_recv,
                        'packets_sent': v.packets_sent,
                        'packets_recv': v.packets_recv
                    } for k, v in stats.items()}
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                data={},
                error=f"Failed to get network info: {e}"
            )
    
    async def _list_connections(self) -> ActionResult:
        """Liste les connexions réseau"""
        try:
            connections = []
            for conn in psutil.net_connections(kind='inet'):
                try:
                    connections.append({
                        'fd': conn.fd,
                        'family': str(conn.family),
                        'type': str(conn.type),
                        'local_address': conn.laddr,
                        'remote_address': conn.raddr,
                        'status': conn.status,
                        'pid': conn.pid
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return ActionResult(
                success=True,
                data={
                    'connections': connections,
                    'count': len(connections)
                }
            )
        except Exception as e:
            return ActionResult(
                success=False,
                data={},
                error=f"Failed to list connections: {e}"
            )
    
    def get_capabilities(self) -> List[str]:
        """Retourne les capacités du module"""
        return ['info', 'process', 'file', 'network']
    
    def get_info(self) -> Dict[str, Any]:
        """Retourne les informations du module"""
        return {
            'name': 'SystemControlModule',
            'version': '1.0.0',
            'description': 'Module de contrôle du système d\'exploitation',
            'capabilities': self.get_capabilities(),
            'platform': platform.system()
        }
