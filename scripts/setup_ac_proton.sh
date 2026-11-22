#!/usr/bin/env bash
set -e

find_pfx() {
    local appid="$1"
    local bases=(
        "$HOME/.local/share/Steam"
        "$HOME/.steam/root"
        "$HOME/.steam/steam"
        "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam"
    )
    for vdf in "$HOME/.local/share/Steam/steamapps/libraryfolders.vdf" "$HOME/.steam/steam/steamapps/libraryfolders.vdf"; do
        if [ -f "$vdf" ]; then
            while IFS= read -r path; do
                bases+=("$path")
            done < <(grep -oE '"path"[[:space:]]+"[^"]+"' "$vdf" | cut -d'"' -f4)
        fi
    done
    for base in "${bases[@]}" /run/media/*/*/SteamLibrary /run/media/*/* /mnt/*/*/SteamLibrary /mnt/*/*; do
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
import mmap, struct, socket, time, os, sys, math

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
TARGET = ("127.0.0.1", 9003)
shm_phys = shm_gfx = shm_stat = None

def _clean_f(v, default=0.0):
    return float(v) if (isinstance(v, (int, float)) and math.isfinite(v)) else float(default)

while True:
    if os.path.exists(r"C:\osw_shm\stop.flag") or os.path.exists(r"C:\osw_shm\stop_ac.flag"):
        sys.exit(0)
    try:
        if shm_phys is None:
            shm_phys = mmap.mmap(-1, 712, tagname="Local\\acpmf_physics", access=mmap.ACCESS_READ)
        if shm_gfx is None:
            shm_gfx = mmap.mmap(-1, 1580, tagname="Local\\acpmf_graphics", access=mmap.ACCESS_READ)
        if shm_stat is None:
            shm_stat = mmap.mmap(-1, 712, tagname="Local\\acpmf_static", access=mmap.ACCESS_READ)

        shm_phys.seek(0)
        p = shm_phys.read(512)
        pkt_id, gas, brake, fuel, gear, rpms, steer, speed_kmh = struct.unpack_from("<ifffiiff", p, 0)
        tc_val, = struct.unpack_from("<f", p, 96)
        p_fl, p_fr, p_rl, p_rr = struct.unpack_from("<ffff", p, 100)
        abs_val, kers_c, kers_i = struct.unpack_from("<fff", p, 136)
        w_fl, w_fr, w_rl, w_rr = struct.unpack_from("<ffff", p, 148)
        t_fl, t_fr, t_rl, t_rr = struct.unpack_from("<ffff", p, 164)
        air_t, road_t = struct.unpack_from("<ff", p, 180)
        bb_val, = struct.unpack_from("<f", p, 352)
        ti_fl, ti_fr, ti_rl, ti_rr = struct.unpack_from("<ffff", p, 368)
        tm_fl, tm_fr, tm_rl, tm_rr = struct.unpack_from("<ffff", p, 384)
        to_fl, to_fr, to_rl, to_rr = struct.unpack_from("<ffff", p, 400)

        if not (-10.0 <= air_t <= 60.0): air_t = 22.0
        if not (-10.0 <= road_t <= 80.0): road_t = 26.0

        shm_gfx.seek(0)
        g = shm_gfx.read(1340)
        completed_laps, position, i_cur_time, i_last_time, i_best_time = struct.unpack_from("<iiiii", g, 132)
        cur_sector, last_sector_ms = struct.unpack_from("<ii", g, 164)
        norm_spline, = struct.unpack_from("<f", g, 248)
        flag_id, = struct.unpack_from("<i", g, 1328)

        shm_stat.seek(0)
        s = shm_stat.read(256)
        max_rpm = 8500
        for off in range(140, 220, 4):
            val, = struct.unpack_from("<i", s, off)
            if 5500 <= val <= 18000:
                max_rpm = val
                break

        msg = struct.pack(
            "<4siififfiiiiiiifffffffffffffffiifi14f",
            b"ACSM",
            int(rpms), int(max_rpm), _clean_f(speed_kmh), int(gear),
            _clean_f(fuel), 60.0,
            int(i_cur_time), int(i_last_time), int(i_best_time),
            int(last_sector_ms) if cur_sector == 1 else 0,
            int(last_sector_ms) if cur_sector == 2 else 0,
            int(completed_laps) + 1, max(1, int(position)), _clean_f(norm_spline),
            _clean_f(t_fl, 25.0), _clean_f(t_fr, 25.0), _clean_f(t_rl, 25.0), _clean_f(t_rr, 25.0),
            _clean_f(air_t, 22.0), _clean_f(road_t, 26.0),
            _clean_f(p_fl), _clean_f(p_fr), _clean_f(p_rl), _clean_f(p_rr),
            _clean_f(w_fl, 100.0), _clean_f(w_fr, 100.0), _clean_f(w_rl, 100.0), _clean_f(w_rr, 100.0),
            int(round(_clean_f(tc_val))), int(round(_clean_f(abs_val))),
            _clean_f(bb_val), int(flag_id),
            _clean_f(ti_fl, 25.0), _clean_f(tm_fl, 25.0), _clean_f(to_fl, 25.0),
            _clean_f(ti_fr, 25.0), _clean_f(tm_fr, 25.0), _clean_f(to_fr, 25.0),
            _clean_f(ti_rl, 25.0), _clean_f(tm_rl, 25.0), _clean_f(to_rl, 25.0),
            _clean_f(ti_rr, 25.0), _clean_f(tm_rr, 25.0), _clean_f(to_rr, 25.0),
            _clean_f(kers_c, 0.0), _clean_f(kers_i, 0.0),
        )
        sock.sendto(msg, TARGET)
    except Exception:
        shm_phys = shm_gfx = shm_stat = None
        time.sleep(0.5)
    time.sleep(0.01)
PYEOF

write_launcher "$SHM_DIR" "start_ac_shm.sh" "ac_shm_sender.py"
echo "[OK] Assetto Corsa (AC) ($APPID): configurato con successo in $SHM_DIR!"
