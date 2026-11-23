# ==============================================================================
# OpenSimWheel Linux Bridge - Multi-Protocol Output Router (100% Open Source)
# Copyright (C) 2026 Alex
# Licensed under the GNU General Public License v3.0 (GPLv3)
# ==============================================================================
import json
import struct
import time
import os

try:
    import serial
except ImportError:
    serial = None


class MultiProtocolRouter:
    def __init__(self):
        self._frame = 0
        self._ser = None
        self._ser_last_try = 0.0
        self.enable_f1_udp = True
        self.enable_open_json_udp = True
        self.open_json_port = 20778
        self.serial_port = ""  # Es. "/dev/ttyACM0" o "/dev/ttyUSB0"
        self.serial_baud = 115200

    def configure(self, enable_f1=True, enable_json=True, json_port=20778, serial_port="", serial_baud=115200):
        self.enable_f1_udp = enable_f1
        self.enable_open_json_udp = enable_json
        self.open_json_port = int(json_port)
        self.serial_port = serial_port.strip()
        self.serial_baud = int(serial_baud)

    def _get_serial(self):
        if not serial or not self.serial_port:
            return None
        if self._ser and self._ser.is_open:
            return self._ser
        now = time.time()
        if now - self._ser_last_try < 3.0:
            return None
        self._ser_last_try = now
        try:
            if os.path.exists(self.serial_port):
                self._ser = serial.Serial(self.serial_port, self.serial_baud, timeout=0, write_timeout=0)
                return self._ser
        except Exception:
            self._ser = None
        return None

    def send_frame(self, out_sock, ip_display, porta_display, dash_state, f1_packets=()):
        self._frame = (self._frame + 1) & 0xFFFFFFFF

        # 1. Standard binario F1 2020 UDP (Volanti Wi-Fi / Display UDP)
        if self.enable_f1_udp and f1_packets:
            for pkt in f1_packets:
                try:
                    out_sock.sendto(pkt, (ip_display, porta_display))
                except Exception:
                    pass

        # 2. Flusso aperto OSW JSON UDP (Per client Linux nativi, app open-source, Monocoque)
        if self.enable_open_json_udp and (self._frame % 2 == 0):
            payload_json = json.dumps({
                "protocol": "OSW_OPEN_TELEMETRY_V1",
                "gear": dash_state.get("gear", "N"),
                "speed": dash_state.get("speed", 0),
                "rpm": dash_state.get("rpm", 0),
                "max_rpm": dash_state.get("max_rpm", 8500),
                "fuel": round(float(dash_state.get("fuel", 0.0)), 2),
                "ers_pct": round(float(dash_state.get("ers", 0.0)), 1),
                "ers_mode": int(dash_state.get("ers_mode", 0)),
                "ers_active": int(dash_state.get("ers_active", 0)),
                "ers_charging": int(dash_state.get("ers_charging", 0)),
                "drs": int(dash_state.get("drs", 0)),
                "tc": int(dash_state.get("tc", 0)),
                "abs": int(dash_state.get("abs", 0)),
                "brake_bias": round(float(dash_state.get("brake_bias", 0.0)), 1),
                "flag": dash_state.get("flag", "none"),
            }, separators=(",", ":")).encode("utf-8")
            try:
                out_sock.sendto(payload_json, (ip_display, self.open_json_port))
            except Exception:
                pass

        # 3. Protocollo Seriale Binario Compatto (Arduino / ESP32 / STM32 / RP2040 su /dev/tty*)
        ser = self._get_serial()
        if ser and (self._frame % 2 == 0):
            try:
                rpm = max(0, min(65535, int(dash_state.get("rpm", 0))))
                max_rpm = max(1, min(65535, int(dash_state.get("max_rpm", 8500))))
                spd = max(0, min(65535, int(dash_state.get("speed", 0))))
                gear_map = {"R": 255, "N": 0}
                g_str = str(dash_state.get("gear", "N"))
                gear_b = gear_map.get(g_str, int(g_str) if g_str.isdigit() else 0)
                ers_b = max(0, min(100, int(round(float(dash_state.get("ers", 0.0))))))
                ers_flags = ((int(dash_state.get("ers_charging", 0)) & 1) << 5) | \
                            ((int(dash_state.get("ers_active", 0)) & 1) << 4) | \
                            (int(dash_state.get("ers_mode", 0)) & 0x0F)
                frame_mcu = struct.pack("<BBHHHBBB", 0xAA, 0x55, rpm, max_rpm, spd, gear_b, ers_b, ers_flags)
                ser.write(frame_mcu)
            except Exception:
                try:
                    self._ser.close()
                except Exception:
                    pass
                self._ser = None


ROUTER = MultiProtocolRouter()
