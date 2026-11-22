# Benutzerhandbuch — OpenSimWheel Linux Bridge v1.4.0

Native 100Hz-Telemetrie-Bridge unter Linux für **Le Mans Ultimate (LMU)**, **rFactor 2 (rF2)**, **Assetto Corsa Competizione (ACC)**, **Assetto Corsa (AC)**, **Assetto Corsa EVO (ACE)**, **RaceRoom Racing Experience (RRRE)** und **Project Motor Racing (PMR)**.

Sendet Echtzeit-Telemetrie (**Drehzahl, Schalt-LEDs, Gänge, Geschwindigkeit, Kraftstoff & verbleibende Runden, TC, ABS, Bremsbalance/Bias, FIA-Flaggen, Reifentemperaturen/IMO, Reifendruck, Verschleiß sowie Runden- und Sektorzeiten**) an:
- **Jedes WLAN-/UDP-Display-Lenkrad oder DDU-Display** nach dem F1-2020/2023-UDP-Standard (`Port 20777` — z. B. Thrustmaster SF1000, eigene ESP32/VoCore-Displays sowie Smartphone-/Tablet-Apps wie SimHub, SimDashboard, DashPanel, RS Dash).
- **Integriertes Web Live Dash + PitWall Timing** (`Port 8080`), direkt im Browser auf PC, Tablet oder Smartphone nutzbar — ganz ohne zusätzliche Hardware.

## 1. Installation
1. Doppelklicke auf **`Installa_OpenSimWheel.desktop`** (oder führe `./core/installer.sh` im Terminal aus).
2. Wähle im Auswahlfenster die auf deinem PC installierten Simulatoren aus, um deren Proton-Bridges automatisch einzurichten.
3. Das Programm wird unter `~/.local/share/OpenSimWheel` installiert und erstellt die Verknüpfung **OpenSimWheel Linux** im Anwendungsmenü und auf dem Desktop.
4. Zur Deinstallation führe `~/.local/share/OpenSimWheel/uninstaller.sh` aus (mit `--purge` werden auch gespeicherte Konfigurationen gelöscht).

## 2. Einrichtung nach Simulator

### Le Mans Ultimate (LMU) & rFactor 2 (rF2) — Ohne externe DLLs
1. **Kein Plugin erforderlich:** OpenSimWheel liest Motordaten, Gänge und alle 4 Räder (IMO-Temperaturen, Druck, Verschleiß) direkt nativ aus dem Prozessspeicher sowie über die lokale REST-API (`Port 6397` für LMU, `Port 5397` für rF2).
2. In den **Steam-Eigenschaften**:
   - Unter **Kompatibilität** eine kompatible Proton-Version wählen (z. B. **`GE-Proton`** oder **`Proton Experimental`**).
   - Unter **Controller** **Steam-Eingabe deaktivieren** wählen (verhindert doppelte Eingaben und zufällige Gangwechsel).
3. Starte den Simulator, öffne anschließend **OpenSimWheel Linux**, wähle **LMU** oder **rF2** und klicke auf **OK**.

### Assetto Corsa Competizione (ACC)
1. Stelle sicher, dass ACC mindestens einmal über Steam gestartet wurde (`AppID 805550`).
2. Führe einmalig **`./setup_acc_proton.sh`** aus (oder wähle **ACC** während der Installation), um die Shared-Memory-Bridge im Steam-Proton-Präfix einzurichten.
3. Starte ACC, öffne dann **OpenSimWheel Linux**, wähle **ACC (Assetto Corsa Competizione)** und klicke auf **OK**.

### Assetto Corsa (AC), Assetto Corsa EVO (ACE) und RaceRoom (RRRE)
1. Stelle sicher, dass jedes Spiel mindestens einmal über Steam gestartet wurde (`AppID 244210` für AC, `3058630` für ACE, `211500` für RRRE).
2. Führe einmalig **`./setup_ac_proton.sh`**, **`./setup_ace_proton.sh`** bzw. **`./setup_rrre_proton.sh`** aus (oder wähle sie während der Installation).
3. Starte den Simulator, öffne **OpenSimWheel Linux**, wähle **AC**, **ACE** oder **RRRE** und klicke auf **OK**.

### Project Motor Racing (PMR)
1. Aktiviere die UDP-Telemetrieausgabe in den Einstellungen von PMR auf Port **`7576`** (oder `5606`).
2. Starte **OpenSimWheel Linux**, wähle **PMR (Project Motor Racing)** und klicke auf **OK**.

## 3. Automatische Netzwerkerkennung & Web Live Dash
- **Auto-Sniffer:** Beim Start erkennt OpenSimWheel automatisch die lokale IP-Adresse deines PCs sowie kompatible WLAN-Displays im Heimnetzwerk.
- **Web Live Dash (`http://<DEINE_PC_IP>:8080`):** Zeigt Drehzahl-LEDs, Gang, Geschwindigkeit, TC, ABS, Bremsbalance, Flaggen-Status, Kraftstoffverbrauch und Reifentemperaturen (umschaltbar zwischen **MEDIA** und **IMO**).
- **PitWall Timing (`http://<DEINE_PC_IP>:8080/timing`):** Vollbild-Zeitnahme mit Position, Runde, aktueller/letzter/bester Rundenzeit und allen 3 Sektoren (`S1 / S2 / S3`), optimiert für Tablets und iPads.
