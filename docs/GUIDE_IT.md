# Guida Utente — OpenSimWheel Linux Bridge v1.3.0

Bridge nativo Linux ottimizzato a **40Hz** (anti-balbuzie Wi-Fi) per **Le Mans Ultimate (LMU)**, **Assetto Corsa Competizione (ACC)**, **Assetto Corsa (AC)**, **Assetto Corsa EVO (ACE)**, **RaceRoom Racing Experience (RRRE)** e **Project Motor Racing (PMR)**.
Invia telemetria in tempo reale (giri motore, LED di cambiata, marce, velocità, carburante, temperature gomme e tempi sul giro) a **Thrustmaster SF1000 (Direct Wi-Fi / Native)**, display DDU UDP (`porta 20777`) e **Web Live Dash + PitWall Timing** (`porta 8080`).

## 1. Installazione e Disinstallazione
1. Esegui **`./install.sh`** da terminale (oppure fai doppio clic su **`Installa_OpenSimWheel.desktop`**).
2. Il programma viene installato in `~/.local/share/OpenSimWheel`, crea il file centrale `~/.config/OpenSimWheel/osw_bridge.ini` e aggiunge l'icona **OpenSimWheel Linux Bridge** nel menu applicazioni.
3. Per disinstallare il programma mantenendo le impostazioni, esegui `./core/uninstaller.sh`.
4. Per rimuovere completamente anche la configurazione (`~/.config/OpenSimWheel`), esegui `./core/uninstaller.sh --purge`.

## 2. Configurazione per Simulatore

### Le Mans Ultimate (LMU)
1. Scarica **`rFactor2SharedMemoryMapPlugin64.dll`** (dal pacchetto *rF2 Shared Memory Map Plugin* / *TinyPedal*) e copiala in `Le Mans Ultimate/Plugins/` (oppure lasciala in `~/Scaricati` prima del passaggio successivo).
2. Esegui una sola volta **`./setup_lmu_plugin.sh`** dalla cartella del progetto: lo script copierà la DLL e abiliterà automaticamente il plugin in `UserData/player/CustomPluginVariables.JSON`.
3. Nelle **Proprietà di Le Mans Ultimate su Steam**:
   - In **Compatibilità**, seleziona una versione Proton compatibile (es. **`Proton Experimental`** o **`GE-Proton`**).
   - In **Controller**, imposta **Disattiva Steam Input**.
4. Nel menu **Controls -> Force Feedback** del gioco, attiva **Invert Force Feedback** se usi un volante Thrustmaster.
5. Avvia LMU, poi apri **OpenSimWheel Linux Bridge**, seleziona **LMU (Le Mans Ultimate)** e premi **OK**.

### Assetto Corsa Competizione (ACC)
1. Esegui una sola volta **`./setup_acc_proton.sh`** per configurare la lettura della Shared Memory nel prefisso Steam Proton di ACC (`AppID 805550`, porta interna `9000`).
2. Avvia ACC, poi apri **OpenSimWheel Linux Bridge**, seleziona **ACC (Assetto Corsa Competizione)** e premi **OK**.

### Assetto Corsa (AC)
1. Avvia almeno una volta il gioco su Steam per creare il prefisso Proton (`AppID 244210`).
2. Esegui una sola volta **`./setup_ac_proton.sh`** (porta interna `9003`, con rilascio automatico della memoria al ritorno al menu).
3. Avvia AC, entra in pista, apri **OpenSimWheel Linux Bridge**, seleziona **AC (Assetto Corsa)** e premi **OK**.

### Assetto Corsa EVO (ACE)
1. Avvia almeno una volta il gioco su Steam per creare il prefisso Proton (`AppID 3058630`).
2. Esegui una sola volta **`./setup_ace_proton.sh`** (porta interna `9005`, lettura nativa `Local\acevo_pmf_*` con rilevamento automatico del limitatore motore reale).
3. Avvia ACE, entra nell'abitacolo, apri **OpenSimWheel Linux Bridge**, seleziona **ACE (Assetto Corsa EVO)** e premi **OK**.

### RaceRoom Racing Experience (RRRE)
1. Avvia almeno una volta il gioco su Steam per creare il prefisso Proton (`AppID 211500`).
2. Esegui una sola volta **`./setup_rrre_proton.sh`** (porta interna `9007`, lettura nativa `Local\$R3E`).
3. **Consigli per volanti Thrustmaster su Linux:**
   - Nelle **Proprietà di RaceRoom su Steam -> Controller**, imposta **Disattiva Steam Input** e nelle **Opzioni di avvio** usa `SDL_JOYSTICK_HIDAPI=1 PROTON_ENABLE_HIDRAW=1 %command%`.
   - Se la pedaliera USB viene rilevata prima del volante (`js0`), duplica il profilo `Keyboard` dentro **Opzioni -> Controlli**, riassegna manualmente **Sterzo Sinistra/Destra** sul volante e attiva **Inverti Force Feedback** se necessario.
4. Avvia RaceRoom, entra in pista, apri **OpenSimWheel Linux Bridge**, seleziona **RRRE (RaceRoom)** e premi **OK**.

### Project Motor Racing (PMR)
1. Attiva l'uscita telemetria UDP nelle impostazioni di PMR sulla porta **`7576`** (o `5606`).
2. Avvia **OpenSimWheel Linux Bridge**, seleziona **PMR (Project Motor Racing)** e premi **OK**.

## 3. Configurazione Centrale (`osw_bridge.ini`) e Auto-Riparazione
- Tutte le porte e i parametri dei simulatori sono isolati in **`~/.config/OpenSimWheel/osw_bridge.ini`** (`[SIM_PMR]`, `[SIM_LMU]`, `[SIM_ACC]`, `[SIM_AC]`, `[SIM_ACE]`, `[SIM_RRRE]`).
- **Protezione anti-eliminazione (Self-Healing):** A ogni avvio, il Bridge verifica automaticamente l'integrità di `osw_bridge.ini` e della cartella `drive_c/osw_shm` nel prefisso Steam del gioco selezionato, ripristinando eventuali file mancanti prima di connettersi.

## 4. Web Live Dash & PitWall Timing
- Mentre il Bridge è attivo, apri dal browser del PC, tablet o smartphone **`http://<IP_DEL_TUO_PC>:8080`** (es. `http://127.0.0.1:8080`).
