#!/bin/bash
###############################################################################
# Roxane OS - Final Setup
# Final configuration and checks
###############################################################################

set -e

echo "Performing final setup..."

ROXANE_HOME="/opt/roxane"

# 1. Create backup script
mkdir -p "$ROXANE_HOME/scripts"
cat > "$ROXANE_HOME/scripts/backup.sh" << 'EOF'
#!/bin/bash
###############################################################################
# Roxane OS - Backup Script
###############################################################################

BACKUP_DIR="/opt/roxane/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/roxane_backup_$TIMESTAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "🔄 Creating backup..."

# Backup database
sudo -u postgres pg_dump roxane_db > /tmp/roxane_db_$TIMESTAMP.sql

# Create backup archive
tar -czf "$BACKUP_FILE" \
    /tmp/roxane_db_$TIMESTAMP.sql \
    /opt/roxane/.env \
    /opt/roxane/data/lora \
    /opt/roxane/config

rm /tmp/roxane_db_$TIMESTAMP.sql

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/roxane_backup_*.tar.gz | tail -n +8 | xargs -r rm

echo "✅ Backup created: $BACKUP_FILE"
EOF
chmod +x "$ROXANE_HOME/scripts/backup.sh"

# 2. Create restore script
cat > "$ROXANE_HOME/scripts/restore.sh" << 'EOF'
#!/bin/bash
###############################################################################
# Roxane OS - Restore Script
###############################################################################

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "🔄 Restoring from backup..."

# Stop services
systemctl stop roxane-*

# Extract backup
tar -xzf "$BACKUP_FILE" -C /tmp

# Restore database
sudo -u postgres psql roxane_db < /tmp/tmp/roxane_db_*.sql

