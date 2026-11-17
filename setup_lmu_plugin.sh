#!/usr/bin/env bash
set -e

echo "=== OpenSimWheel Linux Bridge v1.2.1 - Setup Le Mans Ultimate (LMU) ==="

LMU_DIR=""
for base in "$HOME/.local/share/Steam" "$HOME/.steam/steam" /run/media/*/* /run/media/*/*/SteamLibrary /mnt/* /mnt/*/SteamLibrary; do
    if [ -d "$base/steamapps/common/Le Mans Ultimate" ]; then
        LMU_DIR="$base/steamapps/common/Le Mans Ultimate"
        break
    fi
done

if [ -z "$LMU_DIR" ] && command -v zenity >/dev/null 2>&1; then
    LMU_DIR=$(zenity --file-selection --directory \
        --title="Seleziona la cartella 'Le Mans Ultimate'" \
        --filename="/run/media/$USER/" 2>/dev/null || true)
fi

if [ -z "$LMU_DIR" ] || [ ! -d "$LMU_DIR" ]; then
    echo "LMU non selezionato o cartella non trovata (operazione saltata)."
    exit 0
fi

mkdir -p "$LMU_DIR/Plugins"
mkdir -p "$LMU_DIR/UserData/player"

for dll_src in "$(dirname "$0")/rFactor2SharedMemoryMapPlugin64.dll" "$HOME/Scaricati/rFactor2SharedMemoryMapPlugin64.dll" "$HOME/Downloads/rFactor2SharedMemoryMapPlugin64.dll"; do
    if [ -f "$dll_src" ]; then
        cp "$dll_src" "$LMU_DIR/Plugins/"
        echo "OK Copiata rFactor2SharedMemoryMapPlugin64.dll in $LMU_DIR/Plugins/"
        break
    fi
done

CFG="$LMU_DIR/UserData/player/CustomPluginVariables.JSON"
python3 - "$CFG" << 'PYEOF'
import json, os, sys
cfg = list(sys.argv).pop(1)
data = {}
if os.path.exists(cfg):
    try:
        with open(cfg, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
data["rFactor2SharedMemoryMapPlugin64.dll"] = {" Enabled": 1, "EnableDirectMemoryAccess": 1}
with open(cfg, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print("OK Plugin abilitato in:", cfg)
PYEOF

if [ ! -f "$LMU_DIR/Plugins/rFactor2SharedMemoryMapPlugin64.dll" ]; then
    echo ""
    echo "RICORDA: Copia 'rFactor2SharedMemoryMapPlugin64.dll' dentro:"
    echo "$LMU_DIR/Plugins/"
fi

echo ""
echo "Setup LMU completato! Impostazioni Steam consigliate:"
echo "1. Compatibilità: GE-Proton11-3-LMU o Proton Experimental."
echo "2. Controller: Disattiva Steam Input."
echo "3. Opzioni di Avvio Steam: lascia vuoto (lettura Shared Memory nativa a 100Hz)."
