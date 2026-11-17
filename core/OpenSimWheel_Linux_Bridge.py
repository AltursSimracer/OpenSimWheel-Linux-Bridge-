#!/usr/bin/env python3
import atexit
try:
    from rf2_bridge import elabora_pacchetto_rf2
except ImportError:
    elabora_pacchetto_rf2 = None
from lmu_bridge import elabora_pacchetto_lmu
from ac_ace_bridge import elabora_pacchetto_ac_ace
from rrre_bridge import elabora_pacchetto_rrre
from acc_bridge import ACC_STATE, acc_send_handshake, elabora_pacchetto_acc
# ==============================================================================
# OpenSimWheel Linux Bridge - Native UDP Telemetry Bridge
# Copyright (C) 2026 Alex
# Licensed under the GNU General Public License v3.0 (GPLv3)
# See LICENSE.txt for full license details.
# ==============================================================================
import socket
import sys
import struct
import time
import os
import subprocess
import threading
import configparser
import logging
import json
from logging.handlers import RotatingFileHandler
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_base_dir = os.path.dirname(os.path.abspath(__file__))
_log_file = os.path.join(_base_dir, "bridge.log")
logger = logging.getLogger("OSW_Bridge")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = RotatingFileHandler(_log_file, maxBytes=512000, backupCount=1, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(_handler)

DASH_STATE = {
    "connected": False,
    "gear": "N",
    "speed": 0,
    "rpm": 0,
    "max_rpm": 8500,
    "fuel": 0.0,
    "fuel_laps": 0.0,
    "fuel_per_lap": 0.0,
    "cur_lap": 0.0,
    "last_lap": 0.0,
    "s1": 0.0,
    "s2": 0.0,
    "s3": 0.0,
    "tyre_fl": 0,
    "tyre_fr": 0,
    "tyre_rl": 0,
    "tyre_rr": 0,
    "tyre_fl_imo": list((0, 0, 0)),
    "tyre_fr_imo": list((0, 0, 0)),
    "tyre_rl_imo": list((0, 0, 0)),
    "tyre_rr_imo": list((0, 0, 0)),
    "tyre_press": list((0.0, 0.0, 0.0, 0.0)),
    "tyre_wear": list((100, 100, 100, 100)),
    "tc": 0,
    "abs": 0,
    "brake_bias": 0.0,
    "flag": "none",
    "air_temp": 0,
    "track_temp": 0,
    "packets": 0,
    "hz": 0.0,
    "last_ts": 0.0,
    "hz_counter": 0,
    "hz_timer": time.time()
}

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

LIVE_DASH_HTML = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenSimWheel Live Dash</title>
<style>
  body { background:#0b0d10; color:#f0f3f6; font-family:system-ui,-apple-system,sans-serif; margin:0; padding:16px; display:flex; flex-direction:column; align-items:center; }
  .header { width:100%; max-width:720px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #222831; padding-bottom:10px; margin-bottom:16px; }
  .title { font-size:1.2rem; font-weight:700; letter-spacing:1px; }
  .badge { padding:4px 12px; border-radius:20px; font-size:0.85rem; font-weight:700; background:#3a1c1c; color:#ff5252; }
  .badge.on { background:#163824; color:#2ecc71; }
  .leds { width:100%; max-width:720px; display:grid; grid-template-columns:repeat(15,1fr); gap:6px; margin-bottom:20px; }
  .led { height:16px; border-radius:4px; background:#1c2128; transition:background 0.05s; }
  .grid { width:100%; max-width:720px; display:grid; grid-template-columns:1fr 1.2fr 1fr; gap:14px; align-items:center; text-align:center; }
  .card { background:#13171d; border:1px solid #222831; border-radius:14px; padding:18px 10px; }
  .gear { font-size:5.5rem; font-weight:900; color:#f1c40f; line-height:1; }
  .val { font-size:3rem; font-weight:800; line-height:1.1; }
  .lbl { font-size:0.8rem; color:#8b949e; text-transform:uppercase; letter-spacing:1px; margin-top:6px; }
  .subgrid { width:100%; max-width:720px; display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-top:14px; text-align:center; }
  .subcard { background:#13171d; border:1px solid #222831; border-radius:10px; padding:12px; }
  .subval { font-size:1.3rem; font-weight:700; color:#58a6ff; }
</style>
</head>
<body>
  <div class="header">
    <div class="title">🏁 OpenSimWheel Live Dash</div>
    <div id="status" class="badge">DISCONNESSO</div>
  </div>
  <div class="leds" id="ledbar"></div>
  <div class="grid">
    <div class="card"><div class="val" id="speed">0</div><div class="lbl">km/h</div></div>
    <div class="card"><div class="gear" id="gear">N</div><div class="lbl">GEAR</div></div>
    <div class="card"><div class="val" id="rpm">0</div><div class="lbl">RPM</div></div>
  </div>
  <div class="subgrid">
    <div class="subcard"><div class="subval" id="fuel">F: --.- L</div><div class="lbl">Carburante</div></div>
    <div class="subcard"><div class="subval" id="pkts">0</div><div class="lbl">Pacchetti OSW</div></div>
    <div class="subcard"><div class="subval" id="hz">-- Hz</div><div class="lbl">Frequenza</div></div>
  </div>
<script>
  const bar = document.getElementById("ledbar");
  for(let i=0;i<15;i++){ const d=document.createElement("div"); d.className="led"; bar.appendChild(d); }
  const leds = document.querySelectorAll(".led");
  async function update(){
    try{
      const r = await fetch("/api/telemetry");
      const d = await r.json();
      const st = document.getElementById("status");
      if(d.connected){ st.textContent="CONNESSO"; st.className="badge on"; }
      else { st.textContent="IN ATTESA DEL SIMULATORE..."; st.className="badge"; }
      document.getElementById("gear").textContent = d.gear;
      document.getElementById("speed").textContent = d.speed;
      document.getElementById("rpm").textContent = d.rpm;
      document.getElementById("fuel").textContent = "F: " + d.fuel.toFixed(1) + " L";
      document.getElementById("pkts").textContent = d.packets;
      document.getElementById("hz").textContent = d.hz.toFixed(1) + " Hz";
      const ratio = d.max_rpm > 0 ? Math.min(1, Math.max(0, d.rpm / d.max_rpm)) : 0;
      const lit = Math.round(ratio * 15);
      leds.forEach((el, idx) => {
        if(idx < lit){
          el.style.background = idx < 5 ? "#2ecc71" : (idx < 10 ? "#3498db" : "#e74c3c");
        } else { el.style.background = "#1c2128"; }
      });
    }catch(e){}
  }
  setInterval(update, 60);
</script>
</body>
</html>"""

class LiveDashHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    def do_GET(self):
        if self.path == "/api/telemetry":
            now = time.time()
            DASH_STATE["connected"] = (now - DASH_STATE["last_ts"]) < 1.5
            if not DASH_STATE["connected"]:
                DASH_STATE["hz"] = 0.0
            for w in ("fl", "fr", "rl", "rr"):
                t_val = DASH_STATE.get(f"tyre_{w}", 0)
                imo_val = DASH_STATE.get(f"tyre_{w}_imo")
                if not imo_val or len(imo_val) != 3 or (t_val > 0 and all(x == 0 for x in imo_val)):
                    DASH_STATE[f"tyre_{w}_imo"] = [t_val, t_val, t_val]
            payload = json.dumps(DASH_STATE).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
        elif self.path in ("/timing", "/timing.html"):
            try:
                p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timing.html")
                with open(p, "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(f.read())
            except Exception:
                self.send_error(404)
        else:
            try:
                p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "livedash.html")
                with open(p, "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(f.read())
            except Exception:
                self.send_error(404)


def avvia_server_livedash(ip_nic, porta_web=8080):
    try:
        server = ThreadingHTTPServer(("0.0.0.0", porta_web), LiveDashHandler)
        logger.info(f"Web Live Dash attiva su http://{ip_nic}:{porta_web}")
        threading.Thread(target=server.serve_forever, daemon=True).start()
    except Exception as e:
        logger.warning(f"Impossibile avviare Web Live Dash sulla porta {porta_web}: {e}")

LINGUA_DEFAULT = "it"
PORTA_GIOCO_DEFAULT = 7576
PORTA_DISPLAY_DEFAULT = 20777

DIZIONARIO = {
    "it": {
        "titolo": "OpenSimWheel Linux Bridge",
        "text": "Verifica o modifica i parametri di rete:",
        "label_nic": "IP Locale PC (NIC)",
        "label_ip": "IP Display / Volante",
        "label_vport": "Porta UDP Display",
        "label_gport": "Porta UDP Gioco (o 'auto')",
        "label_lang": "Lingua",
        "info_ok": "Arresta Bridge",
        "corpo_avvio": "Inizializzazione del Bridge telemetrico in corso...",
        "corpo_pista": "Telemetria agganciata con successo!\n\nI dati stanno fluendo verso il display.\nPremi il pulsante qui sotto per arrestare il bridge in modo pulito.",
        "errore_nic": "Errore critico: Impossibile vincolare il socket UDP all'IP selezionato o porta già in uso.",
        "titolo_err": "Errore di Rete"
    },
    "en": {
        "titolo": "OpenSimWheel Linux Bridge",
        "text": "Verify or edit network parameters:",
        "label_nic": "PC Local IP",
        "label_ip": "Display / Wheel IP",
        "label_vport": "Display UDP Port",
        "label_gport": "Game UDP Port (or 'auto')",
        "label_lang": "Language",
        "info_ok": "Stop Bridge",
        "corpo_avvio": "Initializing telemetry Bridge...",
        "corpo_pista": "Telemetry hooked successfully!\n\nData is flowing to your display.\nPress the button below to safely stop the bridge.",
        "errore_nic": "Critical Error: Cannot bind UDP socket to the selected IP or port already in use.",
        "titolo_err": "Network Error"
    },
    "fr": {
        "titolo": "OpenSimWheel Linux Bridge",
        "text": "Vérifiez ou modifiez les paramètres réseau :",
        "label_nic": "IP Locale PC",
        "label_ip": "IP Écran / Volant",
        "label_vport": "Port UDP Écran",
        "label_gport": "Port UDP Jeu (ou 'auto')",
        "label_lang": "Langue",
        "info_ok": "Arrêter le Bridge",
        "corpo_avvio": "Initialisation du Bridge télémétrique...",
        "corpo_pista": "Télémétrie connectée avec succès !\n\nLes données sont transmises à votre écran.\nAppuyez sur le bouton ci-dessous pour arrêter proprement.",
        "errore_nic": "Erreur Critique : Impossible de lier le socket UDP à l'IP sélectionnée.",
        "titolo_err": "Erreur Réseau"
    },
    "es": {
        "titolo": "OpenSimWheel Linux Bridge",
        "text": "Verifica o edita los parámetros de red:",
        "label_nic": "IP Local PC",
        "label_ip": "IP Pantalla / Volante",
        "label_vport": "Puerto UDP Pantalla",
        "label_gport": "Puerto UDP Juego (o 'auto')",
        "label_lang": "Idioma",
        "info_ok": "Detener Bridge",
        "corpo_avvio": "Inicializando el puente de telemetría...",
        "corpo_pista": "¡Telemetría conectada con éxito!\n\nLos datos fluyen hacia tu pantalla.\nPresiona el botón de abajo para detener el puente.",
        "errore_nic": "Error Crítico: No se puede vincular el socket UDP a la IP seleccionada.",
        "titolo_err": "Error de Red"
    },
    "de": {
        "titolo": "OpenSimWheel Linux Bridge",
        "text": "Netzwerkparameter prüfen oder bearbeiten:",
        "label_nic": "Lokale PC-IP",
        "label_ip": "Display / Lenkrad IP",
        "label_vport": "Display UDP-Port",
        "label_gport": "Spiel UDP-Port (oder 'auto')",
        "label_lang": "Sprache",
        "info_ok": "Bridge stoppen",
        "corpo_avvio": "Telemetrie-Bridge wird initialisiert...",
        "corpo_pista": "Telemetrie erfolgreich verbunden!\n\nDaten werden an das Display gesendet.\nUnten klicken, um die Bridge sauber zu beenden.",
        "errore_nic": "Kritischer Fehler: UDP-Socket konnte nicht an die gewählte IP gebunden werden.",
        "titolo_err": "Netzwerkfehler"
    }
}

# --- DA INCOLLARE DOPO carica_configurazione() (PARTE 3/3) ---


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

def rileva_porta_udp_attiva(ip_nic, porta_richiesta):
    porte_note = (7576, 20777, 5606, 9996, 4444)
    if porta_richiesta != 0:
        return porta_richiesta
    logger.info(f"Avvio Auto-Sniffer UDP su {ip_nic}...")
    sockets = {}
    for p in porte_note:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setblocking(False)
            s.bind((ip_nic, p))
            sockets[s] = p
        except Exception:
            pass
    if not sockets:
        return 7576
    import select
    inizio = time.time()
    trovata = None
    while time.time() - inizio < 4.0:
        leggibili, _, _ = select.select(list(sockets.keys()), [], [], 0.2)
        if leggibili:
            primo_sock = next(iter(leggibili))
            trovata = sockets[primo_sock]
            logger.info(f"Auto-Sniffer: Rilevato traffico su porta UDP {trovata}!")
            break
    for s in sockets:
        try:
            s.close()
        except Exception:
            pass
    return trovata if trovata else 7576

def lancia_finestra_zenity(opzioni, lingua="it"):
    mappa_locale = {
        "it": "it_IT.UTF-8",
        "en": "en_US.UTF-8",
        "fr": "fr_FR.UTF-8",
        "es": "es_ES.UTF-8",
        "de": "de_DE.UTF-8"
    }
    env = os.environ.copy()
    loc = mappa_locale.get(lingua.strip().lower(), "it_IT.UTF-8")
    env["LANG"] = loc
    env["LC_ALL"] = loc
    try:
        risultato = subprocess.run(["zenity"] + list(opzioni), env=env, capture_output=True, text=True)
        return risultato.returncode, risultato.stdout.strip()
    except FileNotFoundError:
        return 1, ""

def ottieni_testi_lingua(config, lingua):
    lingua_pulita = lingua.strip().lower()
    base = DIZIONARIO.get(lingua_pulita, DIZIONARIO["en"]).copy()
    testi = {
        "title": base.get("titolo", "OpenSimWheel Linux Bridge"),
        "text": base.get("text", "Verify or edit network parameters:"),
        "label_nic": base.get("label_nic", "PC Local IP"),
        "label_ip": base.get("label_ip", "Display / Wheel IP"),
        "label_vport": base.get("label_vport", "Display UDP Port"),
        "label_gport": base.get("label_gport", "Game UDP Port"),
        "label_lang": base.get("label_lang", "Language"),
        "info_title": base.get("titolo", "OSW Linux Hub Active"),
        "info_text": base.get("corpo_pista", "Telemetry active!"),
        "info_ok": base.get("info_ok", "OK"),
        "err_title": base.get("titolo_err", "Network Error"),
        "err_bind": base.get("errore_nic", "Socket bind error!")
    }
    if config.has_section(lingua_pulita):
        for k in testi:
            if config.has_option(lingua_pulita, k):
                testi[k] = config.get(lingua_pulita, k).replace("\\n", "\n")
    elif config.has_section("en"):
        for k in testi:
            if config.has_option("en", k):
                testi[k] = config.get("en", k).replace("\\n", "\n")
    return testi

def mostra_gui_stato(testi, ip_nic, ip_disp, porta_gioco, sock_in, sock_out, icon_path, lingua="it"):
    _sm = os.environ.get("OSW_SIM_MODE", "PMR")
    _nomi_sim = {
        "PMR": "PMR (Project Motor Racing)",
        "LMU": "LMU (Le Mans Ultimate)",
        "ACC": "ACC (Assetto Corsa Competizione)",
        "AC": "AC (Assetto Corsa)",
        "ACE": "ACE (Assetto Corsa EVO)",
        "RRRE": "RRRE (RaceRoom)",
        "RF2": "rF2 (rFactor 2)"
    }
    _porte_sim = {"LMU": 9002, "ACC": 9000, "AC": 9003, "ACE": 9005, "RRRE": 9007, "RF2": 9001}
    sim_attivo = _nomi_sim.get(_sm, "PMR (Project Motor Racing)")
    porta_effettiva = _porte_sim.get(_sm, porta_gioco)
    corpo = testi["info_text"]
    if "{}" in corpo:
        try:
            corpo = corpo.format(ip_nic, ip_disp, porta_effettiva)
        except Exception:
            corpo = f"PC NIC: {ip_nic}\nDisplay IP: {ip_disp}\nUDP Port: {porta_effettiva}\n\n{corpo}"
    else:
        corpo = f"PC NIC: {ip_nic}\nDisplay IP: {ip_disp}\nUDP Port: {porta_effettiva}\n\n{corpo}"

    corpo = f"Simulatore: {sim_attivo}\n" + corpo

    opts = ["--info", "--title", testi["info_title"], "--text", corpo, "--ok-label", testi["info_ok"], "--width=440"]
    lancia_finestra_zenity(opts, lingua)
    try:
        sock_in.close()
        sock_out.close()
    except Exception:
        pass
    subprocess.run(["pkill", "-f", "acc_shm_sender.py"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "lmu_shm_sender.py"], stderr=subprocess.DEVNULL)
    os._exit(0)

def rileva_gioco_attivo():
    try:
        out = subprocess.check_output(["ps", "-eo", "args"], text=True, stderr=subprocess.DEVNULL).lower()
        if "3058630" in out or "assettocorsaevo" in out or "assetto corsa evo" in out:
            return "ACE (Assetto Corsa EVO)"
        if "244210" in out or "acs.exe" in out or "assettocorsa.exe" in out:
            return "AC (Assetto Corsa)"
        if "211500" in out or "rrre64.exe" in out or "raceroom" in out:
            return "RRRE (RaceRoom)"
        if "2399420" in out or "le mans ultimate" in out:
            return "LMU (Le Mans Ultimate)"
        if "805550" in out or "ac2-win64" in out or "acc.exe" in out or "assetto corsa competizione" in out:
            return "ACC (Assetto Corsa Competizione)"
        if "projectmotorracing" in out or "project motor racing" in out or "pmr.exe" in out:
            return "PMR (Project Motor Racing)"
    except Exception:
        pass
    return "Nessuno (seleziona sotto)"

def carica_configurazione():
    config = configparser.ConfigParser()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_ini = os.path.join(base_dir, "config.ini")
    icon_path = os.path.join(base_dir, "zenity_simracing.png")
    if os.path.exists(file_ini):
        config.read(file_ini, encoding="utf-8")

    lingua = config.get("SETTINGS", "language", fallback=LINGUA_DEFAULT)
    ip_nic = config.get("HARDWARE", "nic_ip", fallback=config.get("SETTINGS", "game_interface_ip", fallback="127.0.0.1"))
    ip_display = config.get("HARDWARE", "volante_ip", fallback=config.get("SETTINGS", "display_ip", fallback="127.0.0.1"))
    porta_gioco = config.getint("SIMULATORE", "ascolto_porta_udp", fallback=config.getint("SETTINGS", "game_port", fallback=PORTA_GIOCO_DEFAULT))
    porta_disp = config.getint("HARDWARE", "volante_porta_udp", fallback=config.getint("SETTINGS", "display_port", fallback=PORTA_DISPLAY_DEFAULT))

    while True:
        testi = ottieni_testi_lingua(config, lingua)

        sezioni_ignora = {"HARDWARE", "SIMULATORE", "SETTINGS"}
        lingue_disp = [s.lower() for s in config.sections() if s.upper() not in sezioni_ignora]
        if not lingue_disp:
            lingue_disp = ["it", "en", "fr", "es", "de"]
        if lingua in lingue_disp:
            lingue_disp.remove(lingua)
            lingue_disp.insert(0, lingua)
        combo_values = "|".join(lingue_disp)

        gioco_rilevato = rileva_gioco_attivo()
        lista_sim = ([gioco_rilevato] if gioco_rilevato != "Nessuno (seleziona sotto)" else []) + [
            "PMR (Project Motor Racing)",
            "LMU (Le Mans Ultimate)",
            "ACC (Assetto Corsa Competizione)",
            "AC (Assetto Corsa)",
            "ACE (Assetto Corsa EVO)",
            "RRRE (RaceRoom)"
        ]

        form_opts = [
            "--forms",
            "--title", testi["title"],
            "--text", f"{testi['text']}  [Gioco rilevato: {gioco_rilevato}]",
            "--separator=|",
            f"--add-entry={testi['label_nic']}",
            f"--add-entry={testi['label_ip']}",
            f"--add-entry={testi['label_vport']}",
            f"--add-entry={testi['label_gport']}",
            f"--add-combo={testi['label_lang']}",
            f"--combo-values={combo_values}",
            "--add-combo=Simulatore / Game",
            f"--combo-values={'|'.join(dict.fromkeys(lista_sim))}",
            "--width=460"
        ]

        rc, out = lancia_finestra_zenity(form_opts, lingua)
        if rc != 0:
            sys.exit(0)

        lingua_precedente = lingua
        if out:
            parti = out.split("|")
            if len(parti) >= 5:
                p0, p1, p2, p3, p4 = parti[:5]
                _scelta_sim = list(parti).pop(5).upper() if len(parti) >= 6 else ""
                if "RF2" in _scelta_sim or "RFACTOR" in _scelta_sim:
                    os.environ["OSW_SIM_MODE"] = "RF2"
                elif "RRRE" in _scelta_sim:
                    os.environ["OSW_SIM_MODE"] = "RRRE"
                elif "ACE" in _scelta_sim:
                    os.environ["OSW_SIM_MODE"] = "ACE"
                elif "ACC" in _scelta_sim:
                    os.environ["OSW_SIM_MODE"] = "ACC"
                elif "AC (" in _scelta_sim or _scelta_sim.strip() == "AC":
                    os.environ["OSW_SIM_MODE"] = "AC"
                elif "LMU" in _scelta_sim:
                    os.environ["OSW_SIM_MODE"] = "LMU"
                else:
                    os.environ["OSW_SIM_MODE"] = "PMR"

                if p0.strip():
                    ip_nic = p0.strip()
                if p1.strip():
                    ip_display = p1.strip()
                if p2.strip().isdigit():
                    porta_disp = int(p2.strip())
                if p3.strip().lower() == "auto":
                    porta_gioco = 0
                elif p3.strip().isdigit():
                    porta_gioco = int(p3.strip())
                if p4.strip():
                    lingua = p4.strip().lower()

                if not config.has_section("HARDWARE"):
                    config.add_section("HARDWARE")
                if not config.has_section("SIMULATORE"):
                    config.add_section("SIMULATORE")
                if not config.has_section("SETTINGS"):
                    config.add_section("SETTINGS")

                config.set("HARDWARE", "nic_ip", ip_nic)
                config.set("HARDWARE", "volante_ip", ip_display)
                config.set("HARDWARE", "volante_porta_udp", str(porta_disp))
                config.set("SIMULATORE", "ascolto_porta_udp", str(porta_gioco))
                config.set("SETTINGS", "language", lingua)
                with open(file_ini, "w", encoding="utf-8") as f_ini:
                    config.write(f_ini)

        if lingua != lingua_precedente:
            continue

        testi = ottieni_testi_lingua(config, lingua)
        break

    return lingua, testi, icon_path, ip_nic, ip_display, porta_gioco, porta_disp


def elabora_e_inietta_pacchetto(data, out_sock, ip_display, porta_display):
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
        DASH_STATE["tyre_fl"] = temp_fl
        DASH_STATE["tyre_fr"] = temp_fr
        DASH_STATE["tyre_rl"] = temp_rl
        DASH_STATE["tyre_rr"] = temp_rr
        DASH_STATE["tyre_fl_imo"] = [temp_fl, temp_fl, temp_fl]
        DASH_STATE["tyre_fr_imo"] = [temp_fr, temp_fr, temp_fr]
        DASH_STATE["tyre_rl_imo"] = [temp_rl, temp_rl, temp_rl]
        DASH_STATE["tyre_rr_imo"] = [temp_rr, temp_rr, temp_rr]
        DASH_STATE["tyre_wear"] = list((max(0, 100 - wear_fl), max(0, 100 - wear_fr), max(0, 100 - wear_rl), max(0, 100 - wear_rr)))
        DASH_STATE["air_temp"] = air_temp_c
        DASH_STATE["track_temp"] = track_temp_c
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
        h1 = struct.pack(hdr, 2020, 1, 0, 1, 1, 123456789, float(tempo), 0, 0, 0)
        p1 = bytearray(227)
        struct.pack_into("<BbbBH", p1, 0, 1, track_temp_c, air_temp_c, 60, track_len_m)
        struct.pack_into("<B", p1, 6, 10)
        struct.pack_into("<B", p1, 19, 1)

        h2 = struct.pack(hdr, 2020, 1, 0, 1, 2, 123456789, float(tempo), 0, 0, 0)
        p2 = bytearray(1168)
        struct.pack_into("<ffHHf", p2, 0, last_lap_time, curr_lap_time, s1_safe, s2_safe, best_lap_time)
        struct.pack_into("<ff", p2, 24, distanza_giro, distanza_tot)
        struct.pack_into("<BBBB", p2, 34, 1, current_lap, 0, settore)
        struct.pack_into("<BBB", p2, 41, 0, 0, 2)

        # Pacchetto 6: Car Telemetry (1347 - 24 = 1323 byte totali)
        h6 = struct.pack(hdr, 2020, 1, 0, 1, 6, 123456789, float(tempo), 0, 0, 0)
        p6 = bytearray(1323)
        struct.pack_into("<HfffB", p6, 0, speed_kmh, 1.0, 0.0, 0.0, 0)
        struct.pack_into("<bHBBH", p6, 15, int(gear_display), rpm, 0, led_pct, led_bits)
        struct.pack_into("<BBBB", p6, 44, temp_rl, temp_rr, temp_fl, temp_fr)
        struct.pack_into("<BBBB", p6, 48, temp_rl, temp_rr, temp_fl, temp_fr)

        # Pacchetto 7: Car Status (1344 - 24 = 1320 byte totali)
        h7 = struct.pack(hdr, 2020, 1, 0, 1, 7, 123456789, float(tempo), 0, 0, 0)
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
        struct.pack_into("<b", p7, 42, fia_flag)

        out_sock.sendto(h1 + p1, (ip_display, porta_display))
        out_sock.sendto(h2 + p2, (ip_display, porta_display))
        out_sock.sendto(h6 + p6, (ip_display, porta_display))
        out_sock.sendto(h7 + p7, (ip_display, porta_display))
    except Exception as e:
        logger.warning(f"Errore elaborazione pacchetto: {e}")


def set_proton_stop_flag(stop=True):
    import glob, os
    for d in (
        glob.glob("/run/media/*/*/SteamLibrary/steamapps/compatdata/*/pfx/drive_c/osw_shm")
        + glob.glob(os.path.expanduser("~/.local/share/Steam/steamapps/compatdata/*/pfx/drive_c/osw_shm"))
        + glob.glob(os.path.expanduser("~/.steam/root/steamapps/compatdata/*/pfx/drive_c/osw_shm"))
    ):
        flag = os.path.join(d, "stop.flag")
        try:
            if stop:
                with open(flag, "w") as f:
                    f.write("1")
            elif os.path.exists(flag):
                os.remove(flag)
        except Exception:
            pass


def cleanup_all_instances():
    import subprocess
    set_proton_stop_flag(True)
    linux_patterns = [
        "ac_ace_bridge.py",
        "acc_bridge.py",
        "lmu_bridge.py",
        "rrre_bridge.py",
    ]
    for pat in linux_patterns:
        subprocess.run(["pkill", "-f", pat], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


atexit.register(cleanup_all_instances)


def load_and_verify_sim_ini(sim_code):
    import configparser, subprocess, os
    ini_paths = [
        os.path.expanduser("~/.config/OpenSimWheel/osw_bridge.ini"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "osw_bridge.ini"),
    ]
    cfg = configparser.ConfigParser()
    for p in ini_paths:
        if os.path.exists(p):
            cfg.read(p, encoding="utf-8")
            break
    section = f"SIM_{sim_code.upper()}"
    if section not in cfg:
        return
    sec = cfg[section]
    auto_repair = cfg.getboolean("HUB_SETTINGS", "auto_ripara_script_proton", fallback=True)
    start_sh = sec.get("script_avvio_shm", "")
    setup_sh = sec.get("script_setup", "")
    stop_flag = sec.get("file_stop", "")
    pfx = sec.get("percorso_prefisso", "")
    if pfx and stop_flag:
        flag_path = os.path.join(pfx, "drive_c", "osw_shm", stop_flag)
        if os.path.exists(flag_path):
            try:
                os.remove(flag_path)
            except Exception:
                pass
    if auto_repair and start_sh and not os.path.exists(start_sh) and os.path.exists(setup_sh):
        subprocess.run(["bash", setup_sh], check=False)


def main():
    set_proton_stop_flag(False)
    lingua, testi, icon_path, ip_nic, ip_display, porta_gioco, porta_disp = carica_configurazione()
    _cfg_tmp = configparser.ConfigParser()
    _cfg_tmp.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini"), encoding="utf-8")
    dispositivo = _cfg_tmp.get("HARDWARE", "periferica", fallback="Thrustmaster SF1000 / UDP")
    print(f"=== {testi['title']} ({lingua.upper()}) - {dispositivo} ===")

    porta_gioco = rileva_porta_udp_attiva(ip_nic, porta_gioco)

    out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    out_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_sock_game = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock_game.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def _avvia_sender_proton(appid, script_name):
        patterns = (
            os.path.expanduser(f"~/.local/share/Steam/steamapps/compatdata/{appid}/pfx/drive_c/osw_shm/{script_name}"),
            f"/run/media/*/*/steamapps/compatdata/{appid}/pfx/drive_c/osw_shm/{script_name}",
            f"/run/media/*/*/SteamLibrary/steamapps/compatdata/{appid}/pfx/drive_c/osw_shm/{script_name}",
            f"/mnt/*/steamapps/compatdata/{appid}/pfx/drive_c/osw_shm/{script_name}",
            f"/mnt/*/SteamLibrary/steamapps/compatdata/{appid}/pfx/drive_c/osw_shm/{script_name}",
        )
        for pat in patterns:
            for m in _glob.glob(pat):
                if os.path.exists(m):
                    subprocess.Popen(("bash", m), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                    logger.info(f"Sender Proton avviato: {m}")
                    return True
        return False

    try:
        udp_sock_game.bind(("0.0.0.0", porta_gioco))
        try:
            out_sock.bind((ip_nic, 0))
        except Exception:
            out_sock.bind(("0.0.0.0", 0))
        avvia_server_livedash(ip_nic, 8080)
        threading.Thread(
            target=mostra_gui_stato,
            args=(testi, ip_nic, ip_display, porta_gioco, udp_sock_game, out_sock, icon_path, lingua),
            daemon=True
        ).start()
    except Exception as e:
        logger.error(f"Errore bind socket: {e}")
        lancia_finestra_zenity(("--error", "--title", testi["err_title"], "--text", testi["err_bind"], "--width=400"), lingua)
        sys.exit(1)

    sim_mode = os.environ.get("OSW_SIM_MODE", "PMR")
    if sim_mode in ("ACC", "AC", "ACE", "RRRE"):
        try:
            udp_sock_game.close()
        except Exception:
            pass
        udp_sock_game = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if sim_mode == "ACC":
            udp_sock_game.bind((ip_nic, 0))
            udp_sock_game.settimeout(0.5)
            acc_port = 9000
            logger.info(f"Modalita ACC attiva -> Handshake verso {ip_nic}:{acc_port}")
            _avvia_sender_proton("805550", "start_acc_shm.sh")
        elif sim_mode == "AC":
            udp_sock_game.bind(("127.0.0.1", 9003))
            udp_sock_game.settimeout(0.5)
            logger.info("Modalita AC (Assetto Corsa) attiva su 127.0.0.1:9003")
            _avvia_sender_proton("244210", "start_ac_shm.sh")
        elif sim_mode == "ACE":
            udp_sock_game.bind(("127.0.0.1", 9005))
            udp_sock_game.settimeout(0.5)
            logger.info("Modalita ACE (Assetto Corsa EVO) attiva su 127.0.0.1:9005")
            _avvia_sender_proton("3058630", "start_ace_shm.sh")
        elif sim_mode == "RRRE":
            udp_sock_game.bind(("127.0.0.1", 9007))
            udp_sock_game.settimeout(0.5)
            logger.info("Modalita RRRE (RaceRoom) attiva su 127.0.0.1:9007")
            _avvia_sender_proton("211500", "start_rrre_shm.sh")

    try:
        while True:
            if os.environ.get("OSW_SIM_MODE") == "LMU" or sim_mode == "LMU":
                elabora_pacchetto_lmu(None, out_sock, ip_display, porta_disp, DASH_STATE, logger)
                time.sleep(0.01)
                continue
            if sim_mode in ("AC", "ACE"):
                try:
                    data, _ = udp_sock_game.recvfrom(4096)
                    elabora_pacchetto_ac_ace(data, out_sock, ip_display, porta_disp, DASH_STATE, logger, sim_name=sim_mode)
                except socket.timeout:
                    pass
                continue
            if sim_mode == "RRRE":
                try:
                    data, _ = udp_sock_game.recvfrom(4096)
                    elabora_pacchetto_rrre(data, out_sock, ip_display, porta_disp, DASH_STATE, logger)
                except socket.timeout:
                    pass
                continue
            if sim_mode == "ACC":
                now_hs = time.time()
                if (ACC_STATE["conn_id"] < 0 or (now_hs - ACC_STATE["last_rx_ts"]) > 3.0) and (now_hs - ACC_STATE["last_hs_ts"]) > 2.0:
                    acc_send_handshake(udp_sock_game, acc_port, ip_nic)
                    ACC_STATE["last_hs_ts"] = now_hs
                try:
                    data, _ = udp_sock_game.recvfrom(4096)
                    elabora_pacchetto_acc(data, out_sock, ip_display, porta_disp, DASH_STATE, logger)
                except socket.timeout:
                    continue
            else:
                data, _ = udp_sock_game.recvfrom(2048)
                elabora_e_inietta_pacchetto(data, out_sock, ip_display, porta_disp)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Errore loop UDP: {e}")
    finally:
        try:
            _t_end = time.time()
            _h6_end = struct.pack("<HBBBBQfIBB", 2020, 1, 0, 1, 6, 123456789, float(_t_end), 0, 0, 0)
            _p6_end = bytearray(1323)
            _h7_end = struct.pack("<HBBBBQfIBB", 2020, 1, 0, 1, 7, 123456789, float(_t_end), 0, 0, 0)
            _p7_end = bytearray(1320)
            out_sock.sendto(_h6_end + _p6_end, (ip_display, porta_disp))
            out_sock.sendto(_h7_end + _p7_end, (ip_display, porta_disp))
        except Exception:
            pass
        udp_sock_game.close()
        out_sock.close()


if __name__ == "__main__":
    main()
