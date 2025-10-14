#!/usr/bin/env python3
"""
Roxane OS - Create Tables Script
Script pour créer les tables PostgreSQL en tant qu'utilisateur postgres
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

import psycopg2
import yaml
from loguru import logger


def create_tables():
    """Crée les tables PostgreSQL"""
    try:
        # Charger la configuration
        config_path = Path(__file__).parent.parent / "config" / "system.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Configuration PostgreSQL
        postgres_config = config['database']['postgres']
        
        logger.info("🚀 Création des tables PostgreSQL...")
        
        # Connexion en tant qu'utilisateur postgres
        conn = psycopg2.connect(
            host=postgres_config['host'],
            port=postgres_config['port'],
            database=postgres_config['database'],
            user='postgres',
            password='postgres'  # Mot de passe postgres
        )
        
        cursor = conn.cursor()
        
        # Script SQL pour créer les tables
        create_tables_sql = """
        -- Créer les extensions
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "pg_trgm";
        CREATE EXTENSION IF NOT EXISTS "btree_gin";
        
        -- Table des utilisateurs
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            preferences JSONB DEFAULT '{}'
        );
        
        -- Table des sessions
        CREATE TABLE IF NOT EXISTS sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            session_token VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            meta_data JSONB DEFAULT '{}'
        );
        
        -- Table des conversations
        CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
            title VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            context JSONB DEFAULT '{}',
            summary TEXT
        );
        
        -- Table des messages
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tokens_used INTEGER DEFAULT 0,
            confidence FLOAT DEFAULT 1.0,
            meta_data JSONB DEFAULT '{}',
            embedding TEXT  -- Pour la recherche sémantique (JSON string)
        );
        
        -- Index pour les performances
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
        CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
        
        -- Index pour la recherche textuelle
        CREATE INDEX IF NOT EXISTS idx_messages_content_gin ON messages USING gin(to_tsvector('french', content));
        CREATE INDEX IF NOT EXISTS idx_conversations_title_gin ON conversations USING gin(to_tsvector('french', title));
        
        -- Fonction pour mettre à jour updated_at
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        -- Triggers pour updated_at
        DROP TRIGGER IF EXISTS update_users_updated_at ON users;
        DROP TRIGGER IF EXISTS update_sessions_updated_at ON sessions;
        DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
        DROP TRIGGER IF EXISTS update_messages_updated_at ON messages;
        
        CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        CREATE TRIGGER update_messages_updated_at BEFORE UPDATE ON messages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        -- Accorder les permissions à l'utilisateur roxane
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO roxane;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO roxane;
        GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO roxane;
        """
        
        # Exécuter le script
        cursor.execute(create_tables_sql)
        conn.commit()
        
        logger.success("✅ Tables créées avec succès")
        
        # Vérifier les tables créées
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        logger.info(f"📊 Tables créées: {[table[0] for table in tables]}")
        
        # Vérifier les permissions
        cursor.execute("""
            SELECT grantee, privilege_type 
            FROM information_schema.role_table_grants 
            WHERE grantee = 'roxane' AND table_schema = 'public'
            LIMIT 5;
        """)
        
        permissions = cursor.fetchall()
        logger.info(f"🔐 Permissions accordées: {permissions}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création des tables: {e}")
        return False


if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)
