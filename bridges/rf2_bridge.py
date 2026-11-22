#!/usr/bin/env python3
# ==============================================================================
# OpenSimWheel Linux Bridge - rFactor 2 / LMU 100% Native REST + RAM Module
# Copyright (C) 2026 Alex
# Licensed under the GNU General Public License v3.0 (GPLv3)
# ==============================================================================

import os
import re
import struct
import ctypes
import time
import math
import json
import threading
import urllib.request
import numpy as np

_libc = ctypes.CDLL("libc.so.6")


class _iovec(ctypes.Structure):
    _fields_ = [("iov_base", ctypes.c_void_p), ("iov_len", ctypes.c_size_t)]


RF2_MEM = {
    "pid": None,
    "is_lmu": False,
    "addr": None,
    "gear_addr": None,
    "wheels_addr": None,
    "bat_addr": None,
    "scan_running": False,
    "http_running": False,
    "last_slow_ts": 0.0,
    "track_len_m": 5800,
    "air_temp": 22,
    "track_temp": 28,
    "cached_player": None,
    "active_port": 5397,
    "max_rpm": 8500,
    "last_valid_s1": 0.0,
    "last_valid_s2": 0.0,
    "local_lap_start": None,
    "local_last_lap": -1,
    "local_last_dist": 0.0,
    "prev_rest_lap": 0.0,
}

_RF2_TYRE_EMA = {}
_RF2_FUEL_STATE = {
    "last_lap": -1,
    "last_fuel": None,
    "start_fuel": None,
    "history": [],
}


def _filtra_temp_rf2(chiave, val_grezzo, fallback_temp=28.0, alpha=0.25):
    if not math.isfinite(val_grezzo) or not (2.0 <= val_grezzo <= 165.0):
        val_grezzo = float(fallback_temp)
    prev = _RF2_TYRE_EMA.get(chiave)
    if prev is None or abs(val_grezzo - prev) > 35.0:
        filtrato = float(val_grezzo)
    else:
        filtrato = (prev * (1.0 - alpha)) + (val_grezzo * alpha)
    _RF2_TYRE_EMA[chiave] = filtrato
    return round(filtrato, 1)


def _read_mem(pid, addr, size):
    if not pid or not addr or size <= 0:
        return None
    buf = ctypes.create_string_buffer(size)
    local_iov = _iovec(ctypes.cast(buf, ctypes.c_void_p), size)
    remote_iov = _iovec(ctypes.c_void_p(addr), size)
    n = _libc.process_vm_readv(pid, ctypes.byref(local_iov), 1, ctypes.byref(remote_iov), 1, 0)
    return buf.raw if n == size else None


def _find_rf2_pid():
    try:
        for p in os.listdir("/proc"):
            if p.isdigit():
                try:
                    with open(f"/proc/{p}/cmdline", "rb") as f:
                        cmd = f.read().decode("utf-8", errors="ignore")
                    if "--type=" not in cmd:
                        if "Le Mans Ultimate.exe" in cmd:
                            return int(p), True
                        if "rFactor2.exe" in cmd:
                            return int(p), False
                except Exception:
                    continue
    except Exception:
        pass
    return None, False


