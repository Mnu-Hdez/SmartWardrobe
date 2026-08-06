#!/bin/bash
# Smart Wardrobe - Kiosk Mode Startup Script
# Used by systemd or autostart to launch Chromium in kiosk mode

# Wait for network and backend to be ready
until curl -sf http://localhost:7000/health > /dev/null; do
    sleep 2
done

# Additional wait for full backend initialization
sleep 3

# Launch Chromium in kiosk mode
exec chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-component-update \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions \
    --disable-sync \
    --disable-translate \
    --no-first-run \
    --disable-background-timer-throttling \
    --disable-renderer-backgrounding \
    --disable-device-discovery-notifications \
    --disable-features=TranslateUI \
    --hide-scrollbars \
    --force-device-scale-factor=1 \
    --start-fullscreen \
    http://localhost:7000"