import os, re, shutil, py_compile

FILES = [
    "OpenSimWheel_Linux_Bridge.py",
    "ac_ace_bridge.py",
    "rf2_bridge.py",
    "lmu_bridge.py",
    "livedash.html",
]

print("=== AVVIO PATCH UNIVERSALE ERS + SF1000 / WEB DASH ===")

# 1. Backup automatico
for fn in FILES:
    if os.path.exists(fn):
        shutil.copy2(fn, fn + ".bak")
        print(f"[BACKUP] Creato {fn}.bak")

# 2. Patch livedash.html (Aggiunta indicatore ERS verde quando attivo + azzurro in ricarica)
if os.path.exists("livedash.html"):
    with open("livedash.html", "r", encoding="utf-8") as f:
        html = f.read()

    if "ers-active" not in html:
        css_ers = """  .elec-item.ers-active { background: rgba(34,197,94,0.22); border: 1px solid #22c55e; color: #22c55e; box-shadow: 0 0 12px rgba(34,197,94,0.45); }
  .elec-item.ers-charging { background: rgba(56,189,248,0.18); border: 1px solid #38bdf8; color: #38bdf8; }
"""
        html = html.replace(".card.flag-yellow", css_ers + "  .card.flag-yellow", 1)

    if 'id="ersBox"' not in html:
        html = html.replace(
            '<div class="elec-item">FLAG <span id="flagTxt">--</span></div>',
            '<div class="elec-item" id="ersBox">ERS <span id="ersTxt">--%</span></div>\n    <div class="elec-item">FLAG <span id="flagTxt">--</span></div>',
            1
        )

    if "ersBox" not in html or "d.ers_active" not in html:
        js_ers = """      const ersBox = document.getElementById("ersBox");
      const ersTxt = document.getElementById("ersTxt");
      if(ersBox && ersTxt){
        ersBox.classList.remove("ers-active", "ers-charging");
        if(d.connected && typeof d.ers === "number" && d.ers >= 0){
          ersTxt.textContent = Math.round(d.ers) + "%";
          if(d.ers_active === 1 || d.ers_active === true) ersBox.classList.add("ers-active");
          else if(d.ers_charging === 1 || d.ers_charging === true) ersBox.classList.add("ers-charging");
        } else {
          ersTxt.textContent = "--%";
        }
      }
"""
        html = html.replace('const fTxt = document.getElementById("flagTxt");', js_ers + '      const fTxt = document.getElementById("flagTxt");', 1)

    with open("livedash.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("[OK] Patch applicata a livedash.html (ERS verde attivo / azzurro ricarica)")

# 3. Patch Python (Core + Satelliti: F1-UDP SF1000 Packet 7 + JSON universale)
ERS_SNIPPET = '''
        # --- INIZIO PATCH ERS UNIVERSALE + SF1000 (PACKET 7) ---
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
'''

# Estrazione specifica AC/ACE (kersCharge @ offset 80, kersInput @ offset 84 della physics struct)
AC_ERS_EXTRACT = '''        ers_pct = 0.0
        ers_active = 0
        ers_charging = 0
        if len(data) >= 88:
            _kc, _ki = struct.unpack_from("<ff", data, 80)
            if 0.0 <= _kc <= 1.0:
                ers_pct = round(_kc * 100.0, 1)
            if _ki > 0.05:
                ers_active = 1
'''

for py_fn in ["OpenSimWheel_Linux_Bridge.py", "ac_ace_bridge.py", "rf2_bridge.py", "lmu_bridge.py"]:
    if not os.path.exists(py_fn):
        continue
    with open(py_fn, "r", encoding="utf-8") as f:
        code = f.read()

    if "PATCH ERS UNIVERSALE" in code:
        print(f"[SKIP] {py_fn} già patchato.")
        continue

    # Per AC/ACE inietta anche lettura kersCharge / kersInput da Shared Memory
    if py_fn in ("ac_ace_bridge.py", "OpenSimWheel_Linux_Bridge.py") and 'flag_str = "none"' in code:
        code = code.replace('        flag_str = "none"', AC_ERS_EXTRACT + '        flag_str = "none"', 1)

    # Inietta il packing Packet 7 + aggiornamento state subito dopo fia_flag
    target = 'struct.pack_into("<b", p7, 42, fia_flag)'
    if target in code:
        # Adatta l'indentazione del blocco alla riga target
        m = re.search(r'^([ \t]*)' + re.escape(target), code, re.M)
        indent = m.group(1) if m else "        "
        indented_snippet = "\n".join(
            (indent + line[8:] if line.startswith("        ") else line)
            for line in ERS_SNIPPET.splitlines()
        )
        code = code.replace(target, target + "\n" + indented_snippet, 1)

        with open(py_fn, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            py_compile.compile(py_fn, doraise=True)
            print(f"[OK] Patch applicata e verificata su {py_fn}")
        except Exception as e:
            shutil.copy2(py_fn + ".bak", py_fn)
            print(f"[ERRORE SINTASSI] Ripristinato backup per {py_fn}: {e}")
    else:
        print(f"[INFO] Pattern p7 non trovato in {py_fn}, nessuna modifica.")

print("=== COMPLETATO! ===")
