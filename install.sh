#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "core" ]; then
    ROOT_DIR="$(dirname "$SCRIPT_DIR")"
else
    ROOT_DIR="$SCRIPT_DIR"
fi

INSTALL_DIR="$HOME/.local/share/OpenSimWheel"
CONFIG_DIR="$HOME/.config/OpenSimWheel"
APPS_DIR="$HOME/.local/share/applications"

SCELTE=""
if command -v zenity >/dev/null 2>&1; then
    SCELTE=$(zenity --list --checklist \
        --title="Installazione OpenSimWheel Linux Bridge v1.3.0" \
        --text="Seleziona i simulatori da configurare automaticamente (Proton / Plugin):" \
        --column="Attiva" --column="ID" --column="Simulatore" \
        FALSE "LMU" "Le Mans Ultimate (Plugin rF2 Shared Memory)" \
        FALSE "ACC" "Assetto Corsa Competizione (Steam Proton)" \
        FALSE "AC"  "Assetto Corsa (Steam Proton)" \
        FALSE "ACE" "Assetto Corsa EVO (Steam Proton)" \
        FALSE "RRRE" "RaceRoom Racing Experience (Steam Proton)" \
        --hide-column=2 --separator="|" --width=520 --height=320 2>/dev/null || exit 0)
fi

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$APPS_DIR"

cp -f "$ROOT_DIR"/core/*.py "$INSTALL_DIR/"
cp -f "$ROOT_DIR"/core/*.html "$INSTALL_DIR/"
cp -f "$ROOT_DIR"/core/zenity_simracing.png "$INSTALL_DIR/"
cp -f "$ROOT_DIR"/core/uninstaller.sh "$INSTALL_DIR/"
cp -f "$ROOT_DIR"/setup_*.sh "$INSTALL_DIR/"

if [ ! -f "$INSTALL_DIR/config.ini" ] && [ -f "$ROOT_DIR/core/config.ini" ]; then
    cp -f "$ROOT_DIR/core/config.ini" "$INSTALL_DIR/config.ini"
fi

chmod +x "$INSTALL_DIR"/setup_*.sh "$INSTALL_DIR/uninstaller.sh" "$INSTALL_DIR/OpenSimWheel_Linux_Bridge.py"

if [ -f "$ROOT_DIR/osw_bridge.ini" ]; then
    cp -f "$ROOT_DIR/osw_bridge.ini" "$INSTALL_DIR/osw_bridge.ini"
    if [ ! -f "$CONFIG_DIR/osw_bridge.ini" ]; then
        cp -f "$ROOT_DIR/osw_bridge.ini" "$CONFIG_DIR/osw_bridge.ini"
    fi
fi

if [ -d "$ROOT_DIR/assets" ]; then
    cp -rf "$ROOT_DIR/assets"/* "$INSTALL_DIR/" 2>/dev/null || true
fi

cat > "$APPS_DIR/opensimwheel-bridge.desktop" << DESKEOF
[Desktop Entry]
Name=OpenSimWheel Linux Bridge
Comment=Telemetry Bridge for Thrustmaster SF1000 & Web Live Dash
TryExec=$INSTALL_DIR/OpenSimWheel_Linux_Bridge.py
Exec=/usr/bin/env python3 $INSTALL_DIR/OpenSimWheel_Linux_Bridge.py
Path=$INSTALL_DIR
Icon=$INSTALL_DIR/zenity_simracing.png
Terminal=false
Type=Application
Categories=Game;Utility;
DESKEOF

chmod 644 "$APPS_DIR/opensimwheel-bridge.desktop"
update-desktop-database "$APPS_DIR" 2>/dev/null || true

IFS="|" read -ra SIMS <<< "$SCELTE"
for sim in "${SIMS[@]}"; do
    case "$sim" in
        LMU)  bash "$ROOT_DIR/setup_lmu_plugin.sh" || true ;;
        ACC)  bash "$ROOT_DIR/setup_acc_proton.sh" || true ;;
        AC)   bash "$ROOT_DIR/setup_ac_proton.sh" || true ;;
        ACE)  bash "$ROOT_DIR/setup_ace_proton.sh" || true ;;
        RRRE) bash "$ROOT_DIR/setup_rrre_proton.sh" || true ;;
    esac
done

if command -v zenity >/dev/null 2>&1; then
    zenity --info --title="OpenSimWheel Linux Bridge v1.3.0" \
        --text="Installazione completata con successo!\n\nTrovi 'OpenSimWheel Linux Bridge' nel menu applicazioni." \
        --width=420 2>/dev/null || true
else
    echo "[OK] OpenSimWheel Linux Bridge v1.3.0 installato e protetto in $INSTALL_DIR!"
fi
