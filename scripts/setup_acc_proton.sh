#!/usr/bin/env bash
set -e

echo "=== OpenSimWheel Linux Bridge v1.4.0 - Setup ACC (Steam Proton) ==="

BASES=(
    "$HOME/.local/share/Steam"
    "$HOME/.steam/root"
    "$HOME/.steam/steam"
    "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam"
)
for vdf in "$HOME/.local/share/Steam/steamapps/libraryfolders.vdf" "$HOME/.steam/steam/steamapps/libraryfolders.vdf"; do
    if [ -f "$vdf" ]; then
        while IFS= read -r path; do
            BASES+=("$path")
        done < <(grep -oE '"path"[[:space:]]+"[^"]+"' "$vdf" | cut -d'"' -f4)
    fi
done

PFX_ACC=""
for base in "${BASES[@]}" /run/media/*/* /run/media/*/*/SteamLibrary /mnt/* /mnt/*/SteamLibrary; do
    if [ -d "$base/steamapps/compatdata/805550/pfx" ]; then
        PFX_ACC="$base/steamapps/compatdata/805550/pfx"
        break
    fi
done

if [ -z "$PFX_ACC" ] && command -v zenity >/dev/null 2>&1; then
    PFX_ACC=$(zenity --file-selection --directory \
        --title="Seleziona la cartella 'pfx' di ACC (compatdata/805550/pfx)" \
        --filename="/run/media/$USER/" 2>/dev/null || true)
fi

if [ -z "$PFX_ACC" ] || [ ! -d "$PFX_ACC" ]; then
    echo "Prefisso Proton ACC (805550) non trovato o non selezionato."
    exit 0
fi

PROTON_WINE=""
for w in \
    "$HOME/.local/share/Steam/steamapps/common/Proton - Experimental/files/bin/wine" \
    "$HOME/.local/share/Steam/steamapps/common/Proton 9.0 (Beta)/files/bin/wine" \
    "$HOME/.local/share/Steam/steamapps/common"/Proton*/files/bin/wine \
    "$HOME/.local/share/Steam/compatibilitytools.d"/*/files/bin/wine \
    /run/media/*/*/SteamLibrary/steamapps/common/Proton*/files/bin/wine \
    /mnt/*/SteamLibrary/steamapps/common/Proton*/files/bin/wine; do
    if [ -x "$w" ]; then
        PROTON_WINE="$w"
        break
    fi
done

if [ -z "$PROTON_WINE" ] && command -v zenity >/dev/null 2>&1; then
    PROTON_WINE=$(zenity --file-selection \
        --title="Seleziona l'eseguibile 'wine' dentro Proton (files/bin/wine)" \
        --filename="$HOME/.local/share/Steam/" 2>/dev/null || true)
fi

if [ -z "$PROTON_WINE" ] || [ ! -x "$PROTON_WINE" ]; then
    echo "Eseguibile Proton wine non trovato."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$PFX_ACC/drive_c/osw_shm"

if [ -f "$SCRIPT_DIR/core/acc_shm_sender.py" ]; then
    cp -f "$SCRIPT_DIR/core/acc_shm_sender.py" "$PFX_ACC/drive_c/osw_shm/"
elif [ -f "$SCRIPT_DIR/../bridges/acc_shm_sender.py" ]; then
    cp -f "$SCRIPT_DIR/../bridges/acc_shm_sender.py" "$PFX_ACC/drive_c/osw_shm/"
elif [ -f "$SCRIPT_DIR/../bridges/acc_shm_sender.py" ]; then
    cp -f "$SCRIPT_DIR/../bridges/acc_shm_sender.py" "$PFX_ACC/drive_c/osw_shm/"
elif [ -f "$SCRIPT_DIR/acc_shm_sender.py" ]; then
    cp -f "$SCRIPT_DIR/acc_shm_sender.py" "$PFX_ACC/drive_c/osw_shm/"
else
    echo "[ERRORE] acc_shm_sender.py non trovato in $SCRIPT_DIR."
    exit 1
fi

if [ ! -f "$PFX_ACC/drive_c/osw_shm/pythonw.exe" ]; then
    echo "Scaricamento Python embeddable per Proton..."
    TMP_ZIP="/tmp/python_embed_osw_$$.zip"
    curl -fsSL "https://python.org" -o "$TMP_ZIP"
    unzip -qo "$TMP_ZIP" -d "$PFX_ACC/drive_c/osw_shm/"
    rm -f "$TMP_ZIP"
fi

cat << EOSH > "$PFX_ACC/drive_c/osw_shm/start_acc_shm.sh"
#!/usr/bin/env bash
pkill -f acc_shm_sender.py 2>/dev/null || true
export WINEPREFIX="$PFX_ACC"
export WINEFSYNC=1
export WINEESYNC=1

# Rileva automaticamente lo stesso binario Proton/Wine usato da ACC (805550) in esecuzione
ACTIVE_WINE=""
for _ in \$(seq 1 30); do
    WS_PID=\$(pgrep -f "wineserver" | while read -r pid; do grep -qz "805550" "/proc/\$pid/environ" 2>/dev/null && echo "\$pid" && break; done)
    if [ -n "\$WS_PID" ] && [ -e "/proc/\$WS_PID/exe" ]; then
        ACTIVE_WINE="\$(dirname "\$(readlink -f "/proc/\$WS_PID/exe")")/wine"
        [ -x "\$ACTIVE_WINE" ] && break
    fi
    sleep 1
done

WINE_TO_USE="\${ACTIVE_WINE:-$PROTON_WINE}"
exec "\$WINE_TO_USE" "C:\\\\osw_shm\\\\pythonw.exe" "C:\\\\osw_shm\\\\acc_shm_sender.py"
EOSH
chmod +x "$PFX_ACC/drive_c/osw_shm/start_acc_shm.sh"

echo "[OK] Modulo telemetria ACC (v1.4.0) configurato correttamente!"
echo "Prefisso ACC : $PFX_ACC"
echo "Proton Wine  : $PROTON_WINE"
