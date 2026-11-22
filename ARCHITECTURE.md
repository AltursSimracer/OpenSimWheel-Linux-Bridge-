# Technical Architecture

## Overview
**OpenSimWheel Linux Bridge** acts as a native Linux telemetry router running at **40Hz** on the UDP output layer (tuned to prevent Wi-Fi buffer bloat on wireless display wheels such as the Thrustmaster SF1000, ESP32/VoCore DDUs, and mobile/tablet apps) while polling simulator memory and local sockets at up to **100Hz**.

## Core Components

### 1. Central Hub & Auto-Healer (`core/OpenSimWheel_Linux_Bridge.py`)
- **Smart Network Auto-Sniffer:** Automatically detects the host PC's LAN/Wi-Fi IP address, scans the local `/24` subnet for active F1-UDP displays or wireless wheels, and listens across standard simulator UDP ports when set to `auto`.
- **Self-Healing Configuration:** Validates `config.ini` and `osw_bridge.ini` at startup, restores missing keys/languages (`IT`, `EN`, `DE`, `FR`, `ES`), cleans up stale `stop*.flag` files, and automatically regenerates Proton Shared Memory bridges if missing.
- **Built-in HTTP Telemetry Server (`port 8080`):** Serves the real-time JSON endpoint (`/api/telemetry`), the primary **Web Live Dash** (`livedash.html`), and the **PitWall Timing** view (`timing.html`) with zero external web server dependencies.

### 2. Simulator Satellites (`core/*_bridge.py`)
Each simulator runs through an isolated parser module that normalizes telemetry into `DASH_STATE` and encodes **F1 2020/2023 UDP packets** (`Packet 1` Session, `Packet 2` Lap Data, `Packet 6` Car Telemetry, `Packet 7` Car Status — including real **TC, ABS, Brake Bias, FIA Flags, 3-zone IMO tyre temps, pressures, wear, and pit-stop-aware Fuel**):
- **Shared Memory Proton Bridges (`ac_ace_bridge.py`, `acc_bridge.py`, `rrre_bridge.py`):** Lightweight Windows embeddable Python senders (`*_shm_sender.py`) run inside the game's active `wineserver` context, reading `Local\acpmf_*`, `Local\acevo_pmf_*`, or `Local\$R3E` via `mmap` and forwarding compact binary frames over localhost UDP (`9001`, `9003`, `9005`, `9007`).
- **DLL-Free Native Memory & REST Scanners (`rf2_bridge.py`, `lmu_bridge.py`):** Reads engine RPM, gears, and 4-wheel IMO/wear/pressure blocks directly from the Wine process address space via Linux `process_vm_readv` combined with the game's local REST API (`5397` / `6397`).
- **Native UDP Listener (`OpenSimWheel_Linux_Bridge.py`):** Directly ingests native UDP telemetry from **Project Motor Racing (PMR)** (`port 7576`).

### 3. Deployment & Maintenance Scripts
- **`install.sh` / `core/installer.sh` & `core/uninstaller.sh`:** Multilingual Zenity GUI installer/uninstaller with desktop integration, config backups, and clean `--purge` support.
- **`setup_*_proton.sh`:** Per-simulator setup scripts that automatically locate Steam/Proton libraries (`libraryfolders.vdf`, `/run/media`, `/mnt`), deploy embeddable Python, and bind launchers to the active `wineserver`.
- **`verifica_e_impacchetta.sh`:** Automated release pipeline that cleans temporary files, runs `py_compile` and `bash -n` checks, normalizes permissions, and generates `SHA256SUMS.txt` alongside `.tar.gz` and `.zip` archives.



