#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_PKG="$SCRIPT_DIR"

INSTALL_DIR="$HOME/.local/share/OpenSimWheel"
CONFIG_DIR="$HOME/.config/OpenSimWheel"
APP_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
BACKUP_DIR="$INSTALL_DIR/backup_config_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$APP_DIR"

# 1. Auto-backup dei file .ini esistenti prima dell'aggiornamento
if ls "$INSTALL_DIR"/*.ini >/dev/null 2>&1; then
    mkdir -p "$BACKUP_DIR"
    cp "$INSTALL_DIR"/*.ini "$BACKUP_DIR/"
    echo "[INFO] Backup configurazioni precedenti salvato in $BACKUP_DIR"
fi

# 2. Copia file core e configurazione centrale osw_bridge.ini
mkdir -p "$INSTALL_DIR/logs"
cp -r "$SCRIPT_DIR"/OpenSimWheel_Linux_Bridge.py "$SCRIPT_DIR"/uninstaller.sh "$SCRIPT_DIR"/*.ini "$SCRIPT_DIR"/LICENSE.txt "$SCRIPT_DIR"/bridges "$SCRIPT_DIR"/web "$SCRIPT_DIR"/scripts "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/OpenSimWheel_Linux_Bridge.py"
[ -f "$INSTALL_DIR/uninstaller.sh" ] && chmod +x "$INSTALL_DIR/uninstaller.sh"
chmod +x "$INSTALL_DIR"/scripts/*.sh 2>/dev/null || true
chmod +x "$INSTALL_DIR"/bridges/*.py 2>/dev/null || true

if [ -f "$ROOT_PKG/osw_bridge.ini" ] && [ ! -f "$CONFIG_DIR/osw_bridge.ini" ]; then
    cp "$ROOT_PKG/osw_bridge.ini" "$CONFIG_DIR/osw_bridge.ini"
fi

# 3. Creazione voce menu e icona Desktop (v1.4.0 universale)
DESKTOP_FILE="$APP_DIR/opensimwheel-linux.desktop"
cat << EOD > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.4.0
Type=Application
Name=OpenSimWheel Linux
Comment=Universal Telemetry Bridge for Sim-Racing Wheels, Wi-Fi Displays & Web LiveDash
Exec=/usr/bin/env python3 "$INSTALL_DIR/OpenSimWheel_Linux_Bridge.py"
Path=$INSTALL_DIR
Icon=$INSTALL_DIR/web/zenity_simracing.png
Terminal=false
Categories=Game;Utility;
StartupNotify=true
EOD

chmod +x "$DESKTOP_FILE"
if [ -d "$DESKTOP_DIR" ]; then
    cp "$DESKTOP_FILE" "$DESKTOP_DIR/OpenSimWheel_Linux.desktop"
    chmod +x "$DESKTOP_DIR/OpenSimWheel_Linux.desktop"
    gio set "$DESKTOP_DIR/OpenSimWheel_Linux.desktop" metadata::trusted true 2>/dev/null || true
fi

update-desktop-database "$APP_DIR" 2>/dev/null || true
echo "[OK] OpenSimWheel Linux v1.4.0 installato in $INSTALL_DIR"

# 4. Configurazione Simulatori Proton & Ottimizzazione Kernel (Zenity 5 lingue + Fallback)
LANG_CODE="${LANG:0:2}"

apply_kernel_shm() {
    local USE_GUI="$1"
    local TMP_CONF
    TMP_CONF=$(mktemp)
    cat << 'EOF' > "$TMP_CONF"
# OpenSimWheel Linux Bridge - Shared Memory & IPC Telemetry Optimization
kernel.shmmax = 2147483648
kernel.shmall = 524288
kernel.yama.ptrace_scope = 0
EOF
    if [ "$USE_GUI" = "1" ] && command -v pkexec >/dev/null 2>&1; then
        pkexec bash -c "install -m 644 '$TMP_CONF' /etc/sysctl.d/99-opensimwheel-shm.conf && sysctl --system >/dev/null" || true
    else
        sudo install -m 644 "$TMP_CONF" /etc/sysctl.d/99-opensimwheel-shm.conf && sudo sysctl --system >/dev/null || true
    fi
    rm -f "$TMP_CONF"
}

if command -v zenity >/dev/null 2>&1; then
    case "$LANG_CODE" in
        it)
            TITLE="Configurazione Simulatori - OpenSimWheel v1.4.0"
            TEXT="Installazione completata!\n\n• LMU, rFactor 2 e PMR: pronti subito (100% nativi, zero plugin).\n• Seleziona i simulatori Proton da configurare automaticamente:"
            COL_SEL="Attiva"
            COL_SIM="Simulatore"
            COL_NOTE="Azione eseguita"
            NOTE_ACC="Configura Shared Memory in Steam Proton (AppID 805550)"
            NOTE_AC="Configura Shared Memory in Steam Proton (AppID 244210)"
            NOTE_ACE="Configura Shared Memory in Steam Proton (AppID 3058630)"
            NOTE_RRRE="Configura Shared Memory in Steam Proton (AppID 211500)"
            KERNEL_TITLE="Ottimizzazione Kernel (Opzionale) - OpenSimWheel"
            KERNEL_TEXT="Vuoi ottimizzare i parametri del kernel Linux (shmmax, shmall, ptrace_scope=0) per garantire l'accesso alla Shared Memory della telemetria tra Proton e i bridge?\n\n(Richiede password di amministratore. Puoi scegliere 'No' se usi già un kernel gaming o preferisci non modificare sysctl.)"
            KERNEL_OK="[OK] Parametri Kernel Shared Memory applicati (/etc/sysctl.d/99-opensimwheel-shm.conf)"
            ;;
        de)
            TITLE="Simulator-Einrichtung - OpenSimWheel v1.4.0"
            TEXT="Installation abgeschlossen!\n\n• LMU, rFactor 2 und PMR: Sofort einsatzbereit (100% nativ, ohne Plugins).\n• Wähle die Proton-Simulatoren für die automatische Einrichtung:"
            COL_SEL="Aktiv"
            COL_SIM="Simulator"
            COL_NOTE="Aktion"
            NOTE_ACC="Shared Memory in Steam Proton einrichten (AppID 805550)"
            NOTE_AC="Shared Memory in Steam Proton einrichten (AppID 244210)"
            NOTE_ACE="Shared Memory in Steam Proton einrichten (AppID 3058630)"
            NOTE_RRRE="Shared Memory in Steam Proton einrichten (AppID 211500)"
            KERNEL_TITLE="Kernel-Optimierung (Optional) - OpenSimWheel"
            KERNEL_TEXT="Möchtest du die Linux-Kernel-Parameter (shmmax, shmall, ptrace_scope=0) für den Shared-Memory-Zugriff zwischen Proton und den Telemetrie-Bridges optimieren?\n\n(Erfordert Administrator-Passwort. Wähle 'Nein', um sysctl unverändert zu lassen.)"
            KERNEL_OK="[OK] Kernel Shared-Memory-Parameter angewendet (/etc/sysctl.d/99-opensimwheel-shm.conf)"
            ;;
        fr)
            TITLE="Configuration Simulateurs - OpenSimWheel v1.4.0"
            TEXT="Installation terminée !\n\n• LMU, rFactor 2 et PMR : prêts immédiatement (100% natif, sans plugin).\n• Sélectionnez les simulateurs Proton à configurer automatiquement :"
            COL_SEL="Activer"
            COL_SIM="Simulateur"
            COL_NOTE="Action"
            NOTE_ACC="Configurer mémoire partagée Steam Proton (AppID 805550)"
            NOTE_AC="Configurer mémoire partagée Steam Proton (AppID 244210)"
            NOTE_ACE="Configurer mémoire partagée Steam Proton (AppID 3058630)"
            NOTE_RRRE="Configurer mémoire partagée Steam Proton (AppID 211500)"
            KERNEL_TITLE="Optimisation du Noyau (Optionnel) - OpenSimWheel"
            KERNEL_TEXT="Voulez-vous optimiser les paramètres du noyau Linux (shmmax, shmall, ptrace_scope=0) pour l'accès à la mémoire partagée entre Proton et les bridges de télémétrie ?\n\n(Mot de passe administrateur requis. Choisissez 'Non' pour ne pas modifier sysctl.)"
            KERNEL_OK="[OK] Paramètres noyau appliqués (/etc/sysctl.d/99-opensimwheel-shm.conf)"
            ;;
        es)
            TITLE="Configuración de Simuladores - OpenSimWheel v1.4.0"
            TEXT="¡Instalación completada!\n\n• LMU, rFactor 2 y PMR: listos de inmediato (100% nativos, sin plugins).\n• Selecciona los simuladores Proton a configurar automáticamente:"
            COL_SEL="Activar"
            COL_SIM="Simulador"
            COL_NOTE="Acción"
            NOTE_ACC="Configurar memoria compartida Steam Proton (AppID 805550)"
            NOTE_AC="Configurar memoria compartida Steam Proton (AppID 244210)"
            NOTE_ACE="Configurar memoria compartida Steam Proton (AppID 3058630)"
            NOTE_RRRE="Configurar memoria compartida Steam Proton (AppID 211500)"
            KERNEL_TITLE="Optimización del Kernel (Opcional) - OpenSimWheel"
            KERNEL_TEXT="¿Deseas optimizar los parámetros del kernel Linux (shmmax, shmall, ptrace_scope=0) para el acceso a la memoria compartida entre Proton y los bridges de telemetría?\n\n(Requiere contraseña de administrador. Elige 'No' si prefieres no modificar sysctl.)"
            KERNEL_OK="[OK] Parámetros del kernel aplicados (/etc/sysctl.d/99-opensimwheel-shm.conf)"
            ;;
        *)
            TITLE="Simulator Setup - OpenSimWheel v1.4.0"
            TEXT="Installation complete!\n\n• LMU, rFactor 2 & PMR: ready out-of-the-box (100% native, zero plugins).\n• Select the Proton simulators to configure automatically:"
            COL_SEL="Enable"
            COL_SIM="Simulator"
            COL_NOTE="Action"
            NOTE_ACC="Configure Steam Proton Shared Memory (AppID 805550)"
            NOTE_AC="Configure Steam Proton Shared Memory (AppID 244210)"
            NOTE_ACE="Configure Steam Proton Shared Memory (AppID 3058630)"
            NOTE_RRRE="Configure Steam Proton Shared Memory (AppID 211500)"
            KERNEL_TITLE="Kernel Optimization (Optional) - OpenSimWheel"
            KERNEL_TEXT="Do you want to optimize Linux kernel parameters (shmmax, shmall, ptrace_scope=0) to ensure telemetry Shared Memory access between Proton and the bridges?\n\n(Requires administrator password. Select 'No' if you already use a gaming kernel or prefer not to touch sysctl.)"
            KERNEL_OK="[OK] Kernel Shared Memory parameters applied (/etc/sysctl.d/99-opensimwheel-shm.conf)"
            ;;
    esac

    SCELTE=$(zenity --list --checklist \
        --title="$TITLE" \
        --text="$TEXT" \
        --width=700 --height=360 \
        --column="$COL_SEL" --column="$COL_SIM" --column="$COL_NOTE" \
        TRUE "ACC" "$NOTE_ACC" \
        TRUE "AC" "$NOTE_AC" \
        TRUE "ACE" "$NOTE_ACE" \
        TRUE "RRRE" "$NOTE_RRRE" 2>/dev/null || true)

     RISULTATI=""
    for SIM_ID in ACC AC ACE RRRE; do
        SCRIPT_NAME="setup_${SIM_ID,,}_proton.sh"
        if [[ "|$SCELTE|" == *"|$SIM_ID|"* ]] && [ -f "$ROOT_PKG/scripts/$SCRIPT_NAME" ]; then
            OUT_SIM=$(bash "$ROOT_PKG/scripts/$SCRIPT_NAME" </dev/null 2>&1 || true)
            RISULTATI="${RISULTATI}${OUT_SIM}\n\n"
        fi
    done

    # Scelta ottimizzazione Kernel Shared Memory (Sì / No)
    case "$LANG_CODE" in
        it)
            K_TITLE="Ottimizzazione Kernel (Opzionale)"
            K_TEXT="Vuoi ottimizzare i parametri del kernel Linux (shmmax, shmall, ptrace_scope=0) per garantire l'accesso alla Shared Memory della telemetria tra Proton e i bridge?\n\n(Richiede password di amministratore. Scegli 'No' se usi già un kernel gaming o non vuoi modificare sysctl.)"
            K_OK="[OK] Kernel Shared Memory ottimizzato (/etc/sysctl.d/99-opensimwheel-shm.conf)"
            ;;
        de)
            K_TITLE="Kernel-Optimierung (Optional)"
            K_TEXT="Möchtest du die Linux-Kernel-Parameter (shmmax, shmall, ptrace_scope=0) für den Shared-Memory-Zugriff zwischen Proton und den Telemetrie-Bridges optimieren?\n\n(Erfordert Administrator-Passwort. Wähle 'Nein', um sysctl unverändert zu lassen.)"
            K_OK="[OK] Kernel Shared Memory optimiert (/etc/sysctl.d/99-opensimwheel-shm.conf)"
            ;;
        fr)
            K_TITLE="Optimisation du Noyau (Optionnel)"
            K_TEXT="Voulez-vous optimiser les paramètres du noyau Linux (shmmax, shmall, ptrace_scope=0) pour l'accès à la mémoire partagée entre Proton et les bridges ?\n\n(Mot de passe administrateur requis. Choisissez 'Non' pour ne pas modifier sysctl.)"
            K_OK="[OK] Noyau Shared Memory optimisé (/etc/sysctl.d/99-opensimwheel-shm.conf)"
            ;;
        es)
            K_TITLE="Optimización del Kernel (Opcional)"
            K_TEXT="¿Deseas optimizar los parámetros del kernel Linux (shmmax, shmall, ptrace_scope=0) para el acceso a la memoria compartida entre Proton y los bridges?\n\n(Requiere contraseña de administrador. Elige 'No' si prefieres no modificar sysctl.)"
            K_OK="[OK] Kernel Shared Memory optimizado (/etc/sysctl.d/99-opensimwheel-shm.conf)"
            ;;
        *)
            K_TITLE="Kernel Optimization (Optional)"
            K_TEXT="Do you want to optimize Linux kernel parameters (shmmax, shmall, ptrace_scope=0) to ensure telemetry Shared Memory access between Proton and the bridges?\n\n(Requires administrator password. Select 'No' if you already use a gaming kernel or prefer not to touch sysctl.)"
            K_OK="[OK] Kernel Shared Memory optimized (/etc/sysctl.d/99-opensimwheel-shm.conf)"
            ;;
    esac

    if zenity --question --title="$K_TITLE" --width=540 --text="$K_TEXT" 2>/dev/null; then
        TMP_SHM=$(mktemp)
        printf "# OpenSimWheel Linux Bridge - Shared Memory\nkernel.shmmax = 2147483648\nkernel.shmall = 524288\nkernel.yama.ptrace_scope = 0\n" > "$TMP_SHM"
        if command -v pkexec >/dev/null 2>&1 && pkexec bash -c "install -m 644 '$TMP_SHM' /etc/sysctl.d/99-opensimwheel-shm.conf && sysctl --system >/dev/null"; then
            RISULTATI="${RISULTATI}${K_OK}\n\n"
        fi
        rm -f "$TMP_SHM"
    fi

    if [ -n "$RISULTATI" ]; then
        zenity --info --title="$TITLE" --width=580 --text="$RISULTATI" 2>/dev/null || true
    fi
else
    echo "[INFO] Zenity non trovato: configurazione automatica dei simulatori Proton trovati..."
    for SCRIPT_NAME in setup_acc_proton.sh setup_ac_proton.sh setup_ace_proton.sh setup_rrre_proton.sh; do
        [ -f "$ROOT_PKG/scripts/$SCRIPT_NAME" ] && bash "$ROOT_PKG/scripts/$SCRIPT_NAME" || true
    done

    echo ""
    read -r -p "Ottimizzare parametri kernel per Shared Memory (shmmax, shmall, ptrace_scope=0)? [s/N]: " OPT_KERNEL
    if [[ "$OPT_KERNEL" =~ ^[sSyY]$ ]]; then
        TMP_SHM=$(mktemp)
        printf "# OpenSimWheel Linux Bridge - Shared Memory\nkernel.shmmax = 2147483648\nkernel.shmall = 524288\nkernel.yama.ptrace_scope = 0\n" > "$TMP_SHM"
        sudo install -m 644 "$TMP_SHM" /etc/sysctl.d/99-opensimwheel-shm.conf && sudo sysctl --system >/dev/null
        rm -f "$TMP_SHM"
        echo "[OK] Parametri kernel applicati (/etc/sysctl.d/99-opensimwheel-shm.conf)"
    fi
fi
