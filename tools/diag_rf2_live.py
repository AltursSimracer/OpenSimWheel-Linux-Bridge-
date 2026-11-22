#!/usr/bin/env python3
import json
import logging
import os
import re
import socket
import struct
import time
import urllib.request
import rf2_bridge as b  # <-- Adatta al nome del tuo modulo

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
logger = logging.getLogger("DIAG_RF2")


def _safe_get_rw_regions(pid):
  regions = []
  try:
    with open(f"/proc/{pid}/maps", "r", encoding="utf-8", errors="ignore") as f:
      for line in f:
        parts = line.split()
        # parts[0] = range, parts[1] = permessi
        if len(parts) < 2 or parts[1] != "rw-p":
          continue
        # Esclude file mappati su disco (/usr, /lib, .dll, .so, ecc.)
        if len(parts) >= 6 and parts[5].startswith("/"):
          continue
        m = re.match(r"([0-9a-f]+)-([0-9a-f]+)", parts[0])
        if m:
          s, e = int(m.group(1), 16), int(m.group(2), 16)
          sz = e - s
          # Max 64 MB (0x4000000) per sicurezza anti-freeze
          if 0x10000 <= sz <= 0x4000000 and s >= 0x1000000:
            regions.append((s, sz))
  except Exception:
    pass
  logger.info(f"Regioni rw-p anonime trovate: {len(regions)}")
  return regions


def _safe_http_poll_worker():
  last_sess = 0.0
  while b.RF2_MEM["http_running"]:
    now = time.time()
    ports = (
        (b.RF2_MEM["active_port"], 6397, 5397, 5396)
        if b.RF2_MEM["is_lmu"]
        else (b.RF2_MEM["active_port"], 5397, 6397, 5396)
    )
    if now - last_sess >= 5.0:
      last_sess = now
      for p in ports:
        try:
          sreq = urllib.request.urlopen(
              f"http://localhost:{p}/rest/watch/sessionInfo", timeout=0.15
          )
          sinfo = json.loads(sreq.read().decode("utf-8", errors="ignore"))
          ld = int(float(sinfo.get("lapDistance", 0)))
          if ld > 500:
            b.RF2_MEM["track_len_m"] = ld
          if "ambientTemp" in sinfo:
            b.RF2_MEM["air_temp"] = int(round(float(sinfo["ambientTemp"])))
          if "trackTemp" in sinfo:
            b.RF2_MEM["track_temp"] = int(round(float(sinfo["trackTemp"])))
          break
        except Exception:
          continue
    for p in ports:
      try:
        req = urllib.request.urlopen(
            f"http://localhost:{p}/rest/watch/standings", timeout=0.15
        )
        standings = json.loads(req.read().decode("utf-8", errors="ignore"))
        if standings and isinstance(standings, list):
          b.RF2_MEM["active_port"] = p
          b.RF2_MEM["cached_player"] = next(
              (v for v in standings if v.get("player")),
              standings[0] if standings else {},
          )
        break
      except Exception:
        continue
    time.sleep(0.10)


b._get_rw_regions = _safe_get_rw_regions
b._http_poll_worker = _safe_http_poll_worker


def main():
  tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  dash_state = {
      "packets": 0,
      "hz_counter": 0,
      "hz_timer": time.time(),
      "hz": 0.0,
  }

  logger.info("Avvio diagnostica su gioco già aperto...")
  last_log = 0.0

  try:
    while True:
      # Mantiene almeno 2.5s tra uno scan e l'altro
      if (
          not b.RF2_MEM["scan_running"]
          and (time.time() - b.RF2_MEM.get("last_scan_ts", 0.0)) < 2.5
      ):
        b.RF2_MEM["last_scan_ts"] = time.time() - 0.5  # posticipa leggermente

      b.elabora_pacchetto_rf2(
          None, tx_sock, "127.0.0.1", 20777, dash_state, logger
      )

      now = time.time()
      if now - last_log >= 1.0:
        last_log = now
        pid = b.RF2_MEM["pid"]
        if not pid:
          print("[ATTESA] Gioco non rilevato...")
          continue

        pl = b.RF2_MEM.get("cached_player")
        if not isinstance(pl, dict):
          print(f"[PID {pid}] Attesa REST API...")
          continue

        in_gar = pl.get("inGarageStall", False)
        veh = pl.get("vehicleName", "?")
        eng = hex(b.RF2_MEM["addr"]) if b.RF2_MEM["addr"] else "NO"
        whl = (
            hex(b.RF2_MEM["wheels_addr"]) if b.RF2_MEM["wheels_addr"] else "NO"
        )

        raw_info = ""
        if b.RF2_MEM["addr"]:
          ebuf = b._read_mem(pid, b.RF2_MEM["addr"], 72)
          if ebuf and len(ebuf) == 72:
            om, _, _, _, lim_om = struct.unpack_from("<ddddd", ebuf, 0)
            raw_info = f" | raw_om={om:.1f} raw_lim={lim_om:.1f}"

        print(
            f"[PID {pid}] '{veh}' Garage={in_gar} | "
            f"Eng={eng} Whl={whl}{raw_info} | "
            f"G:{dash_state.get('gear')} RPM:{dash_state.get('rpm')}/{dash_state.get('max_rpm')} "
            f"SPD:{dash_state.get('speed')}km/h | "
            f"FL:{dash_state.get('tyre_fl')}°C ({dash_state.get('tyre_press', [0])[0]} PSI)"
        )
      time.sleep(0.016)
  except KeyboardInterrupt:
    print("\nDiagnostica terminata.")
  finally:
    b.RF2_MEM["http_running"] = False
    tx_sock.close()


if __name__ == "__main__":
  main()
