#!/usr/bin/env python3
"""
Roxane OS - Database Initialization Script
Script Python pour initialiser la base de données PostgreSQL
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from core.database import DatabaseManager
from core.database.models import Base
import yaml
from loguru import logger


async def main():
    """Initialise la base de données"""
    try:
        # Charger la configuration
        config_path = Path(__file__).parent.parent / "config" / "system.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Configuration PostgreSQL
        postgres_config = config['database']['postgres']
        
        logger.info("🚀 Initialisation de la base de données PostgreSQL...")
        
        # Créer le gestionnaire de base de données
        db_manager = DatabaseManager(postgres_config)
        
        # Initialiser la connexion
        success = await db_manager.initialize()
        
        if success:
            logger.success("✅ Base de données initialisée avec succès")
            
            # Afficher les statistiques
            stats = await db_manager.get_stats()
            logger.info(f"📊 Statistiques: {stats}")
            
        else:
            logger.error("❌ Échec de l'initialisation de la base de données")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation: {e}")
        return 1
    
    finally:
        if 'db_manager' in locals():
            await db_manager.cleanup()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
