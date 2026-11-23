import struct
import time
import math

_TYRE_EMA_STATE = {"fl": None, "fr": None, "rl": None, "rr": None}

def filtra_temp_gomma(ruota, val_grezzo, fallback_temp=25, alpha=0.25):
    if not (0.5 < val_grezzo < 180.0):
        val_grezzo = float(fallback_temp)
    prev = _TYRE_EMA_STATE.get(ruota)
    if prev is None or abs(val_grezzo - prev) > 35.0:
        filtrato = float(val_grezzo)
    else:
        filtrato = (prev * (1.0 - alpha)) + (val_grezzo * alpha)
    _TYRE_EMA_STATE[ruota] = filtrato
    return max(10, min(int(round(filtrato)), 150))

vel_filtrata   = 0.0
vel_mostrata   = 0
lap_progress   = 0.0
prev_progress  = 0.0
lap_start_ts   = None
curr_lap_time  = 0.0
last_lap_time  = 0.0
best_lap_time  = 0.0
s1_time_ms     = 0
s2_time_ms     = 0
s3_time_ms     = 0
current_lap    = 1
track_len_m    = 5412
air_temp_c     = 22
track_temp_c   = 25
fuel_capacity  = 60.0
fuel_lap_start = None
fuel_history   = list()
ultimo_rpm_chk = -1
ultimo_mov_ts  = 0.0
in_pista_attiva = False