def _get_rw_regions(pid):
    regions = []
    try:
        with open(f"/proc/{pid}/maps", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.match(r"([0-9a-f]+)-([0-9a-f]+) rw-[ps]", line)
                if m:
                    s, e = int(m.group(1), 16), int(m.group(2), 16)
                    sz = e - s
                    if 0x10000 <= sz <= 0x10000000 and s >= 0x1000000:
                        regions.append((s, sz))
    except Exception:
        pass
    return regions


def _scan_rf2_wheels(pid, regions):
    with np.errstate(invalid="ignore"):
        for s, sz in regions:
            buf = _read_mem(pid, s, sz)
            if not buf or len(buf) < 4096:
                continue
            for align in (0, 4):
                n8 = (len(buf) - align) // 8
                if n8 <= 130:
                    continue
                a = np.frombuffer(buf, dtype=np.float64, count=n8, offset=align)
                mask = (
                    (a[:-128] >= 275.0) & (a[:-128] <= 430.0) &
                    (a[2:-126] >= 275.0) & (a[2:-126] <= 430.0) &
                    (a[3:-125] >= 275.0) & (a[3:-125] <= 430.0) &
                    (a[4:-124] >= 275.0) & (a[4:-124] <= 430.0) &
                    (a[26:-102] > 0.01) & (a[26:-102] <= 1.0001) &
                    (a[28:-100] >= 80.0) & (a[28:-100] <= 360.0) &
                    (a[58:-70] > 0.01) & (a[58:-70] <= 1.0001) &
                    (a[60:-68] >= 80.0) & (a[60:-68] <= 360.0) &
                    (a[90:-38] > 0.01) & (a[90:-38] <= 1.0001) &
                    (a[92:-36] >= 80.0) & (a[92:-36] <= 360.0) &
                    (a[122:-6] > 0.01) & (a[122:-6] <= 1.0001) &
                    (a[124:-4] >= 80.0) & (a[124:-4] <= 360.0)
                )
                hits = np.flatnonzero(mask)
                if len(hits) > 0:
                    w_off = align + int(hits.item(0)) * 8
                    return int(s + w_off)
    return None


def _scan_rf2_engine(pid, regions):
    candidati = []
    with np.errstate(invalid="ignore"):
        for s, sz in reversed(regions):
            r1 = _read_mem(pid, s, sz)
            if not r1 or len(r1) < 1024:
                continue
            for align in (0, 4):
                n8 = (len(r1) - align - 656) // 8
                if n8 <= 16:
                    continue
                a_om = np.frombuffer(r1, dtype=np.float64, count=n8, offset=align)
                a_t1 = np.frombuffer(r1, dtype=np.float64, count=n8, offset=align + 48)
                a_fl = np.frombuffer(r1, dtype=np.float64, count=n8, offset=align + 56)
                a_t2 = np.frombuffer(r1, dtype=np.float64, count=n8, offset=align + 64)

                mask = (
                    (a_om >= 45.0) & (a_om <= 2500.0) & ((a_om % 1.0) != 0.0) &
                    (a_t1 >= 290.0) & (a_t1 <= 470.0) &
                    (a_fl == 1.0) &
                    (a_t2 >= 290.0) & (a_t2 <= 470.0)
                )
                for idx in np.flatnonzero(mask):
                    off = align + int(idx) * 8
                    addr = int(s + off)
                    chk_g = _read_mem(pid, addr + 632, 12)
                    if chk_g and len(chk_g) == 12:
                        mx, g1, g2 = struct.unpack_from("<iii", chk_g, 0)
                        if 4 <= mx <= 9 and -1 <= g1 <= mx and g1 == g2:
                            candidati.append((addr, float(a_om.item(int(idx)))))

    if not candidati:
        return None
    if len(candidati) == 1:
        addr, _ = candidati.pop(0)
        return int(addr)

    time.sleep(0.06)
    migliore = None
    max_delta = 0.02
    for addr, old_om in candidati:
        chk = _read_mem(pid, addr, 8)
        if chk and len(chk) == 8:
            new_om, = struct.unpack_from("<d", chk, 0)
            delta = abs(new_om - old_om)
            if delta > max_delta:
                max_delta = delta
                migliore = int(addr)

    if migliore:
        return migliore
    addr, _ = candidati.pop(0)
    return int(addr)


def _scan_lmu_battery(pid):
    try:
        regions = _get_rw_regions(pid)
        with open(f"/proc/{pid}/mem", "rb", buffering=0) as mem:
            for base, size in regions:
                if size > 128 * 1024 * 1024:
                    continue
                try:
                    mem.seek(base)
                    buf = mem.read(size)
                except Exception:
                    continue
                for off in range(24, len(buf) - 16, 8):
                    bat, = struct.unpack_from("<d", buf, off)
                    if 0.005 <= bat <= 1.0001 and (bat * 1000) % 1 != 0:
                        k1, k2, k3 = struct.unpack_from("<ddd", buf, off - 24)
                        if 285.0 < k1 < 420.0 and 285.0 < k2 < 420.0 and 285.0 < k3 < 420.0:
                            if abs(k1 - k2) < 15.0 and abs(k2 - k3) < 15.0:
                                return base + off
    except Exception:
        pass
    return None


def _bg_scan_worker(pid, logger):
    try:
        regions = _get_rw_regions(pid)
        if not RF2_MEM.get("bat_addr"):
            RF2_MEM["bat_addr"] = _scan_lmu_battery(pid)
            if RF2_MEM["bat_addr"] and logger:
                logger.info(f"rF2/LMU Nativo: Batteria ibrida agganciata @ 0x{RF2_MEM['bat_addr']:x}")
        if not RF2_MEM["addr"]:
            e_addr = _scan_rf2_engine(pid, regions)
            if e_addr:
                RF2_MEM["addr"] = e_addr
                RF2_MEM["gear_addr"] = e_addr + 632
                if logger:
                    logger.info(f"rF2/LMU Nativo: Motore + Cambio agganciati @ 0x{e_addr:x} (+632)")
        if not RF2_MEM["wheels_addr"]:
            w_addr = _scan_rf2_wheels(pid, regions)
            if w_addr:
                RF2_MEM["wheels_addr"] = w_addr
                if logger:
                    logger.info(f"rF2/LMU Nativo: Blocco 4 ruote agganciato @ 0x{w_addr:x}")
    finally:
        RF2_MEM["scan_running"] = False


def _http_poll_worker():
    last_sess = 0.0
    while RF2_MEM["http_running"]:
        now = time.time()
        ports = (RF2_MEM["active_port"], 6397, 5397, 5396) if RF2_MEM["is_lmu"] else (RF2_MEM["active_port"], 5397, 6397, 5396)
        if now - last_sess >= 5.0:
            last_sess = now
            for p in ports:
                try:
                    sreq = urllib.request.urlopen(f"http://localhost:{p}/rest/watch/sessionInfo", timeout=0.15)
                    sinfo = json.loads(sreq.read().decode("utf-8", errors="ignore"))
                    ld = int(float(sinfo.get("lapDistance", 0)))
                    if ld > 500:
                        RF2_MEM["track_len_m"] = ld
                    if "ambientTemp" in sinfo:
                        RF2_MEM["air_temp"] = int(round(float(sinfo["ambientTemp"])))
                    if "trackTemp" in sinfo:
                        RF2_MEM["track_temp"] = int(round(float(sinfo["trackTemp"])))
                    break
                except Exception:
                    continue
        for p in ports:
            try:
                req = urllib.request.urlopen(f"http://localhost:{p}/rest/watch/standings", timeout=0.15)
                standings = json.loads(req.read().decode("utf-8", errors="ignore"))
                if standings and isinstance(standings, list):
                    RF2_MEM["active_port"] = p
                    RF2_MEM["cached_player"] = next((v for v in standings if v.get("player")), standings)
                break
            except Exception:
                continue
        time.sleep(0.025)


def _get_max_rpm(car_class, veh_name):
    txt = f"{car_class} {veh_name}".upper()
    if any(k in txt for k in ("F1", "FORMULA", "INDY", "OPEN", "DAL", "TATUUS", "FR3", "GP3")):
        return 11800
    if any(k in txt for k in ("LMP", "HYPER", "PROTO", "DPI", "ORECA", "P2", "P3")):
        return 9000
    return 8050


def elabora_pacchetto_rf2(data, out_sock, ip_display, porta_display, dash_state, logger):
    tempo = time.time()

    if not RF2_MEM["http_running"]:
        RF2_MEM["http_running"] = True
        threading.Thread(target=_http_poll_worker, daemon=True).start()

    if not RF2_MEM["pid"] or not os.path.exists(f"/proc/{RF2_MEM['pid']}"):
        pid, is_lmu = _find_rf2_pid()
        RF2_MEM["pid"] = pid
        RF2_MEM["is_lmu"] = is_lmu
        RF2_MEM["addr"] = None
        RF2_MEM["gear_addr"] = None
        RF2_MEM["wheels_addr"] = None
        RF2_MEM["bat_addr"] = None
        if not RF2_MEM["pid"]:
            return
    dash_state["last_ts"] = tempo

    if not RF2_MEM.get("ram_blocked") and (not RF2_MEM["wheels_addr"] or not RF2_MEM["addr"] or not RF2_MEM.get("gear_addr")) and not RF2_MEM["scan_running"] and (tempo - RF2_MEM.get("last_scan_ts", 0.0) >= 1.5):
        RF2_MEM["last_scan_ts"] = tempo
        RF2_MEM["scan_running"] = True
        threading.Thread(target=_bg_scan_worker, args=(RF2_MEM["pid"], logger), daemon=True).start()

    player = RF2_MEM["cached_player"] or {}
    vel_ms = float((player.get("carVelocity") or {}).get("velocity") or 0.0)
    speed_kmh = max(0, min(int(round(vel_ms * 3.6)), 400))

    in_gar_now = bool(player.get("inGarageStall", False))
    if in_gar_now:
        RF2_MEM["addr"] = None
        RF2_MEM["gear_addr"] = None
        RF2_MEM["wheels_addr"] = None
        RF2_MEM["last_scan_ts"] = 0.0
    elif RF2_MEM.get("prev_in_garage", True) and not in_gar_now:
        RF2_MEM["addr"] = None
        RF2_MEM["gear_addr"] = None
        RF2_MEM["last_scan_ts"] = 0.0
    RF2_MEM["prev_in_garage"] = in_gar_now

    veh_id = f"{player.get('carClass', '')}_{player.get('vehicleName', '')}"
    if veh_id != "_" and RF2_MEM.get("last_veh") != veh_id:
        RF2_MEM["last_veh"] = veh_id
        RF2_MEM["max_rpm"] = 0
        RF2_MEM["addr"] = None
        RF2_MEM["gear_addr"] = None
        RF2_MEM["wheels_addr"] = None
        RF2_MEM["bat_addr"] = None
        RF2_MEM["last_scan_ts"] = 0.0

    base_max = _get_max_rpm(player.get("carClass", ""), player.get("vehicleName", ""))
    if RF2_MEM["max_rpm"] == 0:
        RF2_MEM["max_rpm"] = base_max
    max_rpm = RF2_MEM["max_rpm"]

    gear_raw = 0
    rpm_raw = 0.0
    got_rpm = False
    got_gear = False

    if RF2_MEM["addr"]:
        ebuf = _read_mem(RF2_MEM["pid"], RF2_MEM["addr"], 72)
        if ebuf and len(ebuf) == 72:
            omega, = struct.unpack_from("<d", ebuf, 0)
            lim_omega, = struct.unpack_from("<d", ebuf, 32)
            t1_k, fl_one, t2_k = struct.unpack_from("<ddd", ebuf, 48)
            if 0.0 <= omega <= 2500.0 and 280.0 <= t1_k <= 480.0 and fl_one == 1.0 and 280.0 <= t2_k <= 480.0:
                rpm_raw = omega * 9.54929659 * 2.04
                if 450.0 <= lim_omega <= 2200.0:
                    RF2_MEM["max_rpm"] = int(lim_omega * 9.54929659 * 1.02)
                if rpm_raw > RF2_MEM["max_rpm"]:
                    RF2_MEM["max_rpm"] = int(rpm_raw)
                max_rpm = RF2_MEM["max_rpm"]
                got_rpm = True
            else:
                RF2_MEM["addr"] = None
                RF2_MEM["gear_addr"] = None

    if RF2_MEM["gear_addr"] and got_rpm:
        gbuf = _read_mem(RF2_MEM["pid"], RF2_MEM["gear_addr"], 12)
        if gbuf and len(gbuf) == 12:
            mx, g1, g2 = struct.unpack_from("<iii", gbuf, 0)
            if 4 <= mx <= 9 and -1 <= g1 <= mx and g1 == g2:
                gear_raw = int(g1)
                got_gear = True

    if not got_rpm:
        rpm_raw = 0.0
    if not got_gear:
        gear_raw = 0

    core_c = [28.0, 28.0, 28.0, 28.0]
    surf_avg_c = [28.0, 28.0, 28.0, 28.0]
    imo_c = [[28.0, 28.0, 28.0], [28.0, 28.0, 28.0], [28.0, 28.0, 28.0], [28.0, 28.0, 28.0]]
    press_psi = [0.0, 0.0, 0.0, 0.0]
    wear_rem = [100.0, 100.0, 100.0, 100.0]

    if RF2_MEM["wheels_addr"]:
        wbuf = _read_mem(RF2_MEM["pid"], RF2_MEM["wheels_addr"], 1024)
        if wbuf and len(wbuf) == 1024:
            valid_w = True
            for w in range(4):
                off = w * 256
                t_carc_k, _, t1_k, t2_k, t3_k = struct.unpack_from("<ddddd", wbuf, off)
                w_raw, = struct.unpack_from("<d", wbuf, off + 208)
                p_kpa, = struct.unpack_from("<d", wbuf, off + 224)
                if not (260.0 <= t_carc_k <= 450.0 and 260.0 <= t2_k <= 450.0):
                    valid_w = False
                    break
                c_f = _filtra_temp_rf2(f"c_{w}", t_carc_k - 273.15)
                s1 = _filtra_temp_rf2(f"s1_{w}", t1_k - 273.15)
                s2 = _filtra_temp_rf2(f"s2_{w}", t2_k - 273.15)
                s3 = _filtra_temp_rf2(f"s3_{w}", t3_k - 273.15)
                raw_imo = [s3, s2, s1] if w in (0, 2) else [s1, s2, s3]
                core_c[w] = c_f
                imo_c[w] = raw_imo
                surf_avg_c[w] = round(sum(raw_imo) / 3.0, 1)
                if math.isfinite(p_kpa) and 20.0 <= p_kpa <= 400.0:
                    press_psi[w] = round(p_kpa * 0.1450377, 1)
                if math.isfinite(w_raw) and 0.0 <= w_raw <= 1.001:
                    wear_rem[w] = round(max(0.0, min(100.0, w_raw * 100.0)), 1)
            if not valid_w:
                RF2_MEM["wheels_addr"] = None
        else:
            RF2_MEM["wheels_addr"] = None

    fuel_frac = float(player.get("fuelFraction") if player.get("fuelFraction") is not None else 0.5)
    fuel_val = round(fuel_frac * 100.0, 1)
    pos = max(1, int(player.get("position") or 1))
    current_lap = max(1, int(player.get("lapsCompleted") or 0) + 1)
    lap_dist = max(0.0, float(player.get("lapDistance") or 0.0))
    in_garage = bool(player.get("inGarageStall", False))
    pitting = bool(player.get("pitting", False))

    cur_lap_time = max(0.0, float(player.get("timeIntoLap") or 0.0))
    if cur_lap_time <= 0.0:
        lap_start_et = float(player.get("lapStartET") or 0.0)
        cur_et = float(player.get("currentET") or 0.0)
        if cur_et > lap_start_et and lap_start_et >= 0.0:
            cur_lap_time = round(cur_et - lap_start_et, 3)

    nuovo_giro = (
        RF2_MEM["local_last_lap"] != current_lap
        or (RF2_MEM["local_last_dist"] > 500.0 and lap_dist < 100.0)
    )
    rest_avanza = (cur_lap_time > 0.0 and abs(cur_lap_time - RF2_MEM["prev_rest_lap"]) > 0.0005)
    RF2_MEM["prev_rest_lap"] = cur_lap_time

    if rest_avanza and not nuovo_giro:
        RF2_MEM["local_lap_start"] = tempo - cur_lap_time
        RF2_MEM["local_last_lap"] = current_lap
    else:
        if in_garage and speed_kmh == 0 and lap_dist < 10.0 and not RF2_MEM.get("local_lap_start"):
            RF2_MEM["local_lap_start"] = tempo
            RF2_MEM["local_last_lap"] = current_lap
            cur_lap_time = 0.0
        else:
            if RF2_MEM["local_lap_start"] is None or nuovo_giro:
                RF2_MEM["local_lap_start"] = tempo
                RF2_MEM["local_last_lap"] = current_lap
            cur_lap_time = round(max(0.0, tempo - RF2_MEM["local_lap_start"]), 3)
    RF2_MEM["local_last_dist"] = lap_dist

    last_lap_time = max(0.0, float(player.get("lastLapTime") or 0.0))
    best_lap_time = max(0.0, float(player.get("bestLapTime") or 0.0))

    cur_s1 = max(0.0, float(player.get("currentSectorTime1") or 0.0))
    cur_s2_cum = max(0.0, float(player.get("currentSectorTime2") or 0.0))
    last_s1 = max(0.0, float(player.get("lastSectorTime1") or 0.0))
    last_s2_cum = max(0.0, float(player.get("lastSectorTime2") or 0.0))

    if cur_s1 > 0.0:
        s1_sec = cur_s1
        RF2_MEM["last_valid_s1"] = cur_s1
    elif last_s1 > 0.0:
        s1_sec = last_s1
        RF2_MEM["last_valid_s1"] = last_s1
    else:
        s1_sec = RF2_MEM["last_valid_s1"]

    if cur_s2_cum > cur_s1 and cur_s1 > 0.0:
        s2_sec = cur_s2_cum - cur_s1
        RF2_MEM["last_valid_s2"] = s2_sec
    elif last_s2_cum > last_s1 and last_s1 > 0.0:
        s2_sec = last_s2_cum - last_s1
        RF2_MEM["last_valid_s2"] = s2_sec
    else:
        s2_sec = RF2_MEM["last_valid_s2"]

    if last_lap_time > 0.0 and last_s2_cum > 0.0 and last_lap_time > last_s2_cum:
        s3_sec = last_lap_time - last_s2_cum
    else:
        s3_sec = 0.0

    last_f = _RF2_FUEL_STATE["last_fuel"]
    if last_f is not None and abs(fuel_val - last_f) > 0.5:
        _RF2_FUEL_STATE["start_fuel"] = fuel_val
    _RF2_FUEL_STATE["last_fuel"] = fuel_val

    if in_garage or pitting:
        _RF2_FUEL_STATE["start_fuel"] = fuel_val
        _RF2_FUEL_STATE["last_lap"] = current_lap
    else:
        if current_lap != _RF2_FUEL_STATE["last_lap"]:
            if (
                _RF2_FUEL_STATE["last_lap"] > 0
                and current_lap > _RF2_FUEL_STATE["last_lap"]
                and _RF2_FUEL_STATE["start_fuel"] is not None
                and _RF2_FUEL_STATE["start_fuel"] > fuel_val
            ):
                usato = _RF2_FUEL_STATE["start_fuel"] - fuel_val
                if 0.2 <= usato <= 15.0:
                    _RF2_FUEL_STATE["history"].append(usato)
                    if len(_RF2_FUEL_STATE["history"]) > 5:
                        _RF2_FUEL_STATE["history"].pop(0)
            _RF2_FUEL_STATE["start_fuel"] = fuel_val
            _RF2_FUEL_STATE["last_lap"] = current_lap
        elif _RF2_FUEL_STATE["start_fuel"] is None and fuel_val > 0.5:
            _RF2_FUEL_STATE["start_fuel"] = fuel_val

    avg_fuel = (sum(_RF2_FUEL_STATE["history"]) / len(_RF2_FUEL_STATE["history"])) if _RF2_FUEL_STATE["history"] else 2.2
    fuel_laps = round(fuel_val / avg_fuel, 1) if (fuel_val > 0.0 and avg_fuel > 0.05) else 0.0

    rpm = int(round(rpm_raw))
    gear_str = "R" if gear_raw == -1 else ("N" if gear_raw == 0 else str(gear_raw))
    gear_display = int(gear_raw)

    in_pausa = (rpm <= 100)
    idle_rpm = int(max_rpm * 0.30)
    shift_rpm = int(max_rpm * 0.975)

    if in_pausa or max_rpm <= idle_rpm or rpm < idle_rpm:
        led_pct, led_bits, in_fuorigiri = 0, 0, False
    else:
        ratio_rpm = max(0.0, (rpm - idle_rpm) / float(max(1, shift_rpm - idle_rpm)))
        led_pct = int(max(1, min(100, round(ratio_rpm * 100))))
        in_fuorigiri = (rpm >= shift_rpm)
        if in_fuorigiri:
            lampeggio = int(tempo * 16) % 2 == 0
            led_bits = 0x7FFF if lampeggio else 0
            led_pct = 100 if lampeggio else 0
        else:
            num_leds = int(round((led_pct / 100.0) * 15))
            led_bits = (1 << num_leds) - 1 if num_leds > 0 else 0

    c_fl, c_fr, c_rl, c_rr = core_c
    i_fl, i_fr, i_rl, i_rr = imo_c
    s_fl, s_fr, s_rl, s_rr = surf_avg_c
    w_fl, w_fr, w_rl, w_rr = wear_rem

    _bat_raw = float(player.get("batteryChargeFraction") or player.get("ersCharge") or player.get("kersCharge") or 0.0)
    if _bat_raw <= 0.0 and RF2_MEM.get("pid") and RF2_MEM.get("bat_addr"):
        _bbuf = _read_mem(RF2_MEM["pid"], RF2_MEM["bat_addr"], 8)
        if _bbuf and len(_bbuf) == 8:
            _b_mem, = struct.unpack("<d", _bbuf)
            if 0.0 <= _b_mem <= 1.001:
                _bat_raw = _b_mem
        else:
            RF2_MEM["bat_addr"] = None
    ers_pct = round(_bat_raw * 100.0, 1) if 0.0 < _bat_raw <= 1.0 else (round(_bat_raw, 1) if 1.0 < _bat_raw <= 100.0 else 0.0)
    _m_state = int(player.get("electricBoostMotorState") or player.get("ersDeployMode") or 0)
    ers_active = 1 if _m_state in (1, 2) and float(player.get("electricBoostMotorTorque") or 1.0) > 0.0 else 0
    ers_charging = 1 if _m_state == 3 else 0
    s_flags = player.get("sectorFlag") or []
    tc_rf2 = int(player.get("tractionControl") or player.get("tc") or 0)
    abs_rf2 = int(player.get("antiLockBrakes") or player.get("abs") or 0)
    bb_raw_rf2 = float(player.get("frontBrakeBias") or player.get("brakeBias") or 0.0)
    bb_rf2 = round(bb_raw_rf2 * 100.0, 1) if 0.2 <= bb_raw_rf2 <= 0.9 else (round(bb_raw_rf2, 1) if 20.0 <= bb_raw_rf2 <= 90.0 else 56.0)
    dash_state["tc"] = max(0, tc_rf2)
    dash_state["abs"] = max(0, abs_rf2)
    dash_state["brake_bias"] = bb_rf2
    dash_state["flag"] = "yellow" if (isinstance(s_flags, list) and any(x == 1 for x in s_flags)) else "none"
    dash_state["gear"] = gear_str
    dash_state["speed"] = speed_kmh
    dash_state["rpm"] = rpm
    dash_state["max_rpm"] = max_rpm
    dash_state["fuel"] = fuel_val
    dash_state["fuel_laps"] = fuel_laps
    dash_state["fuel_per_lap"] = round(avg_fuel, 2) if _RF2_FUEL_STATE["history"] else 0.0
    dash_state["tyre_fl"] = c_fl
    dash_state["tyre_fr"] = c_fr
    dash_state["tyre_rl"] = c_rl
    dash_state["tyre_rr"] = c_rr
    dash_state["has_imo"] = True
    dash_state["tyre_fl_imo"] = i_fl
    dash_state["tyre_fr_imo"] = i_fr
    dash_state["tyre_rl_imo"] = i_rl
    dash_state["tyre_rr_imo"] = i_rr
    dash_state["tyre_press"] = press_psi
    dash_state["tyre_wear"] = wear_rem
    dash_state["cur_lap"] = cur_lap_time
    dash_state["last_lap"] = last_lap_time
    dash_state["best_lap"] = best_lap_time
    dash_state["lap"] = current_lap
    dash_state["pos"] = pos
    dash_state["air_temp"] = RF2_MEM["air_temp"]
    dash_state["track_temp"] = RF2_MEM["track_temp"]
    eng_t = int(round(float(RF2_MEM.get("water_temp", 92 if rpm > 1200 else 25))))
    dash_state["engine_temp"] = eng_t
    dash_state["s1"] = round(s1_sec, 3)
    dash_state["s2"] = round(s2_sec, 3)
    dash_state["s3"] = round(s3_sec, 3)
    dash_state["packets"] += 1
    dash_state["last_ts"] = tempo
    dash_state["hz_counter"] += 1
    if tempo - dash_state["hz_timer"] >= 1.0:
        dash_state["hz"] = dash_state["hz_counter"] / (tempo - dash_state["hz_timer"])
        dash_state["hz_counter"] = 0
        dash_state["hz_timer"] = tempo

    def _u8(val):
        return max(0, min(int(round(val)), 255))

    track_len_m = RF2_MEM["track_len_m"]
    distanza_giro = min(lap_dist, float(track_len_m))
    lap_progress = distanza_giro / float(max(1, track_len_m))
    settore = 0 if lap_progress < 0.333 else (1 if lap_progress < 0.666 else 2)
    distanza_tot = float(((current_lap - 1) * track_len_m) + distanza_giro)
    s1_safe = max(0, min(int(round(s1_sec * 1000)), 65535))
    s2_safe = max(0, min(int(round(s2_sec * 1000)), 65535))

    _fid = (globals().get("_OSW_FRAME_ID", 0) + 1) & 0xFFFFFFFF
    globals()["_OSW_FRAME_ID"] = _fid
    hdr = "<HBBBBQfIBB"
    h1 = struct.pack(hdr, 2020, 1, 0, 1, 1, 123456789, float(tempo), _fid, 0, 0)
    p1 = bytearray(227)
    struct.pack_into("<BbbBH", p1, 0, 1, RF2_MEM["track_temp"], RF2_MEM["air_temp"], 60, min(65535, track_len_m))
    struct.pack_into("<BB", p1, 6, 10, 0); struct.pack_into("<B", p1, 8, 0)
    struct.pack_into("<B", p1, 19, 1)

    h2 = struct.pack(hdr, 2020, 1, 0, 1, 2, 123456789, float(tempo), _fid, 0, 0)
    p2 = bytearray(1168)
    struct.pack_into("<ffHHf", p2, 0, last_lap_time, cur_lap_time, s1_safe, s2_safe, best_lap_time)
    struct.pack_into("<ff", p2, 24, distanza_giro, distanza_tot)
    struct.pack_into("<BBBB", p2, 34, pos, current_lap, 0, settore)
    struct.pack_into("<BBBBB", p2, 41, 0, 0, 2, 4, 2)

    h6 = struct.pack(hdr, 2020, 1, 0, 1, 6, 123456789, float(tempo), _fid, 0, 0)
    p6 = bytearray(1323)
    struct.pack_into("<HfffB", p6, 0, speed_kmh, 1.0, 0.0, 0.0, 0)
    _rpm_sf = rpm if rpm > 0 else (1800 if RF2_MEM.get("bat_addr") else 0)
    _gear_sf = int(gear_display) if rpm > 0 else (1 if RF2_MEM.get("bat_addr") else 0)
    struct.pack_into("<bHBBH", p6, 15, _gear_sf, _rpm_sf, 0, led_pct, led_bits)
    struct.pack_into("<BBBB", p6, 44, _u8(s_rl), _u8(s_rr), _u8(s_fl), _u8(s_fr))
    struct.pack_into("<BBBB", p6, 48, _u8(c_rl), _u8(c_rr), _u8(c_fl), _u8(c_fr))
    struct.pack_into("<HHHH", p6, 20, 320, 320, 340, 340); struct.pack_into("<H", p6, 36, eng_t if "eng_t" in locals() else int(SHM_DATA.get("engine_temp", 92))); struct.pack_into("<H", p6, 52, max(0, min(eng_t, 250)))

    h7 = struct.pack(hdr, 2020, 1, 0, 1, 7, 123456789, float(tempo), _fid, 0, 0)
    p7 = bytearray(1320)
    tc_f1 = 0 if tc_rf2 <= 0 else (1 if tc_rf2 <= 3 else 2)
    abs_f1 = 1 if abs_rf2 > 0 else 0
    bb_f1 = max(20, min(90, int(round(bb_rf2))))
    struct.pack_into("<BBBBB", p7, 0, tc_f1, abs_f1, 1, bb_f1, 0)
    _f_sf = fuel_val if fuel_val > 0.1 else 45.0
    _fl_sf = fuel_laps if fuel_laps > 0.1 else 15.0
    struct.pack_into("<fff", p7, 5, _f_sf, 100.0, _fl_sf)
    struct.pack_into("<HHB", p7, 17, max(6000, shift_rpm), max(1000, idle_rpm), 8)
    dmg_rl = max(0, min(100, int(round(100.0 - w_rl))))
    dmg_rr = max(0, min(100, int(round(100.0 - w_rr))))
    dmg_fl = max(0, min(100, int(round(100.0 - w_fl))))
    dmg_fr = max(0, min(100, int(round(100.0 - w_fr))))
    struct.pack_into("<BBBB", p7, 25, dmg_rl, dmg_rr, dmg_fl, dmg_fr)
    struct.pack_into("<BB", p7, 29, 16, 16)
    if in_fuorigiri:
        fia_flag = 2 if int(tempo * 20) % 2 == 0 else 4
    else:
        fia_flag = 3 if dash_state["flag"] == "yellow" else 0
    struct.pack_into("<b", p7, 42, fia_flag)

    # --- INIZIO PATCH ERS UNIVERSALE + SF1000 (PACKET 7) ---
    _ers_pct = float(locals().get("ers_pct", locals().get("ers_charge", 0.0)))
    _ers_act = int(locals().get("ers_active", 0))
    _ers_chg = int(locals().get("ers_charging", 0))
    _ers_mod = int(locals().get("ers_mode", 3 if _ers_act else (1 if _ers_pct > 0 else 0)))
    # Calcolo delta automatico per mod/sim che aggiornano solo la carica
    _prev_ers = globals().get("_OSW_PREV_ERS", _ers_pct)
    if _ers_pct > 0.0 and _ers_act == 0 and (_ers_pct < _prev_ers - 0.008):
        _ers_act = 1
        _ers_mod = 3
    elif _ers_pct > 0.0 and _ers_chg == 0 and (_ers_pct > _prev_ers + 0.008):
        _ers_chg = 1
    globals()["_OSW_PREV_ERS"] = _ers_pct
    _ers_joules = max(0.0, min(4000000.0, (_ers_pct / 100.0) * 4000000.0))
    struct.pack_into("<fB", p7, 43, _ers_joules, _ers_mod)
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

    out_sock.sendto(h6 + p6, (ip_display, porta_display))

    if tempo - RF2_MEM["last_slow_ts"] >= 0.2:
        RF2_MEM["last_slow_ts"] = tempo
        h0 = struct.pack(hdr, 2020, 1, 0, 1, 0, 123456789, float(tempo), _fid, 0, 0)
        p0 = bytearray(1440)
        out_sock.sendto(h0 + p0, (ip_display, porta_display))
        out_sock.sendto(h1 + p1, (ip_display, porta_display))
        if distanza_giro > 0.0 or cur_lap_time > 0.0:
            out_sock.sendto(h2 + p2, (ip_display, porta_display))
        out_sock.sendto(h7 + p7, (ip_display, porta_display))
