#!/bin/bash
###############################################################################
# Roxane OS - System Customization
# Customize the OS with Roxane branding and utilities
###############################################################################

set -e

echo "Customizing system..."

# 1. Set hostname
hostnamectl set-hostname roxane-os

# 2. Create custom MOTD
cat > /etc/motd << 'EOF'
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

Welcome to Roxane OS!

Quick commands:
  • roxane-start      - Start Roxane services
  • roxane-stop       - Stop Roxane services
  • roxane-status     - Check service status
  • roxane-logs       - View real-time logs
  • roxane-update     - Update Roxane to latest version

Documentation: /opt/roxane/docs/
Support: https://github.com/jacquesbagui/roxane-os

EOF

# 3. Customize bash prompt for roxane user
cat >> /home/roxane/.bashrc << 'EOF'

# Roxane OS Custom Configuration
export PS1="\[\e[38;5;141m\]roxane-os\[\e[0m\]:\[\e[38;5;99m\]\w\[\e[0m\]$ "

# Roxane aliases
alias roxane-start='sudo systemctl start roxane-core roxane-audio'
alias roxane-stop='sudo systemctl stop roxane-core roxane-audio'
alias roxane-restart='sudo systemctl restart roxane-core roxane-audio'
alias roxane-status='sudo systemctl status roxane-*'
alias roxane-logs='sudo journalctl -u roxane-core -f'
alias roxane-logs-audio='sudo journalctl -u roxane-audio -f'
alias roxane-update='cd /opt/roxane && git pull && sudo systemctl restart roxane-*'
alias roxane-backup='sudo systemctl start roxane-backup.service'
alias roxane-config='nano /opt/roxane/.env'

# Environment
export ROXANE_HOME="/opt/roxane"
export PATH="$ROXANE_HOME/.venv/bin:$PATH"

# Welcome message
if [ -f /etc/roxane-version ]; then
    echo ""
    echo "🤖 Roxane OS v$(cat /etc/roxane-version)"
    echo "   Status: $(systemctl is-active roxane-core 2>/dev/null || echo 'inactive')"
    echo ""
fi
EOF

# 4. Create global roxane commands
cat > /usr/local/bin/roxane-start << 'EOF'
#!/bin/bash
echo "🚀 Starting Roxane services..."
systemctl start roxane-core roxane-audio
sleep 2
systemctl status roxane-core --no-pager
EOF
chmod +x /usr/local/bin/roxane-start

cat > /usr/local/bin/roxane-stop << 'EOF'
#!/bin/bash
echo "⏹️  Stopping Roxane services..."
systemctl stop roxane-core roxane-audio roxane-gui
echo "✅ Roxane stopped"
EOF
chmod +x /usr/local/bin/roxane-stop

cat > /usr/local/bin/roxane-status << 'EOF'
#!/bin/bash
echo "📊 Roxane Services Status:"
echo ""
systemctl status roxane-core --no-pager -l
echo ""
systemctl status roxane-audio --no-pager -l
echo ""
systemctl status roxane-gui --no-pager -l 2>/dev/null || echo "GUI: Not configured"
EOF
chmod +x /usr/local/bin/roxane-status

cat > /usr/local/bin/roxane-logs << 'EOF'
#!/bin/bash
echo "📜 Roxane Core Logs (Ctrl+C to exit):"
echo ""
journalctl -u roxane-core -f
EOF
chmod +x /usr/local/bin/roxane-logs

cat > /usr/local/bin/roxane-update << 'EOF'
#!/bin/bash
echo "🔄 Updating Roxane OS..."
cd /opt/roxane
git pull origin main
pip install -r requirements.txt --upgrade
systemctl restart roxane-*
echo "✅ Roxane updated successfully"
EOF
chmod +x /usr/local/bin/roxane-update

# 5. Create version file
echo "1.0.0" > /etc/roxane-version

# 6. Configure firewall
echo "Configuring firewall..."
ufw --force enable
ufw allow ssh
ufw allow 8000/tcp  # FastAPI
ufw status

# 7. Disable unnecessary services
echo "Disabling unnecessary services..."
systemctl disable snapd 2>/dev/null || true
systemctl disable bluetooth 2>/dev/null || true
systemctl disable cups 2>/dev/null || true

# 8. Optimize system for Roxane
cat >> /etc/sysctl.conf << EOF

# Roxane OS Optimizations
vm.swappiness=10
vm.vfs_cache_pressure=50
fs.file-max=2097152
EOF

sysctl -p

# 9. Create roxane sudoers file
cat > /etc/sudoers.d/roxane << EOF
# Roxane user permissions
roxane ALL=(ALL) NOPASSWD: /bin/systemctl start roxane-*
roxane ALL=(ALL) NOPASSWD: /bin/systemctl stop roxane-*
roxane ALL=(ALL) NOPASSWD: /bin/systemctl restart roxane-*
roxane ALL=(ALL) NOPASSWD: /bin/systemctl status roxane-*
roxane ALL=(ALL) NOPASSWD: /bin/journalctl -u roxane-*
EOF
chmod 0440 /etc/sudoers.d/roxane

echo "✅ System customization complete"