# Restore files
cp /tmp/opt/roxane/.env /opt/roxane/.env
cp -r /tmp/opt/roxane/data/lora/* /opt/roxane/data/lora/ 2>/dev/null || true
cp -r /tmp/opt/roxane/config/* /opt/roxane/config/ 2>/dev/null || true

# Cleanup
rm -rf /tmp/tmp /tmp/opt

# Restart services
systemctl start roxane-*

echo "✅ Restore complete"
EOF
chmod +x "$ROXANE_HOME/scripts/restore.sh"

# 3. Create update script
cat > "$ROXANE_HOME/scripts/update.sh" << 'EOF'
#!/bin/bash
###############################################################################
# Roxane OS - Update Script
###############################################################################

set -e

echo "🔄 Updating Roxane OS..."

cd /opt/roxane

# Backup current version
./scripts/backup.sh

# Stop services
systemctl stop roxane-*

# Pull latest code
git pull origin main

# Update dependencies
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --upgrade

# Run migrations if any
python -m scripts.migrate_db

# Restart services
systemctl start roxane-*

echo "✅ Roxane OS updated successfully"
systemctl status roxane-core --no-pager
EOF
chmod +x "$ROXANE_HOME/scripts/update.sh"

# 4. Create system check script
cat > "$ROXANE_HOME/scripts/check-system.sh" << 'EOF'
#!/bin/bash
###############################################################################
# Roxane OS - System Check
###############################################################################

echo "╔═══════════════════════════════════════╗"
echo "║   Roxane OS - System Check           ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# Check services
echo "📊 Services Status:"
for service in roxane-core roxane-audio roxane-gui; do
    status=$(systemctl is-active $service 2>/dev/null || echo "inactive")
    if [ "$status" = "active" ]; then
        echo "  ✅ $service: $status"
    else
        echo "  ❌ $service: $status"
    fi
done
echo ""

# Check Python
echo "🐍 Python:"
python3 --version
echo ""

# Check PostgreSQL
echo "🗄️  PostgreSQL:"
if systemctl is-active postgresql &>/dev/null; then
    echo "  ✅ Running"
    psql -U roxane -d roxane_db -h localhost -c "SELECT version();" 2>/dev/null | head -3
else
    echo "  ❌ Not running"
fi
echo ""

# Check Redis
echo "📦 Redis:"
if systemctl is-active redis-server &>/dev/null; then
    echo "  ✅ Running"
    redis-cli ping 2>/dev/null || echo "  ⚠️  Not responding"
else
    echo "  ❌ Not running"
fi
echo ""

# Check Docker
echo "🐳 Docker:"
if systemctl is-active docker &>/dev/null; then
    echo "  ✅ Running"
    docker --version
else
    echo "  ❌ Not running"
fi
echo ""

# Check disk space
echo "💾 Disk Space:"
df -h / | tail -1 | awk '{print "  Used: "$3" / "$2" ("$5")"}'
echo ""

# Check memory
echo "🧠 Memory:"
free -h | grep Mem | awk '{print "  Used: "$3" / "$2}'
echo ""

# Check models
echo "🤖 AI Models:"
if [ -d "/opt/roxane/data/models" ]; then
    model_count=$(find /opt/roxane/data/models -maxdepth 1 -type d | wc -l)
    echo "  📁 $((model_count - 1)) models installed"
    du -sh /opt/roxane/data/models | awk '{print "  💿 Size: "$1}'
else
    echo "  ❌ Models directory not found"
fi
echo ""

# Check logs
echo "📜 Recent Errors:"
journalctl -u roxane-core --since "1 hour ago" -p err --no-pager | tail -5 || echo "  ✅ No errors"
echo ""

echo "╔═══════════════════════════════════════╗"
echo "║   Check Complete                     ║"
echo "╚═══════════════════════════════════════╝"
EOF
chmod +x "$ROXANE_HOME/scripts/check-system.sh"

# 5. Create requirements.txt
cat > "$ROXANE_HOME/requirements.txt" << 'EOF'
# Roxane OS - Python Dependencies
# Core
fastapi==0.109.0
uvicorn[standard]==0.27.0
websockets==12.0
python-multipart==0.0.6

# Database
psycopg[binary]==3.1.18
redis==5.0.1
sqlalchemy==2.0.25

# AI/ML
torch==2.1.0
transformers==4.36.0
sentence-transformers==2.3.1
accelerate==0.25.0

# Audio
sounddevice==0.4.6
soundfile==0.12.1
librosa==0.10.1
faster-whisper==0.10.0
TTS==0.22.0

# GUI
PyQt6==6.6.1
PyQt6-WebEngine==6.6.0

# Web
playwright==1.41.0
beautifulsoup4==4.12.3
requests==2.31.0
aiohttp==3.9.1

# Utils
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0
loguru==0.7.2
rich==13.7.0
typer==0.9.0
pyyaml==6.0.1
EOF

# 6. Set all permissions
chown -R roxane:roxane "$ROXANE_HOME"
chmod +x "$ROXANE_HOME/scripts"/*.sh

# 7. Create initial configuration
mkdir -p "$ROXANE_HOME/config"
cat > "$ROXANE_HOME/config/system.yaml" << 'EOF'
# Roxane OS System Configuration

system:
  version: "1.0.0"
  environment: "production"
  log_level: "INFO"
  
models:
  llm:
    name: "TinyLlama-1.1B-Chat-v1.0"
    max_length: 2048
    temperature: 0.7
    top_p: 0.9
  
  embeddings:
    name: "bge-large-en-v1.5"
    dimension: 1024
  
  stt:
    name: "whisper-large-v3"
    language: "fr"
  
  tts:
    name: "xtts-v2"
    language: "fr"
    speed: 1.0

audio:
  vad_threshold: 0.5
  sample_rate: 16000
  
memory:
  short_term_limit: 20
  vector_search_limit: 10
  
permissions:
  level: 2
  require_confirmation: true

gui:
  theme: "dark"
  font_size: 12
EOF

# 8. Create documentation directory
mkdir -p "$ROXANE_HOME/docs"
cat > "$ROXANE_HOME/docs/README.md" << 'EOF'
# Roxane OS Documentation

Welcome to Roxane OS!

## Quick Start

### Starting Roxane
```bash
roxane-start
```

### Checking Status
```bash
roxane-status
```

### Viewing Logs
```bash
roxane-logs
```

### Updating
```bash
roxane-update
```

## Configuration

Edit `/opt/roxane/.env` to configure Roxane.

## Backup & Restore

### Create Backup
```bash
roxane-backup
```

### Restore Backup
```bash
/opt/roxane/scripts/restore.sh /path/to/backup.tar.gz
```

## Troubleshooting

### Check System
```bash
/opt/roxane/scripts/check-system.sh
```

### Reset Roxane
```bash
roxane-stop
cd /opt/roxane
git reset --hard origin/main
roxane-start
```

For more help, visit: https://github.com/jacquesbagui/roxane-os
EOF

# 9. Run system check
echo ""
echo "Running final system check..."
bash "$ROXANE_HOME/scripts/check-system.sh"

echo ""
echo "✅ Final setup complete!"