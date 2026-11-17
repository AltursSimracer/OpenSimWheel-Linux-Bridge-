# Guide Utilisateur — OpenSimWheel Linux Bridge v1.3.0

Pont de télémétrie natif Linux à 100Hz pour **Le Mans Ultimate (LMU)**, **Assetto Corsa Competizione (ACC)**, **Assetto Corsa (AC)**, **Assetto Corsa EVO (ACE)**, **RaceRoom Racing Experience (RRRE)** et **Project Motor Racing (PMR)**.
Envoie la télémétrie en temps réel (régime moteur, LED de changement de rapport, vitesses, vitesse, carburant, températures des pneus, temps au tour) vers **UDP Steering Wheel / Display**, les écrans DDU UDP (`port 20777`) et **Web Live Dash + PitWall Timing** (`port 8080`).

## 1. Installation
1. Double-cliquez sur **`Installa_OpenSimWheel.desktop`** (ou exécutez `./core/installer.sh` dans le terminal).
2. Dans la fenêtre de sélection, cochez les simulateurs installés sur votre PC pour configurer automatiquement leurs plugins et ponts Proton.
3. Le programme s'installe dans `~/.local/share/OpenSimWheel` et crée le raccourci **OpenSimWheel Linux** dans votre menu d'applications et sur le Bureau.
4. Pour désinstaller complètement le programme, exécutez `~/.local/share/OpenSimWheel/uninstaller.sh`.

## 2. Configuration par Simulateur

### Le Mans Ultimate (LMU) — Configuration complète
1. Téléchargez **`rFactor2SharedMemoryMapPlugin64.dll`** (depuis le pack *rF2 Shared Memory Map Plugin* / *TinyPedal*) et placez-la dans `Le Mans Ultimate/Plugins/` (ou laissez-la dans `~/Téléchargements` avant l'étape suivante).
2. Exécutez une seule fois **`./setup_lmu_plugin.sh`** depuis le dossier extrait (ou sélectionnez **LMU** lors de l'installation) : le script copiera la DLL (si trouvée) et activera automatiquement le plugin dans `UserData/player/CustomPluginVariables.JSON`.
3. Dans les **Propriétés Steam de Le Mans Ultimate** :
   - Sous **Compatibilité**, sélectionnez une version Proton compatible avec LMU/EAC (ex. **`GE-Proton11-3-LMU`** ou **`Proton Experimental`**).
   - Sous **Contrôleur**, sélectionnez **Désactiver Steam Input** (évite les doubles entrées et les changements de vitesse aléatoires).
4. Dans le menu en jeu **Controls -> Force Feedback**, activez **Invert Force Feedback** si vous utilisez un volant Thrustmaster.
5. Lancez LMU, ouvrez ensuite **OpenSimWheel Linux**, sélectionnez **LMU (Le Mans Ultimate)** et cliquez sur **OK**.

### Assetto Corsa Competizione (ACC)
1. Exécutez une seule fois **`./setup_acc_proton.sh`** (ou sélectionnez **ACC** lors de l'installation) pour configurer la lecture de la mémoire partagée dans le préfixe Steam Proton d'ACC (`AppID 805550`).
2. Lancez ACC, ouvrez ensuite **OpenSimWheel Linux**, sélectionnez **ACC (Assetto Corsa Competizione)** et cliquez sur **OK**.

### Assetto Corsa (AC), Assetto Corsa EVO (ACE) et RaceRoom (RRRE)
1. Assurez-vous d'avoir lancé chaque jeu au moins une fois sur Steam afin que son préfixe Proton soit créé (`AppID 244210` pour AC, `3058630` pour ACE, `211500` pour RRRE).
2. Exécutez une seule fois **`./setup_ac_proton.sh, setup_ace_proton.sh, setup_rrre_proton.sh`** (ou sélectionnez **AC**, **ACE** et **RRRE** lors de l'installation) pour configurer les ponts de mémoire partagée Proton.
3. Lancez le simulateur, ouvrez **OpenSimWheel Linux**, sélectionnez **AC**, **ACE** ou **RRRE** et cliquez sur **OK**.

### Project Motor Racing (PMR)
1. Activez la sortie télémétrie UDP dans les paramètres de PMR sur le port **`7576`** (ou `5606`).
2. Lancez **OpenSimWheel Linux**, sélectionnez **PMR (Project Motor Racing)** et cliquez sur **OK**.

## 3. Web Live Dash & PitWall Timing
- Pendant que le Bridge est actif, ouvrez **`http://<IP_DE_VOTRE_PC>:8080`** (ex. `http://127.0.0.1:8080`) dans le navigateur de votre PC, tablette ou smartphone.
