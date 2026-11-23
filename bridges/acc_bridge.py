import struct
import time
import socket

SHM_DATA = {
    "ts": 0.0,
    "rpm": 0,
    "max_rpm": 8200,
    "fuel": 50.0,
    "tyres": (75, 75, 75, 75),
    "has_imo": False,
    "imo": None,
    "press": (0.0, 0.0, 0.0, 0.0),
    "wear": (100, 100, 100, 100),
    "tc": 0,
    "abs": 0,
    "bb": 0.0,
    "engine_temp": 90,
    "flag": "none",
    "sock": None,
}
_ACC_TYRE_EMA = {
    "fl": None, "fr": None, "rl": None, "rr": None,
    "fl_i": None, "fl_m": None, "fl_o": None,
    "fr_i": None, "fr_m": None, "fr_o": None,
    "rl_i": None, "rl_m": None, "rl_o": None,
    "rr_i": None, "rr_m": None, "rr_o": None,
}
_ACC_FUEL_STATE = {"last_lap": -1, "start_fuel": None, "history": []}
_ACC_SECTOR_STATE = {"last_s3": 0.0}


def _filtra_temp_acc(ruota, val_grezzo, fallback_temp=75, alpha=0.25):
    if not (0.5 < val_grezzo < 180.0):
        val_grezzo = float(fallback_temp)
    prev = _ACC_TYRE_EMA.get(ruota)
    if prev is None or abs(val_grezzo - prev) > 35.0:
        filtrato = float(val_grezzo)
    else:
        filtrato = (prev * (1.0 - alpha)) + (val_grezzo * alpha)
    _ACC_TYRE_EMA[ruota] = filtrato
    return max(15, min(int(round(filtrato)), 150))


def leggi_shm_acc():
    if SHM_DATA["sock"] is None:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(("127.0.0.1", 9001))
            s.setblocking(False)
            SHM_DATA["sock"] = s
        except Exception:
            return
    while True:
        try:
            pkt, _ = SHM_DATA["sock"].recvfrom(256)
            if len(pkt) >= 40 and pkt[:4] == b"ACCS":
                _, rpms, max_rpm, gear, speed_kmh, fuel, t_fl, t_fr, t_rl, t_rr = struct.unpack_from("<4siiiffffff", pkt, 0)
                if 0 <= rpms <= 18000:
                    SHM_DATA["rpm"] = rpms
                if 5000 <= max_rpm <= 18000:
                    SHM_DATA["max_rpm"] = max_rpm
                if 0.0 <= fuel <= 200.0:
                    SHM_DATA["fuel"] = fuel
                fl_f = _filtra_temp_acc("fl", t_fl, 75)
                fr_f = _filtra_temp_acc("fr", t_fr, 75)
                rl_f = _filtra_temp_acc("rl", t_rl, 75)
                rr_f = _filtra_temp_acc("rr", t_rr, 75)
                SHM_DATA["tyres"] = (fl_f, fr_f, rl_f, rr_f)

                if len(pkt) >= 72:
                    pf1, pf2, pf3, pf4, wf1, wf2, wf3, wf4 = struct.unpack_from("<ffffffff", pkt, 40)
                    SHM_DATA["press"] = (
                        round(pf1, 1) if 5.0 <= pf1 <= 60.0 else 0.0,
                        round(pf2, 1) if 5.0 <= pf2 <= 60.0 else 0.0,
                        round(pf3, 1) if 5.0 <= pf3 <= 60.0 else 0.0,
                        round(pf4, 1) if 5.0 <= pf4 <= 60.0 else 0.0,
                    )

                    def _norm_acc_life(w):
                        if 0.0 <= w <= 1.0:
                            return max(0, min(int(round((1.0 - w) * 100.0)), 100))
                        if 1.0 < w <= 100.0:
                            return max(0, min(int(round(w)), 100))
                        return 100

                    SHM_DATA["wear"] = (_norm_acc_life(wf1), _norm_acc_life(wf2), _norm_acc_life(wf3), _norm_acc_life(wf4))

                if len(pkt) >= 84:
                    tc_v, abs_v, bb_raw = struct.unpack_from("<iif", pkt, 72)
                    SHM_DATA["tc"] = max(0, tc_v)
                    SHM_DATA["abs"] = max(0, abs_v)
                    SHM_DATA["bb"] = round(bb_raw * 100.0, 1) if 0.2 <= bb_raw <= 0.9 else (round(bb_raw, 1) if 20.0 <= bb_raw <= 90.0 else 0.0)
                    if len(pkt) >= 136:
                        flag_id, = struct.unpack_from("<i", pkt, 132)
                        SHM_DATA["flag"] = {1: "blue", 2: "yellow", 4: "white", 5: "checkered", 6: "green"}.get(flag_id, "none")
                    if len(pkt) >= 140:
                        wt_v, = struct.unpack_from("<f", pkt, 136)
                        if 10.0 < wt_v < 180.0:
                            SHM_DATA["engine_temp"] = int(round(wt_v))

                if len(pkt) >= 132:
                    imo_raw = struct.unpack_from("<12f", pkt, 84)
                    if any(0.5 < v < 180.0 for v in imo_raw):
                        SHM_DATA["has_imo"] = True
                        SHM_DATA["imo"] = (
                            [_filtra_temp_acc("fl_i", imo_raw[0], fl_f), _filtra_temp_acc("fl_m", imo_raw[1], fl_f), _filtra_temp_acc("fl_o", imo_raw[2], fl_f)],
                            [_filtra_temp_acc("fr_i", imo_raw[3], fr_f), _filtra_temp_acc("fr_m", imo_raw[4], fr_f), _filtra_temp_acc("fr_o", imo_raw[5], fr_f)],
                            [_filtra_temp_acc("rl_i", imo_raw[6], rl_f), _filtra_temp_acc("rl_m", imo_raw[7], rl_f), _filtra_temp_acc("rl_o", imo_raw[8], rl_f)],
                            [_filtra_temp_acc("rr_i", imo_raw[9], rr_f), _filtra_temp_acc("rr_m", imo_raw[10], rr_f), _filtra_temp_acc("rr_o", imo_raw[11], rr_f)],
                        )
                    else:
                        SHM_DATA["has_imo"] = False
                        SHM_DATA["imo"] = None
                else:
                    SHM_DATA["has_imo"] = False
                    SHM_DATA["imo"] = None

                SHM_DATA["ts"] = time.time()
        except Exception:
            break


