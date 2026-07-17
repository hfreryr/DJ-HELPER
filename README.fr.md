# DJ Helper

*[English version](README.md)*

Application de gestion de bibliothèque musicale pour DJ (Traktor) : tags,
doublons (par nom et par empreinte sonore), intégrité des fichiers,
enrichissement AcoustID, sauvegardes et synchronisation de clé USB.
Windows et macOS.

---

## Installation (utilisateurs)

1. Va sur la page **[Releases](../../releases)** et télécharge
   `DJHelper-windows.zip` ou `DJHelper-macos.zip`. **Tout est inclus**
   (ffmpeg et fpcalc embarqués — si tu les as déjà, tes versions priment).
2. Dézippe, puis :
   - **Windows** : avant d'extraire, clic droit sur le zip téléchargé →
     Propriétés → coche **Débloquer** → OK (Windows marque les fichiers
     téléchargés et .NET refuse de charger un composant marqué — l'app ne
     démarre pas sinon). Puis extrais et lance `DJ Helper.exe`. Si SmartScreen
     s'affiche : « Informations complémentaires » → « Exécuter quand même ».
   - **macOS** : glisse `DJ Helper.app` dans Applications, puis **clic droit →
     Ouvrir** au premier lancement. Build pour Apple Silicon (M1 et suivants) ;
     si macOS propose d'installer Rosetta au premier usage des outils audio,
     accepte. Mac Intel : passe par « Lancer depuis les sources ».
3. Configure dans l'accueil : dossier audio, racine de la clé USB, et une clé
   AcoustID d'**application** (gratuite : https://acoustid.org/new-application).

C'est tout. Aucune autre installation n'est nécessaire.

---

## Lancer depuis les sources (développeurs)

Nécessite Python 3.12, ffmpeg et fpcalc (Chromaprint).

```bash
git clone https://github.com/hfreryr/DJ-HELPER.git && cd DJ-HELPER
pip install -r requirements.txt
# outils audio :
#   macOS   : brew install ffmpeg chromaprint
#   Windows : winget install Gyan.FFmpeg && winget install AcoustID.Chromaprint
#             (ou poser ffmpeg.exe / fpcalc.exe dans le dossier du projet)
python main.py
```

Windows : installe Python depuis python.org en cochant **« Add python.exe to
PATH »**. Évite de travailler dans un dossier synchronisé (OneDrive,
ProtonDrive…) : la synchro peut servir des fichiers périmés.

## Notes

- **Windows + Traktor : fixe une lettre de lecteur à ta clé USB.** Windows
  attribue les lettres au branchement, et Traktor stocke des chemins absolus —
  si ta clé monte en `E:` au lieu de `D:`, toute la collection apparaît
  manquante. À faire une fois par PC : Gestion des disques → clic droit sur la
  partition de la clé → « Modifier la lettre de lecteur et les chemins… » →
  choisis une lettre haute (ex. `T:`). Idem pour la clé de secours (branchée
  seule, même lettre). Configure ensuite Traktor et DJ Helper avec cette lettre.

- Caches de l'app : `~/.djhelper/` (survivent aux mises à jour).
- Les fonctions playlists (doublons via playlists, structure, M3U, hors-playlist)
  lisent le `collection.nml` de Traktor sur la clé. Sans Traktor, les fonctions
  fichiers (tags, doublons par le son, intégrité) restent utilisables.
- Licences : DJ Helper est sous **GPL v3** (`LICENSE`). Les binaires embarqués
  ffmpeg (build GPL) et fpcalc/Chromaprint conservent leurs licences.

## Dépannage

| Symptôme | Solution |
|---|---|
| Windows : plantage au lancement mentionnant `Python.Runtime.dll` | Fichiers bloqués par Windows : clic droit sur le zip → Propriétés → Débloquer, ré-extraire. Ou PowerShell : `Get-ChildItem -Path <dossier> -Recurse \| Unblock-File` |
| Badge ffmpeg/fpcalc rouge (depuis les sources) | Rouvre le terminal ; ou pose les binaires dans le dossier du projet |
| Erreur SSL AcoustID (depuis les sources) | Vérifie que `cacert.pem` est à côté de `core.py` |
| Une mise à jour semble sans effet | Dossier synchronisé périmé ou `__pycache__` : sors le projet de la synchro, supprime `__pycache__` |
