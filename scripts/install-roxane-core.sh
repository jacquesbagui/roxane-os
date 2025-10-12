#!/bin/bash
###############################################################################
# Roxane OS - Core Installation
# Install Python dependencies and setup Roxane Core
###############################################################################

set -e

ROXANE_HOME="/opt/roxane"
ROXANE_USER="roxane"

echo "Installing Roxane Core..."

cd "$ROXANE_HOME"

# Create virtual environment
echo "Creating Python virtual environment..."
sudo -u "$ROXANE_USER" python3 -m venv .venv

# Activate venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install core dependencies
echo "Installing Python dependencies..."

# FastAPI and server
pip install \
    fastapi==0.109.0 \
    uvicorn[standard]==0.27.0 \
    websockets==12.0 \
    python-multipart==0.0.6

# Database
pip install \
    psycopg[binary]==3.1.18 \
    psycopg[pool]==3.1.18 \
    redis==5.0.1 \
    sqlalchemy==2.0.25

# AI/ML Libraries
pip install \
    torch==2.1.0 \
    transformers==4.36.0 \
    sentence-transformers==2.3.1 \
    accelerate==0.25.0 \
    bitsandbytes==0.41.3

# Audio processing
pip install \
    sounddevice==0.4.6 \
    soundfile==0.12.1 \
    librosa==0.10.1 \
    pyaudio==0.2.14 \
    faster-whisper==0.10.0 \
    TTS==0.22.0 \
    silero-vad==4.0.0

# PyQt6 for GUI
pip install \
    PyQt6==6.6.1 \
    PyQt6-WebEngine==6.6.0

# Web scraping
pip install \
    playwright==1.41.0 \
    beautifulsoup4==4.12.3 \
    lxml==5.1.0 \
    requests==2.31.0 \
    aiohttp==3.9.1

# Utilities
pip install \
    python-dotenv==1.0.0 \
    pydantic==2.5.3 \
    pydantic-settings==2.1.0 \
    loguru==0.7.2 \
    rich==13.7.0 \
    typer==0.9.0 \
    pyyaml==6.0.1

# Development tools
pip install \
    pytest==7.4.4 \
    pytest-asyncio==0.21.1 \
    black==23.12.1 \
    ruff==0.1.11 \
    mypy==1.8.0

# Install Playwright browsers
playwright install chromium

# Create .env file
cat > "$ROXANE_HOME/.env" << EOF
# Roxane OS Configuration
ROXANE_ENV=production
ROXANE_VERSION=1.0.0

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=roxane_db
POSTGRES_USER=roxane
POSTGRES_PASSWORD=roxane_secure_pass_2025

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Models
MODELS_DIR=/opt/roxane/data/models
CACHE_DIR=/opt/roxane/data/cache

# API
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/roxane/roxane.log

# Audio
AUDIO_INPUT_DEVICE=default
AUDIO_OUTPUT_DEVICE=default
EOF

# Create logs directory
mkdir -p /var/log/roxane
chown -R "$ROXANE_USER:$ROXANE_USER" /var/log/roxane

# Set permissions
chown -R "$ROXANE_USER:$ROXANE_USER" "$ROXANE_HOME"

echo "✅ Roxane Core installed successfully"
echo ""
echo "Virtual environment: $ROXANE_HOME/.venv"
echo "Configuration: $ROXANE_HOME/.env"