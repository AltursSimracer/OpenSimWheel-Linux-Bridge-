#!/usr/bin/env python3
import os
import re
import struct
import ctypes
import time

_libc = ctypes.CDLL("libc.so.6")

class _iovec(ctypes.Structure):
    _fields_ = [("iov_base", ctypes.c_void_p), ("iov_len", ctypes.c_size_t)]

def _read_mem(pid, addr, size):
    buf = ctypes.create_string_buffer(size)
    local_iov = _iovec(ctypes.cast(buf, ctypes.c_void_p), size)
    remote_iov = _iovec(ctypes.c_void_p(addr), size)
    n = _libc.process_vm_readv(pid, ctypes.byref(local_iov), 1, ctypes.byref(remote_iov), 1, 0)
    return buf.raw if n == size else None

def find_rf2_pid():
    for p in os.listdir("/proc"):
        if p.isdigit():
            try:
                with open(f"/proc/{p}/cmdline", "rb") as f:
                    cmd = f.read().decode("utf-8", errors="ignore")
                if "rFactor2.exe" in cmd and "--type=" not in cmd:
                    return int(p)
            except Exception:
                continue
    return None

def get_rw_regions(pid):
    regions = []
    with open(f"/proc/{pid}/maps", "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.match(r"([0-9a-f]+)-([0-9a-f]+) rw-[ps] (.*)", line)
            if m:
                s, e = int(m.group(1), 16), int(m.group(2), 16)
                tag = m.group(3).strip()
                sz = e - s
                if 0x10000 <= sz <= 0x10000000:
                    regions.append((s, sz, tag))
    return regions

def find_engine_addr(pid, regions):
    import numpy as np
    candidati = []
    with np.errstate(invalid="ignore"):
        for s, sz, _ in regions:
            if not (0x1000000 <= s < 0x200000000):
                continue
            r1 = _read_mem(pid, s, sz)
            if not r1 or len(r1) < 500:
                continue
            for align in (0, 4):
                n8 = (len(r1) - align) // 8
                if n8 <= 60:
                    continue
                a1 = np.frombuffer(r1, dtype=np.float64, count=n8, offset=align)
                mask = (a1 >= 400.0) & (a1 <= 18000.0) & ((a1 % 1.0) != 0.0)
                for idx in np.flatnonzero(mask):
                    off = align + (int(idx) * 8) - 12
                    addr = s + off
                    if (addr % 8) == 4 and off >= 64 and off + 244 <= len(r1):
                        g1, = struct.unpack_from("<i", r1, off)
                        g1_twin, = struct.unpack_from("<i", r1, off + 224)
                        if g1 == g1_twin and -1 <= g1 <= 8:
                            rpm1 = float(a1.item(int(idx)))
                            rpm1_twin, = struct.unpack_from("<d", r1, off + 236)
                            if abs(rpm1 - rpm1_twin) < 5.0:
                                candidati.append((int(addr), rpm1))
    if not candidati:
        return None
    time.sleep(0.03)
    for addr, old_rpm in candidati:
        chk = _read_mem(pid, addr, 20)
        if chk:
            _, new_rpm = struct.unpack_from("<id", chk, 0)
            if abs(new_rpm - old_rpm) > 0.0001 and 350.0 <= new_rpm <= 20000.0:
                return int(addr)
    return candidati[0][0]

def scan_wheels_in_buffer(buf, base_addr, ref_addr=None):
    # Cerca triplette di temperature gomme in Kelvin (290K = 17°C .. 425K = 152°C)
    # ripetute per 4 ruote a passo regolare (stride tipico: 240, 248, 256, 264, 272)
    hits = []
    for stride in (240, 248, 256, 264, 272, 232):
        max_off = len(buf) - (stride * 3 + 24)
        for off in range(0, max_off, 4):
            ok_all = True
            wheels_t = []
            for w in range(4):
                t1, t2, t3 = struct.unpack_from("<ddd", buf, off + w * stride)
                if not all(290.0 <= v <= 425.0 and math.isfinite(v) for v in (t1, t2, t3)):
                    ok_all = False
                    break
                # Scarta valori identici sospetti tipo esattamente 300.000000
                if t1 == t2 == t3 and (t1 % 1.0 == 0.0):
                    ok_all = False
                    break
                wheels_t.append((round(t1 - 273.15, 1), round(t2 - 273.15, 1), round(t3 - 273.15, 1)))
            if ok_all:
                rel = (base_addr + off - ref_addr) if ref_addr else None
                hits.append((off, stride, rel, wheels_t))
    return hits

import math

def main():
    print("=== Diagnostica Memoria Ruote rFactor 2 ===")
    pid = find_rf2_pid()
    if not pid:
        print("[ERRORE] Processo rFactor2.exe non trovato. Avvia rFactor 2 ed entra in pista.")
        return
    print(f"[OK] Trovato rFactor2.exe con PID: {pid}")

    regions = get_rw_regions(pid)
    eng_addr = find_engine_addr(pid, regions)
    if eng_addr:
        g, rpm = struct.unpack_from("<id", _read_mem(pid, eng_addr, 20), 0)
        print(f"[OK] Indirizzo Motore (Gear/RPM): 0x{eng_addr:x} (Gear={g}, RPM={rpm:.1f})")
    else:
        print("[WARN] Indirizzo motore non agganciato, eseguo comunque scan completo...")

    # 1. Cerca prima nella finestra +-4096 byte attorno all'indirizzo motore
    found_any = False
    if eng_addr:
        win_start = eng_addr - 2048
        win_buf = _read_mem(pid, win_start, 6144)
        if win_buf:
            hits = scan_wheels_in_buffer(win_buf, win_start, eng_addr)
            for off, stride, rel, wheels_t in hits:
                found_any = True
                print(f"\n>>> TROVATO BLOCCO 4 RUOTE VICINO A RPM! stride={stride}, offset_da_gear={rel:+d} byte")
                print_wheel_details(win_buf, off, stride, wheels_t)

    # 2. Cerca anche in eventuali memfd:wine-mapping (come LMU)
    for s, sz, tag in regions:
        if "wine-mapping" in tag or sz == 0x50000:
            buf = _read_mem(pid, s, sz)
            if not buf:
                continue
            hits = scan_wheels_in_buffer(buf, s, eng_addr)
            for off, stride, rel, wheels_t in hits:
                found_any = True
                print(f"\n>>> TROVATO BLOCCO 4 RUOTE IN {tag or '0x50000'}! base_off={off}, stride={stride}")
                print_wheel_details(buf, off, stride, wheels_t)

    if not found_any:
        print("\n[INFO] Nessun blocco trovato attorno a RPM o wine-mapping. Eseguo scan su tutte le regioni RW...")
        for s, sz, tag in regions:
            if not (0x1000000 <= s < 0x200000000):
                continue
            buf = _read_mem(pid, s, sz)
            if not buf:
                continue
            hits = scan_wheels_in_buffer(buf, s, eng_addr)
            for off, stride, rel, wheels_t in hits:
                found_any = True
                print(f"\n>>> TROVATO BLOCCO 4 RUOTE IN REGIONE 0x{s:x} ({tag})! off={off}, stride={stride}, rel_gear={rel}")
                print_wheel_details(buf, off, stride, wheels_t)

def print_wheel_details(buf, base_off, stride, wheels_t):
    names = ("FL", "FR", "RL", "RR")
    for w in range(4):
        w_off = base_off + w * stride
        t_imo = wheels_t[w]
        print(f"  [{names[w]}] Temp Tripletta @ +0: {t_imo[0]}°C | {t_imo[1]}°C | {t_imo[2]}°C")
        # Scansiona i double intorno a w_off (-48 .. +64 byte) per trovare Carcassa, Pressione e Usura
        for d_off in range(-48, 72, 8):
            if d_off == 0:
                continue
            pos = w_off + d_off
            if 0 <= pos <= len(buf) - 8:
                val, = struct.unpack_from("<d", buf, pos)
                if not math.isfinite(val):
                    continue
                if 290.0 <= val <= 425.0:
                    print(f"       offset {d_off:+4d}: {val - 273.15:6.1f} °C  (Kelvin={val:.2f}) [Possibile Carcassa/Inner]")
                elif 120.0 <= val <= 300.0:
                    print(f"       offset {d_off:+4d}: {val:6.1f} kPa ({val * 0.1450377:5.1f} PSI) [Possibile Pressione]")
                elif 0.05 <= val <= 1.0001 and val != 1.0:
                    print(f"       offset {d_off:+4d}: {val * 100.0:6.2f} %   (raw={val:.5f}) [Possibile Usura]")

if __name__ == "__main__":
    main()
