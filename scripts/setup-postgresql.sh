#!/bin/bash
# Roxane OS - PostgreSQL Setup Script
# Configure PostgreSQL pour Roxane OS

set -e

echo "🐘 Setting up PostgreSQL for Roxane OS..."

# Configuration
DB_NAME="roxane_db"
DB_USER="roxane"
DB_PASSWORD="roxane_secure_pass_2025"
DB_HOST="localhost"
DB_PORT="5432"
POSTGRES_PASSWORD="postgres"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérifier si PostgreSQL est installé
check_postgresql() {
    if ! command -v psql &> /dev/null; then
        log_error "PostgreSQL n'est pas installé"
        echo "Installez PostgreSQL avec:"
        echo "  macOS: brew install postgresql"
        echo "  Ubuntu: sudo apt-get install postgresql postgresql-contrib"
        echo "  CentOS: sudo yum install postgresql-server postgresql-contrib"
        exit 1
    fi
    
    log_info "PostgreSQL est installé"
}

# Vérifier si le service PostgreSQL est démarré
check_postgresql_service() {
    if ! pg_isready -h $DB_HOST -p $DB_PORT &> /dev/null; then
        log_warn "Service PostgreSQL n'est pas démarré"
        echo "Démarrez PostgreSQL avec:"
        echo "  macOS: brew services start postgresql"
        echo "  Ubuntu: sudo systemctl start postgresql"
        echo "  CentOS: sudo systemctl start postgresql"
        exit 1
    fi
    
    log_info "Service PostgreSQL est démarré"
}

# Créer la base de données
create_database() {
    log_info "Création de la base de données $DB_NAME..."
    
    # Vérifier si la base existe déjà
    if psql -h $DB_HOST -p $DB_PORT -U postgres -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
        log_warn "Base de données $DB_NAME existe déjà"
    else
        # Créer la base de données
        run_psql "CREATE DATABASE $DB_NAME;"
        log_info "Base de données $DB_NAME créée"
    fi
}

# Créer l'utilisateur
create_user() {
    log_info "Création de l'utilisateur $DB_USER..."
    
    # Vérifier si l'utilisateur existe déjà
    if psql -h $DB_HOST -p $DB_PORT -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
        log_warn "Utilisateur $DB_USER existe déjà"
    else
        # Créer l'utilisateur
        run_psql "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
        log_info "Utilisateur $DB_USER créé"
    fi
    
    # Accorder les privilèges
    run_psql "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    run_psql "ALTER USER $DB_USER CREATEDB;"
    run_psql "GRANT CREATE ON SCHEMA public TO $DB_USER;"
    run_psql "GRANT USAGE ON SCHEMA public TO $DB_USER;"
    run_psql "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;"
    run_psql "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;"
    log_info "Privilèges accordés à $DB_USER"
}

# Créer les extensions nécessaires
create_extensions() {
    log_info "Création des extensions PostgreSQL..."
    
    # Se connecter à la base de données et créer les extensions
    run_psql_db "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
    run_psql_db "CREATE EXTENSION IF NOT EXISTS \"pg_trgm\";"
    run_psql_db "CREATE EXTENSION IF NOT EXISTS \"btree_gin\";"
    
    log_info "Extensions créées"
}

# Tester la connexion
test_connection() {
    log_info "Test de la connexion..."
    
    if PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1;" &> /dev/null; then
        log_info "Connexion réussie"
    else
        log_error "Échec de la connexion"
        exit 1
    fi
}

# Créer les tables
create_tables() {
    log_info "Création des tables..."
    
    # Créer un script SQL temporaire
    cat > /tmp/create_tables.sql << 'EOF'
-- Tables pour Roxane OS
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    preferences JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    summary TEXT,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    intent VARCHAR(100),
    intent_confidence FLOAT,
    entities JSONB DEFAULT '{}',
    response_text TEXT,
    response_confidence FLOAT,
    tokens_used INTEGER,
    latency FLOAT,
    embedding BYTEA,
    metadata JSONB DEFAULT '{}'
);

