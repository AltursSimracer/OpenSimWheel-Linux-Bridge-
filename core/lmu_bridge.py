import os, re, struct, time, math, ctypes, json, urllib.request

libc = ctypes.CDLL("libc.so.6")
class iovec(ctypes.Structure):
    _fields_ = [("iov_base", ctypes.c_void_p), ("iov_len", ctypes.c_size_t)]

LMU_STATE = {
    "pid": None,
    "veh_base": None,
    "last_slow_ts": 0.0,
    "rest_cache": {"pos": 1, "lap": 1, "cur_lap": 0.0, "last_lap": 0.0, "best_lap": 0.0, "s1": 0.0, "s2": 0.0, "lap_dist": 0.0},
    "last_rest_ts": 0.0
}

_LMU_TYRE_EMA = {}
_LMU_FUEL_STATE = {"last_lap": -1, "start_fuel": None, "history": list()}

def _filtra_temp_lmu(chiave, val_grezzo, fallback_temp=26, alpha=0.25):
    if not (2.0 <= val_grezzo <= 165.0):
        val_grezzo = float(fallback_temp)
    prev = _LMU_TYRE_EMA.get(chiave)
    if prev is None or abs(val_grezzo - prev) > 35.0:
        filtrato = float(val_grezzo)
    else:
        filtrato = (prev * (1.0 - alpha)) + (val_grezzo * alpha)
    _LMU_TYRE_EMA[chiave] = filtrato
    return max(10, min(int(round(filtrato)), 155))

