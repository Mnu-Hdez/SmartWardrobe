#!/bin/bash
# Smart Wardrobe - Raspberry Pi Deployment Script
# Installs systemd service, nginx, chromium kiosk mode

set -e

echo "=== Smart Wardrobe Pi Setup ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Variables
APP_DIR="/opt/smart-wardrobe"
SERVICE_USER="wardrobe"
DOMAIN="${1:-localhost}"

# Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y \
    docker.io \
    docker-compose \
    nginx \
    chromium-browser \
    xserver-xorg \
    xinit \
    x11-xserver-utils \
    unclutter \
    curl

# Create service user
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$APP_DIR" "$SERVICE_USER"
fi

# Create app directory
mkdir -p "$APP_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"

# Clone or copy project (assumes you've copied files to $APP_DIR)
echo "Setting up project in $APP_DIR..."
# In practice, you'd git clone or scp your project here

# Build and start containers
cd "$APP_DIR"
docker-compose --profile prod up -d --build

# Configure nginx
echo "Configuring nginx..."
cat > /etc/nginx/sites-available/smart-wardrobe << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:7000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/smart-wardrobe /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Create systemd service for kiosk mode
echo "Creating kiosk systemd service..."
cat > /etc/systemd/system/smart-wardrobe-kiosk.service << 'EOF'
[Unit]
Description=Smart Wardrobe Kiosk
After=graphical.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=wardrobe
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/wardrobe/.Xauthority
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-translate \
    --no-first-run \
    --fast \
    --fast-start \
    --disable-features=TranslateUI \
    --disable-ipc-flooding-protection \
    --password-store=basic \
    --use-gl=egl \
    http://localhost:7000/kiosk
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

# Configure auto-login for wardrobe user
mkdir -p /etc/systemd/system/getty@tty1.service.d/
cat > /etc/systemd/system/getty@tty1.service.d/override.conf << 'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin wardrobe --noclear %I $TERM
EOF

# Enable services
systemctl daemon-reload
systemctl enable nginx
systemctl enable smart-wardrobe-kiosk

# Configure X11 for kiosk
cat > /home/wardrobe/.xinitrc << 'EOF'
#!/bin/bash
xset s off
xset -dpms
xset s noblank
unclutter -idle 0.5 -root &
exec chromium-browser --kiosk http://localhost:7000/kiosk
EOF
chown wardrobe:wardrobe /home/wardrobe/.xinitrc
chmod +x /home/wardrobe/.xinitrc

# Create .Xauthority
touch /home/wardrobe/.Xauthority
chown wardrobe:wardrobe /home/wardrobe/.Xauthority

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Copy your project files to $APP_DIR"
echo "2. Run: cd $APP_DIR && docker-compose --profile prod up -d --build"
echo "3. Reboot to start kiosk mode: reboot"
echo ""
echo "To enable Let's Encrypt SSL:"
echo "  certbot --nginx -d your-domain.com"
echo ""
echo "Kiosk will auto-start on boot at http://localhost:7000/kiosk"