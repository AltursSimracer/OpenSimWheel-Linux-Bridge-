# Guía de Usuario — OpenSimWheel Linux Bridge v1.3.0

Puente de telemetría nativo de Linux a 100Hz para **Le Mans Ultimate (LMU)**, **Assetto Corsa Competizione (ACC)**, **Assetto Corsa (AC)**, **Assetto Corsa EVO (ACE)**, **RaceRoom Racing Experience (RRRE)** y **Project Motor Racing (PMR)**.
Envía telemetría en tiempo real (RPM, LED de cambio, marchas, velocidad, combustible, temperaturas de neumáticos, tiempos por vuelta) a **UDP Steering Wheel / Display**, pantallas DDU UDP (`puerto 20777`) y **Web Live Dash + PitWall Timing** (`puerto 8080`).

## 1. Instalación
1. Haz doble clic en **`Installa_OpenSimWheel.desktop`** (o ejecuta `./core/installer.sh` en la terminal).
2. En la ventana de selección, marca los simuladores instalados en tu PC para configurar automáticamente sus plugins y puentes Proton.
3. El programa se instala en `~/.local/share/OpenSimWheel` y crea el acceso directo **OpenSimWheel Linux** en tu menú de aplicaciones y en el Escritorio.
4. Para desinstalar completamente el programa, ejecuta `~/.local/share/OpenSimWheel/uninstaller.sh`.

## 2. Configuración por Simulador

### Le Mans Ultimate (LMU) — Configuración completa
1. Descarga **`rFactor2SharedMemoryMapPlugin64.dll`** (del paquete *rF2 Shared Memory Map Plugin* / *TinyPedal*) y cópiala en `Le Mans Ultimate/Plugins/` (o déjala en `~/Descargas` antes del siguiente paso).
2. Ejecuta una sola vez **`./setup_lmu_plugin.sh`** desde la carpeta extraída (o selecciona **LMU** durante la instalación): el script copiará la DLL (si la encuentra) y activará automáticamente el plugin en `UserData/player/CustomPluginVariables.JSON`.
3. En las **Propiedades de Le Mans Ultimate en Steam**:
   - En **Compatibilidad**, selecciona una versión de Proton compatible con LMU/EAC (ej. **`GE-Proton11-3-LMU`** o **`Proton Experimental`**).
   - En **Mando**, selecciona **Desactivar Steam Input** (evita entradas duplicadas y cambios de marcha aleatorios).
4. En el menú del juego **Controls -> Force Feedback**, activa **Invert Force Feedback** si usas un volante Thrustmaster.
5. Inicia LMU, luego abre **OpenSimWheel Linux**, selecciona **LMU (Le Mans Ultimate)** y pulsa **OK**.

### Assetto Corsa Competizione (ACC)
1. Ejecuta una sola vez **`./setup_acc_proton.sh`** (o selecciona **ACC** durante la instalación) para configurar la lectura de memoria compartida en el prefijo Steam Proton de ACC (`AppID 805550`).
2. Inicia ACC, luego abre **OpenSimWheel Linux**, selecciona **ACC (Assetto Corsa Competizione)** y pulsa **OK**.

### Assetto Corsa (AC), Assetto Corsa EVO (ACE) y RaceRoom (RRRE)
1. Asegúrate de haber iniciado cada juego al menos una vez en Steam para que se cree su prefijo Proton (`AppID 244210` para AC, `3058630` para ACE, `211500` para RRRE).
2. Ejecuta una sola vez **`./setup_ac_proton.sh, setup_ace_proton.sh, setup_rrre_proton.sh`** (o selecciona **AC**, **ACE** y **RRRE** durante la instalación) para configurar los puentes de memoria compartida en Proton.
3. Inicia el simulador, abre **OpenSimWheel Linux**, selecciona **AC**, **ACE** o **RRRE** y pulsa **OK**.

### Project Motor Racing (PMR)
1. Activa la salida de telemetría UDP en los ajustes de PMR en el puerto **`7576`** (o `5606`).
2. Inicia **OpenSimWheel Linux**, selecciona **PMR (Project Motor Racing)** y pulsa **OK**.

## 3. Web Live Dash & PitWall Timing
- Mientras el Bridge esté activo, abre **`http://<IP_DE_TU_PC>:8080`** (ej. `http://127.0.0.1:8080`) en el navegador de tu PC, tablet o smartphone.
