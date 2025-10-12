#!/bin/bash
###############################################################################
# Roxane OS - Docker Installation
###############################################################################

set -e

echo "Installing Docker..."

# Remove old versions
apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Install Docker using official script
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sh /tmp/get-docker.sh
rm /tmp/get-docker.sh

# Install Docker Compose
DOCKER_COMPOSE_VERSION="2.24.0"
curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Add roxane user to docker group
usermod -aG docker roxane

# Enable and start Docker
systemctl enable docker
systemctl start docker

# Wait for Docker to be ready
sleep 3

# Test Docker installation
if docker run --rm hello-world &>/dev/null; then
    echo "✅ Docker installed successfully"
else
    echo "⚠️  Docker installed but test failed (may need reboot)"
fi

# Show versions
echo ""
echo "Docker version:"
docker --version

echo "Docker Compose version:"
docker-compose --version

echo ""
echo "⚠️  Note: User 'roxane' needs to logout/login for Docker group permissions"