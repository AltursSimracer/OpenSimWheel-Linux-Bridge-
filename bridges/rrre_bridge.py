import socket
import struct
import time

R3E_PKT_FMT = "<4siififffffffiifffffff"
R3E_PKT_SIZE = struct.calcsize(R3E_PKT_FMT)

_R3E_TYRE_EMA = {
    "fl": None, "fr": None, "rl": None, "rr": None,
    "fl_i": None, "fl_m": None, "fl_o": None,
    "fr_i": None, "fr_m": None, "fr_o": None,
    "rl_i": None, "rl_m": None, "rl_o": None,
    "rr_i": None, "rr_m": None, "rr_o": None,
}
_R3E_FUEL_STATE = {"last_lap": -1, "start_fuel": None, "history": []}
_R3E_SECTOR_STATE = {"seen_s1": 0.0, "seen_s2": 0.0, "last_s3": 0.0}


def _filtra_temp_r3e(ruota, val_grezzo, fallback_temp=25, alpha=0.25):
    if not (0.5 < val_grezzo < 180.0):
        val_grezzo = float(fallback_temp)
    prev = _R3E_TYRE_EMA.get(ruota)
    if prev is None or abs(val_grezzo - prev) > 35.0:
        filtrato = float(val_grezzo)
    else:
        filtrato = (prev * (1.0 - alpha)) + (val_grezzo * alpha)
    _R3E_TYRE_EMA[ruota] = filtrato
    return max(10, min(int(round(filtrato)), 150))


