#!/bin/bash
###############################################################################
# Roxane OS - Systemd Services Installation
# Install and configure all Roxane systemd services
###############################################################################

set -e

ROXANE_HOME="/opt/roxane"
SYSTEMD_DIR="/etc/systemd/system"

echo "Installing systemd services..."

# 1. Roxane Core Service
cat > "$SYSTEMD_DIR/roxane-core.service" << EOF
[Unit]
Description=Roxane OS - Core Engine
Documentation=https://github.com/jacquesbagui/roxane-os
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=simple
User=roxane
Group=roxane
WorkingDirectory=$ROXANE_HOME
Environment="PATH=$ROXANE_HOME/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$ROXANE_HOME"
EnvironmentFile=$ROXANE_HOME/.env
ExecStart=$ROXANE_HOME/.venv/bin/python -m api.server
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/opt/roxane /var/log/roxane

[Install]
WantedBy=multi-user.target
EOF

# 2. Roxane Audio Service
cat > "$SYSTEMD_DIR/roxane-audio.service" << EOF
[Unit]
Description=Roxane OS - Audio Pipeline
After=roxane-core.service
Requires=roxane-core.service

[Service]
Type=simple
User=roxane
Group=roxane
WorkingDirectory=$ROXANE_HOME
Environment="PATH=$ROXANE_HOME/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$ROXANE_HOME"
EnvironmentFile=$ROXANE_HOME/.env
ExecStart=$ROXANE_HOME/.venv/bin/python -m core.audio.manager
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 3. Roxane GUI Service (si environnement graphique)
cat > "$SYSTEMD_DIR/roxane-gui.service" << EOF
[Unit]
Description=Roxane OS - GUI Interface
After=roxane-core.service graphical.target
Requires=roxane-core.service

[Service]
Type=simple
User=roxane
Group=roxane
WorkingDirectory=$ROXANE_HOME
Environment="DISPLAY=:0"
Environment="PATH=$ROXANE_HOME/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$ROXANE_HOME"
Environment="QT_QPA_PLATFORM=xcb"
EnvironmentFile=$ROXANE_HOME/.env
ExecStart=$ROXANE_HOME/.venv/bin/python gui/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
EOF

# 4. Roxane Database Backup Service (timer)
cat > "$SYSTEMD_DIR/roxane-backup.service" << EOF
[Unit]
Description=Roxane OS - Database Backup
After=postgresql.service

[Service]
Type=oneshot
User=roxane
Group=roxane
WorkingDirectory=$ROXANE_HOME
Environment="PATH=$ROXANE_HOME/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$ROXANE_HOME/scripts/backup.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 5. Roxane Backup Timer (daily at 3am)
cat > "$SYSTEMD_DIR/roxane-backup.timer" << EOF
[Unit]
Description=Roxane OS - Daily Backup Timer
Requires=roxane-backup.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable services (but don't start yet)
systemctl enable roxane-core.service
systemctl enable roxane-audio.service
# systemctl enable roxane-gui.service  # Uncomment if GUI needed
systemctl enable roxane-backup.timer

echo "✅ Systemd services installed"
echo ""
echo "Available services:"
echo "  • roxane-core.service    - Main engine"
echo "  • roxane-audio.service   - Audio pipeline"
echo "  • roxane-gui.service     - GUI interface"
echo "  • roxane-backup.timer    - Daily backup"
echo ""
echo "Use 'roxane-start' to start all services"