#!/usr/bin/env python3
import configparser
import json
import os
import sys
import time
import urllib.request

def get_api_url():
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.ini")
    if os.path.exists(cfg_path):
        cfg = configparser.ConfigParser()
        cfg.read(cfg_path)
        nic = cfg.get("HARDWARE", "nic_ip", fallback="").strip()
        if nic and nic not in ("0.0.0.0", "127.0.0.1"):
            return f"http://{nic}:8080/api/telemetry"
    return "http://127.0.0"

def main():
    url = get_api_url()
    print(f"=== SNIFFER LIVE ERS / TC / ABS / BIAS -> {url} ===")
    print("Stampa una riga ad ogni variazione (CTRL+C per uscire)...\n", flush=True)

    last_sig = None
    last_heartbeat = 0.0

    try:
        while True:
            try:
                req = urllib.request.urlopen(url, timeout=0.5)
                d = json.loads(req.read().decode("utf-8"))

                conn = d.get("connected", False)
                ers = round(float(d.get("ers", 0.0)), 1)
                ers_act = int(d.get("ers_active", 0))
                ers_chg = int(d.get("ers_charging", 0))
                tc = d.get("tc", 0)
                abs_v = d.get("abs", 0)
                bb = round(float(d.get("brake_bias", 0.0)), 1)
                spd = int(d.get("speed", 0))
                gear = d.get("gear", "N")

                stato = "DEPLOY" if ers_act else ("HARVEST" if ers_chg else "IDLE")
                sig = (conn, ers, stato, tc, abs_v, bb)
                now = time.time()

                # Stampa subito quando cambia un valore (o ogni 5s se tutto fermo)
                if sig != last_sig or (now - last_heartbeat >= 5.0):
                    ts = time.strftime("%H:%M:%S")
                    if not conn:
                        print(f"[{ts}] IN ATTESA PACCHETTI DAL SIMULATORE...", flush=True)
                    else:
                        print(
                            f"[{ts}] {spd:3d} km/h (G:{gear}) | "
                            f"ERS: {ers:5.1f}% [{stato:<7}] | "
                            f"TC: {tc} | ABS: {abs_v} | BIAS: {bb:4.1f}%",
                            flush=True
                        )
                    last_sig = sig
                    last_heartbeat = now

            except Exception as e:
                print(f"[ERRORE] Bridge non raggiungibile ({e})", flush=True)
                time.sleep(1.0)

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[STOP] Sniffer terminato.")

if __name__ == "__main__":
    main()
