import mmap
import struct
import socket
import time
import os
import sys
import math

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
TARGET = ("127.0.0.1", 9001)
shm_phys = None
shm_stat = None


def _clean_f(v, default=0.0):
    return float(v) if (isinstance(v, (int, float)) and math.isfinite(v)) else float(default)


while True:
    if os.path.exists(r"C:\osw_shm\stop.flag"):
        sys.exit(0)
    try:
        if shm_phys is None:
            shm_phys = mmap.mmap(-1, 712, tagname="Local\\acpmf_physics", access=mmap.ACCESS_READ)
        if shm_stat is None:
            shm_stat = mmap.mmap(-1, 712, tagname="Local\\acpmf_static", access=mmap.ACCESS_READ)

        shm_phys.seek(0)
        p = shm_phys.read(512)
        pkt_id, gas, brake, fuel, gear, rpms, steer, speed_kmh = struct.unpack_from("<ifffiiff", p, 0)
        tc_val, = struct.unpack_from("<f", p, 96)
        p_fl, p_fr, p_rl, p_rr = struct.unpack_from("<ffff", p, 100)
        abs_val, = struct.unpack_from("<f", p, 136)
        w_fl, w_fr, w_rl, w_rr = struct.unpack_from("<ffff", p, 148)
        t_fl, t_fr, t_rl, t_rr = struct.unpack_from("<ffff", p, 164)
        bb_val, = struct.unpack_from("<f", p, 352)
        water_temp, = struct.unpack_from("<f", p, 360)

        # Lettura IMO reali da SPageFilePhysics:
        # offset 368: tyreTempI[4] (FL, FR, RL, RR)
        # offset 384: tyreTempM[4] (FL, FR, RL, RR)
        # offset 400: tyreTempO[4] (FL, FR, RL, RR)
        ti_fl, ti_fr, ti_rl, ti_rr = struct.unpack_from("<ffff", p, 368)
        tm_fl, tm_fr, tm_rl, tm_rr = struct.unpack_from("<ffff", p, 384)
        to_fl, to_fr, to_rl, to_rr = struct.unpack_from("<ffff", p, 400)

        shm_stat.seek(0)
        s = shm_stat.read(256)
        max_rpm = 8500
        for off in range(140, 220, 4):
            val, = struct.unpack_from("<i", s, off)
            if 5500 <= val <= 15000:
                max_rpm = val
                break

        msg = struct.pack(
            "<4siiiffffffffffffffiif13f",
            b"ACCS",
            int(rpms), int(max_rpm), int(gear),
            _clean_f(speed_kmh), _clean_f(fuel),
            _clean_f(t_fl, 75.0), _clean_f(t_fr, 75.0),
            _clean_f(t_rl, 75.0), _clean_f(t_rr, 75.0),
            _clean_f(p_fl, 0.0), _clean_f(p_fr, 0.0),
            _clean_f(p_rl, 0.0), _clean_f(p_rr, 0.0),
            _clean_f(w_fl, 100.0), _clean_f(w_fr, 100.0),
            _clean_f(w_rl, 100.0), _clean_f(w_rr, 100.0),
            int(round(_clean_f(tc_val, 0.0))),
            int(round(_clean_f(abs_val, 0.0))),
            _clean_f(bb_val, 0.0),
            _clean_f(ti_fl, 75.0), _clean_f(tm_fl, 75.0), _clean_f(to_fl, 75.0),
            _clean_f(ti_fr, 75.0), _clean_f(tm_fr, 75.0), _clean_f(to_fr, 75.0),
            _clean_f(ti_rl, 75.0), _clean_f(tm_rl, 75.0), _clean_f(to_rl, 75.0),
            _clean_f(ti_rr, 75.0), _clean_f(tm_rr, 75.0), _clean_f(to_rr, 75.0),
            _clean_f(water_temp, 90.0),
        )
        sock.sendto(msg, TARGET)
    except Exception:
        shm_phys = None
        shm_stat = None
        time.sleep(0.5)
    time.sleep(0.01)


