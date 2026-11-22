#!/usr/bin/env python3
import os
import py_compile
import re
import shutil

TARGET_FILE = "rf2_bridge.py"  # <-- Metti qui il nome esatto del tuo file


def apply_patch():
  if not os.path.exists(TARGET_FILE):
    print(f"Errore: file '{TARGET_FILE}' non trovato nella cartella corrente.")
    return

  # 1. Backup automatico di sicurezza
  backup_file = TARGET_FILE + ".bak"
  shutil.copy2(TARGET_FILE, backup_file)
  print(f"[OK] Backup creato: {backup_file}")

  with open(TARGET_FILE, "r", encoding="utf-8") as f:
    src = f.read()

  # --- PATCH 1: _get_rw_regions (solo regioni anonime rw-p <= 128 MB) ---
  new_get_rw = '''def _get_rw_regions(pid):
    regions = []
    try:
        with open(f"/proc/{pid}/maps", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if " rw-p " not in line or " /" in line:
                    continue
                m = re.match(r"([0-9a-f]+)-([0-9a-f]+)", line)
                if m:
                    s, e = int(m.group(1), 16), int(m.group(2), 16)
                    sz = e - s
                    if 0x10000 <= sz <= 0x8000000 and s >= 0x1000000:
                        regions.append((s, sz))
    except Exception:
        pass
    return regions'''

  src, n1 = re.subn(
      r"def _get_rw_regions\(pid\):.*?(?=\n\ndef )",
      new_get_rw,
      src,
      count=1,
      flags=re.DOTALL,
  )

  # --- PATCH 2: _scan_rf2_wheels (compatibile rF2 + LMU + priorita giocatore) ---
  new_scan_wheels = '''def _scan_rf2_wheels(pid, regions):
    fallback_addr = None
    with np.errstate(invalid="ignore"):
        for s, sz in reversed(regions):
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
                    (a[58:-70] > 0.01) & (a[58:-70] <= 1.0001) &
                    (a[90:-38] > 0.01) & (a[90:-38] <= 1.0001) &
                    (a[122:-6] > 0.01) & (a[122:-6] <= 1.0001)
                )
                for h in np.flatnonzero(mask):
                    w_off = align + int(h) * 8
                    if float(a.item(int(h) + 26)) < 0.9999999:
                        return int(s + w_off)
                    if fallback_addr is None:
                        fallback_addr = int(s + w_off)
    return fallback_addr'''

  src, n2 = re.subn(
      r"def _scan_rf2_wheels\(pid, regions\):.*?(?=\n\ndef )",
      new_scan_wheels,
      src,
      count=1,
      flags=re.DOTALL,
  )

  # --- PATCH 3: Throttling HTTP worker a 10 Hz + fallback sicuro cached_player ---
  src, n3a = re.subn(
      r'RF2_MEM\["cached_player"\]\s*=\s*next\(\(v for v in standings if'
      r' v\.get\("player"\)\),\s*standings(?:\)?)\)',
      'RF2_MEM["cached_player"] = next((v for v in standings if'
      ' v.get("player")), standings if standings else {})',
      src,
  )
  src, n3b = re.subn(r"time\.sleep\(0\.025\)", "time.sleep(0.10)", src)

  # --- PATCH 4: Intervallo retry scan da 0.4s a 2.5s ---
  src, n4 = re.subn(
      r'\(tempo - RF2_MEM\.get\("last_scan_ts", 0\.0\) >= 0\.4\)',
      '(tempo - RF2_MEM.get("last_scan_ts", 0.0) >= 2.5)',
      src,
  )

  print(
      f"[INFO] Patch applicate: regions={n1}, wheels={n2},"
      f" player_fix={n3a}, http_10hz={n3b}, scan_retry={n4}"
  )

  tmp_file = TARGET_FILE + ".tmp"
  with open(tmp_file, "w", encoding="utf-8") as f:
    f.write(src)

  # Verifica compilazione sintattica prima di sostituire l'originale
  try:
    py_compile.compile(tmp_file, doraise=True)
    os.replace(tmp_file, TARGET_FILE)
    print(f"[SUCCESSO] '{TARGET_FILE}' aggiornato e validato senza errori!")
  except Exception as e:
    print(f"[ERRORE SINTASSI] Ripristino annullato: {e}")
    if os.path.exists(tmp_file):
      os.remove(tmp_file)


if __name__ == "__main__":
  apply_patch()
