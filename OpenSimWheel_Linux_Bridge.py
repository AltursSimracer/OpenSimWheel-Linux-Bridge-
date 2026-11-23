#!/usr/bin/env python3
import atexit
import glob as _glob
import select
import shutil
import math

def smooth_temp(prev_val, new_val, alpha=0.25):
    if new_val is None or math.isnan(new_val) or new_val <= 0.0 or new_val > 300.0:
        return prev_val if (prev_val and prev_val > 0.0) else 0.0
    if not prev_val or prev_val <= 0.0:
        return round(float(new_val), 1)
    return round(prev_val * (1.0 - alpha) + float(new_val) * alpha, 1)

def build_imo(prev_imo, imo_tuple_or_single, fallback_temp, alpha=0.25):
    if isinstance(imo_tuple_or_single, (list, tuple)) and len(imo_tuple_or_single) == 3:
        prev = prev_imo if (isinstance(prev_imo, list) and len(prev_imo) == 3) else [0.0, 0.0, 0.0]
        return [
            smooth_temp(prev[0], imo_tuple_or_single[0], alpha),
            smooth_temp(prev[1], imo_tuple_or_single[1], alpha),
            smooth_temp(prev[2], imo_tuple_or_single[2], alpha),
        ]
    t = round(fallback_temp, 1)
    return [t, t, t]
try:
    from bridges.rf2_bridge import elabora_pacchetto_rf2
except ImportError:
    elabora_pacchetto_rf2 = None
from concurrent.futures import ThreadPoolExecutor
from bridges.lmu_bridge import elabora_pacchetto_lmu
from bridges.pmr_bridge import elabora_pacchetto_pmr
from bridges.ac_ace_bridge import elabora_pacchetto_ac_ace
from bridges.rrre_bridge import elabora_pacchetto_rrre
from bridges.acc_bridge import ACC_STATE, acc_send_handshake, elabora_pacchetto_acc
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
_log_file = os.path.join(_base_dir, "logs", "bridge.log")
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
    "engine_temp": 0,
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
            # Storico giri personale automatico (funziona su tutti i simulatori)
            hist = DASH_STATE.setdefault("lap_history", [])
            ll = float(DASH_STATE.get("last_lap") or 0.0)
            lp = int(DASH_STATE.get("lap") or 1)
            if ll > 1.0 and (not hist or abs(hist[0]["time"] - ll) > 0.002 or hist[0]["lap"] != lp - 1):
                s1v = float(DASH_STATE.get("s1") or 0.0)
                s2v = float(DASH_STATE.get("s2") or 0.0)
                s3v = float(DASH_STATE.get("s3") or 0.0)
                if s3v <= 0.01 and s1v > 0.01 and s2v > 0.01 and ll > (s1v + s2v):
                    s3v = round(ll - s1v - s2v, 3)
                hist.insert(0, {"lap": max(1, lp - 1), "time": round(ll, 3), "s1": round(s1v, 3), "s2": round(s2v, 3), "s3": round(s3v, 3)})
                if len(hist) > 25:
                    del hist[25:]
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
                p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "timing.html")
                with open(p, "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(f.read())
            except Exception:
                self.send_error(404)
        else:
            try:
                p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "livedash.html")
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
        _lan_ip = _osw_rileva_ip_pc() if ip_nic in ("0.0.0.0", "127.0.0.1") else ip_nic
        logger.info(f"Web Live Dash attiva -> PC: http://127.0.0.1:{porta_web} | Smartphone/Tablet: http://{_lan_ip}:{porta_web}")
        threading.Thread(target=server.serve_forever, daemon=True).start()
    except Exception as e:
        logger.warning(f"Impossibile avviare Web Live Dash sulla porta {porta_web}: {e}")

LINGUA_DEFAULT = "it"
PORTA_GIOCO_DEFAULT = 7576
PORTA_DISPLAY_DEFAULT = 20777

