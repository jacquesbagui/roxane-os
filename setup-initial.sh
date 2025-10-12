#!/bin/bash
###############################################################################
# Roxane OS - Initial Setup (First Boot)
# Ce script est à exécuter après l'installation d'Ubuntu
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Roxane OS - Configuration Initiale${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

echo -e "${BLUE}[1/8] Mise à jour du système...${NC}"
apt update
apt upgrade -y

echo -e "${BLUE}[2/8] Installation outils de base...${NC}"
apt install -y \
    build-essential \
    git \
    curl \
    wget \
    vim \
    htop \
    tree \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

echo -e "${BLUE}[3/8] Installation Python 3.12...${NC}"
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip

# Définir Python 3.12 par défaut
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
update-alternatives --set python3 /usr/bin/python3.12

echo -e "${BLUE}[4/8] Installation PostgreSQL...${NC}"
apt install -y postgresql postgresql-contrib

# Démarrer PostgreSQL
systemctl enable postgresql
systemctl start postgresql

echo -e "${BLUE}[5/8] Installation Redis...${NC}"
apt install -y redis-server

# Configurer Redis
sed -i 's/supervised no/supervised systemd/g' /etc/redis/redis.conf
systemctl enable redis-server
systemctl restart redis-server

echo -e "${BLUE}[6/8] Installation Docker...${NC}"
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER
rm get-docker.sh

echo -e "${BLUE}[7/8] Installation Node.js et npm...${NC}"
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

echo -e "${BLUE}[8/8] Configuration firewall...${NC}"
ufw allow OpenSSH
ufw allow 8000/tcp  # FastAPI
ufw allow 5432/tcp  # PostgreSQL
ufw allow 6379/tcp  # Redis
ufw --force enable

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✅ Configuration terminée !${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

echo "Versions installées :"
echo "  Python: $(python3 --version)"
echo "  PostgreSQL: $(psql --version | head -n1)"
echo "  Redis: $(redis-server --version)"
echo "  Docker: $(docker --version)"
echo "  Node.js: $(node --version)"
echo ""
echo "⚠️  Redémarrez la session pour activer Docker :"
echo "   exit"
echo "   ssh roxane-vm"
echo ""
echo "📝 Prochaine étape : Exécuter install-roxane-os.sh"