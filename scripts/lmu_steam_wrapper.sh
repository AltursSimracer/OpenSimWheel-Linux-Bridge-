#!/usr/bin/env bash
PFX_LMU="/run/media/alex/Steam_Race/SteamLibrary/steamapps/compatdata/2399420/pfx"
GE_WINE="/home/alex/.local/share/Steam/compatibilitytools.d/GE-Proton11-3-LMU/files/bin/wine"
(
    sleep 15
    WINEPREFIX="$PFX_LMU" "$GE_WINE" "C:\\osw_shm\\python.exe" "C:\\osw_shm\\lmu_shm_sender.py" >/dev/null 2>&1
) &
WRAP_PID=$!
"$@"
kill $WRAP_PID 2>/dev/null || true
