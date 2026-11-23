# Guida Utente — OpenSimWheel Linux Bridge v1.4.0

Bridge nativo Linux ottimizzato a **40Hz** (anti-balbuzie Wi-Fi) per **rFactor 2 (rF2)**, **Le Mans Ultimate (LMU)**, **Assetto Corsa Competizione (ACC)**, **Assetto Corsa (AC)**, **Assetto Corsa EVO (ACE)**, **RaceRoom Racing Experience (RRRE)** e **Project Motor Racing (PMR)**.

Invia telemetria in tempo reale (**giri motore, LED di cambiata, marce, velocità, carburante e giri rimanenti, TC, ABS, ripartizione frenata/Bias, bandiere FIA, temperature gomme/IMO, pressioni, usura e tempi sul giro/settori**) a:
- **Qualsiasi volante con display Wi-Fi/UDP o schermo DDU** compatibile con lo standard UDP F1 2020/2023 (`porta 20777` — incluso Thrustmaster SF1000, volanti custom ESP32/VoCore e app per smartphone/tablet come SimHub, SimDashboard, DashPanel, RS Dash).
- **Web Live Dash + PitWall Timing integrati** (`porta 8080`), accessibili dal browser di qualsiasi PC, tablet o smartphone senza hardware aggiuntivo.

## 1. Installazione e Disinstallazione
1. Esegui **`./installer.sh`** da terminale (oppure fai doppio clic su **`Installa_OpenSimWheel.desktop`**).
2. Seleziona i simulatori installati: per **rF2** e **LMU** l'installer abilita automaticamente la lettura nativa della RAM (`kernel.yama.ptrace_scope = 0`) senza richiedere alcun plugin esterno.
3. Il programma viene installato in `~/.local/share/OpenSimWheel`, crea il file centrale `~/.config/OpenSimWheel/osw_bridge.ini` e aggiunge l'icona **OpenSimWheel Linux** nel menu applicazioni e sul Desktop.
4. Per disinstallare mantenendo le impostazioni esegui `~/.local/share/OpenSimWheel/uninstaller.sh` (oppure `./uninstaller.sh --purge` per rimuovere anche `~/.config/OpenSimWheel`).

## 2. Configurazione per Simulatore

### rFactor 2 (rF2) e Le Mans Ultimate (LMU) — 100% Nativo (Zero Plugin)
1. **Nessun plugin richiesto:** Non copiare alcuna `.dll` nella cartella `Plugins/` del gioco (evita crash su Proton 9.0 / GE-Proton). Il Bridge legge motore, marce e dati IMO/usura/pressione delle 4 ruote direttamente tramite API REST nativa (`5397` / `6397`) e scansione RAM Linux.
2. Nelle **Proprietà su Steam**:
   - In **Compatibilità**, seleziona **`Proton 9.0`** o **`Proton Experimental`** per rF2, e **`GE-Proton`** / **`Proton Experimental`** per LMU.
   - In **Controller**, imposta **Disattiva Steam Input**.
3. Nel menu **Controls -> Force Feedback** del gioco, attiva **Invert Force Feedback** se usi un volante Thrustmaster.
4. Avvia il gioco, apri **OpenSimWheel Linux**, seleziona **RF2** o **LMU** e premi **OK**.

