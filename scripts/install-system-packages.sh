#!/bin/bash
###############################################################################
# Roxane OS - System Packages Installation
# Install all required system packages
###############################################################################

set -e

echo "Installing system packages..."

# Development tools
apt install -y \
    build-essential \
    cmake \
    pkg-config \
    libtool \
    autoconf \
    automake

# Version control
apt install -y \
    git \
    git-lfs

# Network tools
apt install -y \
    curl \
    wget \
    net-tools \
    iputils-ping \
    dnsutils \
    openssh-server \
    openssh-client

# System utilities
apt install -y \
    htop \
    btop \
    tmux \
    screen \
    tree \
    ncdu \
    vim \
    nano \
    less \
    jq \
    yq \
    ripgrep \
    fd-find \
    bat \
    unzip \
    zip \
    p7zip-full \
    tar \
    gzip \
    bzip2

# System libraries
apt install -y \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Audio libraries (for TTS/STT)
apt install -y \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    sox \
    libsox-fmt-all

# Graphics libraries (for PyQt6)
apt install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    libdbus-1-3

# Python build dependencies
apt install -y \
    libssl-dev \
    libffi-dev \
    libsqlite3-dev \
    libbz2-dev \
    libreadline-dev \
    libncursesw5-dev \
    libxml2-dev \
    libxmlsec1-dev \
    liblzma-dev

# Database client tools
apt install -y \
    postgresql-client \
    redis-tools

# System monitoring
apt install -y \
    sysstat \
    iotop \
    nethogs \
    lm-sensors

# Firewall
apt install -y \
    ufw

echo "✅ System packages installed successfully"