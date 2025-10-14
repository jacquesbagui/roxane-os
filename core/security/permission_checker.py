"""
Roxane OS - Permission Checker Implementation
Vérification des permissions et sécurité
"""

from typing import Dict, Any, List
from loguru import logger

from core.interfaces import IPermissionChecker, Action


class DefaultPermissionChecker(IPermissionChecker):
    """
    Vérificateur de permissions par défaut
    
    Single Responsibility: Gère uniquement les permissions
    """
    
    # Commandes bloquées (blacklist)
    BLACKLISTED_COMMANDS = [
        r"rm\s+-rf\s+/",
        r"dd\s+if=/dev/(zero|random)",
        r"mkfs\.",
        r":(){ :|:& };:",  # Fork bomb
        r"chmod\s+-R\s+777\s+/",
        r">/dev/sda",
    ]
    
    # Niveaux de permission requis par type d'action
    REQUIRED_LEVELS = {
        'web_search': 0,       # Lecture seule
        'question': 0,
        'greeting': 0,
        'file_read': 0,
        'file_write': 1,       # Écriture fichiers user
        'file_delete': 1,
        'system_command': 2,   # Commandes système
        'file_operation': 1,
        'package_install': 3,  # Installation packages
        'sudo_command': 4,     # Sudo
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le vérificateur
        
        Args:
            config: Configuration avec niveau de permission
        """
        self._permission_level = config.get('permissions', {}).get('level', 2)
        self._require_confirmation = config.get('permissions', {}).get(
            'require_confirmation',
            True
        )
        logger.info(f"Permission checker initialized (level={self._permission_level})")
    
    async def check_permission(
        self,
        action: Action,
        user_id: str
    ) -> bool:
        """
        Vérifie si l'utilisateur a la permission
        
        Args:
            action: Action à vérifier
            user_id: Identifiant utilisateur
            
        Returns:
            True si autorisé, False sinon
        """
        # Vérifier blacklist
        if self._is_blacklisted(action):
            logger.warning(f"❌ Action blacklisted: {action.type}")
            return False
        
        # Vérifier niveau de permission
        required_level = self.REQUIRED_LEVELS.get(action.type, 2)
        
        if self._permission_level < required_level:
            logger.warning(
                f"❌ Permission denied: {action.type} "
                f"(required={required_level}, current={self._permission_level})"
            )
            return False
        
        logger.debug(f"✅ Permission granted: {action.type}")
        return True
    
    def _is_blacklisted(self, action: Action) -> bool:
        """Vérifie si l'action contient une commande blacklistée"""
        import re
        
        # Récupérer la commande si c'est une action système
        command = action.parameters.get('command', '')
        
        if not command:
            return False
        
        # Vérifier contre la blacklist
        for pattern in self.BLACKLISTED_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        
        return False
    
    async def require_confirmation(self, action: Action) -> bool:
        """
        Vérifie si l'action nécessite une confirmation
        
        Args:
            action: Action à vérifier
            
        Returns:
            True si confirmation requise
        """
        if not self._require_confirmation:
            return False
        
        # Actions nécessitant toujours confirmation
        critical_actions = [
            'file_delete',
            'system_command',
            'package_install',
            'sudo_command'
        ]
        
        # Ou si explicitement demandé
        if action.require_confirmation:
            return True
        
        return action.type in critical_actions