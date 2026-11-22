#!/usr/bin/env python3
import json
import logging
import os
import re
import socket
import struct
import time
import urllib.request
import numpy as np
import rf2_bridge as b  # <-- Adatta solo se il tuo modulo ha un nome diverso

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
logger = logging.getLogger("TEST_FINAL")


def _safe_get_rw_regions(pid):
  regions = []
  try:
    with open(f"/proc/{pid}/maps", "r", encoding="utf-8", errors="ignore") as f:
      for line in f:
        parts = line.split()
        if len(parts) < 2 or parts != "rw-p":
          continue
        if len(parts) >= 6 and parts.startswith("/"):
          continue
        m = re.match(r"([0-9a-f]+)-([0-9a-f]+)", parts)
        if m:
          s, e = int(m.group(1), 16), int(m.group(2), 16)
          sz = e - s
          if 0x10000 <= sz <= 0x8000000 and s >= 0x1000000:
            regions.append((s, sz))
  except Exception:
    pass
  return regions


def _universal_scan_rf2_wheels(pid, regions):
  fallback_addr = None
  with np.errstate(invalid="ignore"):
    for s, sz in reversed(regions):
      buf = b._read_mem(pid, s, sz)
      if not buf or len(buf) < 4096:
        continue
      for align in (0, 4):
        n8 = (len(buf) - align) // 8
        if n8 <= 130:
          continue
        a = np.frombuffer(buf, dtype=np.float64, count=n8, offset=align)
        # Maschera compatibile con rF2 e LMU (senza vincolo p224 che su rF2 vale -FLT_MAX)
        mask = (
            (a[:-128] >= 275.0)
            & (a[:-128] <= 430.0)
            & (a[2:-126] >= 275.0)
            & (a[2:-126] <= 430.0)
            & (a[3:-125] >= 275.0)
            & (a[3:-125] <= 430.0)
            & (a[4:-124] >= 275.0)
            & (a[4:-124] <= 430.0)
            & (a[26:-102] > 0.01)
            & (a[26:-102] <= 1.0001)
            & (a[58:-70] > 0.01)
            & (a[58:-70] <= 1.0001)
            & (a[90:-38] > 0.01)
            & (a[90:-38] <= 1.0001)
            & (a[122:-6] > 0.01)
            & (a[122:-6] <= 1.0001)
        )
        for h in np.flatnonzero(mask):
          w_off = align + int(h) * 8
          # Priorità all'auto del giocatore con gomma già attiva (w_raw < 1.0) rispetto alle AI ferme
          if float(a.item(int(h) + 26)) < 0.9999999:
            return int(s + w_off)
          if fallback_addr is None:
            fallback_addr = int(s + w_off)
  return fallback_addr


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
              standings if standings else {},
          )
        break
      except Exception:
        continue
    time.sleep(0.10)


b._get_rw_regions = _safe_get_rw_regions
b._scan_rf2_wheels = _universal_scan_rf2_wheels
b._http_poll_worker = _safe_http_poll_worker


def main():
  tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  dash_state = {
      "packets": 0,
      "hz_counter": 0,
      "hz_timer": time.time(),
      "hz": 0.0,
  }
  logger.info("Test finale 1.4.0 rF2/LMU avviato (patch in RAM)...")
  last_log = 0.0

  try:
    while True:
      b.elabora_pacchetto_rf2(
          None, tx_sock, "127.0.0.1", 20777, dash_state, logger
      )
      now = time.time()
      if now - last_log >= 1.0:
        last_log = now
        pid = b.RF2_MEM["pid"]
        pl = b.RF2_MEM.get("cached_player")
        if not pid or not isinstance(pl, dict):
          continue
        eng = hex(b.RF2_MEM["addr"]) if b.RF2_MEM["addr"] else "NO"
        whl = (
            hex(b.RF2_MEM["wheels_addr"]) if b.RF2_MEM["wheels_addr"] else "NO"
        )
        print(
            f"[PID {pid}] '{pl.get('vehicleName')}' | Eng={eng} Whl={whl} | "
            f"G:{dash_state.get('gear')} RPM:{dash_state.get('rpm')}/{dash_state.get('max_rpm')} "
            f"SPD:{dash_state.get('speed')}km/h | "
            f"Core:[{dash_state.get('tyre_fl')}, {dash_state.get('tyre_fr')}, {dash_state.get('tyre_rl')}, {dash_state.get('tyre_rr')}]°C | "
            f"IMO_FL:{dash_state.get('tyre_fl_imo')} | Wear:{dash_state.get('tyre_wear')}"
        )
      time.sleep(0.016)
  except KeyboardInterrupt:
    print("\nTest completato.")
  finally:
    b.RF2_MEM["http_running"] = False
    tx_sock.close()


if __name__ == "__main__":
  main()
