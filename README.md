# DJ Helper

*[Version française](README.fr.md)*

Music library manager for DJs (Traktor): tags, duplicates (by name and by
audio fingerprint), file integrity, AcoustID enrichment, backups and USB
stick synchronization. Windows and macOS.

---

## Installation (users)

1. Go to the **[Releases](../../releases)** page and download
   `DJHelper-windows.zip` or `DJHelper-macos.zip`. **Everything is included**
   (ffmpeg and fpcalc are bundled — if you already have them installed, your
   versions take priority and the bundled copies are simply ignored).
2. Unzip, then:
   - **Windows**: before extracting, right-click the downloaded zip →
     Properties → check **Unblock** → OK (Windows flags downloaded files and
     .NET refuses to load flagged components — the app won't start otherwise).
     Then extract and run `DJ Helper.exe`. If SmartScreen shows a warning:
     "More info" → "Run anyway" (unsigned app).
   - **macOS**: drag `DJ Helper.app` to Applications, then **right-click →
     Open** on first launch (unidentified developer warning, one time only).
     The build targets Apple Silicon (M1 and later); if macOS offers to install
     Rosetta on first use of the audio tools, accept. Intel Macs: use the
     "Running from source" method below.
3. Configure from the Home tab: audio folder, USB stick root, and an AcoustID
   **application** key (free: https://acoustid.org/new-application).

That's it. Nothing else to install.

---

## Running from source (developers)

Requires Python 3.12, ffmpeg and fpcalc (Chromaprint).

```bash
git clone https://github.com/hfreryr/DJ-HELPER.git && cd DJ-HELPER
pip install -r requirements.txt
# audio tools:
#   macOS   : brew install ffmpeg chromaprint
#   Windows : winget install Gyan.FFmpeg && winget install AcoustID.Chromaprint
#             (or drop ffmpeg.exe / fpcalc.exe into the project folder)
python main.py
```

Windows: install Python from python.org and make sure to check **"Add
python.exe to PATH"**. Avoid working from a cloud-synced folder (OneDrive,
ProtonDrive…): sync can serve stale files.

## Notes

- **Windows + Traktor: assign a fixed drive letter to your USB stick.** Windows
  assigns letters on plug-in, and Traktor stores absolute paths — if your stick
  mounts as `E:` instead of `D:`, your whole collection shows as missing. Fix it
  once per PC: Disk Management → right-click the stick's partition → "Change
  Drive Letter and Paths…" → pick a high letter (e.g. `T:`). Do the same for
  your spare stick (plugged alone, same letter). Then configure Traktor and
  DJ Helper using that letter.

- App caches live in `~/.djhelper/` (they survive updates).
- Playlist features (playlist-aware duplicate resolution, structure backup,
  M3U vault, tracks-without-playlist) read Traktor's `collection.nml` from the
  USB stick. Without Traktor, all file-level features (tags, audio duplicates,
  integrity) remain fully usable.
- Licensing: DJ Helper is **GPL v3** (see `LICENSE`). Bundled binaries —
  ffmpeg (GPL build) and fpcalc/Chromaprint — keep their respective licenses.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Windows: crash at launch mentioning `Python.Runtime.dll` | The downloaded files are blocked: right-click the zip → Properties → Unblock, re-extract. Or in PowerShell: `Get-ChildItem -Path <folder> -Recurse \| Unblock-File` |
| ffmpeg/fpcalc badge red (running from source) | Reopen the terminal; or drop the binaries into the project folder |
| AcoustID SSL error (running from source) | Check that `cacert.pem` sits next to `core.py` |
| An update seems to have no effect | Stale synced folder or `__pycache__`: move the project out of sync, delete `__pycache__` |
