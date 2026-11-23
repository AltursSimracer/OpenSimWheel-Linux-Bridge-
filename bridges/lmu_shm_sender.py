import ctypes, struct, socket, time, math

k32 = ctypes.windll.kernel32
k32.OpenFileMappingW.restype = ctypes.c_void_p
k32.MapViewOfFile.restype = ctypes.c_void_p

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
DEST = ("127.0.0.1", 9009)

hMap = None
ptr = None

def connect_lmu():
    global hMap, ptr
    if ptr:
        return True
    hMap = k32.OpenFileMappingW(0x0004, False, "LMU_Data")
    if hMap:
        ptr = k32.MapViewOfFile(hMap, 0x0004, 0, 0, 0)
    return bool(ptr)

def find_player_idx(raw):
    for idx in range(129000, 326000, 4):
        try:
            max_rpm, = struct.unpack_from("<d", raw, idx - 264)
            if 4000.0 <= max_rpm <= 22000.0:
                gear, = struct.unpack_from("<i", raw, idx - 444)
                rpm, water_t = struct.unpack_from("<dd", raw, idx - 440)
                if -1 <= gear <= 8 and 0.0 <= rpm <= 22500.0 and 15.0 <= water_t <= 180.0:
                    return idx
        except Exception:
            break
    return -1

while True:
    if not connect_lmu():
        time.sleep(0.5)
        continue
    try:
        raw = ctypes.string_at(ptr, 327680)
        idx = find_player_idx(raw)
        if idx < 0:
            time.sleep(0.2)
            continue

        base = idx - 796
        lap_num, = struct.unpack_from("<i", raw, base + 24)
        vx, vy, vz = struct.unpack_from("<ddd", raw, base + 192)
        speed_kmh = math.sqrt(vx*vx + vy*vy + vz*vz) * 3.6
        gear, = struct.unpack_from("<i", raw, idx - 444)
        rpm, water_t, oil_t, clutch_rpm = struct.unpack_from("<dddd", raw, idx - 440)
        fuel, max_rpm = struct.unpack_from("<dd", raw, idx - 272)
        fuel_cap, = struct.unpack_from("<d", raw, idx - 184)
        flap_act = raw[idx - 179]
        flap_leg = raw[idx - 178]
        rear_bias, = struct.unpack_from("<d", raw, idx - 132)
        bat_frac, = struct.unpack_from("<d", raw, idx - 92)
        boost_tq, = struct.unpack_from("<d", raw, idx - 84)
        boost_state = raw[idx - 44]
        tc_val = raw[idx - 38]
        abs_val = raw[idx - 32]
        soc_pct, virt_en = struct.unpack_from("<ff", raw, idx - 20)

        yellow_state, = struct.unpack_from("<b", raw, 1761)
        sec_f0, sec_f1, sec_f2 = struct.unpack_from("<bbb", raw, 1762)
        v0 = 2192
        lap_dist, = struct.unpack_from("<d", raw, v0 + 108)
        best_lap, last_lap = struct.unpack_from("<dd", raw, v0 + 148)
        place = raw[v0 + 204]

        wheels = []
        for w_idx, t_off in enumerate((976, 1236, 1496, 1756)):
            press_kpa, = struct.unpack_from("<d", raw, base + t_off - 8)
            t_l, t_c, t_r = struct.unpack_from("<ddd", raw, base + t_off)
            wear, = struct.unpack_from("<d", raw, base + t_off + 24)
            if w_idx in (0, 2):
                t_in, t_mid, t_out = t_r, t_c, t_l
            else:
                t_in, t_mid, t_out = t_l, t_c, t_r
            wheels.extend([
                round(press_kpa * 0.1450377, 1) if 20.0 <= press_kpa <= 400.0 else 0.0,
                round(t_in - 273.15, 1) if 250.0 <= t_in <= 450.0 else 28.0,
                round(t_mid - 273.15, 1) if 250.0 <= t_mid <= 450.0 else 28.0,
                round(t_out - 273.15, 1) if 250.0 <= t_out <= 450.0 else 28.0,
                round(max(0.0, min(100.0, wear * 100.0)), 1) if 0.0 <= wear <= 1.01 else 100.0,
            ])

        pkt = struct.pack(
            "<idddddddddBBBbbBdddffBBB20f",
            int(gear), float(rpm), float(max_rpm), float(speed_kmh),
            float(water_t), float(fuel), float(fuel_cap), float(rear_bias),
            float(bat_frac), float(boost_tq),
            int(boost_state), int(tc_val), int(abs_val),
            int(yellow_state), int(max(sec_f0, sec_f1, sec_f2)), int(place),
            float(lap_dist), float(best_lap), float(last_lap),
            float(soc_pct), float(virt_en), int(max(1, lap_num + 1)),
            int(flap_act), int(flap_leg),
            *wheels
        )
        sock.sendto(pkt, DEST)
        time.sleep(0.016)
    except Exception:
        ptr = None
        time.sleep(0.5)
