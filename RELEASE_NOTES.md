# OpenSimWheel Linux Bridge v1.3.0

## Italiano
### Novità e Miglioramenti
- **Configurazione centrale isolata (`osw_bridge.ini`):** Sezioni dedicate (`[SIM_PMR]`, `[SIM_LMU]`, `[SIM_ACC]`, `[SIM_AC]`, `[SIM_ACE]`, `[SIM_RRRE]`, `[SIM_RF2]`) con porte UDP dedicate per eliminare qualsiasi conflitto al cambio simulatore.
- **Script Proton dedicati:** Suddivisione in `setup_ac_proton.sh`, `setup_ace_proton.sh`, `setup_rrre_proton.sh` e `setup_acc_proton.sh`.
- **Protezione Auto-Riparante (Self-Healing):** Ripristino automatico di `osw_bridge.ini`, rimozione dei file `stop*.flag` residui e rigenerazione automatica di `drive_c/osw_shm` nei prefissi Steam prima di ogni connessione.
- **Supporto nativo Assetto Corsa EVO (`ACE`):** Lettura della nuova Shared Memory `Local\acevo_pmf_*`, rilevamento automatico del limitatore reale dell'auto e sincronizzazione marce sul Thrustmaster SF1000.
- **Supporto completo RaceRoom (`RRRE` v3.6):** Allineamento agli offset aggiornati di `Local\$R3E`, protezione `NaN`/`Inf` e pacchetto binario `R3EM` da 84 byte.
- **Stabilità Thrustmaster SF1000 e Proton:** Rate ottimizzato a 40 Hz anti-balbuzie Wi-Fi, protezione istanza singola, rilascio automatico `mmap` al ritorno ai box/menu e chiusura pulita dei processi.

---

## English
### What's New & Improvements
- **Isolated Central Configuration (`osw_bridge.ini`):** Dedicated sections (`[SIM_PMR]`, `[SIM_LMU]`, `[SIM_ACC]`, `[SIM_AC]`, `[SIM_ACE]`, `[SIM_RRRE]`, `[SIM_RF2]`) with exclusive UDP ports to prevent any cross-simulator interference.
- **Independent Proton Setup Scripts:** Split into `setup_ac_proton.sh`, `setup_ace_proton.sh`, `setup_rrre_proton.sh`, and `setup_acc_proton.sh`.
- **Self-Healing Protection:** Automatically restores `osw_bridge.ini`, cleans up stale `stop*.flag` files, and rebuilds `drive_c/osw_shm` inside Steam Proton prefixes on startup if missing.
- **Native Assetto Corsa EVO (`ACE`) Support:** Reads the new `Local\acevo_pmf_*` Shared Memory, dynamically detects the car's real rev-limiter, and aligns gears on the Thrustmaster SF1000.
- **Full RaceRoom (`RRRE` v3.6) Support:** Updated `Local\$R3E` memory offsets, `NaN`/`Inf` safety guards, and 84-byte `R3EM` binary packet alignment.
- **Thrustmaster SF1000 & Proton Stability:** Optimized 40 Hz rate to eliminate Wi-Fi display stutter, single-instance lock, automatic `mmap` release when returning to menus, and clean process shutdown.
