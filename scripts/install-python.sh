#!/bin/bash
###############################################################################
# Roxane OS - Python 3.12 Installation
###############################################################################

set -e

echo "Installing Python 3.12..."

# Add deadsnakes PPA for Python 3.12
add-apt-repository ppa:deadsnakes/ppa -y
apt update

# Install Python 3.12 and tools
apt install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3.12-distutils \
    python3-pip \
    python3-setuptools \
    python3-wheel

# Set Python 3.12 as default
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
update-alternatives --set python3 /usr/bin/python3.12

# Create symlink for python
ln -sf /usr/bin/python3.12 /usr/bin/python

# Upgrade pip
python3 -m pip install --upgrade pip setuptools wheel

# Install Poetry (dependency manager)
curl -sSL https://install.python-poetry.org | python3 -
ln -sf /root/.local/bin/poetry /usr/local/bin/poetry

# Verify installation
echo ""
echo "Python version:"
python3 --version

echo "Pip version:"
pip3 --version

echo "Poetry version:"
poetry --version

echo "✅ Python 3.12 installed successfully"