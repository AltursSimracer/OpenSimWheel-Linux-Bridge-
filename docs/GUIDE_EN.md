# User Guide — OpenSimWheel Linux Bridge v1.4.0

Native Linux telemetry bridge optimized at **40Hz** (Wi-Fi anti-stutter) for **rFactor 2 (rF2)**, **Le Mans Ultimate (LMU)**, **Assetto Corsa Competizione (ACC)**, **Assetto Corsa (AC)**, **Assetto Corsa EVO (ACE)**, **RaceRoom Racing Experience (RRRE)**, and **Project Motor Racing (PMR)**.

Streams real-time telemetry (**RPM, shift LEDs, gears, speed, fuel & remaining laps, TC, ABS, Brake Bias, FIA flags, 3-zone IMO tyre temps, pressures, wear, and lap/sector times**) to:
- **Any Wi-Fi / UDP Steering Wheel or DDU Display** supporting the F1 2020/2023 UDP standard (`port 20777` — including Thrustmaster SF1000, custom ESP32/VoCore displays, and smartphone/tablet apps like SimHub, SimDashboard, DashPanel, RS Dash).
- **Built-in Web Live Dash + PitWall Timing** (`port 8080`), accessible from any PC, tablet, or smartphone browser with zero extra hardware.

## 1. Installation and Uninstallation
1. Run **`./installer.sh`** from a terminal (or double-click **`Installa_OpenSimWheel.desktop`**).
2. Select your installed simulators: for **rF2** and **LMU**, the installer automatically enables native Linux RAM reading (`kernel.yama.ptrace_scope = 0`) without requiring any external DLL plugins.
3. The application installs to `~/.local/share/OpenSimWheel`, creates `~/.config/OpenSimWheel/osw_bridge.ini`, and adds **OpenSimWheel Linux** to your application menu and desktop.
4. To uninstall while keeping settings run `~/.local/share/OpenSimWheel/uninstaller.sh` (or `./uninstaller.sh --purge` to remove `~/.config/OpenSimWheel` as well).

## 2. Per-Simulator Setup

### rFactor 2 (rF2) & Le Mans Ultimate (LMU) — 100% Native (No Plugins)
1. **No external plugins required:** Do not place any `.dll` files inside the game's `Plugins/` folder (prevents startup crashes on Proton 9.0 / GE-Proton). The Bridge reads engine, gears, and 4-wheel IMO/wear/pressure data directly via native REST API (`5397` / `6397`) and Linux RAM scanning.
2. In **Steam Properties**:
   - Under **Compatibility**, select **`Proton 9.0`** or **`Proton Experimental`** for rF2, and **`GE-Proton`** / **`Proton Experimental`** for LMU.
   - Under **Controller**, select **Disable Steam Input**.
3. In the game's **Controls -> Force Feedback** menu, enable **Invert Force Feedback** if using a Thrustmaster wheel.
4. Launch the game, open **OpenSimWheel Linux**, select **RF2** or **LMU**, and click **OK**.

### Assetto Corsa Competizione (ACC)
1. Launch ACC at least once on Steam to initialize its Proton prefix (`AppID 805550`).
2. Run **`./scripts/setup_acc_proton.sh`** once (or select **ACC** during installation) to configure Shared Memory forwarding inside the ACC Steam Proton prefix (ports `9000`/`9001`).
3. Launch ACC, open **OpenSimWheel Linux**, select **ACC (Assetto Corsa Competizione)**, and click **OK**.

### Assetto Corsa (AC)
1. Launch the game at least once on Steam to initialize its Proton prefix (`AppID 244210`).
2. Run **`./scripts/setup_ac_proton.sh`** once (internal port `9003`, with automatic `mmap` release when returning to the menu).
3. Launch AC, open **OpenSimWheel Linux**, select **AC (Assetto Corsa)**, and click **OK**.

### Assetto Corsa EVO (ACE)
1. Launch the game at least once on Steam to initialize its Proton prefix (`AppID 3058630`).
2. Run **`./scripts/setup_ace_proton.sh`** once (internal port `9005`, native `Local\acevo_pmf_*` reader with automatic real engine rev-limiter detection).
3. Launch ACE, open **OpenSimWheel Linux**, select **ACE (Assetto Corsa EVO)**, and click **OK**.

### RaceRoom Racing Experience (RRRE)
1. Launch the game at least once on Steam to initialize its Proton prefix (`AppID 211500`).
2. Run **`./scripts/setup_rrre_proton.sh`** once (internal port `9007`, native `Local\$R3E` reader).
3. **Wheel Tips on Linux:**
   - In **Steam Properties for RaceRoom -> Controller**, select **Disable Steam Input** and set Launch Options to `SDL_JOYSTICK_HIDAPI=1 PROTON_ENABLE_HIDRAW=1 %command%`.
4. Launch RaceRoom, open **OpenSimWheel Linux**, select **RRRE (RaceRoom)**, and click **OK**.

### Project Motor Racing (PMR)
1. Enable UDP telemetry output in PMR settings on port **`7576`** (or `5606`).
2. Open **OpenSimWheel Linux**, select **PMR (Project Motor Racing)**, and click **OK**.

## 3. Smart Auto-Sniffer, Central Config & Web Live Dash
- **Auto-Sniffer:** On startup, OpenSimWheel automatically detects your PC's local LAN/Wi-Fi IP address and scans the network for compatible UDP display wheels or tablets.
- **Central Config (`osw_bridge.ini`):** All simulator ports and self-healing settings are stored in `~/.config/OpenSimWheel/osw_bridge.ini` (`[SIM_RF2]`, `[SIM_LMU]`, `[SIM_ACC]`, `[SIM_AC]`, `[SIM_ACE]`, `[SIM_RRRE]`, `[SIM_PMR]`).
- **Web Live Dash (`http://<YOUR_PC_IP>:8080`):** Displays shift LEDs, gear, speed, TC, ABS, Brake Bias, active FIA flags, fuel consumption, and tyre temps (toggleable between **MEDIA** and **IMO**).
- **PitWall Timing (`http://<YOUR_PC_IP>:8080/timing`):** Fullscreen timing view with position, lap, current/last/best lap times, and all 3 sectors (`S1 / S2 / S3`), optimized for tablets and iPads.

## Optional Kernel Optimization (Proton Shared Memory & IPC)

During installation (`./installer.sh`), you are asked whether to apply an optional kernel Shared Memory profile (`/etc/sysctl.d/99-opensimwheel-shm.conf`):
- `kernel.shmmax = 2147483648` and `kernel.shmall = 524288`: ensures ample `/dev/shm` shared memory buffers for 100Hz telemetry.
- `kernel.yama.ptrace_scope = 0`: allows external telemetry bridges to attach to Shared Memory exposed by Wine/Proton processes on distros with strict IPC policies (e.g., Ubuntu/Debian).

> **Note:** If you already run a gaming-tuned kernel (e.g., CachyOS, Liquorix) or prefer not to touch `sysctl`, you can safely select **No**. If enabled, `./uninstaller.sh` automatically removes `/etc/sysctl.d/99-opensimwheel-shm.conf`.
