#!/usr/bin/env python3
import configparser, socket, struct, time

cfg = configparser.ConfigParser()
cfg.read("config.ini")
IP = cfg.get("HARDWARE", "volante_ip", fallback="192.168.1.26")
PORT = cfg.getint("HARDWARE", "volante_porta_udp", fallback=20777)

# Header F1 2023: 29 byte (<HBBBBBQfIBB)
HDR23 = "<HBBBBBQfIBB"
def hdr(pkt_id, t, fid):
    return struct.pack(HDR23, 2023, 23, 1, 0, 1, pkt_id, 123456789, float(t), fid, 0, 0)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"=== TEST UFFICIALE THRUSTMASTER FORMATO 2023 -> {IP}:{PORT} ===")
print("ERS impostato a 85% (3.4 MJ), Mode 2 (Overtake), PSI 23.2/24.1, Bias 58%.")
print("Guarda il display SF1000 (Premi CTRL+C per uscire).\n")

fid = 1
t0 = time.time()
try:
    while True:
        t = time.time() - t0

        # Packet 1: Session F1 2023 (29 + 615 = 644 byte)
        p1 = bytearray(615)
        struct.pack_into("<BbbBH", p1, 0, 1, 28, 22, 60, 5000)
        struct.pack_into("<B", p1, 6, 0)
        struct.pack_into("<B", p1, 19, 1)
        sock.sendto(hdr(1, t, fid) + p1, (IP, PORT))

        # Packet 2: Lap Data F1 2023 (29 + 1102 = 1131 byte -> 22 * 50B + 2)
        p2 = bytearray(1102)
        struct.pack_into("<IIHH", p2, 0, 88500, 42100, 28100, 31200)
        struct.pack_into("<ff", p2, 20, 2400.0, 7400.0)
        struct.pack_into("<BBBB", p2, 32, 1, 2, 0, 1)
        struct.pack_into("<BBBBB", p2, 39, 1, 2, 0, 0, 0)
        sock.sendto(hdr(2, t, fid) + p2, (IP, PORT))

        # Packet 6: Car Telemetry F1 2023 (29 + 1323 = 1352 byte -> 22 * 60B + 3)
        p6 = bytearray(1323)
        struct.pack_into("<HfffB", p6, 0, 268, 0.9, 0.0, 0.0, 0)
        struct.pack_into("<bHBBH", p6, 15, 7, 11400, 1, 75, 0x07FF)
        struct.pack_into("<HHHH", p6, 20, 310, 310, 330, 330)
        struct.pack_into("<BBBB", p6, 28, 88, 89, 92, 93)
        struct.pack_into("<BBBB", p6, 32, 88, 89, 92, 93)
        struct.pack_into("<H", p6, 36, 95)
        struct.pack_into("<ffff", p6, 38, 23.2, 23.3, 24.1, 24.2)
        sock.sendto(hdr(6, t, fid) + p6, (IP, PORT))

        # Packet 7: Car Status F1 2023 (29 + 1210 = 1239 byte -> 22 * 55B)
        # Offset F1 2023 per auto 0:
        # 0..4: tc, abs, fuelMix, brakeBias, pitLimiter
        # 5..16: fuelInTank, fuelCapacity, fuelRemainingLaps
        # 17..21: maxRPM, idleRPM, maxGears
        # 22..24: drsAllowed, drsActivationDistance
        # 25..27: actualTyreCompound, visualTyreCompound, tyresAgeLaps
        # 28: vehicleFiaFlags
        # 29..36: enginePowerICE (float), enginePowerMGUK (float)
        # 37..40: ersStoreEnergy (float = 3400000.0 -> 85%!)
        # 41: ersDeployMode (uint8 = 2 -> Overtake!)
        # 42..53: ersHarvestedMGUK, ersHarvestedMGUH, ersDeployedThisLap
        p7 = bytearray(1210)
        struct.pack_into("<BBBBB", p7, 0, 1, 1, 1, 58, 0)
        struct.pack_into("<fff", p7, 5, 34.5, 100.0, 12.4)
        struct.pack_into("<HHB", p7, 17, 11800, 3500, 8)
        struct.pack_into("<BH", p7, 22, 1, 0)
        struct.pack_into("<BBBb", p7, 25, 16, 16, 4, 0)
        struct.pack_into("<ff", p7, 29, 550000.0, 120000.0)
        struct.pack_into("<fBfff", p7, 37, 3400000.0, 2, 800000.0, 0.0, 600000.0)
        sock.sendto(hdr(7, t, fid) + p7, (IP, PORT))

        fid += 1
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\n[STOP] Test terminato.")
