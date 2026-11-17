#!/usr/bin/env bash
set -e
INSTALL_DIR="$HOME/.local/share/OpenSimWheel"
CONFIG_DIR="$HOME/.config/OpenSimWheel"
APPS_DIR="$HOME/.local/share/applications"

echo "=== Disinstallazione OpenSimWheel Linux Bridge v1.3.0 ==="

pkill -15 -f "OpenSimWheel_Linux_Bridge.py" 2>/dev/null || true
pkill -15 -f "_shm_sender.py" 2>/dev/null || true

rm -rf "$INSTALL_DIR"
rm -f "$APPS_DIR/opensimwheel-bridge.desktop"
update-desktop-database "$APPS_DIR" 2>/dev/null || true

if [ "$1" = "--purge" ]; then
    rm -rf "$CONFIG_DIR"
    echo "[OK] Rimossa anche la configurazione in $CONFIG_DIR."
else
    echo "[INFO] Configurazione conservata in $CONFIG_DIR (usa --purge per rimuoverla)."
fi

echo "[OK] OpenSimWheel Linux Bridge v1.3.0 disinstallato con successo."