DIZIONARIO = {
    "it": {
        "title": "OpenSimWheel Linux Bridge",
        "text": "Verifica o modifica i parametri di rete:",
        "label_nic": "IP Locale PC (NIC)",
        "label_ip": "IP Display / Volante",
        "label_vport": "Porta UDP Display",
        "label_gport": "Porta UDP Gioco (o 'auto')",
        "label_lang": "Lingua",
        "info_ok": "Arresta Bridge",
        "corpo_avvio": "Inizializzazione del Bridge telemetrico in corso...",
        "corpo_pista": "Telemetria agganciata con successo!\n\nI dati stanno fluendo verso il display.\nPremi il pulsante qui sotto per arrestare il bridge in modo pulito.",
        "err_bind": "Errore critico: Impossibile vincolare il socket UDP all'IP selezionato o porta già in uso.",
        "err_title": "Errore di Rete"
    },
    "en": {
        "title": "OpenSimWheel Linux Bridge",
        "text": "Verify or edit network parameters:",
        "label_nic": "PC Local IP",
        "label_ip": "Display / Wheel IP",
        "label_vport": "Display UDP Port",
        "label_gport": "Game UDP Port (or 'auto')",
        "label_lang": "Language",
        "info_ok": "Stop Bridge",
        "corpo_avvio": "Initializing telemetry Bridge...",
        "corpo_pista": "Telemetry hooked successfully!\n\nData is flowing to your display.\nPress the button below to safely stop the bridge.",
        "err_bind": "Critical Error: Cannot bind UDP socket to the selected IP or port already in use.",
        "err_title": "Network Error"
    },
    "fr": {
        "title": "OpenSimWheel Linux Bridge",
        "text": "Vérifiez ou modifiez les paramètres réseau :",
        "label_nic": "IP Locale PC",
        "label_ip": "IP Écran / Volant",
        "label_vport": "Port UDP Écran",
        "label_gport": "Port UDP Jeu (ou 'auto')",
        "label_lang": "Langue",
        "info_ok": "Arrêter le Bridge",
        "corpo_avvio": "Initialisation du Bridge télémétrique...",
        "corpo_pista": "Télémétrie connectée avec succès !\n\nLes données sont transmises à votre écran.\nAppuyez sur le bouton ci-dessous pour arrêter proprement.",
        "err_bind": "Erreur Critique : Impossible de lier le socket UDP à l'IP sélectionnée.",
        "err_title": "Erreur Réseau"
    },
    "es": {
        "title": "OpenSimWheel Linux Bridge",
        "text": "Verifica o edita los parámetros de red:",
        "label_nic": "IP Local PC",
        "label_ip": "IP Pantalla / Volante",
        "label_vport": "Puerto UDP Pantalla",
        "label_gport": "Puerto UDP Juego (o 'auto')",
        "label_lang": "Idioma",
        "info_ok": "Detener Bridge",
        "corpo_avvio": "Inicializando el puente de telemetría...",
        "corpo_pista": "¡Telemetría conectada con éxito!\n\nLos datos fluyen hacia tu pantalla.\nPresiona el botón de abajo para detener el puente.",
        "err_bind": "Error Crítico: No se puede vincular el socket UDP a la IP seleccionada.",
        "err_title": "Error de Red"
    },
    "de": {
        "title": "OpenSimWheel Linux Bridge",
        "text": "Netzwerkparameter prüfen oder bearbeiten:",
        "label_nic": "Lokale PC-IP",
        "label_ip": "Display / Lenkrad IP",
        "label_vport": "Display UDP-Port",
        "label_gport": "Spiel UDP-Port (oder 'auto')",
        "label_lang": "Sprache",
        "info_ok": "Bridge stoppen",
        "corpo_avvio": "Telemetrie-Bridge wird initialisiert...",
        "corpo_pista": "Telemetrie erfolgreich verbunden!\n\nDaten werden an das Display gesendet.\nUnten klicken, um die Bridge sauber zu beenden.",
        "err_bind": "Kritischer Fehler: UDP-Socket konnte nicht an die gewählte IP gebunden werden.",
        "err_title": "Netzwerkfehler"
    }
}

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
    loc = mappa_locale.get(lingua.strip().lower(), "C.UTF-8")
    env["LANG"] = loc
    env["LC_ALL"] = loc
    try:
        risultato = subprocess.run(["zenity"] + list(opzioni), env=env, capture_output=True, text=True)
        if risultato.returncode != 0 and not risultato.stdout.strip():
            env["LANG"] = "C.UTF-8"
            env["LC_ALL"] = "C.UTF-8"
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
        if "365960" in out or "rfactor2.exe" in out or "rfactor 2" in out:
            return "rF2 (rFactor 2)"
        if "2399420" in out or "le mans ultimate" in out:
            return "LMU (Le Mans Ultimate)"
        if "805550" in out or "ac2-win64" in out or "acc.exe" in out or "assetto corsa competizione" in out:
            return "ACC (Assetto Corsa Competizione)"
        if "projectmotorracing" in out or "project motor racing" in out or "pmr.exe" in out:
            return "PMR (Project Motor Racing)"
    except Exception:
        pass
    return "Nessuno (seleziona sotto)"


