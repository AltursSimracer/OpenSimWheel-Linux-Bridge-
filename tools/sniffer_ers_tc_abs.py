#!/usr/bin/env python3
"""
Sniffer Universale ERS / TC / ABS / Brake Bias per OpenSimWheel Linux Bridge
Supporta tutti i simulatori: AC, ACE, ACC, rF2, LMU, R3E, PMR.
- Modalità 1 (Bridge attivo): legge lo stream unificato dal Bridge (HTTP /api/telemetry)
  e mostra in tempo reale ERS %, stato erogazione/ricarica, TC, ABS e Brake Bias.
- Modalità 2 (Standalone / Raw UDP): se il Bridge è spento, ascolta direttamente le porte
  UDP dei simulatori (9003 AC/ACE/LMU/rF2/PMR, 9005 R3E) e decodifica header/lunghezza.
"""

import json
import socket
import struct
import sys
import time
import urllib.request

API_URL = "http://127.0.0"
UDP_PORTS = [9003, 9005]


def format_bar(pct, width=20):
    pct = max(0.0, min(100.0, float(pct)))
    filled = int(round((pct / 100.0) * width))
    return "[" + ("#" * filled) + ("-" * (width - filled)) + f"] {pct:5.1f}%"


def sniff_from_bridge():
    print("=================================================================")
    print(" SNIFFER UNIVERSALE ERS / TC / ABS / BIAS (Modalita' Live Bridge)")
    print(" Leggo in tempo reale da http://127.0.0")
    print(" Premi CTRL+C per uscire.")
    print("=================================================================\n")

    last_line = ""
    while True:
        try:
            req = urllib.request.urlopen(API_URL, timeout=0.5)
            d = json.loads(req.read().decode("utf-8"))

            conn = d.get("connected", False)
            sim = d.get("sim", "N/D")
            ers = float(d.get("ers", 0.0))
            ers_act = int(d.get("ers_active", 0))
            ers_chg = int(d.get("ers_charging", 0))
            ers_mod = int(d.get("ers_mode", 0))
            tc = d.get("tc", 0)
            abs_v = d.get("abs", 0)
            bb = float(d.get("brake_bias", 0.0))
            spd = int(d.get("speed", 0))
            gear = d.get("gear", "N")

            if ers_act:
                stato_ers = "DEPLOY (EROGAZIONE)"
            elif ers_chg:
                stato_ers = "HARVEST (RICARICA)"
            elif ers > 0:
                stato_ers = f"IDLE (MODE {ers_mod})"
            else:
                stato_ers = "NON ATTIVO / 0%"

            if not conn:
                line = f"\r[IN ATTESA TELEMETRIA] Sim: {sim:<6} | Nessun pacchetto attivo dal gioco...          "
            else:
                bar = format_bar(ers, 16)
                line = (
                    f"\r[{sim:<4}] {spd:3d}km/h G:{gear:<2} | "
                    f"ERS: {bar} ({stato_ers:<19}) | "
                    f"TC: {str(tc):<2} | ABS: {str(abs_v):<2} | BIAS: {bb:4.1f}%"
                )

            if line != last_line:
                sys.stdout.write(line)
                sys.stdout.flush()
                last_line = line

            time.sleep(0.1)
        except urllib.error.URLError:
            return False
        except KeyboardInterrupt:
            print("\n\n[STOP] Sniffer terminato.")
            sys.exit(0)
        except Exception as e:
            sys.stdout.write(f"\r[ERRORE LETTURA] {e}          ")
            sys.stdout.flush()
            time.sleep(0.5)


def sniff_raw_udp():
    print("=================================================================")
    print(" SNIFFER UNIVERSALE RAW UDP (Bridge spento - Ascolto diretto)")
    print(f" Porte monitorate: {UDP_PORTS} | Premi CTRL+C per uscire.")
    print("=================================================================\n")

    socks = []
    for p in UDP_PORTS:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(("0.0.0.0", p))
            s.setblocking(False)
            socks.append((p, s))
        except OSError as e:
            print(f"[AVVISO] Porta {p} occupata ({e})")

    if not socks:
        print("[ERRORE] Nessuna porta disponibile per lo sniff diretto.")
        return

    try:
        while True:
            for port, s in socks:
                try:
                    data, addr = s.recvfrom(4096)
                    magic = data[:4]
                    info = f"Port {port} | Len={len(data)}B | Magic={magic}"

                    # Decodifica rapida AC / ACE (ACSM)
                    if magic == b"ACSM" and len(data) >= 188:
                        tc_v, abs_v, bb_v, _ = struct.unpack_from("<iifi", data, 116)
                        kc, ki = struct.unpack_from("<ff", data, 180)
                        ers_p = kc * 100.0 if 0.0 <= kc <= 1.0 else kc
                        info = (
                            f"[AC/ACE Raw] ERS={ers_p:5.1f}% (Input={ki:.2f}) | "
                            f"TC={tc_v} | ABS={abs_v} | BIAS={bb_v*100 if bb_v<=1 else bb_v:.1f}%"
                        )
                    # Decodifica rapida ACC (ACCS)
                    elif magic == b"ACCS" and len(data) >= 84:
                        tc_v, abs_v, bb_v = struct.unpack_from("<iif", data, 72)
                        info = (
                            f"[ACC Raw] ERS=N/A | TC={tc_v} | ABS={abs_v} | "
                            f"BIAS={bb_v*100 if bb_v<=1 else bb_v:.1f}%"
                        )

                    sys.stdout.write(f"\r{info:<85}")
                    sys.stdout.flush()
                except BlockingIOError:
                    pass
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("\n\n[STOP] Sniffer terminato.")
    finally:
        for _, s in socks:
            s.close()


if __name__ == "__main__":
    # Prova prima a collegarsi al Bridge attivo; se non risponde, passa allo sniff UDP grezzo
    res = sniff_from_bridge()
    if res is False:
        print("[INFO] Bridge non attivo su porta 8080, avvio ascolto UDP diretto...\n")
        sniff_raw_udp()
