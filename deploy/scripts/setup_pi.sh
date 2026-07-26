#!/bin/bash
# Smart Wardrobe - Raspberry Pi Setup Script
# Run as: curl -sSL https://raw.githubusercontent.com/your-repo/smart-wardrobe/main/deploy/scripts/setup_pi.sh | bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Check if running as pi user
if [[ "$USER" != "pi" ]]; then
    log_error "This script must be run as the 'pi' user"
    exit 1
fi

PROJECT_DIR="/home/pi/smart-wardrobe"
VENV_DIR="$PROJECT_DIR/venv"

log_info "Starting Smart Wardrobe Raspberry Pi setup..."

# 1. Update system
log_info "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Install system dependencies
log_info "Installing system dependencies..."
sudo apt install -y \
    python3-venv python3-dev \
    nginx \
    chromium-browser \
    git \
    curl \
    build-essential \
    libopenblas-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    libsqlite3-dev

# 3. Clone repository if not exists
if [[ ! -d "$PROJECT_DIR" ]]; then
    log_info "Cloning repository..."
    git clone https://github.com/your-repo/smart-wardrobe.git "$PROJECT_DIR"
else
    log_info "Repository already exists, pulling latest..."
    cd "$PROJECT_DIR" && git pull
fi

# 4. Create virtual environment
if [[ ! -d "$VENV_DIR" ]]; then
    log_info "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# 5. Install Python dependencies
log_info "Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
"$VENV_DIR/bin/pip" install -e "$PROJECT_DIR[dev]"

# Install PyTorch for ARM64 (Raspberry Pi)
log_info "Installing PyTorch for ARM64..."
"$VENV_DIR/bin/pip" install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 6. Download AI models
log_info "Downloading AI models (this may take a while)..."
cd "$PROJECT_DIR"
"$VENV_DIR/bin/python" -c "
from backend.vision.segmenter import SAMSegmenter
from backend.vision.classifier import CLIPClassifier
segmenter = SAMSegmenter()
classifier = CLIPClassifier()
print('Models downloaded successfully!')
" || log_warn "Model download failed - will retry on first run"

# 7. Initialize database
log_info "Initializing database..."
"$VENV_DIR/bin/python" -c "
from backend.database.connection import init_db
init_db()
print('Database initialized!')
"

# 8. Configure environment
if [[ ! -f "$PROJECT_DIR/.env" ]]; then
    log_info "Creating .env from example..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    log_warn "Please edit $PROJECT_DIR/.env with your configuration"
fi

# 9. Configure systemd service
log_info "Installing systemd service..."
sudo cp "$PROJECT_DIR/deploy/systemd/smart_wardrobe.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable smart-wardrobe

# 10. Configure nginx
log_info "Configuring nginx..."
sudo cp "$PROJECT_DIR/deploy/nginx/smart_wardrobe.conf" /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/smart_wardrobe.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl enable nginx

# 11. Configure Chromium kiosk mode
log_info "Setting up Chromium kiosk mode..."
mkdir -p /home/pi/.config/autostart
cat > /home/pi/.config/autostart/smart-wardrobe-kiosk.desktop << EOF
[Desktop Entry]
Type=Application
Name=Smart Wardrobe Kiosk
Exec=chromium-browser --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble --disable-component-update --disable-background-networking --disable-default-apps --disable-extensions --disable-sync --disable-translate --no-first-run --disable-background-timer-throttling --disable-renderer-backgrounding --disable-device-discovery-notifications http://localhost:8000/kiosk
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF

# 12. Disable screen blanking
log_info "Disabling screen blanking..."
sudo sed -i '/^#\?xserver-command=/a xserver-command=X -s 0 -dpms' /etc/lightdm/lightdm.conf
mkdir -p /home/pi/.config/lxsession/LXDE-pi/
cat > /home/pi/.config/lxsession/LXDE-pi/autostart << EOF
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash
@xset s off
@xset -dpms
@xset s noblank
EOF

# 13. Set up log rotation
log_info "Configuring log rotation..."
sudo tee /etc/logrotate.d/smart-wardrobe > /dev/null << EOF
/home/pi/smart-wardrobe/data/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 pi pi
}
EOF

# 14. Start services
log_info "Starting services..."
sudo systemctl start smart-wardrobe
sudo systemctl start nginx

# Wait for service to be ready
sleep 5

# 15. Verify installation
log_info "Verifying installation..."
if curl -sf http://localhost:8000/health > /dev/null; then
    log_info "✓ Backend is healthy!"
else
    log_warn "Backend health check failed - check logs with: sudo journalctl -u smart-wardrobe -f"
fi

if curl -sf http://localhost/health > /dev/null; then
    log_info "✓ Nginx proxy is working!"
else
    log_warn "Nginx health check failed"
fi

log_info ""
log_info "========================================="
log_info "Smart Wardrobe setup complete!"
log_info "========================================="
log_info ""
log_info "Access the UI at: http://$(hostname -I | awk '{print $1}')"
log_info "Or locally at: http://localhost:8000"
log_info ""
log_info "Useful commands:"
log_info "  View logs:     sudo journalctl -u smart-wardrobe -f"
log_info "  Restart app:   sudo systemctl restart smart-wardrobe"
log_info "  Edit config:   nano $PROJECT_DIR/.env"
log_info ""
log_warn "Remember to:"
log_warn "1. Edit $PROJECT_DIR/.env with your AI provider settings"
log_warn "2. Reboot to test kiosk mode: sudo reboot"
log_warn "3. Configure camera permissions if using Pi Camera"