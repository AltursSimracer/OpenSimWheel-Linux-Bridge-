import socket
import struct
import time

AC_PKT_FMT = "<4siififfiiiiiiifffffff"
AC_PKT_SIZE = struct.calcsize(AC_PKT_FMT)

TARGETS = [("127.0.0.1", 9003), ("127.0.0.1", 9005)]
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def build_acsm_packet(speed_kmh, rpm, max_rpm, gear_raw, ers_charge_01, ers_input_01, lap_prog=0.25):
    # Header + dati base (84 byte)
    base = struct.pack(
        AC_PKT_FMT,
        b"ACSM",
        int(rpm),
        int(max_rpm),
        float(speed_kmh),
        int(gear_raw),
        48.5,   # fuel_l
        110.0,  # max_fuel_l
        42500,  # cur_lap_ms
        81200,  # last_lap_ms
        80950,  # best_lap_ms
        27100,  # s1_ms
        54300,  # s2_ms
        3,      # current_lap
        1,      # pos
        float(lap_prog),
        84.0, 85.0, 81.0, 82.0, # gomme C
        24.0, 32.0              # aria / pista C
    )
    # 32 byte pressioni (26.5 psi) e vita gomme (0.96 = 96%)
    tyres = struct.pack("<ffffffff", 26.5, 26.6, 26.2, 26.3, 0.96, 0.96, 0.97, 0.97)
    # 16 byte elettronica (TC=2, ABS=1, BB=56.5%, Flag=0)
    elec = struct.pack("<iifi", 2, 1, 0.565, 0)
    # 8 byte ERS (kersCharge 0..1, kersInput 0..1)
    ers = struct.pack("<ff", float(ers_charge_01), float(ers_input_01))
    return base + tyres + elec + ers

print("============================================================")
print(" TEST VISIVO ERS (PACCHETTO ACSM REALE) -> 127.0.0.1:9003 / 9005")
print(" Assicurati di aver premuto AVVIA su Assetto Corsa (AC) nel Bridge!")
print(" Premi CTRL+C per fermare.")
print("============================================================\n")

try:
    ciclo = 1
    prog = 0.1
    while True:
        # FASE 1: 10 SECONDI EROGAZIONE ERS (VERDE SU DASH + OVERTAKE SU SF1000)
        print(f"[CICLO {ciclo} - FASE 1/3 (10s)] EROGAZIONE ERS ATTIVA (OVERTAKE)")
        print(" -> Web Dash: riquadro ERS VERDE BRILLANTE (100% -> 40%)")
        print(" -> SF1000:   barra ERS scende + modalita' OVERTAKE\n")
        for step in range(200):
            charge = 1.0 - (step / 200.0) * 0.60
            prog = (prog + 0.002) % 1.0
            pkt = build_acsm_packet(298.0, 11800, 12500, 9, charge, 1.0, prog)
            for t in TARGETS:
                sock.sendto(pkt, t)
            time.sleep(0.05)

        # FASE 2: 10 SECONDI RICARICA ERS (AZZURRO SU DASH)
        print(f"[CICLO {ciclo} - FASE 2/3 (10s)] RICARICA ERS (HARVEST)")
        print(" -> Web Dash: riquadro ERS AZZURRO (40% -> 95%)")
        print(" -> SF1000:   barra ERS risale + modalita' MEDIUM\n")
        for step in range(200):
            charge = 0.40 + (step / 200.0) * 0.55
            prog = (prog + 0.001) % 1.0
            pkt = build_acsm_packet(142.0, 7400, 12500, 5, charge, 0.0, prog)
            for t in TARGETS:
                sock.sendto(pkt, t)
            time.sleep(0.05)

        # FASE 3: 8 SECONDI IDLE / MANTENIMENTO (NEUTRO SU DASH)
        print(f"[CICLO {ciclo} - FASE 3/3 (8s)] ERS MANTENIMENTO (IDLE 95%)")
        print(" -> Web Dash: riquadro ERS neutro fisso al 95%\n")
        for step in range(160):
            prog = (prog + 0.0015) % 1.0
            pkt = build_acsm_packet(218.0, 9300, 12500, 7, 0.95, 0.0, prog)
            for t in TARGETS:
                sock.sendto(pkt, t)
            time.sleep(0.05)

        ciclo += 1

except KeyboardInterrupt:
    print("\n[STOP] Test terminato.")
finally:
    sock.close()