-- Indexes pour les performances
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
CREATE INDEX IF NOT EXISTS idx_messages_intent ON messages(intent);

-- Index GIN pour la recherche textuelle
CREATE INDEX IF NOT EXISTS idx_messages_content_gin ON messages USING gin(to_tsvector('french', content));
CREATE INDEX IF NOT EXISTS idx_messages_entities_gin ON messages USING gin(entities);

-- Fonction pour mettre à jour updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers pour updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EOF
    
    # Exécuter le script
    PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f /tmp/create_tables.sql
    
    # Nettoyer
    rm /tmp/create_tables.sql
    
    log_info "Tables créées"
}

# Corriger les privilèges pour un utilisateur existant
fix_permissions() {
    log_info "Correction des privilèges pour l'utilisateur $DB_USER..."
    
    run_psql "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    run_psql "GRANT CREATE ON SCHEMA public TO $DB_USER;"
    run_psql "GRANT USAGE ON SCHEMA public TO $DB_USER;"
    run_psql "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;"
    run_psql "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;"
    
    # Accorder les privilèges sur les tables existantes
    run_psql_db "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;"
    run_psql_db "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;"
    
    log_info "Privilèges corrigés"
}

# Fonction principale
main() {
    log_info "Configuration de PostgreSQL pour Roxane OS"
    
    check_postgresql
    check_postgresql_service
    create_database
    create_user
    create_extensions
    test_connection
    create_tables
    
    log_info "✅ Configuration PostgreSQL terminée"
    
    echo ""
    echo "Configuration de connexion:"
    echo "  Host: $DB_HOST"
    echo "  Port: $DB_PORT"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo "  Password: $DB_PASSWORD"
    echo ""
    echo "URL de connexion:"
    echo "  postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
}

# Fonction pour corriger les permissions seulement
fix_permissions_only() {
    log_info "Correction des permissions PostgreSQL pour Roxane OS"
    
    check_postgresql
    check_postgresql_service
    fix_permissions
    test_connection
    
    log_info "✅ Permissions corrigées"
}

# Fonction pour afficher l'aide
show_help() {
    echo "Usage: $0 [OPTIONS] [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  setup          Configuration complète (défaut)"
    echo "  fix-permissions Correction des permissions seulement"
    echo "  help           Afficher cette aide"
    echo ""
    echo "Options:"
    echo "  -p PASSWORD    Mot de passe pour l'utilisateur postgres"
    echo "  -h             Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0                                    # Configuration complète"
    echo "  $0 fix-permissions                   # Corriger les permissions"
    echo "  $0 -p monmotdepasse setup            # Avec mot de passe postgres"
}

# Parser les arguments
while getopts "p:h" opt; do
    case $opt in
        p)
            POSTGRES_PASSWORD="$OPTARG"
            ;;
        h)
            show_help
            exit 0
            ;;
        \?)
            echo "Option invalide: -$OPTARG" >&2
            show_help
            exit 1
            ;;
    esac
done

shift $((OPTIND-1))

# Fonction pour exécuter psql avec mot de passe
run_psql() {
    local sql="$1"
    if [ -n "$POSTGRES_PASSWORD" ]; then
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h $DB_HOST -p $DB_PORT -U postgres -c "$sql"
    else
        psql -h $DB_HOST -p $DB_PORT -U postgres -c "$sql"
    fi
}

run_psql_db() {
    local sql="$1"
    if [ -n "$POSTGRES_PASSWORD" ]; then
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h $DB_HOST -p $DB_PORT -U postgres -d $DB_NAME -c "$sql"
    else
        psql -h $DB_HOST -p $DB_PORT -U postgres -d $DB_NAME -c "$sql"
    fi
}

# Exécuter selon la commande
case "${1:-setup}" in
    "setup")
        main
        ;;
    "fix-permissions")
        fix_permissions_only
        ;;
    "help")
        show_help
        ;;
    *)
        echo "Commande inconnue: $1"
        show_help
        exit 1
        ;;
esac