def elabora_pacchetto_pmr(data, out_sock, ip_display, porta_display, DASH_STATE, logger):
    global vel_filtrata, vel_mostrata
    global lap_progress, prev_progress, lap_start_ts, curr_lap_time, last_lap_time, best_lap_time
    global s1_time_ms, s2_time_ms, s3_time_ms, current_lap, track_len_m, air_temp_c, track_temp_c
    global fuel_capacity, fuel_lap_start, fuel_history, ultimo_rpm_chk, ultimo_mov_ts, in_pista_attiva

    lung = len(data)
    tempo = time.time()

    if lung not in (101, 79, 964):
        return

    if lung == 101:
        prog, = struct.unpack_from("<f", data, 60)
        if 0.0 <= prog <= 1.0:
            if 0.85 < prev_progress <= 0.999 and 0.0001 <= prog < 0.10 and vel_filtrata > 30.0:
                if lap_start_ts is not None:
                    tempo_giro = tempo - lap_start_ts
                    if tempo_giro > 15.0:
                        last_lap_time = tempo_giro
                        if s1_time_ms > 0 and s2_time_ms > 0:
                            s3_time_ms = max(0, int(round((tempo_giro * 1000) - s1_time_ms - s2_time_ms)))
                        if best_lap_time == 0.0 or tempo_giro < best_lap_time:
                            best_lap_time = tempo_giro
                        current_lap += 1
                lap_start_ts = tempo
                s1_time_ms = 0
                s2_time_ms = 0
            if lap_start_ts is not None:
                if prev_progress < 0.333 and prog >= 0.333:
                    s1_time_ms = int((tempo - lap_start_ts) * 1000)
                elif prev_progress < 0.666 and prog >= 0.666:
                    s2_time_ms = int(((tempo - lap_start_ts) * 1000) - s1_time_ms)
            prev_progress = prog
            lap_progress = prog
        return

    if lung == 79:
        t_len, = struct.unpack_from("<f", data, 56)
        t_air, = struct.unpack_from("<f", data, 68)
        t_trk, = struct.unpack_from("<f", data, 72)
        if 500.0 < t_len < 30000.0:
            track_len_m = int(round(t_len))
        if -10.0 < t_air < 60.0:
            air_temp_c = int(round(t_air))
        if -10.0 < t_trk < 80.0:
            track_temp_c = int(round(t_trk))
        return

    try:
        packet_type, = struct.unpack_from("<B", data, 4)
        if packet_type != 0:
            return

        rpm_f, = struct.unpack_from("<f", data, 616)
        rpm = int(rpm_f) if 0 < rpm_f < 18000 else 0

        max_rpm_f, = struct.unpack_from("<f", data, 924)
        max_rpm = int(max_rpm_f) if 4000 < max_rpm_f < 18000 else 7100

        if rpm > 0:
            ultimo_mov_ts = tempo
        in_pausa = (rpm == 0) or ((tempo - ultimo_mov_ts) > 0.8)

        vel_ms, = struct.unpack_from("<f", data, 140)
        vel_reale = abs(vel_ms) * 3.56 if -5.0 < vel_ms < 120.0 else 0.0
        vel_filtrata = (vel_filtrata * 0.25) + (vel_reale * 0.75)
        if not hasattr(elabora_e_inietta_pacchetto, "last_vel_ts"):
            elabora_e_inietta_pacchetto.last_vel_ts = 0.0

        if vel_filtrata < 1.2:
            vel_mostrata = 0
        elif (tempo - elabora_e_inietta_pacchetto.last_vel_ts) >= 0.02:
            if abs(vel_filtrata - vel_mostrata) >= 0.45:
                vel_mostrata = int(round(vel_filtrata))
                elabora_e_inietta_pacchetto.last_vel_ts = tempo
        speed_kmh = max(0, min(vel_mostrata, 360))

        gear_raw, = struct.unpack_from("<B", data, 821)
        if gear_raw in (14, 15, 255):
            gear_display = -1
            gear_str = "R"
        elif gear_raw == 0:
            gear_display = 0
            gear_str = "N"
        else:
            gear_display = max(1, min(gear_raw, 8))
            gear_str = str(gear_display)

        in_pista_attiva = (not in_pausa) and (gear_display >= 1) and (rpm > 1800) and (vel_filtrata > 15.0)
        fuel_l, = struct.unpack_from("<f", data, 508)
        fuel_in_tank = max(0.0, min(fuel_l, 200.0)) if 0.0 <= fuel_l <= 200.0 else 0.0
        if fuel_in_tank > fuel_capacity:
            fuel_capacity = fuel_in_tank
        if fuel_lap_start is None and fuel_in_tank > 0.5 and in_pista_attiva:
            fuel_lap_start = fuel_in_tank
        avg_fuel = (sum(fuel_history) / len(fuel_history)) if fuel_history else 2.2
        fuel_laps = round(fuel_in_tank / avg_fuel, 1) if (fuel_in_tank > 0 and avg_fuel > 0.05) else 0.0

        t_fl, = struct.unpack_from("<f", data, 76)
        t_fr, = struct.unpack_from("<f", data, 200)
        t_rl, = struct.unpack_from("<f", data, 324)
        t_rr, = struct.unpack_from("<f", data, 448)

        fallback_temp = max(15, min(track_temp_c if track_temp_c > 0 else 25, 45))
        temp_fl = filtra_temp_gomma("fl", t_fl, fallback_temp)
        temp_fr = filtra_temp_gomma("fr", t_fr, fallback_temp)
        temp_rl = filtra_temp_gomma("rl", t_rl, fallback_temp)
        temp_rr = filtra_temp_gomma("rr", t_rr, fallback_temp)

        u_fl, = struct.unpack_from("<f", data, 92)
        u_fr, = struct.unpack_from("<f", data, 216)
        u_rl, = struct.unpack_from("<f", data, 340)
        u_rr, = struct.unpack_from("<f", data, 464)

        wear_rl = max(0, min(int(round((1.0 - u_rl) * 100)), 100)) if 0.0 <= u_rl <= 1.0 else 0
        wear_rr = max(0, min(int(round((1.0 - u_rr) * 100)), 100)) if 0.0 <= u_rr <= 1.0 else 0
        wear_fl = max(0, min(int(round((1.0 - u_fl) * 100)), 100)) if 0.0 <= u_fl <= 1.0 else 0
        wear_fr = max(0, min(int(round((1.0 - u_fr) * 100)), 100)) if 0.0 <= u_fr <= 1.0 else 0

        idle_rpm = 1500
        if in_pausa or max_rpm <= idle_rpm:
            led_pct = 0
            led_bits = 0
            in_fuorigiri = False
        else:
            ratio_rpm = (rpm - idle_rpm) / float(max_rpm - idle_rpm)
            led_pct = int(max(0, min(100, (ratio_rpm / 0.92) * 100)))
            in_fuorigiri = (led_pct >= 100)
            if in_fuorigiri:
                lampeggio = int(tempo * 18) % 2 == 0
                led_bits = 0x7FFF if lampeggio else 0
                led_pct = 100 if lampeggio else 0
            else:
                num_leds = int(round((led_pct / 100.0) * 15))
                led_bits = (1 << num_leds) - 1 if num_leds > 0 else 0

        if lap_start_ts is not None and not in_pausa:
            curr_lap_time = tempo - lap_start_ts

        DASH_STATE["gear"] = gear_str
        DASH_STATE["speed"] = speed_kmh
        DASH_STATE["rpm"] = rpm
        DASH_STATE["max_rpm"] = max_rpm
        DASH_STATE["fuel"] = fuel_in_tank
        DASH_STATE["fuel_laps"] = fuel_laps
        DASH_STATE["fuel_per_lap"] = round(avg_fuel, 2) if fuel_history else 0.0
        DASH_STATE["cur_lap"] = curr_lap_time
        DASH_STATE["last_lap"] = last_lap_time
        DASH_STATE["best_lap"] = best_lap_time
        DASH_STATE["lap"] = current_lap
        DASH_STATE["pos"] = 1
        DASH_STATE["s1"] = s1_time_ms / 1000.0
        DASH_STATE["s2"] = s2_time_ms / 1000.0
        DASH_STATE["s3"] = s3_time_ms / 1000.0
        # --- INIZIO BLOCCO GOMME RIFINITO ---
        DASH_STATE["tyre_fl"] = smooth_temp(DASH_STATE.get("tyre_fl", 0.0), temp_fl)
        DASH_STATE["tyre_fr"] = smooth_temp(DASH_STATE.get("tyre_fr", 0.0), temp_fr)
        DASH_STATE["tyre_rl"] = smooth_temp(DASH_STATE.get("tyre_rl", 0.0), temp_rl)
        DASH_STATE["tyre_rr"] = smooth_temp(DASH_STATE.get("tyre_rr", 0.0), temp_rr)

        # Sostituisci None con (in, mid, out) se il sim supporta i 3 settori
        imo_fl_raw = None
        imo_fr_raw = None
        imo_rl_raw = None
        imo_rr_raw = None

        DASH_STATE["has_imo"] = imo_fl_raw is not None
        DASH_STATE["tyre_fl_imo"] = build_imo(DASH_STATE.get("tyre_fl_imo"), imo_fl_raw, DASH_STATE["tyre_fl"])
        DASH_STATE["tyre_fr_imo"] = build_imo(DASH_STATE.get("tyre_fr_imo"), imo_fr_raw, DASH_STATE["tyre_fr"])
        DASH_STATE["tyre_rl_imo"] = build_imo(DASH_STATE.get("tyre_rl_imo"), imo_rl_raw, DASH_STATE["tyre_rl"])
        DASH_STATE["tyre_rr_imo"] = build_imo(DASH_STATE.get("tyre_rr_imo"), imo_rr_raw, DASH_STATE["tyre_rr"])

        DASH_STATE["tyre_wear"] = [
            round(max(0.0, min(100.0, 100.0 - wear_fl)), 1),
            round(max(0.0, min(100.0, 100.0 - wear_fr)), 1),
            round(max(0.0, min(100.0, 100.0 - wear_rl)), 1),
            round(max(0.0, min(100.0, 100.0 - wear_rr)), 1),
        ]
        # --- FINE BLOCCO GOMME RIFINITO ---

        DASH_STATE["air_temp"] = air_temp_c
        DASH_STATE["track_temp"] = track_temp_c
        eng_t = 92 if rpm > 1200 else max(20, track_temp_c)
        DASH_STATE["engine_temp"] = eng_t
        DASH_STATE["packets"] += 1
        DASH_STATE["last_ts"] = tempo
        DASH_STATE["hz_counter"] += 1
        if tempo - DASH_STATE["hz_timer"] >= 1.0:
            DASH_STATE["hz"] = DASH_STATE["hz_counter"] / (tempo - DASH_STATE["hz_timer"])
            DASH_STATE["hz_counter"] = 0
            DASH_STATE["hz_timer"] = tempo

        settore = 0 if lap_progress < 0.333 else (1 if lap_progress < 0.666 else 2)
        distanza_giro = float(lap_progress * track_len_m)
        distanza_tot = float(((current_lap - 1) + lap_progress) * track_len_m)

        s1_safe = max(0, min(int(s1_time_ms), 65535))
        s2_safe = max(0, min(int(s2_time_ms), 65535))

        hdr = "<HBBBBQfIBB"
        h1 = struct.pack(hdr, 2020, 1, 0, 1, 1, 123456789, float(tempo), _fid, 0, 0)
        p1 = bytearray(227)
        struct.pack_into("<BbbBH", p1, 0, 1, track_temp_c, air_temp_c, 60, track_len_m)
        struct.pack_into("<BB", p1, 6, 10, 0); struct.pack_into("<B", p1, 8, 0)
        struct.pack_into("<B", p1, 19, 0)

        h2 = struct.pack(hdr, 2020, 1, 0, 1, 2, 123456789, float(tempo), _fid, 0, 0)
        p2 = bytearray(1168)
        struct.pack_into("<ffHHf", p2, 0, last_lap_time, curr_lap_time, s1_safe, s2_safe, best_lap_time)
        struct.pack_into("<ff", p2, 24, distanza_giro, distanza_tot)
        struct.pack_into("<BBBB", p2, 34, 1, current_lap, 0, settore)
        struct.pack_into("<BBBBB", p2, 41, 0, 0, 2, 4, 2)

        # Pacchetto 6: Car Telemetry (1347 - 24 = 1323 byte totali)
        h6 = struct.pack(hdr, 2020, 1, 0, 1, 6, 123456789, float(tempo), _fid, 0, 0)
        p6 = bytearray(1323)
        struct.pack_into("<HfffB", p6, 0, speed_kmh, 1.0, 0.0, 0.0, 0)
        struct.pack_into("<bHBBH", p6, 15, int(gear_display), rpm, 0, led_pct, led_bits)
        struct.pack_into("<BBBB", p6, 44, temp_rl, temp_rr, temp_fl, temp_fr)
        struct.pack_into("<BBBB", p6, 48, temp_rl, temp_rr, temp_fl, temp_fr)
        struct.pack_into("<HHHH", p6, 20, 320, 320, 340, 340); struct.pack_into("<H", p6, 36, eng_t if "eng_t" in locals() else int(SHM_DATA.get("engine_temp", 92))); struct.pack_into("<H", p6, 52, eng_t)

        # Pacchetto 7: Car Status (1344 - 24 = 1320 byte totali)
        h7 = struct.pack(hdr, 2020, 1, 0, 1, 7, 123456789, float(tempo), _fid, 0, 0)
        p7 = bytearray(1320)
        struct.pack_into("<BBBBB", p7, 0, 2, 1, 1, 50, 0)
        struct.pack_into("<fff", p7, 5, fuel_in_tank, fuel_capacity, fuel_laps)
        # Offset 17: maxRPM e idleRPM (fondamentali per far lampeggiare l'SF1000!)
        soglia_cambiata = int(max_rpm * 0.92) if max_rpm > 2000 else 6500
        struct.pack_into("<HHB", p7, 17, soglia_cambiata, idle_rpm, 8)
        struct.pack_into("<BBBB", p7, 25, wear_rl, wear_rr, wear_fl, wear_fr)
        struct.pack_into("<BB", p7, 29, 16, 16)
        # Alterna 2 (Blu sinistra) e 4 (Rosso destra) al punto di cambiata per illuminare entrambi i lati!
        if in_fuorigiri:
            fia_flag = 2 if int(tempo * 20) % 2 == 0 else 4
        else:
            fia_flag = 0
               struct.pack_into("<b", p7, 38, fia_flag)

        # --- INIZIO PATCH ERS UNIVERSALE + SF1000 (PACKET 7 - OFFSET ESATTO 38/39) ---
        _ers_pct = float(locals().get("ers_pct", locals().get("ers_charge", 0.0)))
        _ers_act = int(locals().get("ers_active", 0))
        _ers_chg = int(locals().get("ers_charging", 0))
        _ers_mod = int(locals().get("ers_mode", 3 if _ers_act else (1 if _ers_pct > 0 else 0)))
        # Calcolo delta automatico per mod/sim che aggiornano solo la carica
        _prev_ers = globals().get("_OSW_PREV_ERS", _ers_pct)
        if _ers_pct > 0.0 and _ers_act == 0 and (_ers_pct < _prev_ers - 0.04):
            _ers_act = 1
            _ers_mod = 3
        elif _ers_pct > 0.0 and _ers_chg == 0 and (_ers_pct > _prev_ers + 0.04):
            _ers_chg = 1
        globals()["_OSW_PREV_ERS"] = _ers_pct
        _ers_joules = max(0.0, min(4000000.0, (_ers_pct / 100.0) * 4000000.0))
        struct.pack_into("<fB", p7, 39, _ers_joules, _ers_mod)
        if "DASH_STATE" in locals() or "DASH_STATE" in globals():
            DASH_STATE["ers"] = round(_ers_pct, 1)
            DASH_STATE["ers_active"] = _ers_act
            DASH_STATE["ers_charging"] = _ers_chg
            DASH_STATE["ers_mode"] = _ers_mod
        if "dash_state" in locals():
            dash_state["ers"] = round(_ers_pct, 1)
            dash_state["ers_active"] = _ers_act
            dash_state["ers_charging"] = _ers_chg
            dash_state["ers_mode"] = _ers_mod
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
        logger.warning(f"Errore elaborazione pacchetto: {e}")

