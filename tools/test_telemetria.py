cat << 'EOF' > /tmp/test_telemetria.py
#!/usr/bin/env python3
import socket
import struct
import time
import math

IP_BRIDGE = "127.0.0.1"
PORTA_BRIDGE = 9000  # Imposta la stessa "Game UDP Port" della finestra Zenity (es. 9000 o 7573)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def invia_pacchetto_79():
    buf = bytearray(79)
    struct.pack_into("<f", buf, 56, 5793.0)  # track_len_m
    struct.pack_into("<f", buf, 68, 24.0)    # air_temp_c
    struct.pack_into("<f", buf, 72, 31.0)    # track_temp_c
    sock.sendto(buf, (IP_BRIDGE, PORTA_BRIDGE))

def invia_pacchetto_101(prog):
    buf = bytearray(101)
    struct.pack_into("<f", buf, 60, prog)
    sock.sendto(buf, (IP_BRIDGE, PORTA_BRIDGE))

def invia_pacchetto_964(rpm, max_rpm, vel_ms, gear, fuel, t_gomme, u_gomme):
    buf = bytearray(964)
    struct.pack_into("<B", buf, 4, 0)           # packet_type = 0
    struct.pack_into("<f", buf, 140, vel_ms)    # vel_ms
    struct.pack_into("<f", buf, 508, fuel)      # fuel_l
    struct.pack_into("<f", buf, 616, rpm)       # rpm
    struct.pack_into("<B", buf, 821, gear)      # gear_raw
    struct.pack_into("<f", buf, 924, max_rpm)   # max_rpm

    # Temperature gomme (FL, FR, RL, RR)
    struct.pack_into("<f", buf, 76,  t_gomme[0])
    struct.pack_into("<f", buf, 200, t_gomme[1])
    struct.pack_into("<f", buf, 324, t_gomme[2])
    struct.pack_into("<f", buf, 448, t_gomme[3])

    # Usura residua gomme (1.0 = nuova, 0.0 = finita)
    struct.pack_into("<f", buf, 92,  u_gomme[0])
    struct.pack_into("<f", buf, 216, u_gomme[1])
    struct.pack_into("<f", buf, 340, u_gomme[2])
    struct.pack_into("<f", buf, 464, u_gomme[3])

    sock.sendto(buf, (IP_BRIDGE, PORTA_BRIDGE))

print(f"Invio telemetria sintetica su {IP_BRIDGE}:{PORTA_BRIDGE} (CTRL+C per fermare)...")
invia_pacchetto_79()

t0 = time.time()
fuel = 35.0
usura = 0.98
pit_eseguito = False
ultimo_info = 0.0

try:
    while True:
        now = time.time()
        dt = now - t0

        # Invia info pista ogni 2 secondi
        if now - ultimo_info >= 2.0:
            invia_pacchetto_79()
            ultimo_info = now

        # Un giro completo ogni 20 secondi (prog da 0.0 a 1.0)
        prog = (dt % 20.0) / 20.0
        invia_pacchetto_101(prog)

        # Velocità oscillante tra 80 e 290 km/h (in m/s per il bridge: kmh / 3.56)
        vel_kmh = 85.0 + abs(math.sin(dt * 0.45)) * 205.0
        vel_ms = vel_kmh / 3.56
        gear = min(6, max(1, int(vel_kmh // 48) + 1))

        # RPM proporzionali alla marcia + picco fuorigiri ogni 10s
        if int(dt) % 10 == 9:
            rpm = 8450.0
        else:
            rpm = 3800.0 + ((vel_kmh % 48) / 48.0) * 4300.0

        # Consumo carburante + Pit-stop simulato al secondo 25
        if dt > 25.0 and not pit_eseguito:
            fuel = 75.0
            usura = 1.0
            pit_eseguito = True
            print("\n[TEST] Pit-Stop simulato! Rifornimento -> 75.0L e gomme nuove.")
        else:
            fuel = max(1.0, fuel - 0.015)
            usura = max(0.20, usura - 0.0005)

        t_gomme = (
            78.0 + math.sin(dt) * 4.0,
            81.0 + math.sin(dt) * 4.0,
            74.0 + math.cos(dt) * 3.0,
            76.0 + math.cos(dt) * 3.0,
        )
        u_gomme = (usura, usura - 0.01, usura - 0.02, usura - 0.02)

        invia_pacchetto_964(rpm, 8500.0, vel_ms, gear, fuel, t_gomme, u_gomme)

        print(
            f"\rGiro prog: {prog*100:5.1f}% | Vel: {int(vel_kmh):3d} km/h | M: {gear} | "
            f"RPM: {int(rpm):4d} | Fuel: {fuel:4.1f}L | Gomme: {int(usura*100)}%",
            end="",
            flush=True
        )
        time.sleep(0.02)  # 50 Hz
except KeyboardInterrupt:
    print("\nTest completato.")
EOF
python3 /tmp/test_telemetria.py
