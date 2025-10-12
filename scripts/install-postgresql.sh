#!/bin/bash
###############################################################################
# Roxane OS - PostgreSQL Installation with pgvector
###############################################################################

set -e

echo "Installing PostgreSQL..."

# Install PostgreSQL 15
apt install -y postgresql-15 postgresql-contrib-15 postgresql-server-dev-15

# Start and enable PostgreSQL
systemctl enable postgresql
systemctl start postgresql

# Wait for PostgreSQL to be ready
sleep 5

echo "Installing pgvector extension..."

# Install dependencies for pgvector
apt install -y git build-essential

# Clone and build pgvector
cd /tmp
rm -rf pgvector
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install

# Create Roxane database and user
sudo -u postgres psql << EOF
-- Create user
CREATE USER roxane WITH PASSWORD 'roxane_secure_pass_2025';

-- Create database
CREATE DATABASE roxane_db OWNER roxane;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE roxane_db TO roxane;
ALTER USER roxane CREATEDB;

-- Connect to roxane_db and create extension
\c roxane_db
CREATE EXTENSION IF NOT EXISTS vector;

-- Create tables
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    user_message TEXT,
    roxane_response TEXT,
    actions JSONB,
    context JSONB,
    embedding vector(1024)
);

CREATE TABLE IF NOT EXISTS preferences (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    action_type VARCHAR(100),
    command TEXT,
    output TEXT,
    status VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding vector(1024),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX ON conversations USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON knowledge_base USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON conversations(timestamp);
CREATE INDEX ON system_logs(timestamp);

-- Grant permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO roxane;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO roxane;

\q
EOF

# Configure PostgreSQL for remote connections (if needed)
PG_CONF="/etc/postgresql/15/main/postgresql.conf"
PG_HBA="/etc/postgresql/15/main/pg_hba.conf"

# Backup original configs
cp "$PG_CONF" "$PG_CONF.backup"
cp "$PG_HBA" "$PG_HBA.backup"

# Allow connections from localhost
echo "host    roxane_db    roxane    127.0.0.1/32    md5" >> "$PG_HBA"
echo "host    roxane_db    roxane    ::1/128         md5" >> "$PG_HBA"

# Restart PostgreSQL
systemctl restart postgresql

echo "✅ PostgreSQL with pgvector installed successfully"
echo "   Database: roxane_db"
echo "   User: roxane"
echo "   Password: roxane_secure_pass_2025"