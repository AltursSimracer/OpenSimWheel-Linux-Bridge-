# OpenSimWheel Linux Bridge v1.4.0

Native Linux 100Hz telemetry bridge for **Le Mans Ultimate (LMU)**, **rFactor 2 (rF2)**, **Assetto Corsa Competizione (ACC)**, **Assetto Corsa (AC)**, **Assetto Corsa EVO (ACE)**, **RaceRoom Racing Experience (RRRE)**, and **Project Motor Racing (PMR)**.

Routes real-time telemetry (**RPM, shift LEDs, gears, speed, fuel & remaining laps, TC, ABS, Brake Bias, FIA flags, tyre temps/IMO, pressures, wear, and lap/sector times**) to:
- **Any Wi-Fi / UDP Steering Wheel or DDU Display** supporting the F1 2020/2023 UDP standard (`port 20777` — including Thrustmaster SF1000, ESP32/VoCore custom wheels, and mobile/tablet apps like SimHub, SimDashboard, DashPanel, RS Dash).
- **Built-in Web Live Dash + PitWall Timing** (`http://<PC-IP>:8080` and `/timing`), accessible from any PC, tablet, or smartphone browser with zero extra hardware.

## Key Features
- **Smart Auto-Sniffer & Self-Healing:** Automatically detects your PC's local LAN/Wi-Fi IP, scans the network for UDP display wheels/tablets, validates `config.ini`, and repairs Proton SHM scripts on startup.
- **Unified Telemetry Across All 7 Sims:** Consistent TC, ABS, Brake Bias, FIA Flags, and pit-stop-aware Fuel calculations across both hardware displays and the Web Live Dash.
- **Zero-Plugin Native rF2 & LMU:** Reads engine, gears, and 4-wheel IMO data directly via Linux kernel memory (`process_vm_readv`) + local REST API (`5397`/`6397`).

## Quick Installation & Setup
1. Double-click **`Installa_OpenSimWheel.desktop`** (or run `./installer.sh` in terminal) and select the simulators you want to configure automatically.
2. **Proton Shared Memory Bridges (AC, ACC, ACE, RRRE):** Automatically configured during installation (or run `./scripts/setup_ac_proton.sh`, `./scripts/setup_acc_proton.sh`, `./scripts/setup_ace_proton.sh`, `./scripts/setup_rrre_proton.sh` once).
3. **rFactor 2 (rF2), Le Mans Ultimate (LMU), & Project Motor Racing (PMR):** Ready out-of-the-box with no external plugins required.
4. Launch **OpenSimWheel Linux**, verify the auto-detected IPs, select your simulator (**LMU**, **rF2**, **ACC**, **AC**, **ACE**, **RRRE**, or **PMR**), and click **OK**.

## Documentation
- English: `docs/GUIDE_EN.md`
- Italiano: `docs/GUIDE_IT.md`
- Deutsch: `docs/GUIDE_DE.md`
- Français: `docs/GUIDE_FR.md`
- Español: `docs/GUIDE_ES.md`


---

## Support the Project / Supporta il Progetto

**OpenSimWheel Linux Bridge** is completely free and open source (GPL-3.0). If this project is useful during your stints on track and you'd like to buy me a coffee to support development and testing on new simulators, any contribution is welcome!

**OpenSimWheel Linux Bridge** è completamente gratuito e open source (GPL-3.0). Se questo progetto ti è utile nei tuoi stint in pista e vuoi offrirmi un caffè per supportare lo sviluppo e i test su nuovi simulatori, qualsiasi contributo è benvenuto!

[![Ko-fi](https://img.shields.io/badge/Support%20on-Ko--fi-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/alturs)
[![PayPal](https://img.shields.io/badge/Donate-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://www.paypal.me/Alturs329)