ACC_STATE = {
    "conn_id": -1,
    "player_car": -1,
    "max_rpm": 7200,
    "track_len": 5000,
    "air_temp": 22,
    "track_temp": 26,
    "last_hs_ts": 0.0,
    "last_rx_ts": 0.0,
    "last_slow_ts": 0.0,
}


def acc_send_handshake(sock, acc_port=9000, target_ip="127.0.0.1"):
    buf = bytearray()
    buf += struct.pack("<BB", 1, 4)
    for s in ("OSW_Bridge", "asd"):
        b = s.encode("utf-8")
        buf += struct.pack("<H", len(b)) + b
    buf += struct.pack("<i", 16)
    buf += struct.pack("<H", 0)
    try:
        sock.sendto(bytes(buf), (target_ip, acc_port))
        if target_ip != "127.0.0.1":
            sock.sendto(bytes(buf), ("127.0.0.1", acc_port))
    except Exception:
        pass


def acc_parse_lap_info(data, off):
    if off + 9 > len(data):
        return 0, [], len(data)
    lap_ms, car_idx, drv_idx, split_cnt = struct.unpack_from("<iHHB", data, off)
    off += 9
    splits = []
    for _ in range(split_cnt):
        if off + 4 <= len(data):
            sp, = struct.unpack_from("<i", data, off)
            splits.append(sp if 0 < sp < 600000 else 0)
            off += 4
    off += 4
    return lap_ms, splits, off
