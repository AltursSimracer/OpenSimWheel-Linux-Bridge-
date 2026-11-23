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

APPID="211500"
PFX_DIR=$(find_pfx "$APPID") || { echo "[ERRORE] Prefisso Steam per RaceRoom ($APPID) non trovato."; exit 1; }
SHM_DIR="$PFX_DIR/pfx/drive_c/osw_shm"
install_python_embed "$SHM_DIR"

cat << 'PYEOF' > "$SHM_DIR/rrre_shm_sender.py"
import mmap, struct, socket, time, os, sys, math

def cf(v, d=0.0):
    return v if (isinstance(v, (int, float)) and math.isfinite(v)) else d

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
TARGET = ("127.0.0.1", 9007)
shm = None

while True:
    if os.path.exists(r"C:\osw_shm\stop.flag") or os.path.exists(r"C:\osw_shm\stop_rrre.flag"):
        sys.exit(0)
    try:
        if shm is None:
            shm = mmap.mmap(-1, 4096, tagname="Local\\$R3E", access=mmap.ACCESS_READ)
        shm.seek(0)
        buf = shm.read(4096)

        rps, max_rps = struct.unpack_from("<ff", buf, 1396)
        rpm = int(cf(rps) * 9.5492965855)
        max_rpm = int(cf(max_rps) * 9.5492965855) if cf(max_rps) > 10 else 8500
        speed_ms, = struct.unpack_from("<f", buf, 1392)
        speed_kmh = cf(speed_ms) * 3.6
        gear, = struct.unpack_from("<i", buf, 1408)
        fuel_l, max_fuel_l = struct.unpack_from("<ff", buf, 1456)
        cur_lap_s, last_lap_s, best_lap_s = struct.unpack_from("<fff", buf, 1280)
        s1_s, s2_s = struct.unpack_from("<ff", buf, 1320)
        lap_num, pos = struct.unpack_from("<ii", buf, 1252)
        lap_dist, track_len = struct.unpack_from("<ff", buf, 1264)
        lap_prog = (lap_dist / track_len) if track_len > 1.0 else 0.0
        flg_y = struct.unpack_from("<i", buf, 888)[0] if len(buf) >= 892 else 0
        flg_b = struct.unpack_from("<i", buf, 896)[0] if len(buf) >= 900 else 0
        tc_set = struct.unpack_from("<i", buf, 1476)[0] if len(buf) >= 1480 else 0
        abs_set = struct.unpack_from("<i", buf, 1484)[0] if len(buf) >= 1488 else 0
        bb_rear = struct.unpack_from("<f", buf, 1556)[0] if len(buf) >= 1560 else 0.0
        w_fl, w_fr, w_rl, w_rr = struct.unpack_from("<ffff", buf, 1652)
        t_fl, t_fr, t_rl, t_rr = struct.unpack_from("<ffff", buf, 1748)
        p_fl, p_fr, p_rl, p_rr = struct.unpack_from("<ffff", buf, 1796)

        # Lettura Push-to-Pass (offset 1560) + BatterySoC (offset 2208)
        p2p_avail, p2p_eng, p2p_left = struct.unpack_from("<iii", buf, 1560)
        bat_soc = struct.unpack_from("<f", buf, 2208)[0] if len(buf) >= 2212 else -1.0

        if 0.0 <= cf(bat_soc, -1.0) <= 100.0:
            ers_pct_out = float(bat_soc)
            ers_act_out = 1 if (cf(bat_soc) > 0.0 and p2p_eng == 1) else 0
        elif p2p_avail == 1 and p2p_left >= 0:
            ers_pct_out = min(100.0, float(p2p_left) * 10.0)
            ers_act_out = 1 if p2p_eng == 1 else 0
        else:
            ers_pct_out = -1.0
            ers_act_out = 0

        imo_vals = struct.unpack_from("<12f", buf, 1700)

        msg = struct.pack(
            "<4siififffffffiifffffffffffffffiifi12ffi",
            b"R3EM",
            max(0, rpm), max(1000, max_rpm), max(0.0, speed_kmh), gear,
            max(0.0, cf(fuel_l)), max(1.0, cf(max_fuel_l, 50.0)),
            max(0.0, cf(cur_lap_s)), max(0.0, cf(last_lap_s)), max(0.0, cf(best_lap_s)),
            max(0.0, cf(s1_s)), max(0.0, cf(s2_s)),
            max(1, lap_num), max(1, pos), max(0.0, min(1.0, cf(lap_prog))),
            cf(t_fl, 60.0), cf(t_fr, 60.0), cf(t_rl, 60.0), cf(t_rr, 60.0), 22.0, 26.0,
            cf(p_fl, 0.0), cf(p_fr, 0.0), cf(p_rl, 0.0), cf(p_rr, 0.0),
            cf(w_fl, 1.0), cf(w_fr, 1.0), cf(w_rl, 1.0), cf(w_rr, 1.0),
            int(tc_set), int(abs_set), cf(bb_rear, 0.0), int(2 if flg_y == 1 else (1 if flg_b == 1 else 0)),
            *[cf(x, 60.0) for x in imo_vals],
            ers_pct_out, ers_act_out
        )
        sock.sendto(msg, TARGET)
    except Exception:
        shm = None
        time.sleep(0.5)
    time.sleep(0.025)
PYEOF
