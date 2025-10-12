#!/bin/bash
###############################################################################
# Roxane OS - Master Installation Script
# Version: 1.0.0
# Description: Installation automatique complète de Roxane OS
###############################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
ROXANE_VERSION="1.0.0"
ROXANE_HOME="/opt/roxane"
ROXANE_USER="roxane"
ROXANE_REPO="https://github.com/jacquesbagui/roxane-os.git"
LOG_FILE="/var/log/roxane-install.log"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

# Header
clear
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██████╗  ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗███████╗   ║
║   ██╔══██╗██╔═══██╗╚██╗██╔╝██╔══██╗████╗  ██║██╔════╝   ║
║   ██████╔╝██║   ██║ ╚███╔╝ ███████║██╔██╗ ██║█████╗     ║
║   ██╔══██╗██║   ██║ ██╔██╗ ██╔══██║██║╚██╗██║██╔══╝     ║
║   ██║  ██║╚██████╔╝██╔╝ ██╗██║  ██║██║ ╚████║███████╗   ║
║   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝   ║
║                                                           ║
║              AI-Powered Personal Assistant OS             ║
║                    Version 1.0.0                          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF

echo ""
log "${PURPLE}Starting Roxane OS installation...${NC}"
echo ""

# Create log file
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

# Check Ubuntu version
if ! grep -q "Ubuntu 25.10" /etc/os-release; then
    log_warning "This script is designed for Ubuntu 25.10 LTS"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Installation steps
TOTAL_STEPS=12
CURRENT_STEP=0

step() {
    CURRENT_STEP=$((CURRENT_STEP + 1))
    echo ""
    log "${CYAN}[Step $CURRENT_STEP/$TOTAL_STEPS] $1${NC}"
    echo ""
}

# Step 1: System Update
step "Updating system packages"
apt update && apt upgrade -y
log_success "System updated"

# Step 2: Install system packages
step "Installing system packages"
bash "$(dirname "$0")/scripts/install-system-packages.sh"
log_success "System packages installed"

# Step 3: Install Python 3.12
step "Installing Python 3.12"
bash "$(dirname "$0")/scripts/install-python.sh"
log_success "Python 3.12 installed"

# Step 4: Install PostgreSQL
step "Installing PostgreSQL + pgvector"
bash "$(dirname "$0")/scripts/install-postgresql.sh"
log_success "PostgreSQL installed"

# Step 5: Install Redis
step "Installing Redis"
bash "$(dirname "$0")/scripts/install-redis.sh"
log_success "Redis installed"

# Step 6: Install Docker
step "Installing Docker"
bash "$(dirname "$0")/scripts/install-docker.sh"
log_success "Docker installed"

# Step 7: Setup Roxane user and directories
step "Setting up Roxane user and directories"
if ! id "$ROXANE_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$ROXANE_USER"
    log_success "User $ROXANE_USER created"
else
    log_warning "User $ROXANE_USER already exists"
fi

mkdir -p "$ROXANE_HOME"
chown -R "$ROXANE_USER:$ROXANE_USER" "$ROXANE_HOME"
log_success "Directories created"

# Step 8: Clone Roxane repository
step "Cloning Roxane repository"
if [ -d "$ROXANE_HOME/.git" ]; then
    log_warning "Repository already exists, pulling latest changes"
    cd "$ROXANE_HOME" && sudo -u "$ROXANE_USER" git pull
else
    sudo -u "$ROXANE_USER" git clone "$ROXANE_REPO" "$ROXANE_HOME"
fi
log_success "Repository cloned"

# Step 9: Install Roxane Core
step "Installing Roxane Core"
bash "$(dirname "$0")/scripts/install-roxane-core.sh"
log_success "Roxane Core installed"

# Step 10: Download AI models
step "Downloading AI models (this may take a while...)"
bash "$(dirname "$0")/scripts/download-models.sh"
log_success "AI models downloaded"

# Step 11: Install systemd services
step "Installing systemd services"
bash "$(dirname "$0")/scripts/install-services.sh"
log_success "Services installed"

# Step 12: Final configuration
step "Applying final configuration"
bash "$(dirname "$0")/scripts/customize-system.sh"
bash "$(dirname "$0")/scripts/final-setup.sh"
log_success "Configuration complete"

# Installation complete
echo ""
echo ""
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              ✅ Installation Complete! ✅                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo ""

log_success "Roxane OS v$ROXANE_VERSION installed successfully!"
echo ""
echo "📝 Installation log: $LOG_FILE"
echo ""
echo "🚀 Available commands:"
echo "   • roxane-start      - Start Roxane services"
echo "   • roxane-stop       - Stop Roxane services"
echo "   • roxane-status     - Check service status"
echo "   • roxane-logs       - View real-time logs"
echo "   • roxane-update     - Update Roxane"
echo ""
echo "🔄 System will reboot in 10 seconds..."
echo "   Press Ctrl+C to cancel"
echo ""

sleep 10
reboot