### Assetto Corsa Competizione (ACC)
1. Avvia almeno una volta ACC su Steam per inizializzare il prefisso Proton (`AppID 805550`).
2. Esegui una sola volta **`./scripts/setup_acc_proton.sh`** (oppure seleziona **ACC** durante l'installazione) per configurare la lettura della Shared Memory nel prefisso Steam Proton (porte `9000`/`9001`).
3. Avvia ACC, apri **OpenSimWheel Linux**, seleziona **ACC (Assetto Corsa Competizione)** e premi **OK**.

### Assetto Corsa (AC)
1. Avvia almeno una volta il gioco su Steam per creare il prefisso Proton (`AppID 244210`).
2. Esegui una sola volta **`./scripts/setup_ac_proton.sh`** (porta interna `9003`, con rilascio automatico della memoria al ritorno al menu).
3. Avvia AC, apri **OpenSimWheel Linux**, seleziona **AC (Assetto Corsa)** e premi **OK**.

### Assetto Corsa EVO (ACE)
1. Avvia almeno una volta il gioco su Steam per creare il prefisso Proton (`AppID 3058630`).
2. Esegui una sola volta **`./scripts/setup_ace_proton.sh`** (porta interna `9005`, lettura nativa `Local\acevo_pmf_*` con rilevamento automatico del limitatore motore reale).
3. Avvia ACE, apri **OpenSimWheel Linux**, seleziona **ACE (Assetto Corsa EVO)** e premi **OK**.

### RaceRoom Racing Experience (RRRE)
1. Avvia almeno una volta il gioco su Steam per creare il prefisso Proton (`AppID 211500`).
2. Esegui una sola volta **`./scripts/setup_rrre_proton.sh`** (porta interna `9007`, lettura nativa `Local\$R3E`).
3. **Consigli per volanti su Linux:**
   - Nelle **Proprietà di RaceRoom su Steam -> Controller**, imposta **Disattiva Steam Input** e nelle **Opzioni di avvio** usa `SDL_JOYSTICK_HIDAPI=1 PROTON_ENABLE_HIDRAW=1 %command%`.
4. Avvia RaceRoom, apri **OpenSimWheel Linux**, seleziona **RRRE (RaceRoom)** e premi **OK**.

### Project Motor Racing (PMR)
1. Attiva l'uscita telemetria UDP nelle impostazioni di PMR sulla porta **`7576`** (o `5606`).
2. Avvia **OpenSimWheel Linux**, seleziona **PMR (Project Motor Racing)** e premi **OK**.

## 3. Auto-Sniffer di Rete, Configurazione Centrale e Web Live Dash
- **Auto-Sniffer:** All'avvio, OpenSimWheel rileva automaticamente l'IP locale del tuo PC e scansiona la rete domestica per trovare volanti con display UDP o tablet compatibili.
- **Configurazione Centrale (`osw_bridge.ini`):** Tutte le porte e i parametri auto-riparanti sono salvati in `~/.config/OpenSimWheel/osw_bridge.ini` (`[SIM_RF2]`, `[SIM_LMU]`, `[SIM_ACC]`, `[SIM_AC]`, `[SIM_ACE]`, `[SIM_RRRE]`, `[SIM_PMR]`).
- **Web Live Dash (`http://<IP_DEL_TUO_PC>:8080`):** Mostra LED di cambiata, marcia, velocità, TC, ABS, ripartizione frenata, bandiere FIA attive, consumo carburante e temperature gomme (commutabile tra **MEDIA** e **IMO**).
- **PitWall Timing (`http://<IP_DEL_TUO_PC>:8080/timing`):** Schermata a tutto schermo con posizione, giro, tempi attuale/ultimo/migliore e tutti e 3 i settori (`S1 / S2 / S3`), ottimizzata per tablet e iPad.

## Ottimizzazione Opzionale Kernel (Shared Memory & IPC Proton)

Durante l'installazione (`./installer.sh`), viene chiesto se applicare un profilo opzionale per la memoria condivisa del kernel (`/etc/sysctl.d/99-opensimwheel-shm.conf`):
- `kernel.shmmax = 2147483648` e `kernel.shmall = 524288`: garantiscono buffer `/dev/shm` sufficienti per la telemetria ad alta frequenza (100Hz).
- `kernel.yama.ptrace_scope = 0`: consente ai bridge esterni di leggere la memoria condivisa esposta dai processi Wine/Proton sulle distribuzioni con restrizioni IPC attive (es. Ubuntu/Debian).

> **Nota:** Se utilizzi già un kernel ottimizzato per il gaming (es. CachyOS, Liquorix) o preferisci non modificare `sysctl`, puoi scegliere **No** in sicurezza. Se attivato, `./uninstaller.sh` rimuove automaticamente `/etc/sysctl.d/99-opensimwheel-shm.conf`.
