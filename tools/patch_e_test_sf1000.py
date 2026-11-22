#!/usr/bin/env python3
import logging
import os
import py_compile
import re
import shutil
import socket
import struct
import time

TARGET_FILE = "rf2_bridge.py"


def patch_region_cache():
  shutil.copy2(TARGET_FILE, TARGET_FILE + ".bak2")
  with open(TARGET_FILE, "r", encoding="utf-8") as f:
    src = f.read()

  # Aggiunge last_eng_reg e last_whl_reg a RF2_MEM se non presenti
  if '"last_eng_reg"' not in src:
    src = src.replace(
        '"wheels_addr": None,',
        '"wheels_addr": None,\n    "last_eng_reg": None,\n   '
        ' "last_whl_reg": None,',
        1,
    )

  # Aggiorna _bg_scan_worker per provare prima le ultime regioni valide (< 0.05s al riaggancio)
  new_worker = '''def _bg_scan_worker(pid, logger):
    try:
        regions = _get_rw_regions(pid)
        if not RF2_MEM["addr"]:
            eng_regs = list(regions)
            if RF2_MEM.get("last_eng_reg") in eng_regs:
                eng_regs.remove(RF2_MEM["last_eng_reg"])
                eng_regs.append(RF2_MEM["last_eng_reg"])  # reversed() lo mette per primo!
            e_addr = _scan_rf2_engine(pid, eng_regs)
            if e_addr:
                RF2_MEM["addr"] = e_addr
                RF2_MEM["gear_addr"] = e_addr + 632
                for r in regions:
                    if r <= e_addr <= r + r:
                        RF2_MEM["last_eng_reg"] = r
                        break
                if logger:
                    logger.info(f"rF2/LMU Nativo: Motore + Cambio agganciati @ 0x{e_addr:x} (+632)")
        if not RF2_MEM["wheels_addr"]:
            whl_regs = list(regions)
            if RF2_MEM.get("last_whl_reg") in whl_regs:
                whl_regs.remove(RF2_MEM["last_whl_reg"])
                whl_regs.append(RF2_MEM["last_whl_reg"])  # reversed() lo mette per primo!
            w_addr = _scan_rf2_wheels(pid, whl_regs)
            if w_addr:
                RF2_MEM["wheels_addr"] = w_addr
                for r in regions:
                    if r <= w_addr <= r + r:
                        RF2_MEM["last_whl_reg"] = r
                        break
                if logger:
                    logger.info(f"rF2/LMU Nativo: Blocco 4 ruote agganciato @ 0x{w_addr:x}")
    finally:
        RF2_MEM["scan_running"] = False'''

  src, n = re.subn(
      r"def _bg_scan_worker\(pid, logger\):.*?(?=\n\ndef )",
      new_worker,
      src,
      count=1,
      flags=re.DOTALL,
  )
  tmp = TARGET_FILE + ".tmp"
  with open(tmp, "w", encoding="utf-8") as f:
    f.write(src)
  py_compile.compile(tmp, doraise=True)
  os.replace(tmp, TARGET_FILE)
  print(f"[OK] Cache regioni applicata (match={n}) e sintassi verificata.")


def test_sf1000_packets():
  import rf2_bridge as b

  logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
  log = logging.getLogger("SF1000_TEST")

  rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  rx_sock.bind(("127.0.0.1", 20777))
  rx_sock.setblocking(False)
  tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  ds = {"packets": 0, "hz_counter": 0, "hz_timer": time.time(), "hz": 0.0}
  pkt_counts = {1: 0, 2: 0, 6: 0, 7: 0}
  last_p6 = None
  last_p7 = None

  print("Raccolta e decodifica pacchetti F1 2020 (SF1000) per 8 secondi...")
  t0 = time.time()
  while time.time() - t0 < 8.0:
    b.elabora_pacchetto_rf2(None, tx_sock, "127.0.0.1", 20777, ds, log)
    while True:
      try:
        data, _ = rx_sock.recvfrom(2048)
        if len(data) >= 24:
          # Header F1 2020 (24 byte): packetId è al byte 5
          pkt_id = data
          pkt_counts[pkt_id] = pkt_counts.get(pkt_id, 0) + 1
          payload = data[24:]
          if pkt_id == 6 and len(payload) >= 52:
            spd = struct.unpack_from("<H", payload, 0)
            gear, rpm, _, led_pct, led_bits = struct.unpack_from(
                "<bHBBH", payload, 15
            )
            t_surf = struct.unpack_from("<BBBB", payload, 44)
            t_core = struct.unpack_from("<BBBB", payload, 48)
            last_p6 = (spd, gear, rpm, led_pct, bin(led_bits), t_surf, t_core)
          elif pkt_id == 7 and len(payload) >= 30:
            fuel, cap, fuel_laps = struct.unpack_from("<fff", payload, 5)
            shift_rpm, idle_rpm, _ = struct.unpack_from("<HHB", payload, 17)
            dmg = struct.unpack_from("<BBBB", payload, 25)
            last_p7 = (
                round(fuel, 1),
                round(fuel_laps, 1),
                shift_rpm,
                idle_rpm,
                dmg,
            )
      except BlockingIOError:
        break
    time.sleep(0.016)

  b.RF2_MEM["http_running"] = False
  rx_sock.close()
  tx_sock.close()

  print("\n--- RISULTATO PACCHETTI UDP F1 2020 (SF1000) ---")
  print(f"Conteggio pacchetti inviati in 8s: {pkt_counts}")
  if last_p6:
    print(
        f"Packet 6 (Telemetria): Speed={last_p6}km/h | Gear={last_p6} |"
        f" RPM={last_p6} | LED={last_p6}% ({last_p6})"
    )
    print(
        f"   Gomme SF1000 (RL,RR,FL,FR): Surf={last_p6}°C | Core={last_p6}°C"
    )
  if last_p7:
    print(
        f"Packet 7 (Status): Fuel={last_p7}% ({last_p7} laps) |"
        f" ShiftRPM={last_p7} IdleRPM={last_p7} | TyreDmg={last_p7}%"
    )


if __name__ == "__main__":
  patch_region_cache()
  test_sf1000_packets()
