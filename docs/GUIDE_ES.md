# Guía de Usuario — OpenSimWheel Linux Bridge v1.4.0

Puente de telemetría nativo de Linux optimizado a **40Hz** (anti-tartamudeo Wi-Fi) para **rFactor 2 (rF2)**, **Le Mans Ultimate (LMU)**, **Assetto Corsa Competizione (ACC)**, **Assetto Corsa (AC)**, **Assetto Corsa EVO (ACE)**, **RaceRoom Racing Experience (RRRE)** y **Project Motor Racing (PMR)**.

Envía telemetría en tiempo real (**RPM, LED de cambio, marchas, velocidad, combustible y vueltas restantes, TC, ABS, reparto de frenada/Bias, banderas FIA, temperaturas de neumáticos/IMO, presiones, desgaste y tiempos por vuelta/sector**) a:
- **Cualquier volante con pantalla Wi-Fi/UDP o pantalla DDU** compatible con el estándar UDP F1 2020/2023 (`puerto 20777` — incluyendo Thrustmaster SF1000, volantes custom ESP32/VoCore y apps para móvil/tablet como SimHub, SimDashboard, DashPanel, RS Dash).
- **Web Live Dash + PitWall Timing integrados** (`puerto 8080`), accesibles desde el navegador de cualquier PC, tablet o smartphone sin hardware adicional.

## 1. Instalación y Desinstalación
1. Ejecuta **`./install.sh`** en la terminal (o haz doble clic en **`Installa_OpenSimWheel.desktop`**).
2. Selecciona los simuladores instalados en tu PC: para **rF2** y **LMU**, el instalador habilita automáticamente la lectura nativa de RAM en Linux (`kernel.yama.ptrace_scope = 0`) sin necesidad de plugins DLL externos.
3. El programa se instala en `~/.local/share/OpenSimWheel`, crea `~/.config/OpenSimWheel/osw_bridge.ini` y añade **OpenSimWheel Linux** a tu menú de aplicaciones y al Escritorio.
4. Para desinstalar conservando la configuración ejecuta `~/.local/share/OpenSimWheel/uninstaller.sh` (o `./uninstaller.sh --purge` para borrar también `~/.config/OpenSimWheel`).

## 2. Configuración por Simulador

### rFactor 2 (rF2) y Le Mans Ultimate (LMU) — 100% Nativo (Sin Plugins)
1. **No se requieren plugins externos:** No copies ningún archivo `.dll` en la carpeta `Plugins/` del juego (evita cierres al iniciar en Proton 9.0 / GE-Proton). El Bridge lee motor, marchas y datos IMO/desgaste/presión de las 4 ruedas directamente mediante API REST nativa (`5397` / `6397`) y escaneo de RAM en Linux.
2. En las **Propiedades en Steam**:
   - En **Compatibilidad**, selecciona **`Proton 9.0`** o **`Proton Experimental`** para rF2, y **`GE-Proton`** / **`Proton Experimental`** para LMU.
   - En **Mando**, selecciona **Desactivar Steam Input** (evita entradas duplicadas y cambios de marcha aleatorios).
3. En el menú del juego **Controls -> Force Feedback**, activa **Invert Force Feedback** si usas un volante Thrustmaster.
4. Inicia el juego, abre **OpenSimWheel Linux**, selecciona **RF2** o **LMU** y pulsa **OK**.

### Assetto Corsa Competizione (ACC)
1. Inicia ACC al menos una vez en Steam para crear su prefijo Proton (`AppID 805550`).
2. Ejecuta una sola vez **`./setup_acc_proton.sh`** (o selecciona **ACC** durante la instalación) para configurar la lectura de memoria compartida en el prefijo Proton (puertos `9000`/`9001`).
3. Inicia ACC, abre **OpenSimWheel Linux**, selecciona **ACC (Assetto Corsa Competizione)** y pulsa **OK**.

### Assetto Corsa (AC), Assetto Corsa EVO (ACE) y RaceRoom (RRRE)
1. Asegúrate de haber iniciado cada juego al menos una vez en Steam para inicializar su prefijo Proton (`AppID 244210` para AC, `3058630` para ACE, `211500` para RRRE).
2. Ejecuta una sola vez **`./setup_ac_proton.sh`**, **`./setup_ace_proton.sh`** o **`./setup_rrre_proton.sh`** (o selecciónalos durante la instalación).
3. **Consejo para volantes en RaceRoom:** En **Propiedades de Steam -> Mando**, desactiva Steam Input y añade en opciones de lanzamiento: `SDL_JOYSTICK_HIDAPI=1 PROTON_ENABLE_HIDRAW=1 %command%`.
4. Inicia el simulador, abre **OpenSimWheel Linux**, selecciona **AC**, **ACE** o **RRRE** y pulsa **OK**.

### Project Motor Racing (PMR)
1. Activa la salida de telemetría UDP en los ajustes de PMR en el puerto **`7576`** (o `5606`).
2. Abre **OpenSimWheel Linux**, selecciona **PMR (Project Motor Racing)** y pulsa **OK**.

## 3. Auto-Sniffer de Red, Configuración Central y Web Live Dash
- **Auto-Sniffer:** Al iniciar, OpenSimWheel detecta automáticamente la IP local de tu PC y escanea la red doméstica en busca de volantes con pantalla UDP o tablets compatibles.
- **Configuración Central (`osw_bridge.ini`):** Todos los puertos y ajustes auto-reparables se guardan en `~/.config/OpenSimWheel/osw_bridge.ini` (`[SIM_RF2]`, `[SIM_LMU]`, `[SIM_ACC]`, `[SIM_AC]`, `[SIM_ACE]`, `[SIM_RRRE]`, `[SIM_PMR]`).
- **Web Live Dash (`http://<IP_DE_TU_PC>:8080`):** Muestra LED de cambio, marcha, velocidad, TC, ABS, reparto de frenada, banderas FIA activas, consumo de combustible y temperatura de neumáticos (conmutable entre **MEDIA** e **IMO**).
- **PitWall Timing (`http://<IP_DE_TU_PC>:8080/timing`):** Pantalla completa de cronometraje con posición, vuelta, tiempos actual/último/mejor y los 3 sectores (`S1 / S2 / S3`), optimizada para tablets y iPad.