def elabora_pacchetto_acc(data, out_sock, ip_display, porta_display, dash_state, logger):
    if not data or len(data) < 2:
        return
    tempo = time.time()
    ACC_STATE["last_rx_ts"] = tempo
    leggi_shm_acc()
    msg_type = data[0]

    if msg_type == 1 and len(data) >= 6:
        conn_id, success = struct.unpack_from("<iB", data, 1)
        if success:
            ACC_STATE["conn_id"] = conn_id
            logger.info(f"ACC Connesso! Connection ID: {conn_id}")

    elif msg_type == 2 and len(data) >= 30:
        try:
            focused_car, = struct.unpack_from("<i", data, 15)
            if focused_car >= 0:
                ACC_STATE["player_car"] = focused_car
            off = 19
            for _ in range(3):
                if off + 2 <= len(data):
                    slen, = struct.unpack_from("<H", data, off)
                    off += 2 + slen
            if off + 16 <= len(data):
                ACC_STATE["air_temp"] = max(-10, min(int(data[off + 11]), 80))
                ACC_STATE["track_temp"] = max(-10, min(int(data[off + 12]), 90))
        except Exception:
            pass

    elif msg_type == 3 and len(data) >= 38:
        try:
            car_idx, drv_idx, drv_cnt, gear_raw = struct.unpack_from("<HHBB", data, 1)
            if ACC_STATE["player_car"] == -1:
                ACC_STATE["player_car"] = car_idx
            if car_idx != ACC_STATE["player_car"]:
                return

            if gear_raw == 0:
                gear_display, gear_str = -1, "R"
            elif gear_raw == 1:
                gear_display, gear_str = 0, "N"
            else:
                gear_display = max(1, min(gear_raw - 1, 8))
                gear_str = str(gear_display)

            speed_kmh, pos, cup_pos, track_pos, spline_pos, laps = struct.unpack_from("<HHHHfH", data, 20)
            speed_kmh = max(0, min(int(speed_kmh), 360))
            current_lap = int(laps) + 1
            lap_progress = max(0.0, min(float(spline_pos), 1.0))

            off = 38
            best_ms, _, off = acc_parse_lap_info(data, off)
            last_ms, last_splits, off = acc_parse_lap_info(data, off)
            curr_ms, curr_splits, off = acc_parse_lap_info(data, off)

            if (tempo - SHM_DATA["ts"]) < 1.0:
                rpm = SHM_DATA["rpm"]
                max_rpm = SHM_DATA["max_rpm"]
                fuel_l = SHM_DATA["fuel"]
                t_fl, t_fr, t_rl, t_rr = SHM_DATA["tyres"]
                has_real_imo = SHM_DATA["has_imo"]
                imo_data = SHM_DATA["imo"]
                in_pausa = (rpm == 0)
            else:
                max_rpm = 8200
                rpm = 0
                fuel_l = 0.0
                fallback_t = max(15, min(ACC_STATE["track_temp"], 45))
                t_fl = t_fr = t_rl = t_rr = fallback_t
                has_real_imo = False
                imo_data = None
                in_pausa = True

            curr_lap_time = (curr_ms / 1000.0) if 0 < curr_ms < 600000 else 0.0
            last_lap_time = (last_ms / 1000.0) if 0 < last_ms < 600000 else 0.0
            best_lap_time = (best_ms / 1000.0) if 0 < best_ms < 600000 else 0.0

            s1_time_ms = curr_splits[0] if len(curr_splits) >= 1 and curr_splits[0] > 0 else (last_splits[0] if len(last_splits) >= 1 else 0)
            s2_time_ms = curr_splits[1] if len(curr_splits) >= 2 and curr_splits[1] > 0 else (last_splits[1] if len(last_splits) >= 2 else 0)

            s3_s = 0.0
            if len(last_splits) >= 3 and last_splits[2] > 0:
                s3_s = round(last_splits[2] / 1000.0, 3)
            elif last_lap_time > 0.0 and len(last_splits) >= 2 and last_splits[0] > 0 and last_splits[1] > 0:
                diff_s3 = last_lap_time - ((last_splits[0] + last_splits[1]) / 1000.0)
                if 1.0 < diff_s3 < 300.0:
                    s3_s = round(diff_s3, 3)
            if s3_s > 0.0:
                _ACC_SECTOR_STATE["last_s3"] = s3_s

            idle_rpm = int(max_rpm * 0.40)
            if in_pausa or max_rpm <= idle_rpm:
                led_pct, led_bits, in_fuorigiri = 0, 0, False
            else:
                ratio_rpm = (rpm - idle_rpm) / float(max_rpm - idle_rpm)
                led_pct = int(max(0, min(100, (ratio_rpm / 0.88) * 100)))
                in_fuorigiri = (led_pct >= 100)
                if in_fuorigiri:
                    lampeggio = int(tempo * 18) % 2 == 0
                    led_bits = 0x7FFF if lampeggio else 0
                    led_pct = 100 if lampeggio else 0
                else:
                    num_leds = int(round((led_pct / 100.0) * 15))
                    led_bits = (1 << num_leds) - 1 if num_leds > 0 else 0

            dash_state["gear"] = gear_str
            dash_state["speed"] = speed_kmh
            dash_state["rpm"] = rpm
            dash_state["max_rpm"] = max_rpm
            if _ACC_FUEL_STATE["last_lap"] != current_lap:
                if _ACC_FUEL_STATE["last_lap"] > 0 and _ACC_FUEL_STATE["start_fuel"] is not None and fuel_l > 0:
                    used = _ACC_FUEL_STATE["start_fuel"] - fuel_l
                    if 0.05 < used < 25.0:
                        _ACC_FUEL_STATE["history"].append(used)
                        if len(_ACC_FUEL_STATE["history"]) > 3:
                            _ACC_FUEL_STATE["history"].pop(0)
                _ACC_FUEL_STATE["last_lap"] = current_lap
                if fuel_l > 0:
                    _ACC_FUEL_STATE["start_fuel"] = fuel_l
            elif _ACC_FUEL_STATE["start_fuel"] is not None and fuel_l > _ACC_FUEL_STATE["start_fuel"] + 0.5:
                _ACC_FUEL_STATE["start_fuel"] = fuel_l
            avg_fuel_acc = (sum(_ACC_FUEL_STATE["history"]) / len(_ACC_FUEL_STATE["history"])) if _ACC_FUEL_STATE["history"] else 2.5
            fuel_laps_acc = round(fuel_l / avg_fuel_acc, 1) if (fuel_l > 0 and avg_fuel_acc > 0.05) else 0.0

            dash_state["fuel"] = fuel_l
            dash_state["fuel_laps"] = fuel_laps_acc
            dash_state["fuel_per_lap"] = round(avg_fuel_acc, 2) if _ACC_FUEL_STATE["history"] else 0.0
            dash_state["cur_lap"] = curr_lap_time
            dash_state["last_lap"] = last_lap_time
            dash_state["best_lap"] = best_lap_time
            dash_state["lap"] = current_lap
            dash_state["pos"] = max(1, int(pos))
            dash_state["s1"] = s1_time_ms / 1000.0
            dash_state["s2"] = s2_time_ms / 1000.0
            dash_state["s3"] = _ACC_SECTOR_STATE["last_s3"]
            dash_state["tyre_fl"] = t_fl
            dash_state["tyre_fr"] = t_fr
            dash_state["tyre_rl"] = t_rl
            dash_state["tyre_rr"] = t_rr
            dash_state["has_imo"] = has_real_imo
            if has_real_imo and imo_data is not None:
                dash_state["tyre_fl_imo"] = imo_data[0]
                dash_state["tyre_fr_imo"] = imo_data[1]
                dash_state["tyre_rl_imo"] = imo_data[2]
                dash_state["tyre_rr_imo"] = imo_data[3]
            else:
                dash_state["tyre_fl_imo"] = [t_fl, t_fl, t_fl]
                dash_state["tyre_fr_imo"] = [t_fr, t_fr, t_fr]
                dash_state["tyre_rl_imo"] = [t_rl, t_rl, t_rl]
                dash_state["tyre_rr_imo"] = [t_rr, t_rr, t_rr]
            dash_state["tyre_press"] = list(SHM_DATA["press"])
            dash_state["tyre_wear"] = list(SHM_DATA["wear"])
            dash_state["tc"] = SHM_DATA["tc"]
            dash_state["abs"] = SHM_DATA["abs"]
            dash_state["brake_bias"] = SHM_DATA["bb"]
            dash_state["ers"] = -1
            dash_state["ers_active"] = 0
            dash_state["ers_charging"] = 0
            dash_state["ers_mode"] = 0
            dash_state["flag"] = SHM_DATA["flag"]
            dash_state["air_temp"] = ACC_STATE["air_temp"]
            dash_state["track_temp"] = ACC_STATE["track_temp"]
            dash_state["engine_temp"] = SHM_DATA["engine_temp"]
            dash_state["packets"] += 1
            dash_state["last_ts"] = tempo
            dash_state["hz_counter"] += 1
            if tempo - dash_state["hz_timer"] >= 1.0:
                dash_state["hz"] = dash_state["hz_counter"] / (tempo - dash_state["hz_timer"])
                dash_state["hz_counter"] = 0
                dash_state["hz_timer"] = tempo

            settore = 0 if lap_progress < 0.333 else (1 if lap_progress < 0.666 else 2)
            track_len_m = ACC_STATE["track_len"]
            distanza_giro = float(lap_progress * track_len_m)
            distanza_tot = float(((current_lap - 1) + lap_progress) * track_len_m)
            s1_safe = max(0, min(int(s1_time_ms), 65535))
            s2_safe = max(0, min(int(s2_time_ms), 65535))

            hdr = "<HBBBBQfIBB"
            h1 = struct.pack(hdr, 2020, 1, 0, 1, 1, 123456789, float(tempo), 0, 0, 0)
            p1 = bytearray(227)
            struct.pack_into("<BbbBH", p1, 0, 1, ACC_STATE["track_temp"], ACC_STATE["air_temp"], 60, track_len_m)
            struct.pack_into("<B", p1, 6, 10)
            struct.pack_into("<B", p1, 19, 1)

            h2 = struct.pack(hdr, 2020, 1, 0, 1, 2, 123456789, float(tempo), 0, 0, 0)
            p2 = bytearray(1168)
            struct.pack_into("<ffHHf", p2, 0, last_lap_time, curr_lap_time, s1_safe, s2_safe, best_lap_time)
            struct.pack_into("<ff", p2, 24, distanza_giro, distanza_tot)
            struct.pack_into("<BBBB", p2, 34, max(1, int(pos)), current_lap, 0, settore)
            struct.pack_into("<BBB", p2, 41, 0, 0, 2)

            h6 = struct.pack(hdr, 2020, 1, 0, 1, 6, 123456789, float(tempo), 0, 0, 0)
            p6 = bytearray(1323)
            struct.pack_into("<HfffB", p6, 0, speed_kmh, 1.0, 0.0, 0.0, 0)
            struct.pack_into("<bHBBH", p6, 15, int(gear_display), rpm, 0, led_pct, led_bits)
            struct.pack_into("<BBBB", p6, 44, t_rl, t_rr, t_fl, t_fr)
            struct.pack_into("<BBBB", p6, 48, t_rl, t_rr, t_fl, t_fr)
            struct.pack_into("<HHHH", p6, 20, 320, 320, 340, 340); struct.pack_into("<H", p6, 36, eng_t if "eng_t" in locals() else int(SHM_DATA.get("engine_temp", 92))); struct.pack_into("<H", p6, 52, max(0, min(int(SHM_DATA["engine_temp"]), 250)))

            h7 = struct.pack(hdr, 2020, 1, 0, 1, 7, 123456789, float(tempo), 0, 0, 0)
            p7 = bytearray(1320)
            tc_f1 = 0 if SHM_DATA["tc"] <= 0 else (1 if SHM_DATA["tc"] <= 4 else 2)
            abs_f1 = 1 if SHM_DATA["abs"] > 0 else 0
            bb_f1 = max(20, min(90, int(round(SHM_DATA["bb"])))) if SHM_DATA["bb"] > 0 else 50
            struct.pack_into("<BBBBB", p7, 0, tc_f1, abs_f1, 1, bb_f1, 0)
            struct.pack_into("<fff", p7, 5, fuel_l, 100.0, fuel_laps_acc)
            soglia_cambiata = int(max_rpm * 0.88) if max_rpm > 2000 else 7500
            struct.pack_into("<HHB", p7, 17, soglia_cambiata, idle_rpm, 8)
            w_acc = SHM_DATA["wear"]
            w_fl = max(0, min(100, int(round(100.0 - w_acc[0]))))
            w_fr = max(0, min(100, int(round(100.0 - w_acc[1]))))
            w_rl = max(0, min(100, int(round(100.0 - w_acc[2]))))
            w_rr = max(0, min(100, int(round(100.0 - w_acc[3]))))
            struct.pack_into("<BBBB", p7, 25, w_rl, w_rr, w_fl, w_fr)
            struct.pack_into("<BB", p7, 29, 16, 16)
            _fia_map = {"green": 1, "blue": 2, "yellow": 3, "white": 4}
            if in_fuorigiri:
                fia_flag = 2 if int(tempo * 20) % 2 == 0 else 4
            else:
                fia_flag = _fia_map.get(SHM_DATA["flag"], 0)
            struct.pack_into("<b", p7, 42, fia_flag)

            out_sock.sendto(h6 + p6, (ip_display, porta_display))
            if tempo - ACC_STATE["last_slow_ts"] >= 0.2:
                ACC_STATE["last_slow_ts"] = tempo
                out_sock.sendto(h1 + p1, (ip_display, porta_display))
                out_sock.sendto(h2 + p2, (ip_display, porta_display))
                out_sock.sendto(h7 + p7, (ip_display, porta_display))
        except Exception:
            pass
