#!/bin/bash
###############################################################################
# Roxane OS - Redis Installation
###############################################################################

set -e

echo "Installing Redis..."

# Install Redis
apt install -y redis-server redis-tools

# Configure Redis
REDIS_CONF="/etc/redis/redis.conf"
cp "$REDIS_CONF" "$REDIS_CONF.backup"

# Configure Redis for Roxane
sed -i 's/supervised no/supervised systemd/g' "$REDIS_CONF"
sed -i 's/# maxmemory <bytes>/maxmemory 2gb/g' "$REDIS_CONF"
sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/g' "$REDIS_CONF"

# Enable persistence
sed -i 's/save ""/# save ""/g' "$REDIS_CONF"
echo 'save 900 1' >> "$REDIS_CONF"
echo 'save 300 10' >> "$REDIS_CONF"
echo 'save 60 10000' >> "$REDIS_CONF"

# Start and enable Redis
systemctl enable redis-server
systemctl restart redis-server

# Wait for Redis to be ready
sleep 2

# Test Redis connection
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis installed and running successfully"
else
    echo "❌ Redis installation failed"
    exit 1
fi

echo "   Redis is listening on: 127.0.0.1:6379"