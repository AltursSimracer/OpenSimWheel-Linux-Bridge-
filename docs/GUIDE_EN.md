# User Guide — OpenSimWheel Linux Bridge v1.3.0

Native Linux telemetry bridge optimized at **40Hz** (Wi-Fi anti-stutter) for **Le Mans Ultimate (LMU)**, **Assetto Corsa Competizione (ACC)**, **Assetto Corsa (AC)**, **Assetto Corsa EVO (ACE)**, **RaceRoom Racing Experience (RRRE)**, and **Project Motor Racing (PMR)**.
Streams real-time telemetry (RPM, shift LEDs, gears, speed, fuel, tire temperatures, and lap times) to **Thrustmaster SF1000 (Direct Wi-Fi / Native)**, UDP DDU displays (`port 20777`), and **Web Live Dash + PitWall Timing** (`port 8080`).

## 1. Installation and Uninstallation
1. Run **`./install.sh`** from a terminal (or double-click **`Installa_OpenSimWheel.desktop`**).
2. The application installs to `~/.local/share/OpenSimWheel`, creates the central config file `~/.config/OpenSimWheel/osw_bridge.ini`, and adds **OpenSimWheel Linux Bridge** to your application menu.
3. To uninstall while keeping your settings, run `./core/uninstaller.sh`.
4. To completely remove configuration files (`~/.config/OpenSimWheel`) as well, run `./core/uninstaller.sh --purge`.

## 2. Per-Simulator Setup

### Le Mans Ultimate (LMU)
1. Download **`rFactor2SharedMemoryMapPlugin64.dll`** (from the *rF2 Shared Memory Map Plugin* / *TinyPedal* package) and place it in `Le Mans Ultimate/Plugins/` (or leave it in `~/Downloads` before the next step).
2. Run **`./setup_lmu_plugin.sh`** once from the project folder: the script copies the DLL and automatically enables the plugin in `UserData/player/CustomPluginVariables.JSON`.
3. In **Steam Properties for Le Mans Ultimate**:
   - Under **Compatibility**, select a compatible Proton version (e.g., **`Proton Experimental`** or **`GE-Proton`**).
   - Under **Controller**, select **Disable Steam Input**.
4. In the game's **Controls -> Force Feedback** menu, enable **Invert Force Feedback** if using a Thrustmaster wheel.
5. Launch LMU, open **OpenSimWheel Linux Bridge**, select **LMU (Le Mans Ultimate)**, and click **OK**.

### Assetto Corsa Competizione (ACC)
1. Run **`./setup_acc_proton.sh`** once to configure Shared Memory forwarding inside the ACC Steam Proton prefix (`AppID 805550`, internal port `9000`).
2. Launch ACC, open **OpenSimWheel Linux Bridge**, select **ACC (Assetto Corsa Competizione)**, and click **OK**.

### Assetto Corsa (AC)
1. Launch the game at least once on Steam to initialize its Proton prefix (`AppID 244210`).
2. Run **`./setup_ac_proton.sh`** once (internal port `9003`, with automatic `mmap` release when returning to the menu).
3. Launch AC, enter the track, open **OpenSimWheel Linux Bridge**, select **AC (Assetto Corsa)**, and click **OK**.

### Assetto Corsa EVO (ACE)
1. Launch the game at least once on Steam to initialize its Proton prefix (`AppID 3058630`).
2. Run **`./setup_ace_proton.sh`** once (internal port `9005`, native `Local\acevo_pmf_*` reader with automatic real engine rev-limiter detection).
3. Launch ACE, sit in the cockpit, open **OpenSimWheel Linux Bridge**, select **ACE (Assetto Corsa EVO)**, and click **OK**.

### RaceRoom Racing Experience (RRRE)
1. Launch the game at least once on Steam to initialize its Proton prefix (`AppID 211500`).
2. Run **`./setup_rrre_proton.sh`** once (internal port `9007`, native `Local\$R3E` reader).
3. **Thrustmaster Wheel Tips on Linux:**
   - In **Steam Properties for RaceRoom -> Controller**, select **Disable Steam Input** and set Launch Options to `SDL_JOYSTICK_HIDAPI=1 PROTON_ENABLE_HIDRAW=1 %command%`.
   - If separate USB pedals are detected before the wheel (`js0`), duplicate the `Keyboard` profile under **Options -> Controls**, manually bind **Steer Left/Right** to the wheel, and enable **Invert Force Feedback** if needed.
4. Launch RaceRoom, enter the track, open **OpenSimWheel Linux Bridge**, select **RRRE (RaceRoom)**, and click **OK**.

### Project Motor Racing (PMR)
1. Enable UDP telemetry output in PMR settings on port **`7576`** (or `5606`).
2. Open **OpenSimWheel Linux Bridge**, select **PMR (Project Motor Racing)**, and click **OK**.

## 3. Central Config (`osw_bridge.ini`) & Self-Healing
- All simulator ports and settings are isolated inside **`~/.config/OpenSimWheel/osw_bridge.ini`** (`[SIM_PMR]`, `[SIM_LMU]`, `[SIM_ACC]`, `[SIM_AC]`, `[SIM_ACE]`, `[SIM_RRRE]`).
- **Anti-Deletion Protection (Self-Healing):** On every startup, the Bridge automatically verifies `osw_bridge.ini` and the `drive_c/osw_shm` folder inside the selected game's Steam prefix, restoring any missing files before connecting.

## 4. Web Live Dash & PitWall Timing
- While the Bridge is running, open **`http://<YOUR_PC_IP>:8080`** (e.g., `http://127.0.0.1:8080`) from any PC, tablet, or smartphone browser.
