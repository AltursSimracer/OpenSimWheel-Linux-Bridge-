# OpenSimWheel Linux Bridge v1.4.0

## Italiano
### Novità e Miglioramenti
- **Compatibilità Universale & Auto-Sniffer di Rete:** Funziona con **qualsiasi volante con display Wi-Fi/UDP** (standard F1 2020, incluso Thrustmaster SF1000), app dashboard su smartphone/tablet e **Web Live Dash + PitWall Timing** (`porta 8080`). Rilevamento automatico dell'IP locale del PC, scansione della rete per trovare il display e auto-riparazione dei file di configurazione.
- **Telemetria Unificata (TC, ABS, Brake Bias, Bandiere & Fuel):** Allineamento completo dei parametri di assetto ed elettronica in tempo reale sia sui pacchetti UDP per il volante che sulla Web Live Dash su tutti e 7 i simulatori (**PMR, LMU, rF2, ACC, AC, ACE, RRRE**), incluso il reset automatico del consumo carburante dopo i pit-stop.
- **Web Live Dash & Temperature Gomme IMO:** Supporto alle temperature gomme a 3 settori (**Inner / Middle / Outer**) con orientamento speculare reale, gradiente colore dinamico, filtro anti-sfarfallio EMA e PitWall Timing (`/timing`) ottimizzato per tablet/iPad.
- **Configurazione centrale isolata (`osw_bridge.ini`) & Script Proton dedicati:** Sezioni separate per ogni simulatore, installer/uninstaller multilingua con Zenity e script Proton auto-riparanti (`setup_ac_proton.sh`, `setup_ace_proton.sh`, `setup_rrre_proton.sh`, `setup_acc_proton.sh`).

---

## English
### What's New & Improvements
- **Universal Display Compatibility & Smart Network Sniffer:** Works with **any Wi-Fi/UDP display steering wheel** (F1 2020 UDP standard, including Thrustmaster SF1000), mobile/tablet dashboard apps, and the built-in **Web Live Dash + PitWall Timing** (`port 8080`). Automatically detects your PC's LAN IP, scans for active UDP displays, and self-heals `config.ini`.
- **Unified Telemetry (TC, ABS, Brake Bias, FIA Flags & Fuel):** Real-time Traction Control, ABS, Brake Bias, FIA Flags, and pit-stop-aware Fuel consumption are now mapped consistently to both hardware UDP packets and the Web Live Dash across all 7 supported sims (**PMR, LMU, rF2, ACC, AC, ACE, RRRE**).
- **Web Live Dash & 3-Zone IMO Tyre Temps:** Inner/Middle/Outer tyre temperature visualization with mirrored left/right layout, smooth HSL color gradients, EMA anti-flicker filtering, and mobile/iPad-ready PitWall Timing (`/timing`).
- **Isolated Configuration (`osw_bridge.ini`) & Self-Healing Proton Bridges:** Dedicated per-sim sections, multilingual Zenity installer/uninstaller, and resilient Proton Shared Memory setup scripts (`setup_ac_proton.sh`, `setup_ace_proton.sh`, `setup_rrre_proton.sh`, `setup_acc_proton.sh`).