def _read_mem(pid, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = libc.process_vm_readv(
        pid,
        ctypes.byref(iovec(ctypes.cast(buf, ctypes.c_void_p), size)), 1,
        ctypes.byref(iovec(ctypes.c_void_p(addr), size)), 1, 0
    )
    return buf.raw if n == size else None

def _find_lmu_pid():
    for p in os.listdir("/proc"):
        if p.isdigit():
            try:
                cmd = open(f"/proc/{p}/cmdline", "rb").read().decode(errors="ignore")
                if "Le Mans Ultimate.exe" in cmd:
                    return int(p)
            except Exception:
                pass
    return None

def _find_player_base(pid):
    try:
        with open(f"/proc/{pid}/maps", "r") as f:
            for line in f:
                m = re.match(r"([0-9a-f]+)-([0-9a-f]+) rw-s .*?/memfd:wine-mapping", line)
                if m:
                    s, e = int(m.group(1), 16), int(m.group(2), 16)
                    if (e - s) == 0x50000:
                        raw = _read_mem(pid, s, e - s)
                        if not raw:
                            continue
                        for off in range(352, len(raw) - 600, 4):
                            gear, rpm = struct.unpack_from("<id", raw, off)
                            if -1 <= gear <= 8 and 300.0 <= rpm <= 18000.0:
                                fuel, max_rpm = struct.unpack_from("<dd", raw, off + 172)
                                if 4500.0 <= max_rpm <= 18000.0 and 0.1 <= fuel <= 250.0:
                                    return s + off - 352
    except Exception:
        pass
    return None

def _poll_rest_timing(tempo):
    if tempo - LMU_STATE["last_rest_ts"] < 0.2:
        return
    LMU_STATE["last_rest_ts"] = tempo
    try:
        req = urllib.request.urlopen("http://localhost:6397/rest/watch/standings", timeout=0.08)
        standings = json.loads(req.read().decode("utf-8", errors="ignore"))
        if standings:
            pl = next((v for v in standings if v.get("player")), standings)
            LMU_STATE["rest_cache"] = {
                "pos": max(1, int(pl.get("position", 1))),
                "lap": max(1, int(pl.get("lapsCompleted", 0)) + 1),
                "cur_lap": max(0.0, float(pl.get("timeIntoLap", 0.0))),
                "last_lap": max(0.0, float(pl.get("lastLapTime", 0.0))),
                "best_lap": max(0.0, float(pl.get("bestLapTime", 0.0))),
                "s1": max(0.0, float(pl.get("currentSectorTime1", 0.0))),
                "s2": max(0.0, float(pl.get("currentSectorTime2", 0.0))),
                "lap_dist": max(0.0, float(pl.get("lapDistance", 0.0))),
            }
    except Exception:
        pass

def elabora_pacchetto_lmu(data, out_sock, ip_display, porta_display, dash_state, logger):
    tempo = time.time()
    pid = LMU_STATE["pid"]
    if not pid or not os.path.exists(f"/proc/{pid}"):
        pid = _find_lmu_pid()
        LMU_STATE["pid"] = pid
        LMU_STATE["veh_base"] = None
    if not pid:
        return

    base = LMU_STATE["veh_base"]
    if not base:
        base = _find_player_base(pid)
        LMU_STATE["veh_base"] = base
    if not base:
        return

    v = _read_mem(pid, base, 1800)
    if not v:
        LMU_STATE["veh_base"] = None
        return

    try:
        vx, vy, vz = struct.unpack_from("<ddd", v, 184)
        speed_kmh = max(0, min(int(round(math.sqrt(vx*vx + vy*vy + vz*vz) * 3.6)), 400))
        gear_raw, engine_rpm = struct.unpack_from("<id", v, 352)
        fuel_val, engine_max_rpm = struct.unpack_from("<dd", v, 524)

        rpm = max(0, min(int(round(engine_rpm)), 20000))
        max_rpm = int(round(engine_max_rpm)) if 4500 <= engine_max_rpm <= 20000 else 8000
        if rpm == 0 and max_rpm == 8000 and fuel_val <= 0.0:
            LMU_STATE["veh_base"] = None
            return

        if gear_raw < 0:
            gear_display, gear_str = -1, "R"
        elif gear_raw == 0:
            gear_display, gear_str = 0, "N"
        else:
            gear_display = max(1, min(int(gear_raw), 8))
            gear_str = str(gear_display)

        t_fl = t_fr = t_rl = t_rr = 26
        imo_fl = list((26, 26, 26))
        imo_fr = list((26, 26, 26))
        imo_rl = list((26, 26, 26))
        imo_rr = list((26, 26, 26))
        press_list = list((0.0, 0.0, 0.0, 0.0))
        life_list = list((100, 100, 100, 100))

        wheel_names = ("fl", "fr", "rl", "rr")
        for idx, w_off in enumerate((752, 1000, 1248, 1496)):
            w_key = wheel_names.__getitem__(idx)
            if w_off + 176 <= len(v):
                wear_raw, = struct.unpack_from("<d", v, w_off + 120)
                if 0.0 <= wear_raw <= 1.0:
                    life_list.__setitem__(idx, max(0, min(int(round(wear_raw * 100.0)), 100)))
                press_kpa, = struct.unpack_from("<d", v, w_off + 160)
                if 50.0 <= press_kpa <= 450.0:
                    press_list.__setitem__(idx, round(press_kpa * 0.1450377, 1))
                zones_c = None
                for k_off in (128, 136):
                    t1, t2, t3 = struct.unpack_from("<ddd", v, w_off + k_off)
                    if all(275.0 <= val <= 450.0 for val in (t1, t2, t3)):
                        c1 = _filtra_temp_lmu(f"{w_key}_0", t1 - 273.15, 26)
                        c2 = _filtra_temp_lmu(f"{w_key}_1", t2 - 273.15, 26)
                        c3 = _filtra_temp_lmu(f"{w_key}_2", t3 - 273.15, 26)
                        zones_c = (c1, c2, c3)
                        break
                if zones_c is not None:
                    c1, c2, c3 = zones_c
                    avg_t = int(round((c1 + c2 + c3) / 3.0))
                    if idx == 0:
                        t_fl = avg_t
                        imo_fl = list((c3, c2, c1))
                    elif idx == 1:
                        t_fr = avg_t
                        imo_fr = list((c1, c2, c3))
                    elif idx == 2:
                        t_rl = avg_t
                        imo_rl = list((c3, c2, c1))
                    elif idx == 3:
                        t_rr = avg_t
                        imo_rr = list((c1, c2, c3))

        in_pausa = (rpm == 0)
        idle_rpm = int(max_rpm * 0.25)
        if in_pausa or max_rpm <= idle_rpm:
            led_pct, led_bits, in_fuorigiri = 0, 0, False
        else:
            ratio_rpm = (rpm - idle_rpm) / float(max_rpm - idle_rpm)
            led_pct = int(max(0, min(100, (ratio_rpm / 0.90) * 100)))
            in_fuorigiri = (led_pct >= 100)
            if in_fuorigiri:
                lampeggio = int(tempo * 18) % 2 == 0
                led_bits = 0x7FFF if lampeggio else 0
                led_pct = 100 if lampeggio else 0
            else:
                num_leds = int(round((led_pct / 100.0) * 15))
                led_bits = (1 << num_leds) - 1 if num_leds > 0 else 0

        _poll_rest_timing(tempo)
        rc = LMU_STATE["rest_cache"]
        fuel_clean = round(max(0.0, fuel_val), 1)

        dash_state["gear"] = gear_str
        dash_state["speed"] = speed_kmh
        dash_state["rpm"] = rpm
        dash_state["max_rpm"] = max_rpm
        lap_lmu = rc["lap"]
        if _LMU_FUEL_STATE["last_lap"] != lap_lmu:
            if _LMU_FUEL_STATE["last_lap"] > 0 and _LMU_FUEL_STATE["start_fuel"] is not None and fuel_clean > 0:
                used = _LMU_FUEL_STATE["start_fuel"] - fuel_clean
                if 0.05 < used < 25.0:
                    _LMU_FUEL_STATE["history"].append(used)
                    if len(_LMU_FUEL_STATE["history"]) > 3:
                        _LMU_FUEL_STATE["history"].pop(0)
            _LMU_FUEL_STATE["last_lap"] = lap_lmu
            if fuel_clean > 0:
                _LMU_FUEL_STATE["start_fuel"] = fuel_clean
        avg_fuel_lmu = (sum(_LMU_FUEL_STATE["history"]) / len(_LMU_FUEL_STATE["history"])) if _LMU_FUEL_STATE["history"] else 2.8
        fuel_laps_lmu = round(fuel_clean / avg_fuel_lmu, 1) if (fuel_clean > 0 and avg_fuel_lmu > 0.05) else 0.0

        dash_state["fuel"] = fuel_clean
        dash_state["fuel_laps"] = fuel_laps_lmu
        dash_state["fuel_per_lap"] = round(avg_fuel_lmu, 2) if _LMU_FUEL_STATE["history"] else 0.0
        dash_state["tyre_fl"] = t_fl
        dash_state["tyre_fr"] = t_fr
        dash_state["tyre_rl"] = t_rl
        dash_state["tyre_rr"] = t_rr
        dash_state["tyre_fl_imo"] = imo_fl
        dash_state["tyre_fr_imo"] = imo_fr
        dash_state["tyre_rl_imo"] = imo_rl
        dash_state["tyre_rr_imo"] = imo_rr
        dash_state["tyre_press"] = press_list
        dash_state["tyre_wear"] = life_list
        if len(v) >= 368:
            r_bias, = struct.unpack_from("<d", v, 360)
            if 0.05 <= r_bias <= 0.95:
                dash_state["brake_bias"] = round((1.0 - r_bias) * 100.0, 1)
        s_flags = rest_data.get("sectorFlag", [])
        if isinstance(s_flags, list) and any(x == 1 for x in s_flags):
            dash_state["flag"] = "yellow"
        else:
            dash_state["flag"] = "none"
        dash_state["cur_lap"] = rc["cur_lap"]
        dash_state["last_lap"] = rc["last_lap"]
        dash_state["best_lap"] = rc["best_lap"]
        dash_state["lap"] = rc["lap"]
        dash_state["pos"] = rc["pos"]
        dash_state["s1"] = rc["s1"]
        dash_state["s2"] = rc["s2"]
        dash_state["packets"] += 1
        dash_state["last_ts"] = tempo
        dash_state["hz_counter"] += 1
        if tempo - dash_state["hz_timer"] >= 1.0:
            dash_state["hz"] = dash_state["hz_counter"] / (tempo - dash_state["hz_timer"])
            dash_state["hz_counter"] = 0
            dash_state["hz_timer"] = tempo

        track_len_m = 13626
        distanza_giro = min(rc["lap_dist"], float(track_len_m))
        lap_progress = distanza_giro / float(track_len_m)
        settore = 0 if lap_progress < 0.333 else (1 if lap_progress < 0.666 else 2)
        distanza_tot = float(((rc["lap"] - 1) * track_len_m) + distanza_giro)
        s1_safe = max(0, min(int(round(rc["s1"] * 1000)), 65535))
        s2_safe = max(0, min(int(round(rc["s2"] * 1000)), 65535))

        hdr = "<HBBBBQfIBB"
        h1 = struct.pack(hdr, 2020, 1, 0, 1, 1, 123456789, float(tempo), 0, 0, 0)
        p1 = bytearray(227)
        struct.pack_into("<BbbBH", p1, 0, 1, 28, 22, 60, track_len_m)
        struct.pack_into("<B", p1, 6, 10)
        struct.pack_into("<B", p1, 19, 1)

        h2 = struct.pack(hdr, 2020, 1, 0, 1, 2, 123456789, float(tempo), 0, 0, 0)
        p2 = bytearray(1168)
        struct.pack_into("<ffHHf", p2, 0, rc["last_lap"], rc["cur_lap"], s1_safe, s2_safe, rc["best_lap"])
        struct.pack_into("<ff", p2, 24, distanza_giro, distanza_tot)
        struct.pack_into("<BBBB", p2, 34, rc["pos"], rc["lap"], 0, settore)
        struct.pack_into("<BBB", p2, 41, 0, 0, 2)

        h6 = struct.pack(hdr, 2020, 1, 0, 1, 6, 123456789, float(tempo), 0, 0, 0)
        p6 = bytearray(1323)
        struct.pack_into("<HfffB", p6, 0, speed_kmh, 1.0, 0.0, 0.0, 0)
        struct.pack_into("<bHBBH", p6, 15, int(gear_display), rpm, 0, led_pct, led_bits)
        struct.pack_into("<BBBB", p6, 44, t_rl, t_rr, t_fl, t_fr)
        struct.pack_into("<BBBB", p6, 48, t_rl, t_rr, t_fl, t_fr)

        h7 = struct.pack(hdr, 2020, 1, 0, 1, 7, 123456789, float(tempo), 0, 0, 0)
        p7 = bytearray(1320)
        struct.pack_into("<BBBBB", p7, 0, 2, 1, 1, 50, 0)
        struct.pack_into("<fff", p7, 5, fuel_clean, 120.0, fuel_laps_lmu)
        struct.pack_into("<HHB", p7, 17, int(max_rpm * 0.90), idle_rpm, 8)
        w_fl = max(0, 100 - life_list.__getitem__(0))
        w_fr = max(0, 100 - life_list.__getitem__(1))
        w_rl = max(0, 100 - life_list.__getitem__(2))
        w_rr = max(0, 100 - life_list.__getitem__(3))
        struct.pack_into("<BBBB", p7, 25, w_rl, w_rr, w_fl, w_fr)
        struct.pack_into("<BB", p7, 29, 16, 16)
        fia_flag = (2 if int(tempo * 20) % 2 == 0 else 4) if in_fuorigiri else 0
        struct.pack_into("<b", p7, 42, fia_flag)

        out_sock.sendto(h6 + p6, (ip_display, porta_display))
        if tempo - LMU_STATE["last_slow_ts"] >= 0.2:
            LMU_STATE["last_slow_ts"] = tempo
            out_sock.sendto(h1 + p1, (ip_display, porta_display))
            out_sock.sendto(h2 + p2, (ip_display, porta_display))
            out_sock.sendto(h7 + p7, (ip_display, porta_display))
    except Exception as e:
        logger.warning(f"Errore pacchetto LMU: {e}")
