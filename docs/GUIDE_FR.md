# Guide Utilisateur — OpenSimWheel Linux Bridge v1.4.0

Pont de télémétrie natif Linux optimisé à **40Hz** (anti-saccade Wi-Fi) pour **rFactor 2 (rF2)**, **Le Mans Ultimate (LMU)**, **Assetto Corsa Competizione (ACC)**, **Assetto Corsa (AC)**, **Assetto Corsa EVO (ACE)**, **RaceRoom Racing Experience (RRRE)** et **Project Motor Racing (PMR)**.

Envoie la télémétrie en temps réel (**régime moteur, LED de changement de rapport, vitesses, vitesse, carburant et tours restants, TC, ABS, répartition de freinage/Bias, drapeaux FIA, températures des pneus/IMO, pressions, usure et temps au tour/secteur**) vers :
- **Tout volant avec écran Wi-Fi/UDP ou écran DDU** compatible avec le standard UDP F1 2020/2023 (`port 20777` — y compris Thrustmaster SF1000, volants custom ESP32/VoCore et applications mobile/tablette comme SimHub, SimDashboard, DashPanel, RS Dash).
- **Web Live Dash + PitWall Timing intégrés** (`port 8080`), accessibles depuis le navigateur de n'importe quel PC, tablette ou smartphone sans matériel supplémentaire.

## 1. Installation et Désinstallation
1. Exécutez **`./install.sh`** dans le terminal (ou double-cliquez sur **`Installa_OpenSimWheel.desktop`**).
2. Sélectionnez les simulateurs installés sur votre PC : pour **rF2** et **LMU**, l'installateur active automatiquement la lecture native de la RAM Linux (`kernel.yama.ptrace_scope = 0`) sans aucun plugin DLL externe.
3. Le programme s'installe dans `~/.local/share/OpenSimWheel`, crée `~/.config/OpenSimWheel/osw_bridge.ini` et ajoute **OpenSimWheel Linux** à votre menu d'applications et sur le Bureau.
4. Pour désinstaller tout en conservant vos paramètres, exécutez `~/.local/share/OpenSimWheel/uninstaller.sh` (ou `./uninstaller.sh --purge` pour supprimer également `~/.config/OpenSimWheel`).

## 2. Configuration par Simulateur

### rFactor 2 (rF2) et Le Mans Ultimate (LMU) — 100% Natif (Sans Plugins)
1. **Aucun plugin externe requis :** Ne placez aucun fichier `.dll` dans le dossier `Plugins/` du jeu (évite les plantages au démarrage sous Proton 9.0 / GE-Proton). Le Bridge lit le moteur, les rapports et les données IMO/usure/pression des 4 roues directement via l'API REST native (`5397` / `6397`) et le scan RAM Linux.
2. Dans les **Propriétés Steam** :
   - Sous **Compatibilité**, sélectionnez **`Proton 9.0`** ou **`Proton Experimental`** pour rF2, et **`GE-Proton`** / **`Proton Experimental`** pour LMU.
   - Sous **Contrôleur**, sélectionnez **Désactiver Steam Input** (évite les doubles entrées et les changements de vitesse aléatoires).
3. Dans le menu en jeu **Controls -> Force Feedback**, activez **Invert Force Feedback** si vous utilisez un volant Thrustmaster.
4. Lancez le jeu, ouvrez **OpenSimWheel Linux**, sélectionnez **RF2** ou **LMU** et cliquez sur **OK**.

## Assetto Corsa Competizione (ACC)
1. Lancez ACC au moins une fois sur Steam pour initialiser son préfixe Proton (`AppID 805550`).
2. Exécutez une seule fois **`./setup_acc_proton.sh`** (ou sélectionnez **ACC** lors de l'installation) pour configurer la lecture de la mémoire partagée dans le préfixe Proton (ports `9000`/`9001`).
3. Lancez ACC, ouvrez **OpenSimWheel Linux**, sélectionnez **ACC (Assetto Corsa Competizione)** et cliquez sur **OK**.

## Assetto Corsa (AC), Assetto Corsa EVO (ACE) et RaceRoom (RRRE)
1. Assurez-vous d'avoir lancé chaque jeu au moins une fois sur Steam afin d'initialiser son préfixe Proton (`AppID 244210` pour AC, `3058630` pour ACE, `211500` pour RRRE).
2. Exécutez une seule fois **`./setup_ac_proton.sh`**, **`./setup_ace_proton.sh`** ou **`./setup_rrre_proton.sh`** (ou sélectionnez-les lors de l'installation).
3. **Conseil pour les volants sous RaceRoom :** Dans **Propriétés Steam -> Contrôleur**, désactivez Steam Input et ajoutez dans les options de lancement : `SDL_JOYSTICK_HIDAPI=1 PROTON_ENABLE_HIDRAW=1 %command%`.
4. Lancez le simulateur, ouvrez **OpenSimWheel Linux**, sélectionnez **AC**, **ACE** ou **RRRE** et cliquez sur **OK**.

## Project Motor Racing (PMR)
1. Activez la sortie télémétrie UDP dans les paramètres de PMR sur le port **`7576`** (ou `5606`).
2. Ouvrez **OpenSimWheel Linux**, sélectionnez **PMR (Project Motor Racing)** et cliquez sur **OK**.

## 3. Auto-Sniffer Réseau, Configuration Centrale et Web Live Dash
- **Auto-Sniffer :** Au démarrage, OpenSimWheel détecte automatiquement l'IP locale de votre PC et scanne le réseau domestique pour trouver les volants à écran UDP ou tablettes compatibles.
- **Configuration Centrale (`osw_bridge.ini`) :** Tous les ports et paramètres auto-réparables sont enregistrés dans `~/.config/OpenSimWheel/osw_bridge.ini` (`[SIM_RF2]`, `[SIM_LMU]`, `[SIM_ACC]`, `[SIM_AC]`, `[SIM_ACE]`, `[SIM_RRRE]`, `[SIM_PMR]`).
- **Web Live Dash (`http://<IP_DE_VOTRE_PC>:8080`) :** Affiche LED de changement de rapport, vitesse engagée, vitesse, TC, ABS, répartition de freinage, drapeaux FIA actifs, consommation de carburant et température des pneus (commutable entre **MEDIA** et **IMO**).
- **PitWall Timing (`http://<IP_DE_VOTRE_PC>:8080/timing`) :** Écran plein format de chronométrage avec position, tour, temps actuel/dernier/meilleur et les 3 secteurs (`S1 / S2 / S3`), optimisé pour tablettes et iPad.

