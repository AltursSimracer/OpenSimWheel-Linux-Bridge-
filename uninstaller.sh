#!/usr/bin/env bash
set -e

INSTALL_DIR="$HOME/.local/share/OpenSimWheel"
CONFIG_DIR="$HOME/.config/OpenSimWheel"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
HAS_GUI=false
[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && command -v zenity >/dev/null 2>&1 && HAS_GUI=true

echo "=== Disinstallazione OpenSimWheel Linux Bridge v1.4.0 ==="

# 1. Termina in modo pulito il Core e tutti i satelliti attivi
pkill -15 -f "OpenSimWheel_Linux_Bridge.py" 2>/dev/null || true
pkill -15 -f "_shm_sender.py" 2>/dev/null || true
pkill -15 -f "OpenSimWheel" 2>/dev/null || true
sleep 0.5

# 2. Rimuove cartella programma e TUTTI i collegamenti (menu + desktop, vecchi e nuovi nomi)
rm -rf "$INSTALL_DIR"
rm -f "$APPS_DIR/opensimwheel-linux.desktop" "$APPS_DIR/opensimwheel-bridge.desktop"
rm -f "$DESKTOP_DIR/OpenSimWheel_Linux.desktop" "$DESKTOP_DIR/OpenSimWheel_Bridge.desktop"
update-desktop-database "$APPS_DIR" 2>/dev/null || true

# 3. Gestione pulizia configurazione (--purge da terminale OPPURE domanda grafica)
PURGE=false
if [ "${1:-}" = "--purge" ]; then
    PURGE=true
elif [ "$HAS_GUI" = true ] && [ -d "$CONFIG_DIR" ]; then
    if zenity --question --title="OpenSimWheel Linux Bridge v1.4.0" \
        --text="Vuoi eliminare anche le impostazioni salvate (IP volante, porte, log) in:\n$CONFIG_DIR?\n\n(Scegli 'No' se stai solo reinstallando o aggiornando)" \
        --width=450 2>/dev/null; then
        PURGE=true
    fi
fi

if [ "$PURGE" = true ]; then
    rm -rf "$CONFIG_DIR"
    MSG="Disinstallazione completata!\n\nRimossa anche la configurazione in $CONFIG_DIR."
    echo "[OK] Rimossa anche la configurazione in $CONFIG_DIR."
else
    MSG="Disinstallazione completata!\n\nConfigurazione conservata in $CONFIG_DIR."
    echo "[INFO] Configurazione conservata in $CONFIG_DIR."
fi

echo "[OK] OpenSimWheel Linux Bridge v1.4.0 disinstallato con successo."

if [ "$HAS_GUI" = true ]; then
    zenity --info --title="OpenSimWheel Linux Bridge v1.4.0" \
        --text="$MSG" --width=420 2>/dev/null || true
fi


