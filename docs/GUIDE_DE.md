# Benutzerhandbuch — OpenSimWheel Linux Bridge v1.3.0

Native 100Hz-Telemetrie-Bridge unter Linux für **Le Mans Ultimate (LMU)**, **Assetto Corsa Competizione (ACC)**, **Assetto Corsa (AC)**, **Assetto Corsa EVO (ACE)**, **RaceRoom Racing Experience (RRRE)** und **Project Motor Racing (PMR)**.
Sendet Echtzeit-Telemetrie (Drehzahl, Schalt-LEDs, Gänge, Geschwindigkeit, Kraftstoff, Reifentemperaturen, Rundenzeiten) an **UDP Steering Wheel / Display**, UDP-DDU-Displays (`Port 20777`) und **Web Live Dash + PitWall Timing** (`Port 8080`).

## 1. Installation
1. Doppelklicke auf **`Installa_OpenSimWheel.desktop`** (oder führe `./core/installer.sh` im Terminal aus).
2. Wähle im Auswahlfenster die auf deinem PC installierten Simulatoren aus, um deren Plugins und Proton-Bridges automatisch einzurichten.
3. Das Programm wird unter `~/.local/share/OpenSimWheel` installiert und erstellt die Verknüpfung **OpenSimWheel Linux** im Anwendungsmenü und auf dem Desktop.
4. Zur vollständigen Deinstallation führe `~/.local/share/OpenSimWheel/uninstaller.sh` aus.

## 2. Einrichtung nach Simulator

### Le Mans Ultimate (LMU) — Vollständige Anleitung
1. Lade **`rFactor2SharedMemoryMapPlugin64.dll`** herunter (aus dem Paket *rF2 Shared Memory Map Plugin* / *TinyPedal*) und kopiere sie nach `Le Mans Ultimate/Plugins/` (oder lasse sie vor dem nächsten Schritt in `~/Downloads`).
2. Führe einmalig **`./setup_lmu_plugin.sh`** aus dem entpackten Ordner aus (oder wähle **LMU** während der Installation): Das Skript kopiert die DLL (falls gefunden) und aktiviert das Plugin automatisch in `UserData/player/CustomPluginVariables.JSON`.
3. In den **Steam-Eigenschaften von Le Mans Ultimate**:
   - Unter **Kompatibilität** eine mit LMU/EAC kompatible Proton-Version wählen (z. B. **`GE-Proton11-3-LMU`** oder **`Proton Experimental`**).
   - Unter **Controller** **Steam-Eingabe deaktivieren** wählen (verhindert doppelte Eingaben und zufällige Gangwechsel).
4. Im Spielmenü **Controls -> Force Feedback** bei Verwendung eines Thrustmaster-Lenkrads **Invert Force Feedback** aktivieren.
5. Starte LMU, öffne anschließend **OpenSimWheel Linux**, wähle **LMU (Le Mans Ultimate)** und klicke auf **OK**.

### Assetto Corsa Competizione (ACC)
1. Führe einmalig **`./setup_acc_proton.sh`** aus (oder wähle **ACC** während der Installation), um das Auslesen des Shared Memory im Steam-Proton-Präfix von ACC (`AppID 805550`) einzurichten.
2. Starte ACC, öffne dann **OpenSimWheel Linux**, wähle **ACC (Assetto Corsa Competizione)** und klicke auf **OK**.

### Assetto Corsa (AC), Assetto Corsa EVO (ACE) und RaceRoom (RRRE)
1. Stelle sicher, dass jedes Spiel mindestens einmal über Steam gestartet wurde, damit das Proton-Präfix erstellt wird (`AppID 244210` für AC, `3058630` für ACE, `211500` für RRRE).
2. Führe einmalig **`./setup_ac_proton.sh, setup_ace_proton.sh, setup_rrre_proton.sh`** aus (oder wähle **AC**, **ACE** und **RRRE** während der Installation), um die Proton-Shared-Memory-Bridges einzurichten.
3. Starte den Simulator, öffne **OpenSimWheel Linux**, wähle **AC**, **ACE** oder **RRRE** und klicke auf **OK**.

### Project Motor Racing (PMR)
1. Aktiviere die UDP-Telemetrieausgabe in den Einstellungen von PMR auf Port **`7576`** (oder `5606`).
2. Starte **OpenSimWheel Linux**, wähle **PMR (Project Motor Racing)** und klicke auf **OK**.

## 3. Web Live Dash & PitWall Timing
- Während die Bridge läuft, öffne im Browser deines PCs, Tablets oder Smartphones **`http://<DEINE_PC_IP>:8080`** (z. B. `http://127.0.0.1:8080`).
