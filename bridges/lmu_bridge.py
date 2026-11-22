import struct
import time
import math

_LMU_STATE = {
    "last_ts": 0.0,
    "last_slow_ts": 0.0,
    "prev_ers": -1.0,
    "frame_id": 0,
}

# Formato pacchetto UDP inviato da lmu_shm_sender.py (127.0.0.1:9009)
_LMU_FMT = "<idddddddddBBBbbBdddffBBB20f"
_LMU_SIZE = struct.calcsize(_LMU_FMT)


def elabora_pacchetto_lmu(data, out_sock, ip_display, porta_display, dash_state, logger):
    if not data or len(data) < _LMU_SIZE:
        return

    tempo = time.time()
    unpacked = struct.unpack_from(_LMU_FMT, data, 0)
    (
        gear_raw, rpm_raw, max_rpm_raw, speed_raw,
        water_t, fuel_l, fuel_cap, rear_bias,
        bat_frac, boost_tq,
        boost_state, tc_val, abs_val,
        yellow_state, max_sec_flag, place,
        lap_dist, best_lap, last_lap,
        soc_pct, virt_en, current_lap,
        flap_act, flap_leg
    ) = unpacked[:24]
    wheels = unpacked[24:44]

    rpm = max(0, min(int(round(rpm_raw)), 22000))
    max_rpm = max(6500, int(round(max_rpm_raw))) if max_rpm_raw > 2000 else 8500
    speed_kmh = max(0, min(int(round(speed_raw)), 420))
    gear_display = max(-1, min(int(gear_raw), 9))

    idle_rpm = max(1000, int(max_rpm * 0.16))
    shift_rpm = max(idle_rpm + 1500, int(max_rpm * 0.96))

    in_fuorigiri = (rpm >= shift_rpm and rpm > 2500)
    if rpm <= idle_rpm + 120:
        led_pct = 0
        led_bits = 0
    else:
        span = max(1, shift_rpm - idle_rpm)
        led_pct = max(0, min(int(round(((rpm - idle_rpm) / span) * 100.0)), 100))
        if in_fuorigiri:
            led_bits = 0x7FFF if int(tempo * 20) % 2 == 0 else 0
        else:
            num_leds = int(round((led_pct / 100.0) * 15))
            led_bits = (1 << num_leds) - 1 if num_leds > 0 else 0

    # Gomme IMO (FL=0..4, FR=5..9, RL=10..14, RR=15..19)
    press_psi = [wheels[0], wheels[5], wheels[10], wheels[15]]
    imo_fl = [wheels[3], wheels[2], wheels[1]]
    imo_fr = [wheels[6], wheels[7], wheels[8]]
    imo_rl = [wheels[13], wheels[12], wheels[11]]
    imo_rr = [wheels[16], wheels[17], wheels[18]]
    wear_rem = [wheels[4], wheels[9], wheels[14], wheels[19]]

    s_fl = round(sum(imo_fl) / 3.0, 1)
    s_fr = round(sum(imo_fr) / 3.0, 1)
    s_rl = round(sum(imo_rl) / 3.0, 1)
    s_rr = round(sum(imo_rr) / 3.0, 1)

    # Batteria & ERS reale da LMU_Data (mBatteryChargeFraction / mSoC + mElectricBoostMotorState)
    if 0.0 <= bat_frac <= 1.001:
        ers_pct = round(bat_frac * 100.0, 1)
    elif 0.0 < soc_pct <= 100.0:
        ers_pct = round(soc_pct, 1)
    else:
        ers_pct = 0.0

    # mElectricBoostMotorState: 0=unavailable, 1=inactive, 2=propulsion (Deploy Verde), 3=regeneration (Harvest Azzurro)
    ers_active = 1 if (boost_state == 2 or boost_tq > 5.0) else 0
    ers_charging = 1 if (boost_state == 3 or boost_tq < -5.0) else 0
    prev_e = _LMU_STATE["prev_ers"]
    if prev_e >= 0.0 and ers_pct > 0.0 and ers_active == 0 and ers_charging == 0:
        if ers_pct < prev_e - 0.008:
            ers_active = 1
        elif ers_pct > prev_e + 0.008:
            ers_charging = 1
    _LMU_STATE["prev_ers"] = ers_pct
    ers_mode = 3 if ers_active else (1 if ers_pct > 0.0 else 0)

    # Brake Bias anteriore (LMU fornisce mRearBrakeBias 0.0..1.0)
    if 0.15 <= rear_bias <= 0.85:
        front_bias = round((1.0 - rear_bias) * 100.0, 1)
    else:
        front_bias = 58.0

    # Bandiera FIA reale (gialla globale o di settore)
    flag_str = "yellow" if (yellow_state in (1, 2, 3, 4) or max_sec_flag == 1) else "none"

    fuel_val = round(max(0.0, fuel_l), 1)
    fuel_cap_val = round(max(1.0, fuel_cap), 1) if fuel_cap > 1.0 else 100.0
    fuel_laps = round(fuel_val / 2.6, 1) if fuel_val > 0.1 else 0.0
    eng_t = max(0, min(int(round(water_t)), 250))

    # Aggiornamento Web Live Dash
    dash_state["sim"] = "Le Mans Ultimate"
    dash_state["rpm"] = rpm
    dash_state["max_rpm"] = max_rpm
    dash_state["speed"] = speed_kmh
    dash_state["gear"] = "R" if gear_display == -1 else ("N" if gear_display == 0 else str(gear_display))
    dash_state["led_pct"] = led_pct
    dash_state["fuel"] = fuel_val
    dash_state["fuel_cap"] = fuel_cap_val
    dash_state["fuel_laps"] = fuel_laps
    dash_state["tc"] = int(tc_val)
    dash_state["abs"] = int(abs_val)
    dash_state["bias"] = front_bias
    dash_state["flag"] = flag_str
    dash_state["ers"] = ers_pct
    dash_state["ers_active"] = ers_active
    dash_state["ers_charging"] = ers_charging
    dash_state["ers_mode"] = ers_mode
    dash_state["drs"] = 1 if flap_act > 0 else 0
    dash_state["drs_avail"] = 1 if flap_leg == 2 else 0
    dash_state["engine_temp"] = eng_t
    dash_state["tyre_fl"] = s_fl
    dash_state["tyre_fr"] = s_fr
    dash_state["tyre_rl"] = s_rl
    dash_state["tyre_rr"] = s_rr
    dash_state["has_imo"] = True
    dash_state["tyre_fl_imo"] = imo_fl
    dash_state["tyre_fr_imo"] = imo_fr
    dash_state["tyre_rl_imo"] = imo_rl
    dash_state["tyre_rr_imo"] = imo_rr
    dash_state["tyre_press"] = press_psi
    dash_state["tyre_wear"] = wear_rem
    dash_state["best_lap"] = max(0.0, round(best_lap, 3))
    dash_state["last_lap"] = max(0.0, round(last_lap, 3))
    dash_state["lap"] = max(1, int(current_lap))
    dash_state["pos"] = max(1, int(place))
    dash_state["packets"] += 1
    dash_state["last_ts"] = tempo
    dash_state["hz_counter"] += 1
    if tempo - dash_state["hz_timer"] >= 1.0:
        dash_state["hz"] = dash_state["hz_counter"] / (tempo - dash_state["hz_timer"])
        dash_state["hz_counter"] = 0
        dash_state["hz_timer"] = tempo

    # Invio pacchetti UDP F1 2020 verso SF1000
    def _u8(v):
        return max(0, min(int(round(v)), 255))

    _LMU_STATE["frame_id"] = (_LMU_STATE["frame_id"] + 1) & 0xFFFFFFFF
    fid = _LMU_STATE["frame_id"]
    hdr = "<HBBBBQfIBB"

    h6 = struct.pack(hdr, 2020, 1, 0, 1, 6, 123456789, float(tempo), fid, 0, 0)
    p6 = bytearray(1323)
    struct.pack_into("<HfffB", p6, 0, speed_kmh, 1.0, 0.0, 0.0, 0)
    struct.pack_into("<bHBBH", p6, 15, int(gear_display), rpm, 0, led_pct, led_bits)
    struct.pack_into("<HHHH", p6, 20, 320, 320, 340, 340)
    struct.pack_into("<H", p6, 36, eng_t)
    struct.pack_into("<BBBB", p6, 44, _u8(s_rl), _u8(s_rr), _u8(s_fl), _u8(s_fr))
    struct.pack_into("<BBBB", p6, 48, _u8(s_rl), _u8(s_rr), _u8(s_fl), _u8(s_fr))
    struct.pack_into("<H", p6, 52, eng_t)
    out_sock.sendto(h6 + p6, (ip_display, porta_display))

    if tempo - _LMU_STATE["last_slow_ts"] >= 0.1:
        _LMU_STATE["last_slow_ts"] = tempo
        h0 = struct.pack(hdr, 2020, 1, 0, 1, 0, 123456789, float(tempo), fid, 0, 0)
        p0 = bytearray(1440)
        h1 = struct.pack(hdr, 2020, 1, 0, 1, 1, 123456789, float(tempo), fid, 0, 0)
        p1 = bytearray(227)
        struct.pack_into("<BbbBH", p1, 0, 1, 28, 22, 60, 5793)
        struct.pack_into("<B", p1, 6, 10)
        struct.pack_into("<B", p1, 19, 1)

        h7 = struct.pack(hdr, 2020, 1, 0, 1, 7, 123456789, float(tempo), fid, 0, 0)
        p7 = bytearray(1320)
        tc_f1 = 0 if tc_val <= 0 else (1 if tc_val <= 4 else 2)
        abs_f1 = 1 if abs_val > 0 else 0
        bb_f1 = max(20, min(90, int(round(front_bias))))
        struct.pack_into("<BBBBB", p7, 0, tc_f1, abs_f1, 1, bb_f1, 0)
        struct.pack_into("<fff", p7, 5, fuel_val if fuel_val > 0.1 else 45.0, fuel_cap_val, fuel_laps if fuel_laps > 0.1 else 15.0)
        struct.pack_into("<HHB", p7, 17, shift_rpm, idle_rpm, 8)
        fia_flag = 2 if (in_fuorigiri and int(tempo * 20) % 2 == 0) else (3 if flag_str == "yellow" else 0)
        struct.pack_into("<b", p7, 42, fia_flag)
        ers_joules = max(0.0, min(4000000.0, (ers_pct / 100.0) * 4000000.0))
        struct.pack_into("<fB", p7, 43, ers_joules, ers_mode)

        out_sock.sendto(h0 + p0, (ip_display, porta_display))
        out_sock.sendto(h1 + p1, (ip_display, porta_display))
        out_sock.sendto(h7 + p7, (ip_display, porta_display))