def elabora_pacchetto_rrre(data, out_sock, ip_display, porta_display, dash_state, logger):
    if not data or len(data) < R3E_PKT_SIZE:
        return

    try:
        unpacked = struct.unpack_from(R3E_PKT_FMT, data, 0)
        if unpacked != b"R3EM":
            return

        (_, rpm, max_rpm, speed_f, gear_raw,
         fuel_l, max_fuel_l, curr_lap_s, last_lap_s, best_lap_s,
         s1_s, s2_s, current_lap, pos, lap_progress,
         t_fl, t_fr, t_rl, t_rr, air_t, track_t) = unpacked

        p_fl = p_fr = p_rl = p_rr = 0.0
        life_fl = life_fr = life_rl = life_rr = 100
        if len(data) >= R3E_PKT_SIZE + 32:
            pf1, pf2, pf3, pf4, wf1, wf2, wf3, wf4 = struct.unpack_from("<ffffffff", data, R3E_PKT_SIZE)
            p_fl = round(pf1 * 0.1450377, 1) if 50.0 <= pf1 <= 450.0 else 0.0
            p_fr = round(pf2 * 0.1450377, 1) if 50.0 <= pf2 <= 450.0 else 0.0
            p_rl = round(pf3 * 0.1450377, 1) if 50.0 <= pf3 <= 450.0 else 0.0
            p_rr = round(pf4 * 0.1450377, 1) if 50.0 <= pf4 <= 450.0 else 0.0
            life_fl = max(0, min(int(round(wf1 * 100.0)), 100)) if 0.0 <= wf1 <= 1.0 else 100
            life_fr = max(0, min(int(round(wf2 * 100.0)), 100)) if 0.0 <= wf2 <= 1.0 else 100
            life_rl = max(0, min(int(round(wf3 * 100.0)), 100)) if 0.0 <= wf3 <= 1.0 else 100
            life_rr = max(0, min(int(round(wf4 * 100.0)), 100)) if 0.0 <= wf4 <= 1.0 else 100

        tc_v = abs_v = 0
        bb_v = 0.0
        flag_str = "none"
        if len(data) >= R3E_PKT_SIZE + 48:
            tc_v, abs_v, bb_rear, flag_id = struct.unpack_from("<iifi", data, R3E_PKT_SIZE + 32)
            if 0.05 <= bb_rear <= 0.95:
                bb_v = round((1.0 - bb_rear) * 100.0, 1)
            flag_str = {1: "blue", 2: "yellow"}.get(flag_id, "none")

        tempo = time.time()
        rpm = max(0, min(rpm, 20000))
        max_rpm = max(4000, min(max_rpm, 20000)) if max_rpm > 1000 else 8500
        speed_kmh = max(0, min(int(round(speed_f)), 380))

        if gear_raw < 0:
            gear_display = -1
            gear_str = "R"
        elif gear_raw == 0:
            gear_display = 0
            gear_str = "N"
        else:
            gear_display = max(1, min(gear_raw, 8))
            gear_str = str(gear_display)

        in_pausa = (rpm == 0)
        idle_rpm = 1200

        if in_pausa or max_rpm <= idle_rpm:
            led_pct = 0
            led_bits = 0
            in_fuorigiri = False
        else:
            ratio_rpm = (rpm - idle_rpm) / float(max_rpm - idle_rpm)
            led_pct = int(max(0, min(100, (ratio_rpm / 0.93) * 100)))
            in_fuorigiri = (led_pct >= 100)
            if in_fuorigiri:
                lampeggio = int(tempo * 18) % 2 == 0
                led_bits = 0x7FFF if lampeggio else 0
                led_pct = 100 if lampeggio else 0
            else:
                num_leds = int(round((led_pct / 100.0) * 15))
                led_bits = (1 << num_leds) - 1 if num_leds > 0 else 0

        fuel_in_tank = max(0.0, min(fuel_l, 200.0))
        fuel_cap = max(fuel_in_tank, max_fuel_l, 1.0)
        lap_now = max(1, current_lap)
        if _R3E_FUEL_STATE["last_lap"] != lap_now:
            if _R3E_FUEL_STATE["last_lap"] > 0 and _R3E_FUEL_STATE["start_fuel"] is not None and fuel_in_tank > 0:
                used = _R3E_FUEL_STATE["start_fuel"] - fuel_in_tank
                if 0.05 < used < 25.0:
                    _R3E_FUEL_STATE["history"].append(used)
                    if len(_R3E_FUEL_STATE["history"]) > 3:
                        _R3E_FUEL_STATE["history"].pop(0)
            _R3E_FUEL_STATE["last_lap"] = lap_now
            if fuel_in_tank > 0:
                _R3E_FUEL_STATE["start_fuel"] = fuel_in_tank
        elif _R3E_FUEL_STATE["start_fuel"] is not None and fuel_in_tank > _R3E_FUEL_STATE["start_fuel"] + 0.5:
            _R3E_FUEL_STATE["start_fuel"] = fuel_in_tank

        avg_fuel = (sum(_R3E_FUEL_STATE["history"]) / len(_R3E_FUEL_STATE["history"])) if _R3E_FUEL_STATE["history"] else 2.2
        fuel_laps = round(fuel_in_tank / avg_fuel, 1) if (fuel_in_tank > 0 and avg_fuel > 0.05) else 0.0
        air_temp_c = max(-10, min(int(round(air_t)), 60))
        track_temp_c = max(-10, min(int(round(track_t)), 80))
        fallback_temp = max(15, min(track_temp_c if track_temp_c > 0 else 25, 45))

        temp_fl = _filtra_temp_r3e("fl", t_fl, fallback_temp)
        temp_fr = _filtra_temp_r3e("fr", t_fr, fallback_temp)
        temp_rl = _filtra_temp_r3e("rl", t_rl, fallback_temp)
        temp_rr = _filtra_temp_r3e("rr", t_rr, fallback_temp)

        has_real_imo = False
        imo_fl = [temp_fl, temp_fl, temp_fl]
        imo_fr = [temp_fr, temp_fr, temp_fr]
        imo_rl = [temp_rl, temp_rl, temp_rl]
        imo_rr = [temp_rr, temp_rr, temp_rr]

        if len(data) >= R3E_PKT_SIZE + 96:
            imo_raw = struct.unpack_from("<12f", data, R3E_PKT_SIZE + 48)
            if any(0.5 < v < 180.0 for v in imo_raw):
                has_real_imo = True
                imo_fl = [_filtra_temp_r3e("fl_i", imo_raw, temp_fl), _filtra_temp_r3e("fl_m", imo_raw, temp_fl), _filtra_temp_r3e("fl_o", imo_raw, temp_fl)]
                imo_fr = [_filtra_temp_r3e("fr_i", imo_raw, temp_fr), _filtra_temp_r3e("fr_m", imo_raw, temp_fr), _filtra_temp_r3e("fr_o", imo_raw, temp_fr)]
                imo_rl = [_filtra_temp_r3e("rl_i", imo_raw, temp_rl), _filtra_temp_r3e("rl_m", imo_raw, temp_rl), _filtra_temp_r3e("rl_o", imo_raw, temp_rl)]
                imo_rr = [_filtra_temp_r3e("rr_i", imo_raw, temp_rr), _filtra_temp_r3e("rr_m", imo_raw, temp_rr), _filtra_temp_r3e("rr_o", imo_raw, temp_rr)]

        curr_lap_s = max(0.0, curr_lap_s)
        last_lap_s = max(0.0, last_lap_s)
        best_lap_s = max(0.0, best_lap_s)

        s1_clean = max(0.0, s1_s)
        s2_clean = max(0.0, s2_s)
        if s1_clean > 0.0:
            _R3E_SECTOR_STATE["seen_s1"] = s1_clean
        if s2_clean > 0.0:
            _R3E_SECTOR_STATE["seen_s2"] = s2_clean
        if last_lap_s > 0.0 and _R3E_SECTOR_STATE["seen_s1"] > 0.0 and _R3E_SECTOR_STATE["seen_s2"] > 0.0:
            diff_s3 = last_lap_s - (_R3E_SECTOR_STATE["seen_s1"] + _R3E_SECTOR_STATE["seen_s2"])
            if 1.0 < diff_s3 < 300.0:
                _R3E_SECTOR_STATE["last_s3"] = round(diff_s3, 3)

        s1_safe = max(0, min(int(s1_clean * 1000), 65535)) if s1_clean > 0 else 0
        s2_safe = max(0, min(int(s2_clean * 1000), 65535)) if s2_clean > 0 else 0
        lap_num = max(1, current_lap)
        pos_num = max(1, pos)

        dash_state["gear"] = gear_str
        dash_state["speed"] = speed_kmh
        dash_state["rpm"] = rpm
        dash_state["max_rpm"] = max_rpm
        dash_state["fuel"] = fuel_in_tank
        dash_state["fuel_laps"] = fuel_laps
        dash_state["fuel_per_lap"] = round(avg_fuel, 2) if _R3E_FUEL_STATE["history"] else 0.0
        dash_state["cur_lap"] = curr_lap_s
        dash_state["last_lap"] = last_lap_s
        dash_state["best_lap"] = best_lap_s
        dash_state["lap"] = lap_num
        dash_state["pos"] = pos_num
        dash_state["s1"] = s1_clean
        dash_state["s2"] = s2_clean
        dash_state["s3"] = _R3E_SECTOR_STATE["last_s3"]
        dash_state["tyre_fl"] = temp_fl
        dash_state["tyre_fr"] = temp_fr
        dash_state["tyre_rl"] = temp_rl
        dash_state["tyre_rr"] = temp_rr
        dash_state["has_imo"] = has_real_imo
        dash_state["tyre_fl_imo"] = imo_fl
        dash_state["tyre_fr_imo"] = imo_fr
        dash_state["tyre_rl_imo"] = imo_rl
        dash_state["tyre_rr_imo"] = imo_rr
        dash_state["tyre_press"] = [p_fl, p_fr, p_rl, p_rr]
        dash_state["tyre_wear"] = [life_fl, life_fr, life_rl, life_rr]
        dash_state["tc"] = max(0, tc_v)
        dash_state["abs"] = max(0, abs_v)
        dash_state["brake_bias"] = bb_v
        dash_state["flag"] = flag_str
        dash_state["air_temp"] = air_temp_c
        dash_state["track_temp"] = track_temp_c
        eng_t = 92 if rpm > 1200 else max(20, track_temp_c)
        dash_state["engine_temp"] = eng_t
        dash_state["packets"] += 1
        dash_state["last_ts"] = tempo
        dash_state["hz_counter"] += 1
        if tempo - dash_state["hz_timer"] >= 1.0:
            dash_state["hz"] = dash_state["hz_counter"] / (tempo - dash_state["hz_timer"])
            dash_state["hz_counter"] = 0
            dash_state["hz_timer"] = tempo

        track_len_m = 5000
        settore = 0 if lap_progress < 0.333 else (1 if lap_progress < 0.666 else 2)
        distanza_giro = float(max(0.0, min(1.0, lap_progress)) * track_len_m)
        distanza_tot = float(((lap_num - 1) + max(0.0, min(1.0, lap_progress))) * track_len_m)

        hdr = "<HBBBBQfIBB"
        h1 = struct.pack(hdr, 2020, 1, 0, 1, 1, 123456789, float(tempo), _fid, 0, 0)
        p1 = bytearray(227)
        struct.pack_into("<BbbBH", p1, 0, 1, track_temp_c, air_temp_c, 60, track_len_m)
        struct.pack_into("<B", p1, 6, 10)
        struct.pack_into("<B", p1, 19, 1)

        h2 = struct.pack(hdr, 2020, 1, 0, 1, 2, 123456789, float(tempo), _fid, 0, 0)
        p2 = bytearray(1168)
        struct.pack_into("<ffHHf", p2, 0, last_lap_s, curr_lap_s, s1_safe, s2_safe, best_lap_s)
        struct.pack_into("<ff", p2, 24, distanza_giro, distanza_tot)
        struct.pack_into("<BBBB", p2, 34, pos_num, lap_num, 0, settore)
        struct.pack_into("<BBBBB", p2, 41, 0, 0, 2, 4, 2)

        h6 = struct.pack(hdr, 2020, 1, 0, 1, 6, 123456789, float(tempo), _fid, 0, 0)
        p6 = bytearray(1323)
        struct.pack_into("<HfffB", p6, 0, speed_kmh, 1.0, 0.0, 0.0, 0)
        struct.pack_into("<bHBBH", p6, 15, int(gear_display), rpm, 0, led_pct, led_bits)
        struct.pack_into("<BBBB", p6, 44, temp_rl, temp_rr, temp_fl, temp_fr)
        struct.pack_into("<BBBB", p6, 48, temp_rl, temp_rr, temp_fl, temp_fr)
        struct.pack_into("<HHHH", p6, 20, 320, 320, 340, 340); struct.pack_into("<H", p6, 36, eng_t if "eng_t" in locals() else int(SHM_DATA.get("engine_temp", 92))); struct.pack_into("<H", p6, 52, eng_t)

        h7 = struct.pack(hdr, 2020, 1, 0, 1, 7, 123456789, float(tempo), _fid, 0, 0)
        p7 = bytearray(1320)
        tc_f1 = 0 if tc_v <= 0 else (1 if tc_v <= 3 else 2)
        abs_f1 = 1 if abs_v > 0 else 0
        bb_f1 = max(20, min(90, int(round(bb_v)))) if bb_v > 0 else 50
        struct.pack_into("<BBBBB", p7, 0, tc_f1, abs_f1, 1, bb_f1, 0)
        struct.pack_into("<fff", p7, 5, fuel_in_tank, fuel_cap, fuel_laps)
        soglia_cambiata = int(max_rpm * 0.93) if max_rpm > 2000 else 7500
        struct.pack_into("<HHB", p7, 17, soglia_cambiata, idle_rpm, 8)
        struct.pack_into("<BBBB", p7, 25, max(0, 100 - life_rl), max(0, 100 - life_rr), max(0, 100 - life_fl), max(0, 100 - life_fr))
        struct.pack_into("<BB", p7, 29, 16, 16)
        _fia_map = {"green": 1, "blue": 2, "yellow": 3, "white": 4}
        if in_fuorigiri:
            fia_flag = 2 if int(tempo * 20) % 2 == 0 else 4
        else:
            fia_flag = _fia_map.get(flag_str, 0)
        struct.pack_into("<b", p7, 42, fia_flag)
        # --- INIZIO PATCH ERS UNIVERSALE ---
        struct.pack_into("<fBfff", p7, 43, 0.0, 0, 0.0, 0.0, 0.0)
        if "dash_state" in locals():
            dash_state["ers"] = 0.0
            dash_state["ers_active"] = 0
            dash_state["ers_charging"] = 0
            dash_state["ers_mode"] = 0
        # --- FINE PATCH ERS ---

        _fid = (globals().get("_OSW_FRAME_ID", 0) + 1) & 0xFFFFFFFF
        globals()["_OSW_FRAME_ID"] = _fid
        h0 = struct.pack(hdr, 2020, 1, 0, 1, 0, 123456789, float(tempo), _fid, 0, 0)
        p0 = bytearray(1440)
        out_sock.sendto(h0 + p0, (ip_display, porta_display))
        out_sock.sendto(h1 + p1, (ip_display, porta_display))
        out_sock.sendto(h2 + p2, (ip_display, porta_display))
        out_sock.sendto(h6 + p6, (ip_display, porta_display))
        out_sock.sendto(h7 + p7, (ip_display, porta_display))
    except Exception as e:
        logger.warning(f"Errore pacchetto RRRE: {e}")
