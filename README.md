# OpenSimWheel Linux Bridge v1.3.0

Native Linux 100Hz telemetry bridge for **Le Mans Ultimate (LMU)**, **Assetto Corsa Competizione (ACC)**, **Assetto Corsa (AC)**, **Assetto Corsa EVO (ACE)**, **RaceRoom Racing Experience (RRRE)**, and **Project Motor Racing (PMR)**.
Routes real-time telemetry (RPM, shift LEDs, gears, speed, fuel, tyre temperatures, lap times) to **UDP Steering Wheel / Display**, UDP DDU displays (`port 20777`), and the built-in **Web Live Dash + PitWall Timing** (`port 8080`).

## Quick Installation & Setup
1. Double-click **`Installa_OpenSimWheel.desktop`** (or run `./core/installer.sh` in terminal) and select the simulators you want to configure automatically.
2. **For Le Mans Ultimate (LMU):** Place `rFactor2SharedMemoryMapPlugin64.dll` in `Le Mans Ultimate/Plugins/` (or `~/Downloads`) and run `./setup_lmu_plugin.sh` once to enable it in `CustomPluginVariables.JSON`.
3. **For Assetto Corsa Competizione (ACC):** Run `./setup_acc_proton.sh` once (or select ACC during installation) to enable Shared Memory in Steam Proton.
4. **For Assetto Corsa (AC), Assetto Corsa EVO (ACE), and RaceRoom (RRRE):** Run `./setup_ac_proton.sh, setup_ace_proton.sh, setup_rrre_proton.sh, setup_acc_proton.sh` once (or select them during installation) to configure Proton Shared Memory bridges.
5. Launch **OpenSimWheel Linux**, select your simulator (**LMU**, **ACC**, **AC**, **ACE**, **RRRE**, or **PMR**), and click **OK**.

## Documentation
- English: `docs/GUIDE_EN.md`
- Italiano: `docs/GUIDE_IT.md`
- Deutsch: `docs/GUIDE_DE.md`
- Français: `docs/GUIDE_FR.md`
- Español: `docs/GUIDE_ES.md`