def _osw_ip_valido(ip_str):
    if not ip_str or not isinstance(ip_str, str):
        return False
    parts = ip_str.strip().split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False

def _osw_rileva_ip_pc():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if _osw_ip_valido(ip) and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    try:
        out = subprocess.check_output(["hostname", "-I"], text=True, stderr=subprocess.DEVNULL)
        for token in out.split():
            if _osw_ip_valido(token) and not token.startswith("127.") and not token.startswith("172.17."):
                return token
    except Exception:
        pass
    return "127.0.0.1"

def _osw_cerca_display_in_rete(ip_pc):
    if not _osw_ip_valido(ip_pc) or ip_pc.startswith("127."):
        return None
    prefisso = ".".join(ip_pc.split(".")[:3])
    logger.info(f"[Auto-Sniffer] Ricerca display/volante Wi-Fi su {prefisso}.0/24...")
    def _ping(i):
        target = f"{prefisso}.{i}"
        if target == ip_pc:
            return None
        r = subprocess.run(["ping", "-c", "1", "-W", "1", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return target if r.returncode == 0 else None
    attivi = []
    with ThreadPoolExecutor(max_workers=64) as ex:
        for ip_t in ex.map(_ping, range(1, 255)):
            if ip_t:
                attivi.append(ip_t)
    mac_wifi = ("24:0a:c4", "30:ae:a4", "3c:71:bf", "84:cc:a8", "94:b9:7e", "a4:cf:12", "ac:67:b2", "c4:4f:33", "cc:50:e3", "d8:a0:1d", "dc:4f:22", "ec:fa:bc", "f0:08:d1", "f4:cf:a2")
    try:
        with open("/proc/net/arp", "r", encoding="utf-8") as f:
            for line in f.readlines()[1:]:
                cols = line.split()
                if len(cols) >= 4 and cols[0] in attivi and any(cols[3].lower().startswith(m) for m in mac_wifi):
                    logger.info(f"[Auto-Sniffer] Rilevato display/volante Wi-Fi su IP: {cols[0]}")
                    return cols[0]
    except Exception:
        pass
    candidati = [h for h in attivi if not h.endswith(".1") and not h.endswith(".254")]
    return candidati[0] if len(candidati) == 1 else None

def carica_configurazione():
    config = configparser.ConfigParser()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_ini = os.path.join(base_dir, "config.ini")
    icon_path = os.path.join(base_dir, "web", "zenity_simracing.png")
    if os.path.exists(file_ini):
        config.read(file_ini, encoding="utf-8")

    lingua = config.get("SETTINGS", "language", fallback=LINGUA_DEFAULT)
    ip_nic = config.get("HARDWARE", "nic_ip", fallback=config.get("SETTINGS", "game_interface_ip", fallback="127.0.0.1"))
    ip_display = config.get("HARDWARE", "volante_ip", fallback=config.get("SETTINGS", "display_ip", fallback="127.0.0.1"))
    porta_gioco = config.getint("SIMULATORE", "ascolto_porta_udp", fallback=config.getint("SETTINGS", "game_port", fallback=PORTA_GIOCO_DEFAULT))
    porta_disp = config.getint("HARDWARE", "volante_porta_udp", fallback=config.getint("SETTINGS", "display_port", fallback=PORTA_DISPLAY_DEFAULT))

    if not _osw_ip_valido(ip_nic) or ip_nic in ("127.0.0.1", "0.0.0.0"):
        _auto_nic = _osw_rileva_ip_pc()
        if _auto_nic != "127.0.0.1":
            ip_nic = _auto_nic
    if not _osw_ip_valido(ip_display) or ip_display == "127.0.0.1":
        _auto_disp = _osw_cerca_display_in_rete(ip_nic)
        if _auto_disp:
            ip_display = _auto_disp

    mappa_lingue = {
        "it": "IT - Italiano",
        "en": "EN - English",
        "de": "DE - Deutsch",
        "fr": "FR - Français",
        "es": "ES - Español"
    }

    gioco_rilevato = rileva_gioco_attivo()
    sim_selezionato = gioco_rilevato if gioco_rilevato != "Nessuno (seleziona sotto)" else "PMR (Project Motor Racing)"

    while True:
        testi = ottieni_testi_lingua(config, lingua)

        lc = lingua.strip().lower() if lingua.strip().lower() in mappa_lingue else "it"
        lista_combo_lingue = [mappa_lingue[lc]] + [v for k, v in mappa_lingue.items() if k != lc]
        combo_lingue_str = "|".join(lista_combo_lingue)

        tutti_sim = [
            "PMR (Project Motor Racing)",
            "LMU (Le Mans Ultimate)",
            "ACC (Assetto Corsa Competizione)",
            "AC (Assetto Corsa)",
            "ACE (Assetto Corsa EVO)",
            "RRRE (RaceRoom)",
            "rF2 (rFactor 2)"
        ]
        lista_sim = list(dict.fromkeys([sim_selezionato] + tutti_sim))
        combo_sim_str = "|".join(lista_sim)

        form_opts = [
            "--forms",
            "--title", testi["title"],
            "--text", f"{testi['text']}  [Sim: {gioco_rilevato}]",
            "--separator=|",
            f"--add-entry={testi['label_nic']} [{ip_nic}]",
            f"--add-entry={testi['label_ip']} [{ip_display}]",
            f"--add-entry={testi['label_vport']} [{porta_disp}]",
            f"--add-entry={testi['label_gport']} [{porta_gioco}]",
            f"--add-combo={testi['label_lang']}",
            f"--combo-values={combo_lingue_str}",
            "--add-combo=Simulatore / Game",
            f"--combo-values={combo_sim_str}",
            "--width=460"
        ]

        codice, output = lancia_finestra_zenity(form_opts, lingua)

        if codice != 0:
            sys.exit(0)

        campi = output.split("|")
        if len(campi) >= 1 and campi[0].strip():
            ip_nic = campi[0].strip()
        if len(campi) >= 2 and campi[1].strip():
            ip_display = campi[1].strip()
        if len(campi) >= 3 and campi[2].strip().isdigit():
            porta_disp = int(campi[2].strip())
        if len(campi) >= 4 and campi[3].strip().isdigit():
            porta_gioco = int(campi[3].strip())

        scelta_lingua = campi[4].strip() if len(campi) >= 5 else ""
        nuova_lingua = lc
        if scelta_lingua:
            cod_estratto = scelta_lingua.split("-")[0].strip().lower()
            if cod_estratto in mappa_lingue:
                nuova_lingua = cod_estratto

        if len(campi) >= 6 and campi[5].strip():
            sim_selezionato = campi[5].strip()

        if not config.has_section("SETTINGS"):
            config.add_section("SETTINGS")
        if not config.has_section("HARDWARE"):
            config.add_section("HARDWARE")
        if not config.has_section("SIMULATORE"):
            config.add_section("SIMULATORE")

        config.set("SETTINGS", "language", nuova_lingua)
        config.set("HARDWARE", "nic_ip", ip_nic)
        config.set("HARDWARE", "volante_ip", ip_display)
        config.set("HARDWARE", "volante_porta_udp", str(porta_disp))
        config.set("SIMULATORE", "ascolto_porta_udp", str(porta_gioco))

        with open(file_ini, "w", encoding="utf-8") as f:
            config.write(f)

        if nuova_lingua != lc:
            lingua = nuova_lingua
            continue

        codice_sim = sim_selezionato.split("(")[0].strip().upper()
        if codice_sim in ("PMR", "LMU", "ACC", "AC", "ACE", "RRRE", "RF2"):
            os.environ["OSW_SIM_MODE"] = codice_sim

        break

    return lingua, testi, icon_path, ip_nic, ip_display, porta_gioco, porta_disp

def lancia_finestra_zenity(opzioni, lingua="it"):
    mappa_locale = {
        "it": "it_IT.UTF-8",
        "en": "en_US.UTF-8",
        "fr": "fr_FR.UTF-8",
        "es": "es_ES.UTF-8",
        "de": "de_DE.UTF-8"
    }
    env = os.environ.copy()
    loc = mappa_locale.get(lingua.strip().lower(), "C.UTF-8")
    env["LANG"] = loc
    env["LC_ALL"] = loc
    try:
        risultato = subprocess.run(["zenity"] + list(opzioni), env=env, capture_output=True, text=True)
        # Se Zenity fallisce (es. locale non generato su Linux), ritenta subito con C.UTF-8
        if risultato.returncode != 0 and not risultato.stdout.strip():
            env["LANG"] = "C.UTF-8"
            env["LC_ALL"] = "C.UTF-8"
            risultato = subprocess.run(["zenity"] + list(opzioni), env=env, capture_output=True, text=True)
        return risultato.returncode, risultato.stdout.strip()
    except FileNotFoundError:
        return 1, ""



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
        "bridges/ac_ace_bridge.py",
        "bridges/acc_bridge.py",
        "bridges/lmu_bridge.py",
        "bridges/rrre_bridge.py",
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
    load_and_verify_sim_ini(os.environ.get("OSW_SIM_MODE", "PMR"))
    lingua, testi, icon_path, ip_nic, ip_display, porta_gioco, porta_disp = carica_configurazione()
    _cfg_tmp = configparser.ConfigParser()
    _cfg_tmp.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini"), encoding="utf-8")
    dispositivo = _cfg_tmp.get("HARDWARE", "periferica", fallback="Universal F1-UDP Wheel / Wi-Fi Display / Web LiveDash")
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
    if sim_mode in ("ACC", "AC", "ACE", "RRRE", "LMU"):
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
        elif sim_mode == "LMU":
            udp_sock_game.bind(("127.0.0.1", 9009))
            udp_sock_game.settimeout(0.5)
            logger.info("Modalita LMU (Le Mans Ultimate) attiva su 127.0.0.1:9009")
            _avvia_sender_proton("2399420", "start_lmu_shm.sh")

    try:
        while True:
            if os.environ.get("OSW_SIM_MODE") == "LMU" or sim_mode == "LMU":
                try:
                    data, _ = udp_sock_game.recvfrom(4096)
                    elabora_pacchetto_lmu(data, out_sock, ip_display, porta_disp, DASH_STATE, logger)
                except socket.timeout:
                    elabora_pacchetto_lmu(None, out_sock, ip_display, porta_disp, DASH_STATE, logger)
                    time.sleep(0.03)
                continue
            if (os.environ.get("OSW_SIM_MODE") == "RF2" or sim_mode == "RF2") and elabora_pacchetto_rf2 is not None:
                elabora_pacchetto_rf2(None, out_sock, ip_display, porta_disp, DASH_STATE, logger)
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
                elabora_pacchetto_pmr(data, out_sock, ip_display, porta_disp, DASH_STATE, logger)
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
