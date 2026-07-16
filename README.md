# DJ Helper — installation depuis zéro

Application de gestion de bibliothèque musicale pour DJ (Traktor).
Fonctionne sur **Windows** et **macOS**. Toute la logique est en Python ;
l'interface s'affiche dans une fenêtre native (pywebview).

---

## Installation simple (application prête à l'emploi)

Télécharge la dernière version sur la page **Releases** du dépôt GitHub :
`DJHelper-windows.zip` ou `DJHelper-macos.zip`. **Tout est inclus** (ffmpeg et
fpcalc sont embarqués — si tu les as déjà sur ta machine, tes versions sont
utilisées en priorité et les copies embarquées sont simplement ignorées).
Dézippe, puis :

- **Windows** : ouvre le dossier et lance `DJ Helper.exe`. Au premier lancement,
  SmartScreen peut afficher un avertissement (application non signée) :
  clique « Informations complémentaires » → « Exécuter quand même ».
- **macOS** : glisse `DJ Helper.app` dans Applications. Au premier lancement,
  **clic droit → Ouvrir** (avertissement développeur non identifié, une seule fois).

Il ne reste qu'à configurer l'app (carte Configuration de l'accueil : dossier
audio, racine de la clé, clé AcoustID).

> Licences : DJ Helper est distribué sous **GPL v3** (voir `LICENSE`). Les
> binaires embarqués ffmpeg (build GPL) et fpcalc/Chromaprint conservent leurs
> licences respectives.

---

## Installation sur Windows (10 ou 11)

### 1. Installer Python
1. Télécharge Python 3.12 sur https://www.python.org/downloads/windows/
2. Lance l'installeur. **Coche impérativement « Add python.exe to PATH »**
   en bas de la première fenêtre, puis Install Now.
3. Vérifie dans un terminal (touche Windows → tape `cmd` → Entrée) :
   ```
   python --version
   ```
   Doit afficher `Python 3.12.x`.

### 2. Installer les dépendances Python
Dans le même terminal :
```
python -m pip install pywebview mutagen rapidfuzz numpy certifi
```

### 3. Installer ffmpeg et fpcalc (outils audio)
Deux options — la plus simple est le gestionnaire `winget`, inclus dans Windows :
```
winget install Gyan.FFmpeg
winget install AcoustID.Chromaprint
```
Ferme puis rouvre le terminal après l'installation (pour recharger le PATH).
Vérifie :
```
ffmpeg -version
fpcalc -version
```

Si `winget` n'est pas disponible : télécharge les zips sur
https://www.gyan.dev/ffmpeg/builds/ (ffmpeg) et
https://acoustid.org/chromaprint (fpcalc), puis pose `ffmpeg.exe` et
`fpcalc.exe` **directement dans le dossier DJHelperWeb** — l'app les trouve
aussi à cet emplacement, sans toucher au PATH.

### 4. Récupérer et lancer DJ Helper
1. Dézippe `DJHelperWeb.zip` où tu veux (ex. `C:\DJHelper`). **Évite un dossier
   synchronisé** (OneDrive, ProtonDrive…) : la synchro peut servir des fichiers
   périmés.
2. Dans le terminal :
   ```
   cd C:\DJHelper\DJHelperWeb
   python main.py
   ```
3. La fenêtre s'ouvre. Windows peut demander l'autorisation réseau au premier
   lancement (fonctions AcoustID) : accepte.

### 5. Configurer l'app (premier lancement)
Dans l'onglet **Accueil**, carte Configuration :
1. **Dossier audio** : ta clé USB, ex. `E:\TRACK BASE`.
2. **Racine de la clé** : la racine du volume, ex. `E:\` (là où vit `collection.nml`).
3. **Clé AcoustID** : crée une clé d'**application** (pas une clé de compte)
   sur https://acoustid.org/new-application et colle-la.
4. Vérifie que les badges ffmpeg / fpcalc sont verts dans le statut en bas à gauche.

---

## Installation sur macOS

### 1. Python et Homebrew
```bash
# Homebrew si absent : https://brew.sh
brew install python@3.12 ffmpeg chromaprint
```
(ou Python depuis python.org — dans ce cas ffmpeg/chromaprint via Homebrew quand même)

### 2. Dépendances Python
```bash
pip3.12 install pywebview mutagen rapidfuzz numpy certifi
```

### 3. Lancer
```bash
cd /chemin/vers/DJHelperWeb
python3.12 main.py
```

### 4. Configurer
Comme sur Windows (Dossier audio = `/Volumes/TACLE/TRACK BASE`,
Racine = `/Volumes/TACLE`, clé AcoustID d'application).

---

## Notes importantes

- **Dossiers synchronisés** (ProtonDrive, OneDrive, iCloud…) : ne lance jamais
  l'app depuis un dossier en cours de synchro. Symptôme vécu : les fichiers
  affichés à jour ne le sont pas, les corrections semblent sans effet.
- **Caches** : l'app stocke ses caches dans `~/.djhelper/` (macOS) ou
  `C:\Users\<toi>\.djhelper\` (Windows). Ils survivent aux mises à jour de l'app.
- **Clé AcoustID** : c'est une clé d'application (« Register a new application »
  sur acoustid.org), pas la clé API de ton compte utilisateur.
- **collection.nml** : les fonctions playlists (doublons, structure, M3U,
  hors-playlist) lisent le `collection.nml` de Traktor sur la clé. Sans Traktor,
  les fonctions fichiers (tags, doublons par son, intégrité) restent utilisables.

## Dépannage rapide

| Symptôme | Cause probable | Solution |
|---|---|---|
| `python` introuvable (Windows) | PATH non coché à l'install | Réinstalle Python en cochant « Add to PATH » |
| Badge fpcalc/ffmpeg rouge | Outils absents ou PATH non rechargé | Rouvre le terminal ; ou pose les .exe dans le dossier de l'app |
| Erreur SSL sur AcoustID | Certificats Python absents | L'app embarque `cacert.pem` — vérifie qu'il est bien à côté de `core.py` |
| L'app semble ignorer une mise à jour | Dossier synchronisé périmé, ou cache `__pycache__` | Sors le dossier de la synchro ; supprime `__pycache__` ; relance |
