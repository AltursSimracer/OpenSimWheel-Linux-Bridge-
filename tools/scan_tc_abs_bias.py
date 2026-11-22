#!/usr/bin/env python3
import json
import urllib.request
import numpy as np
import rf2_bridge as b

pid, _ = b._find_rf2_pid()
b._bg_scan_worker(pid, None)
eng = b.RF2_MEM["addr"]
if not eng:
  print(
      "Assicurati di essere fuori dal garage (Drive) e riprova!"
  )
  exit(1)

print(f"Motore agganciato @ {hex(eng)}")

# 1. Verifica cosa espone /rest/garage/getSetup su rF2/LMU
for ep in ("/rest/garage/getSetup", "/rest/garage/UIScreen/CarSetup"):
  try:
    req = urllib.request.urlopen(f"http://localhost:5397{ep}", timeout=0.5)
    txt = req.read().decode("utf-8", errors="ignore")
    print(f"[REST {ep}] OK ({len(txt)} byte) -> estratti:")
    for kw in ("Fuel", "TC", "Traction", "ABS", "Brake", "Bias", "Balance"):
      for line in txt.splitlines():
        if kw.lower() in line.lower():
          print("  ", line.strip()[:100])
  except Exception as e:
    print(f"[REST {ep}] non disponibile: {e}")

# 2. Scanner differenziale RAM (+/- 256 KB intorno al motore)
START = eng - 0x40000
SIZE = 0x80000

input(
    "\n1) Metti l'auto in pista (Drive), guarda TC / ABS / Bias attuali, poi"
    " premi INVIO..."
)
snap1 = b._read_mem(pid, START, SIZE)

input(
    "2) Ora in gioco cambia di 1 scatto BRAKE BIAS (o TC / ABS), poi premi"
    " INVIO..."
)
snap2 = b._read_mem(pid, START, SIZE)

print("\n--- OFFSET TROVATI RISPETTO AL MOTORE (eng + delta) ---")
i1 = np.frombuffer(snap1, dtype=np.int32)
i2 = np.frombuffer(snap2, dtype=np.int32)
for idx in np.flatnonzero(i1 != i2):
  v1, v2 = int(i1.item(int(idx))), int(i2.item(int(idx)))
  if 0 <= v1 <= 20 and 0 <= v2 <= 20 and abs(v2 - v1) <= 3:
    delta = (START + int(idx) * 4) - eng
    print(f"[INT32]   eng {delta:+d} : {v1} -> {v2}")

f1 = np.frombuffer(snap1, dtype=np.float64)
f2 = np.frombuffer(snap2, dtype=np.float64)
for idx in np.flatnonzero(f1 != f2):
  v1, v2 = float(f1.item(int(idx))), float(f2.item(int(idx)))
  if (0.30 <= v1 <= 0.80 and 0.30 <= v2 <= 0.80) or (
      30.0 <= v1 <= 80.0 and 30.0 <= v2 <= 80.0
  ):
    if 0.0005 <= abs(v2 - v1) <= 5.0:
      delta = (START + int(idx) * 8) - eng
      print(f"[FLOAT64] eng {delta:+d} : {v1:.4f} -> {v2:.4f}")
