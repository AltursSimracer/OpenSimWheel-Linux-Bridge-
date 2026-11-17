import socket
import struct
import time

AC_PKT_FMT = "<4siififfiiiiiiifffffff"
AC_PKT_SIZE = struct.calcsize(AC_PKT_FMT)

_AC_TYRE_EMA = {"fl": None, "fr": None, "rl": None, "rr": None}
_AC_FUEL_STATE = {"last_lap": -1, "start_fuel": None, "history": list()}

def _filtra_temp_ac(ruota, val_grezzo, fallback_temp=25, alpha=0.25):
    if not (0.5 < val_grezzo < 180.0):
        val_grezzo = float(fallback_temp)
    prev = _AC_TYRE_EMA.get(ruota)
    if prev is None or abs(val_grezzo - prev) > 35.0:
        filtrato = float(val_grezzo)
    else:
        filtrato = (prev * (1.0 - alpha)) + (val_grezzo * alpha)
    _AC_TYRE_EMA[ruota] = filtrato
    return max(10, min(int(round(filtrato)), 150))

def elabora_pacchetto_ac_ace(data, out_sock, ip_display, porta_display, dash_state, logger, sim_name="AC"):
    if not data or len(data) < AC_PKT_SIZE:
        return

    try:
        unpacked = struct.unpack_from(AC_PKT_FMT, data, 0)
        if unpacked.__getitem__(0) != b"ACSM":
            return

        (_, rpm, max_rpm, speed_f, gear_raw,
         fuel_l, max_fuel_l, cur_lap_ms, last_lap_ms, best_lap_ms,
         s1_ms, s2_ms, current_lap, pos, lap_progress,
         t_fl, t_fr, t_rl, t_rr, air_t, track_t) = unpacked
        p_fl = p_fr = p_rl = p_rr = 0.0
        life_fl = life_fr = life_rl = life_rr = 100
        if len(data) >= AC_PKT_SIZE + 32:
            pf1, pf2, pf3, pf4, wf1, wf2, wf3, wf4 = struct.unpack_from("<ffffffff", data, AC_PKT_SIZE)
            p_fl = round(pf1, 1) if 5.0 <= pf1 <= 60.0 else 0.0
            p_fr = round(pf2, 1) if 5.0 <= pf2 <= 60.0 else 0.0
            p_rl = round(pf3, 1) if 5.0 <= pf3 <= 60.0 else 0.0
            p_rr = round(pf4, 1) if 5.0 <= pf4 <= 60.0 else 0.0
            def _norm_life(w):
                if 0.0 <= w <= 1.0:
                    return max(0, min(int(round((1.0 - w) * 100.0)), 100))
                if 1.0 < w <= 100.0:
                    return max(0, min(int(round(w)), 100))
                return 100
            life_fl, life_fr, life_rl, life_rr = _norm_life(wf1), _norm_life(wf2), _norm_life(wf3), _norm_life(wf4)
        tc_v = abs_v = 0
        bb_v = 0.0
        flag_str = "none"
        if len(data) >= AC_PKT_SIZE + 48:
            tc_v, abs_v, bb_raw, flag_id = struct.unpack_from("<iifi", data, AC_PKT_SIZE + 32)
            bb_v = round(bb_raw * 100.0, 1) if 0.2 <= bb_raw <= 0.9 else (round(bb_raw, 1) if 20.0 <= bb_raw <= 90.0 else 0.0)
            flag_map = {1: "blue", 2: "yellow", 4: "white", 5: "checkered"}
            flag_str = flag_map.get(flag_id, "none")

        tempo = time.time()
        rpm = max(0, min(rpm, 20000))
        max_rpm = max(4000, min(max_rpm, 20000)) if max_rpm > 1000 else 8500
        speed_kmh = max(0, min(int(round(speed_f)), 380))

        if gear_raw == 0:
            gear_display = -1
            gear_str = "R"
        elif gear_raw == 1:
            gear_display = 0
            gear_str = "N"
        else:
            gear_display = max(1, min(gear_raw - 1, 8))
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
        if _AC_FUEL_STATE["last_lap"] != lap_now:
            if _AC_FUEL_STATE["last_lap"] > 0 and _AC_FUEL_STATE["start_fuel"] is not None and fuel_in_tank > 0:
                used = _AC_FUEL_STATE["start_fuel"] - fuel_in_tank
                if 0.05 < used < 25.0:
                    _AC_FUEL_STATE["history"].append(used)
                    if len(_AC_FUEL_STATE["history"]) > 3:
                        _AC_FUEL_STATE["history"].pop(0)
            _AC_FUEL_STATE["last_lap"] = lap_now
            if fuel_in_tank > 0:
                _AC_FUEL_STATE["start_fuel"] = fuel_in_tank
        avg_fuel = (sum(_AC_FUEL_STATE["history"]) / len(_AC_FUEL_STATE["history"])) if _AC_FUEL_STATE["history"] else 2.2
        fuel_laps = round(fuel_in_tank / avg_fuel, 1) if (fuel_in_tank > 0 and avg_fuel > 0.05) else 0.0

        air_temp_c = max(-10, min(int(round(air_t)), 60))
        track_temp_c = max(-10, min(int(round(track_t)), 80))
        fallback_temp = max(15, min(track_temp_c if track_temp_c > 0 else 25, 45))

        temp_fl = _filtra_temp_ac("fl", t_fl, fallback_temp)
        temp_fr = _filtra_temp_ac("fr", t_fr, fallback_temp)
        temp_rl = _filtra_temp_ac("rl", t_rl, fallback_temp)
        temp_rr = _filtra_temp_ac("rr", t_rr, fallback_temp)

        curr_lap_s = max(0.0, cur_lap_ms / 1000.0)
        last_lap_s = max(0.0, last_lap_ms / 1000.0)
        best_lap_s = max(0.0, best_lap_ms / 1000.0)
        s1_safe = max(0, min(s1_ms, 65535))
        s2_safe = max(0, min(s2_ms, 65535))
        lap_num = max(1, current_lap)
        pos_num = max(1, pos)

        dash_state["gear"] = gear_str
        dash_state["speed"] = speed_kmh
        dash_state["rpm"] = rpm
        dash_state["max_rpm"] = max_rpm
        dash_state["fuel"] = fuel_in_tank
        dash_state["fuel_laps"] = fuel_laps
        dash_state["fuel_per_lap"] = round(avg_fuel, 2) if _AC_FUEL_STATE["history"] else 0.0
        dash_state["cur_lap"] = curr_lap_s
        dash_state["last_lap"] = last_lap_s
        dash_state["best_lap"] = best_lap_s
        dash_state["lap"] = lap_num
        dash_state["pos"] = pos_num
        dash_state["s1"] = s1_ms / 1000.0
        dash_state["s2"] = s2_ms / 1000.0
        dash_state["tyre_fl"] = temp_fl
        dash_state["tyre_fr"] = temp_fr
        dash_state["tyre_rl"] = temp_rl
        dash_state["tyre_rr"] = temp_rr
        dash_state["tyre_fl_imo"] = list((temp_fl, temp_fl, temp_fl))
        dash_state["tyre_fr_imo"] = list((temp_fr, temp_fr, temp_fr))
        dash_state["tyre_rl_imo"] = list((temp_rl, temp_rl, temp_rl))
        dash_state["tyre_rr_imo"] = list((temp_rr, temp_rr, temp_rr))
        dash_state["tyre_press"] = list((p_fl, p_fr, p_rl, p_rr))
        dash_state["tyre_wear"] = list((life_fl, life_fr, life_rl, life_rr))
        dash_state["tc"] = max(0, tc_v)
        dash_state["abs"] = max(0, abs_v)
        dash_state["brake_bias"] = bb_v
        dash_state["flag"] = flag_str
        dash_state["air_temp"] = air_temp_c
        dash_state["track_temp"] = track_temp_c
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
        h1 = struct.pack(hdr, 2020, 1, 0, 1, 1, 123456789, float(tempo), 0, 0, 0)
        p1 = bytearray(227)
        struct.pack_into("<BbbBH", p1, 0, 1, track_temp_c, air_temp_c, 60, track_len_m)
        struct.pack_into("<B", p1, 6, 10)
        struct.pack_into("<B", p1, 19, 1)

        h2 = struct.pack(hdr, 2020, 1, 0, 1, 2, 123456789, float(tempo), 0, 0, 0)
        p2 = bytearray(1168)
        struct.pack_into("<ffHHf", p2, 0, last_lap_s, curr_lap_s, s1_safe, s2_safe, best_lap_s)
        struct.pack_into("<ff", p2, 24, distanza_giro, distanza_tot)
        struct.pack_into("<BBBB", p2, 34, pos_num, lap_num, 0, settore)
        struct.pack_into("<BBB", p2, 41, 0, 0, 2)

        h6 = struct.pack(hdr, 2020, 1, 0, 1, 6, 123456789, float(tempo), 0, 0, 0)
        p6 = bytearray(1323)
        struct.pack_into("<HfffB", p6, 0, speed_kmh, 1.0, 0.0, 0.0, 0)
        struct.pack_into("<bHBBH", p6, 15, int(gear_display), rpm, 0, led_pct, led_bits)
        struct.pack_into("<BBBB", p6, 44, temp_rl, temp_rr, temp_fl, temp_fr)
        struct.pack_into("<BBBB", p6, 48, temp_rl, temp_rr, temp_fl, temp_fr)

        h7 = struct.pack(hdr, 2020, 1, 0, 1, 7, 123456789, float(tempo), 0, 0, 0)
        p7 = bytearray(1320)
        struct.pack_into("<BBBBB", p7, 0, 2, 1, 1, 50, 0)
        struct.pack_into("<fff", p7, 5, fuel_in_tank, fuel_cap, fuel_laps)
        soglia_cambiata = int(max_rpm * 0.93) if max_rpm > 2000 else 7500
        struct.pack_into("<HHB", p7, 17, soglia_cambiata, idle_rpm, 8)
        struct.pack_into("<BBBB", p7, 25, max(0, 100 - life_rl), max(0, 100 - life_rr), max(0, 100 - life_fl), max(0, 100 - life_fr))
        struct.pack_into("<BB", p7, 29, 16, 16)
        fia_flag = (2 if int(tempo * 20) % 2 == 0 else 4) if in_fuorigiri else 0
        struct.pack_into("<b", p7, 42, fia_flag)

        out_sock.sendto(h1 + p1, (ip_display, porta_display))
        out_sock.sendto(h2 + p2, (ip_display, porta_display))
        out_sock.sendto(h6 + p6, (ip_display, porta_display))
        out_sock.sendto(h7 + p7, (ip_display, porta_display))
    except Exception as e:
        logger.warning(f"Errore pacchetto AC/ACE: {e}")
