# Changelog - OpenSimWheel Linux Bridge

## v1.4.0 (2026-11-17)
### Novità principali / Key Features
- **Web Live Dash & Temperature Gomme IMO:** Supporto alle temperature gomme a 3 settori (**Inner / Middle / Outer**) con orientamento speculare reale tra lato sinistro (`FL/RL`) e destro (`FR/RR`), gradiente colore dinamico continuo (HSL), filtro anti-sfarfallio EMA e rilevamento automatico `has_imo`.
- **PitWall Timing & Settore 3 (`S3`):** Calcolo automatico e stabile del terzo settore (`S3`) su tutti i simulatori supportati, con layout ottimizzato anche per iPad e browser mobile (`100dvh` e fetch anti-accavallamento).
- **ACC Shared Memory Completo (`acpmf_physics`):** Estesa la lettura della memoria condivisa a 512 byte per estrarre anche il **Brake Bias** reale e i 3 settori **IMO** delle gomme.
- **Fix Le Mans Ultimate (`LMU`) & rFactor 2 (`rF2`):** Risolto un errore sulla lettura delle bandiere di settore REST in LMU, aggiunto il calcolo stabile di `S3` e migliorata la gestione di `tyre_press` e `tyre_wear` al cambio simulatore.
- **Installer, Uninstaller & Documentazione Multilingua:** Aggiornati `installer.sh`, `uninstaller.sh` (con supporto grafico Zenity e flag `--purge`) e allineate tutte e 5 le guide utente (`IT`, `EN`, `DE`, `FR`, `ES`).

---

## v1.3.0 (2026-11-16)
### Novità principali / Key Features
- **Configurazione centrale isolata (`osw_bridge.ini`):** Sezioni dedicate (`[SIM_PMR]`, `[SIM_LMU]`, `[SIM_ACC]`, `[SIM_AC]`, `[SIM_ACE]`, `[SIM_RRRE]`, `[SIM_RF2]`) con porte UDP esclusive per evitare qualsiasi interferenza al cambio simulatore.
- **Script Proton indipendenti:** Suddivisione in `setup_ac_proton.sh`, `setup_ace_proton.sh`, `setup_rrre_proton.sh` e `setup_acc_proton.sh`.
- **Auto-riparazione all'avvio (`_auto_ripara_prefisso_proton`):** Ripristino automatico di `osw_bridge.ini`, pulizia dei file `stop*.flag` residui e rigenerazione automatica di `drive_c/osw_shm` nei prefissi Steam.
- **Assetto Corsa EVO (`ACE`):** Supporto nativo per la nuova memoria condivisa `Local\acevo_pmf_*`, lettura dinamica del limitatore reale (`Offset 204` float) e allineamento marce sul Thrustmaster SF1000.
- **RaceRoom Racing Experience (`RRRE` v3.6):** Allineamento agli offset aggiornati di `Local\$R3E` (`1392` speed, `1396` rps, `1408` gear), protezione `NaN`/`Inf` tramite `math.isfinite()` e pacchetto binario `R3EM` da 84 byte.
- **Stabilità Wi-Fi Thrustmaster SF1000 e Proton:** Frequenza ottimizzata a 40 Hz (`0.025s`) con protezione istanza singola anti-balbuzie sul display Wi-Fi, rilascio automatico `mmap` al ritorno ai box/menu e chiusura pulita dei processi senza `SIGKILL`.

