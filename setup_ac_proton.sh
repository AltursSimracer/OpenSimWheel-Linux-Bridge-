#!/usr/bin/env bash
set -e

find_pfx() {
    local appid="$1"
    for base in "$HOME/.local/share/Steam" "$HOME/.steam/root" "$HOME/.steam/steam" /run/media/*/*/SteamLibrary /run/media/*/* /mnt/*/*/SteamLibrary /mnt/*/*; do
        if [ -d "$base/steamapps/compatdata/$appid/pfx" ]; then
            echo "$base/steamapps/compatdata/$appid"
            return 0
        fi
    done
    return 1
}

install_python_embed() {
    local shm_dir="$1"
    mkdir -p "$shm_dir"
    if [ ! -f "$shm_dir/pythonw.exe" ]; then
        echo "[INFO] Scaricamento Python embeddable per Windows in $shm_dir..."
        curl -fL "https://python.org" -o /tmp/py_embed.zip
        unzip -qo /tmp/py_embed.zip -d "$shm_dir"
        rm -f /tmp/py_embed.zip
    fi
}

write_launcher() {
    local shm_dir="$1"
    local start_sh="$2"
    local sender_py="$3"
    cat << 'SHMEOF' > "$shm_dir/$start_sh"
#!/usr/bin/env bash
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
PFX_ROOT="$(cd "$SELF_DIR/../.." && pwd)"
APPID="$(basename "$(dirname "$PFX_ROOT")")"
export WINEPREFIX="$PFX_ROOT"
export WINEFSYNC=1
export WINEESYNC=1
WS_PID=$(pgrep -f "wineserver" | while read -r pid; do grep -qz "$APPID" "/proc/$pid/environ" 2>/dev/null && echo "$pid" && break; done)
WINE_BIN=""
if test -n "$WS_PID" && test -e "/proc/$WS_PID/exe"; then
    WINE_BIN="$(dirname "$(readlink -f "/proc/$WS_PID/exe")")/wine"
fi
if test -x "$WINE_BIN"; then
    exec "$WINE_BIN" "C:\osw_shm\pythonw.exe" "C:\osw_shm\SENDER_FILE"
fi
SHMEOF
    sed -i "s/SENDER_FILE/$sender_py/g" "$shm_dir/$start_sh"
    chmod +x "$shm_dir/$start_sh"
}

APPID="244210"
PFX_DIR=$(find_pfx "$APPID") || { echo "[ERRORE] Prefisso Steam per Assetto Corsa ($APPID) non trovato."; exit 1; }
SHM_DIR="$PFX_DIR/pfx/drive_c/osw_shm"
install_python_embed "$SHM_DIR"

cat << 'PYEOF' > "$SHM_DIR/ac_shm_sender.py"
import mmap, struct, socket, time, os, sys

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
TARGET = ("127.0.0.1", 9003)
shm_phys = shm_gfx = shm_stat = None

while True:
    if os.path.exists(r"C:\osw_shm\stop.flag"):
        sys.exit(0)
    try:
        if shm_phys is None:
            shm_phys = mmap.mmap(-1, 712, tagname="Local\\acpmf_physics", access=mmap.ACCESS_READ)
        if shm_gfx is None:
            shm_gfx = mmap.mmap(-1, 1580, tagname="Local\\acpmf_graphics", access=mmap.ACCESS_READ)
        if shm_stat is None:
            shm_stat = mmap.mmap(-1, 712, tagname="Local\\acpmf_static", access=mmap.ACCESS_READ)

        shm_phys.seek(0)
        p = shm_phys.read(256)
        pkt_id, gas, brake, fuel, gear, rpms, steer, speed_kmh = struct.unpack_from("<ifffiiff", p, 0)
        tc_val, = struct.unpack_from("<f", p, 96)
        p_fl, p_fr, p_rl, p_rr = struct.unpack_from("<ffff", p, 100)
        abs_val, = struct.unpack_from("<f", p, 136)
        bb_val = struct.unpack_from("<f", p, 352).__getitem__(0) if len(p) >= 356 else 0.0
        flag_id = struct.unpack_from("<i", g, 1328).__getitem__(0) if len(g) >= 1332 else 0
        w_fl, w_fr, w_rl, w_rr = struct.unpack_from("<ffff", p, 148)
        t_fl, t_fr, t_rl, t_rr = struct.unpack_from("<ffff", p, 164)
        air_t, road_t = struct.unpack_from("<ff", p, 180)
        if not (-10.0 <= air_t <= 60.0): air_t = 22.0
        if not (-10.0 <= road_t <= 80.0): road_t = 26.0

        shm_gfx.seek(0)
        g = shm_gfx.read(300)
        completed_laps, position, i_cur_time, i_last_time, i_best_time = struct.unpack_from("<iiiii", g, 132)
        cur_sector, last_sector_ms = struct.unpack_from("<ii", g, 164)
        norm_spline, = struct.unpack_from("<f", g, 248)

        shm_stat.seek(0)
        s = shm_stat.read(256)
        max_rpm = 8500
        for off in range(140, 220, 4):
            val, = struct.unpack_from("<i", s, off)
            if 5500 <= val <= 18000:
                max_rpm = val
                break

        msg = struct.pack(
            "<4siififfiiiiiiifffffffffffffffiifi",
            b"ACSM",
            rpms, max_rpm, speed_kmh, gear,
            fuel, 60.0,
            i_cur_time, i_last_time, i_best_time,
            last_sector_ms if cur_sector == 1 else 0,
            last_sector_ms if cur_sector == 2 else 0,
            completed_laps + 1, max(1, position), norm_spline,
            t_fl, t_fr, t_rl, t_rr, air_t, road_t,
            p_fl, p_fr, p_rl, p_rr, w_fl, w_fr, w_rl, w_rr,
            int(round(tc_val)), int(round(abs_val)), float(bb_val), int(flag_id)
        )
        sock.sendto(msg, TARGET)
    except Exception:
        shm_phys = shm_gfx = shm_stat = None
        time.sleep(0.5)
    time.sleep(0.01)
PYEOF

write_launcher "$SHM_DIR" "start_ac_shm.sh" "ac_shm_sender.py"
echo "[OK] Assetto Corsa (AC) ($APPID): configurato con successo in $SHM_DIR!"
