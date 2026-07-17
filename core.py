"""
core.py — logique métier du socle DJ Helper (version web / pywebview).

Sans Tkinter : tout l'affichage est dans web/.
La détection de doublons est portée fidèlement depuis l'app Tkinter
(normalize_string / parse_filename / _prefer_readable / detect_duplicates /
select_master), pour un comportement identique à celui que Guy connaît.
"""

import os
import re
import shutil
import unicodedata

SUPPORTED = {".mp3", ".flac", ".wav", ".aiff", ".aif", ".m4a", ".aac", ".ogg"}

# Chemin du bundle CA, résolu À L'IMPORT (avant que pywebview ne change le cwd).
# main.py peut le surcharger via resource_path() pour le cas de l'app buildée.
_CA_BUNDLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cacert.pem")


def nml_hash(usb_root):
    """SHA-1 du collection.nml de la clé, ou '' si introuvable/illisible.
    Sert à détecter un changement (playlists, cues) depuis la dernière
    génération du coffre-fort M3U."""
    import hashlib
    try:
        nml = bk_find_collection_nml(usb_root)
        if not nml:
            return ""
        h = hashlib.sha1()
        with open(nml, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _quiet_run():
    """kwargs pour subprocess : sous Windows, empêche l'ouverture d'une console
    furtive à chaque appel de fpcalc/ffmpeg (CREATE_NO_WINDOW)."""
    import sys as _s
    if _s.platform.startswith("win"):
        return {"creationflags": 0x08000000}
    return {}



# ---------------------------------------------------------------------------
# Fichiers parasites à ignorer
# ---------------------------------------------------------------------------
def is_junk(name):
    if name.startswith("._"):
        return True
    if name in (".DS_Store", ".Spotlight-V100", ".Trashes"):
        return True
    if "_doublons_backup_" in name:
        return True
    return False


# ---------------------------------------------------------------------------
# Normalisation et matching (porté du Tkinter)
# ---------------------------------------------------------------------------
NOISE_KEYWORDS = re.compile(
    r"\((?:[^()]*?)(original|radio|extended|club|edit|mix|version|"
    r"remaster|remix|instrumental|acoustic|live)(?:[^()]*?)\)",
    re.IGNORECASE,
)
NOISE_BRACKETS = re.compile(r"\[[^\]]*\]")
COPY_SUFFIX = re.compile(r"\s*\(\d{1,2}\)\s*$")  # marqueur de copie OS : « (1) », « (2) »…
FEATURING = re.compile(r"\b(feat\.?|ft\.?|featuring|avec)\b", re.IGNORECASE)
NOISE_FEAT = re.compile(
    r"\((?:[^()]*?)\b(feat\.?|ft\.?|featuring|with|avec|vs\.?|x)\b(?:[^()]*?)\)",
    re.IGNORECASE,
)
NOISE_YT = re.compile(
    r"\((?:[^()]*?)\b(audio|video|clip|officiel|official|lyrics?|"
    r"visualizer|visualiser|paroles|hd|hq|4k|mv)\b(?:[^()]*?)\)",
    re.IGNORECASE,
)
TRACK_NUMBER_PREFIX = re.compile(r"^\d+\s*[-.\s]+")


def normalize_string(s, keep_versions=False):
    """Minuscules, sans accents, sans parenthèses de bruit, sans ponctuation.
    keep_versions=True préserve les suffixes de version (Remix, Edit, Mix…) :
    utile pour la détection de doublons, où un remix ≠ son original."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = COPY_SUFFIX.sub("", s)
    if not keep_versions:
        s = NOISE_KEYWORDS.sub("", s)
    s = NOISE_FEAT.sub("", s)
    s = NOISE_YT.sub("", s)
    s = NOISE_BRACKETS.sub("", s)
    s = FEATURING.sub("", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_filename(stem):
    """Extrait (artist, title) d'un nom 'Artiste - Titre', sinon (None, None)."""
    cleaned = TRACK_NUMBER_PREFIX.sub("", stem)
    parts = cleaned.split(" - ", 1)
    if len(parts) == 2:
        artist, title = parts[0].strip(), parts[1].strip()
        if artist and title:
            return artist, title
    return None, None


VERSION_SUFFIX = re.compile(
    r"\s*[-–—]\s*[^-–—]*\b("
    r"remaster|remastered|remix|edit|mix|version|live|mono|stereo|anniversary|"
    r"deluxe|original|radio|extended|instrumental|acoustic|single|edition|"
    r"master|rerecorded|re-recorded|\d{4})\b.*$",
    re.IGNORECASE,
)


def strip_version_suffix(title):
    if not title:
        return title
    return VERSION_SUFFIX.sub("", title).strip()


def match_title_key(artist, title):
    """Titre normalisé pour le matching : sans suffixe de version, et débarrassé
    du préfixe artiste quand le tag titre répète « Artiste - Titre »."""
    na = normalize_string(artist or "")
    nt = normalize_string(strip_version_suffix(title or ""))
    if na and nt.startswith(na + " "):
        nt = nt[len(na):].strip()
    return nt


def match_candidates(artist, title):
    """Paires (artiste, titre) normalisées candidates, robustes aux tags sales."""
    cands = []
    na = normalize_string(artist or "")
    nt = match_title_key(artist, title)
    if na and nt:
        cands.append((na, nt))
    raw = title or ""
    if " - " in raw:
        before, after = raw.split(" - ", 1)
        a2 = normalize_string(before)
        t2 = match_title_key(before, after)
        if a2 and t2 and (a2, t2) not in cands:
            cands.append((a2, t2))
    return cands


def _flatten_key(s):
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", nfkd.lower())


def _prefer_readable(tag_val, file_val):
    """Si le tag est un slug dégradé du même contenu que le nom de fichier,
    renvoie la forme lisible du nom de fichier."""
    if tag_val and file_val:
        k = _flatten_key(tag_val)
        if k and k == _flatten_key(file_val) and " " not in tag_val and " " in file_val:
            return file_val
    return tag_val


def _read_artist_title(path):
    """Lit (artist, title) selon le format, comme read_tags du Tkinter.
    AIFF/WAV : frames ID3 TPE1/TIT2 (ce que le retag y écrit)."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".mp3":
            from mutagen.easyid3 import EasyID3
            from mutagen.id3 import ID3NoHeaderError
            try:
                audio = EasyID3(path)
            except ID3NoHeaderError:
                return None, None
            return (audio.get("artist") or [None])[0], (audio.get("title") or [None])[0]
        elif ext == ".flac":
            from mutagen.flac import FLAC
            audio = FLAC(path)
            return (audio.get("artist") or [None])[0], (audio.get("title") or [None])[0]
        elif ext in (".m4a", ".aac"):
            from mutagen.mp4 import MP4
            audio = MP4(path)
            if not audio.tags:
                return None, None
            return ((audio.tags.get("\xa9ART") or [None])[0],
                    (audio.tags.get("\xa9nam") or [None])[0])
        elif ext in (".aiff", ".aif", ".wav"):
            from mutagen.aiff import AIFF
            from mutagen.wave import WAVE
            cls = AIFF if ext in (".aiff", ".aif") else WAVE
            audio = cls(path)
            tags = audio.tags
            if not tags:
                return None, None

            def _ft(fid):
                fr = tags.get(fid)
                if fr is not None and getattr(fr, "text", None):
                    return str(fr.text[0])
                return None
            return _ft("TPE1"), _ft("TIT2")
        else:
            return None, None
    except Exception:
        return None, None


def write_tags(path, artist, title):
    """Écrit artist/title selon le format (porté du Tkinter). True si succès."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".mp3":
            from mutagen.easyid3 import EasyID3
            from mutagen.id3 import ID3NoHeaderError
            try:
                audio = EasyID3(path)
            except ID3NoHeaderError:
                from mutagen import File as MFile
                tmp = MFile(path, easy=True)
                if tmp is None:
                    return False
                tmp.add_tags()
                tmp.save()
                audio = EasyID3(path)
            audio["artist"] = artist
            audio["title"] = title
            audio.save()
            return True
        elif ext == ".flac":
            from mutagen.flac import FLAC
            audio = FLAC(path)
            audio["artist"] = artist
            audio["title"] = title
            audio.save()
            return True
        elif ext in (".m4a", ".aac"):
            from mutagen.mp4 import MP4
            audio = MP4(path)
            if audio.tags is None:
                audio.add_tags()
            audio["\xa9ART"] = artist
            audio["\xa9nam"] = title
            audio.save()
            return True
        elif ext in (".aiff", ".aif", ".wav"):
            from mutagen.aiff import AIFF
            from mutagen.wave import WAVE
            from mutagen.id3 import TPE1, TIT2
            cls = AIFF if ext in (".aiff", ".aif") else WAVE
            audio = cls(path)
            if audio.tags is None:
                audio.add_tags()
            audio.tags["TPE1"] = TPE1(encoding=3, text=artist)
            audio.tags["TIT2"] = TIT2(encoding=3, text=title)
            audio.save()
            return True
        else:
            return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Helpers d'affichage
# ---------------------------------------------------------------------------
def human_size(n):
    n = float(n or 0)
    for unit in ("o", "Ko", "Mo", "Go", "To"):
        if n < 1024:
            return ("%.0f %s" % (n, unit)) if unit in ("o", "Ko") else ("%.1f %s" % (n, unit))
        n /= 1024
    return "%.1f To" % n


def fmt_duration(seconds):
    if not seconds:
        return ""
    s = int(round(seconds))
    return "%d:%02d" % (s // 60, s % 60)


# ---------------------------------------------------------------------------
# Sélection du master (porté du Tkinter) : MP3 d'abord, puis plus haut débit
# ---------------------------------------------------------------------------
def select_master(versions):
    def priority(t):
        is_mp3 = (t.get("ext", "").lower() == "mp3")
        return (0 if is_mp3 else 1,           # MP3 d'abord (contrainte matériel DJ)
                -(t.get("bitrate") or 0),     # puis meilleur débit
                -(t.get("size") or 0),        # à débit égal, le plus gros (moins recompressé)
                len(t.get("name", "")))       # enfin le nom le plus court (le plus propre)
    return min(versions, key=priority)


# ---------------------------------------------------------------------------
# Intégrité — mode rapide (porté du Tkinter : quick_integrity_check)
# Sans ffmpeg : headers, durée, cohérence taille/durée×débit. Lecture seule.
# ---------------------------------------------------------------------------
def quick_integrity_check(path):
    """Retourne {severity, errors}. severity ∈ {ok, warning, critical}."""
    issues = []
    severity = "ok"
    try:
        size = os.path.getsize(path)
        if size == 0:
            return {"severity": "critical", "errors": ["Fichier vide (0 octet)"]}
        if size < 10000:
            issues.append("Fichier suspectement petit (%d octets)" % size)
            severity = "warning"
    except Exception as e:
        return {"severity": "critical", "errors": ["Stat impossible : %s" % e]}

    try:
        from mutagen import File as MFile
        audio = MFile(path)
        if audio is None:
            return {"severity": "critical",
                    "errors": ["Format non reconnu ou header cassé"]}
        duration = getattr(audio.info, "length", 0) or 0
        if duration <= 0:
            issues.append("Durée nulle ou inconnue dans le header")
            severity = "critical"
        elif duration < 30:
            issues.append("Durée très courte (%.1fs)" % duration)
            if severity == "ok":
                severity = "warning"
        bitrate = getattr(audio.info, "bitrate", 0) or 0
        if bitrate and duration:
            theoretical = (bitrate / 8) * duration
            ratio = size / theoretical if theoretical else 0
            if ratio < 0.7:
                issues.append("Taille vs durée×débit faible (%.2f× attendu) "
                              "— probable troncature" % ratio)
                severity = "critical"
    except Exception as e:
        return {"severity": "critical", "errors": ["Header illisible : %s" % e]}

    return {"severity": severity, "errors": issues}


CRITICAL_PATTERNS = [
    re.compile(r"Invalid data found", re.IGNORECASE),
    re.compile(r"Header missing", re.IGNORECASE),
    re.compile(r"Error while decoding", re.IGNORECASE),
    re.compile(r"could not find codec parameters", re.IGNORECASE),
    re.compile(r"Truncated", re.IGNORECASE),
    re.compile(r"premature end", re.IGNORECASE),
    re.compile(r"moov atom not found", re.IGNORECASE),
    re.compile(r"Error opening input", re.IGNORECASE),
    re.compile(r"Failed to read frame size", re.IGNORECASE),
    re.compile(r"Invalid argument", re.IGNORECASE),
    re.compile(r"No such file", re.IGNORECASE),
]
CRIT_ERROR_MIN = 3
SLIDING_SAMPLE_RATE = 22050
OUT_OF_RANGE_SOFT = 4.0     # |x| au-delà = hors de portée du mastering = garbage
OUT_OF_RANGE_HARD = 10.0    # un seul échantillon au-delà = corruption certaine
OOR_MIN_COUNT = 8           # nb min d'échantillons hors-échelle pour flagger


def _oor_verdict(buf):
    """Analyse un buffer PCM f32le. Retourne (is_corrupt, message).
    Ne flagge QUE de la corruption sonore avérée (|x| >> 1.0, impossible en audio
    sain) — pas le clipping/loudness d'un master fort."""
    try:
        import numpy as np
    except Exception:
        return (False, "Analyse sonore indisponible : numpy non installé (pip install numpy).")
    try:
        samples = np.frombuffer(buf, dtype=np.float32)
        samples = samples[np.isfinite(samples)]
        if not samples.size:
            return (False, "")
        a = np.abs(samples)
        absmax = float(a.max())
        n_oor = int(np.count_nonzero(a > OUT_OF_RANGE_SOFT))
        if absmax > OUT_OF_RANGE_HARD or n_oor >= OOR_MIN_COUNT:
            return (True, "Échantillons hors-échelle (corruption) : max |x|=%.1f, "
                          "%d échantillon(s) > %.0f (garbage de décodage, sans rapport "
                          "avec un master fort)." % (absmax, n_oor, OUT_OF_RANGE_SOFT))
        return (False, "")
    except Exception as e:
        return (False, "Analyse sonore échouée : %s" % e)


ACOUSTID_LOOKUP_URL = "https://api.acoustid.org/v2/lookup"
MUSICBRAINZ_WS = "https://musicbrainz.org/ws/2"
COVERART_ARCHIVE = "https://coverartarchive.org"
MB_USER_AGENT = "DJ-Playlist-Helper/1.0 (https://github.com/dj-playlist-helper)"
VERSION_MARKER = re.compile(
    r"\b(rework|re-?work|edit|remix|bootleg|vip|mashup|mash-?up|flip|rerub|"
    r"re-?rub|refix|re-?fix|extended|club mix|radio edit|remaster)\b", re.I)
_RG_SECONDARY_PENALTY = {"compilation", "live", "remix", "soundtrack",
                         "dj-mix", "mixtape/street", "demo", "interview"}


def has_version_marker(title):
    """True si le titre porte un marqueur de version (rework, edit, remix…)."""
    return bool(VERSION_MARKER.search(title or ""))


def _tag_norm(s):
    """Normalise une chaîne pour comparer deux tags (casse / espaces / Unicode)."""
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", (s or "")).strip()).casefold()


def find_fpcalc():
    """Cherche le binaire fpcalc (Chromaprint) : PATH, dossier de l'app,
    emplacements usuels macOS (Homebrew) et Windows."""
    p = shutil.which("fpcalc")
    if p:
        return p
    import sys as _sys
    here = os.path.dirname(os.path.abspath(__file__))
    base = getattr(_sys, "_MEIPASS", here)
    candidates = [
        os.path.join(base, "fpcalc.exe"), os.path.join(base, "fpcalc"),
        os.path.join(here, "fpcalc.exe"), os.path.join(here, "fpcalc"),
        "/usr/local/bin/fpcalc", "/opt/homebrew/bin/fpcalc", "/usr/bin/fpcalc",
        r"C:\Program Files\Chromaprint\fpcalc.exe",
        r"C:\chromaprint\fpcalc.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def acoustid_fingerprint_raw(filepath, fpcalc_path, timeout=120):
    """Empreinte Chromaprint « raw » (liste d'entiers 32 bits) pour comparaison
    LOCALE entre fichiers — pas d'API. Retourne (list[int], duration) ou (None, None)."""
    import subprocess, json
    try:
        proc = subprocess.run([fpcalc_path, "-raw", "-json", str(filepath)],
                              capture_output=True, text=True, timeout=timeout, **_quiet_run())
        if proc.returncode != 0 or not proc.stdout.strip():
            return None, None
        data = json.loads(proc.stdout)
        fp = data.get("fingerprint")
        dur = data.get("duration")
        if not fp or not dur:
            return None, None
        return fp, float(dur)
    except Exception:
        return None, None


# Table de popcount 16 bits (initialisée à la 1re comparaison, partagée).
_FP_POPCOUNT16 = None


def _fp_popcount(x):
    """Nombre total de bits à 1 dans un tableau numpy uint32 (via table 16 bits)."""
    global _FP_POPCOUNT16
    import numpy as np
    if _FP_POPCOUNT16 is None:
        _FP_POPCOUNT16 = np.array([bin(i).count("1") for i in range(65536)],
                                  dtype=np.uint16)
    x = x.astype(np.uint32)
    lo = (x & np.uint32(0xFFFF)).astype(np.uint16)
    hi = ((x >> np.uint32(16)) & np.uint32(0xFFFF)).astype(np.uint16)
    return int(_FP_POPCOUNT16[lo].sum() + _FP_POPCOUNT16[hi].sum())


def fp_similarity(a, b, max_offset=15, min_overlap=40):
    """Similarité [0..1] entre deux empreintes raw (tableaux uint32), robuste à un
    petit décalage (silences d'intro). 1.0 = identique, ~0.5 = sons sans rapport.
    Teste les offsets -max_offset..+max_offset et garde le meilleur recouvrement."""
    import numpy as np
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return 0.0
    best = 0.0
    for off in range(-max_offset, max_offset + 1):
        ia, ib = (off, 0) if off >= 0 else (0, -off)
        n = min(na - ia, nb - ib)
        if n < min_overlap:
            continue
        x = np.bitwise_xor(a[ia:ia + n], b[ib:ib + n])
        sim = 1.0 - _fp_popcount(x) / (32.0 * n)
        if sim > best:
            best = sim
    return best


def acoustid_fingerprint(filepath, fpcalc_path, timeout=60):
    """Empreinte Chromaprint via fpcalc. Retourne (fingerprint, duration) ou (None, None)."""
    import subprocess, json
    try:
        proc = subprocess.run([fpcalc_path, "-json", str(filepath)],
                              capture_output=True, text=True, timeout=timeout, **_quiet_run())
        if proc.returncode != 0 or not proc.stdout.strip():
            return None, None
        data = json.loads(proc.stdout)
        fp = data.get("fingerprint")
        dur = data.get("duration")
        if not fp or not dur:
            return None, None
        return fp, int(round(float(dur)))
    except Exception:
        return None, None


def acoustid_lookup(fingerprint, duration, client_key, timeout=20):
    """Interroge AcoustID. Retourne {status: ok/no_match/error, matches:[(score,artist,title)], error}."""
    import json, ssl, urllib.request, urllib.parse, urllib.error
    ctx = _ssl_ctx()
    try:
        params = urllib.parse.urlencode({
            "client": client_key, "duration": duration, "fingerprint": fingerprint,
            "meta": "recordings", "format": "json"}).encode("utf-8")
        req = urllib.request.Request(
            ACOUSTID_LOOKUP_URL, data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") != "ok":
            err = ""
            if isinstance(data.get("error"), dict):
                err = data["error"].get("message", "")
            return {"status": "error", "matches": [], "error": err or "réponse inattendue"}
        matches = []
        for res in data.get("results", []):
            score = float(res.get("score", 0.0))
            for rec in res.get("recordings", []) or []:
                title = rec.get("title", "") or ""
                artists = rec.get("artists", []) or []
                artist = ", ".join(a.get("name", "") for a in artists if a.get("name"))
                if artist or title:
                    matches.append((score, artist, title))
        matches.sort(key=lambda m: m[0], reverse=True)
        return {"status": "ok" if matches else "no_match", "matches": matches, "error": ""}
    except urllib.error.HTTPError as e:
        msg = ""
        try:
            body = json.loads(e.read().decode("utf-8"))
            if isinstance(body.get("error"), dict):
                msg = body["error"].get("message", "")
        except Exception:
            msg = ""
        return {"status": "error", "matches": [], "error": msg or ("HTTP %d" % e.code)}
    except Exception as e:
        return {"status": "error", "matches": [], "error": str(e)[:120]}


def acoustid_verdict(tag_artist, matches, min_score=0.5, artist_threshold=58):
    """Compare l'artiste taggé à l'identification AcoustID.
    Retourne (verdict, id_artist, id_title), verdict ∈ {match, mismatch, unidentified}."""
    from rapidfuzz import fuzz
    cands = [(a, t) for (sc, a, t) in matches if sc >= min_score and a]
    if not cands:
        return ("unidentified", "", "")
    na = normalize_string(tag_artist)
    if not na:
        return ("unidentified", "", "")
    best = max(fuzz.token_set_ratio(na, normalize_string(a)) for a, _ in cands)
    if best >= artist_threshold:
        return ("match", "", "")
    a, t = cands[0]
    return ("mismatch", a, t)


def _ssl_ctx():
    """Contexte SSL robuste, indépendant du Python et du cwd. Priorité : bundle CA
    embarqué (_CA_BUNDLE, chemin figé à l'import) → certifi → système."""
    import ssl
    try:
        if _CA_BUNDLE and os.path.isfile(_CA_BUNDLE):
            return ssl.create_default_context(cafile=_CA_BUNDLE)
    except Exception:
        pass
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    try:
        return ssl.create_default_context()
    except Exception:
        return None


def acoustid_identify(fingerprint, duration, client_key, timeout=15):
    """Lookup AcoustID enrichi (recordings + release groups). Retourne
    {status, candidates, error} ; candidates triés par score."""
    import json, ssl, urllib.request, urllib.parse, urllib.error
    ctx = _ssl_ctx()
    try:
        params = urllib.parse.urlencode({
            "client": client_key, "duration": int(duration), "fingerprint": fingerprint,
            "meta": "recordings releasegroups compress", "format": "json"}).encode("utf-8")
        req = urllib.request.Request(
            ACOUSTID_LOOKUP_URL, data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") != "ok":
            err = ""
            if isinstance(data.get("error"), dict):
                err = data["error"].get("message", "")
            return {"status": "error", "candidates": [], "error": err or "réponse inattendue"}
        cands = []
        for res in data.get("results", []):
            score = float(res.get("score", 0.0))
            for rec in res.get("recordings", []) or []:
                artists = rec.get("artists", []) or []
                artist = ", ".join(a.get("name", "") for a in artists if a.get("name"))
                rgs = []
                for rg in rec.get("releasegroups", []) or []:
                    rgs.append({"id": rg.get("id"), "title": rg.get("title", "") or "",
                                "type": rg.get("type", "") or "",
                                "secondarytypes": rg.get("secondarytypes", []) or []})
                if artist or rec.get("title"):
                    cands.append({"score": score, "artist": artist,
                                  "title": rec.get("title", "") or "",
                                  "recording_mbid": rec.get("id"), "releasegroups": rgs})
        cands.sort(key=lambda c: c["score"], reverse=True)
        return {"status": "ok" if cands else "no_match", "candidates": cands, "error": ""}
    except urllib.error.HTTPError as e:
        msg = ""
        try:
            body = json.loads(e.read().decode("utf-8"))
            if isinstance(body.get("error"), dict):
                msg = body["error"].get("message", "")
        except Exception:
            msg = ""
        return {"status": "error", "candidates": [], "error": msg or ("HTTP %d" % e.code)}
    except Exception as e:
        return {"status": "error", "candidates": [], "error": str(e)[:120]}


def choose_release_group(releasegroups):
    """Heuristique du meilleur album : album studio sans type pénalisé d'abord,
    puis le plus ancien. Retourne (meilleur_ou_None, liste_ordonnée)."""
    def sort_key(rg):
        primary = (rg.get("type") or "").lower()
        secondaries = {s.lower() for s in (rg.get("secondarytypes") or [])}
        has_penalty = 1 if (secondaries & _RG_SECONDARY_PENALTY) else 0
        is_album = 0 if primary == "album" else 1
        date = rg.get("date") or "9999"
        year = date[:4] if date[:4].isdigit() else "9999"
        return (has_penalty, is_album, year, rg.get("title", ""))
    ordered = sorted(releasegroups or [], key=sort_key)
    return (ordered[0] if ordered else None), ordered


def mb_releasegroup_date(rg_mbid, timeout=15):
    """Année de première sortie d'un release group via MusicBrainz, ou ""."""
    import json, ssl, urllib.request, urllib.error
    if not rg_mbid:
        return ""
    ctx = _ssl_ctx()
    try:
        url = "%s/release-group/%s?fmt=json" % (MUSICBRAINZ_WS, rg_mbid)
        req = urllib.request.Request(url, headers={"User-Agent": MB_USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (data.get("first-release-date") or "")[:4]
    except Exception:
        return ""


def caa_front_cover(rg_mbid, size=500, timeout=25):
    """Pochette front d'un release group via Cover Art Archive.
    Retourne (bytes, mime) ou (None, None) si absente."""
    import ssl, urllib.request, urllib.error
    if not rg_mbid:
        return None, None
    ctx = _ssl_ctx()
    try:
        url = "%s/release-group/%s/front-%d" % (COVERART_ARCHIVE, rg_mbid, size)
        req = urllib.request.Request(url, headers={"User-Agent": MB_USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read(), resp.headers.get("Content-Type", "image/jpeg")
    except Exception:
        return None, None


def _has_embedded_cover(path):
    """True si le fichier a déjà une pochette embarquée."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".mp3":
            from mutagen.id3 import ID3, ID3NoHeaderError
            try:
                t = ID3(str(path))
            except ID3NoHeaderError:
                return False
            return any(k.startswith("APIC") for k in t.keys())
        if ext in (".aiff", ".aif", ".wav"):
            from mutagen.aiff import AIFF
            from mutagen.wave import WAVE
            t = (AIFF if ext in (".aiff", ".aif") else WAVE)(str(path)).tags
            return bool(t and any(k.startswith("APIC") for k in t.keys()))
        if ext == ".flac":
            from mutagen.flac import FLAC
            return len(FLAC(str(path)).pictures) > 0
        if ext in (".m4a", ".mp4", ".aac"):
            from mutagen.mp4 import MP4
            t = MP4(str(path)).tags
            return bool(t and t.get("covr"))
    except Exception:
        return False
    return False


def read_current_field(path, field):
    """Lit un champ simple (title/artist), pour la protection de version."""
    ext = os.path.splitext(path)[1].lower()
    frame = {"title": "TIT2", "artist": "TPE1"}[field]
    try:
        if ext == ".mp3":
            from mutagen.id3 import ID3, ID3NoHeaderError
            try:
                t = ID3(str(path))
            except ID3NoHeaderError:
                return ""
            v = t.get(frame)
            return str(v.text[0]) if v and v.text else ""
        if ext in (".aiff", ".aif", ".wav"):
            from mutagen.aiff import AIFF
            from mutagen.wave import WAVE
            audio = (AIFF if ext in (".aiff", ".aif") else WAVE)(str(path))
            t = audio.tags
            if not t:
                return ""
            v = t.get(frame)
            return str(v.text[0]) if v and v.text else ""
        if ext == ".flac":
            from mutagen.flac import FLAC
            return (FLAC(str(path)).get(field) or [""])[0]
        if ext in (".m4a", ".mp4", ".aac"):
            from mutagen.mp4 import MP4
            key = {"title": "\xa9nam", "artist": "\xa9ART"}[field]
            return (MP4(str(path)).get(key) or [""])[0]
    except Exception:
        return ""
    return ""


def write_full_tags(path, meta, cover=None, cover_mime="image/jpeg", protect_version=True):
    """Écrit les champs fournis (non vides). N'ajoute la pochette que si aucune
    n'est présente. Protège le titre s'il porte un marqueur de version.
    meta : artist, title, album, date, genre, tracknumber, albumartist.
    Retourne (ok, info {written:[], skipped:[]})."""
    ext = os.path.splitext(path)[1].lower()
    info = {"written": [], "skipped": []}
    m = dict(meta)

    if protect_version and m.get("title"):
        cur = read_current_field(path, "title")
        if cur and has_version_marker(cur):
            m.pop("title", None)
            info["skipped"].append("titre (version protégée)")

    add_cover = cover is not None and not _has_embedded_cover(path)
    if cover is not None and not add_cover:
        info["skipped"].append("pochette (déjà présente)")

    try:
        if ext in (".mp3", ".aiff", ".aif", ".wav"):
            from mutagen.id3 import (ID3, ID3NoHeaderError, TPE1, TIT2, TALB,
                                     TDRC, TCON, TRCK, TPE2, APIC)
            if ext == ".mp3":
                try:
                    tags = ID3(str(path))
                except ID3NoHeaderError:
                    tags = ID3()
            else:
                from mutagen.aiff import AIFF
                from mutagen.wave import WAVE
                cls = AIFF if ext in (".aiff", ".aif") else WAVE
                audio = cls(str(path))
                if audio.tags is None:
                    audio.add_tags()
                tags = audio.tags
            frame_map = {"artist": ("TPE1", TPE1), "title": ("TIT2", TIT2),
                         "album": ("TALB", TALB), "date": ("TDRC", TDRC),
                         "genre": ("TCON", TCON), "tracknumber": ("TRCK", TRCK),
                         "albumartist": ("TPE2", TPE2)}
            for field, (key, frame_cls) in frame_map.items():
                val = m.get(field)
                if val:
                    tags.setall(key, [frame_cls(encoding=3, text=str(val))])
                    info["written"].append(field)
            if add_cover:
                tags.delall("APIC")
                tags.add(APIC(encoding=3, mime=cover_mime, type=3, desc="Cover", data=cover))
                info["written"].append("cover")
            if ext == ".mp3":
                tags.save(str(path))
            else:
                audio.save()
            return True, info

        if ext == ".flac":
            from mutagen.flac import FLAC, Picture
            audio = FLAC(str(path))
            for field in ("artist", "title", "album", "genre"):
                if m.get(field):
                    audio[field] = str(m[field]); info["written"].append(field)
            if m.get("date"):
                audio["date"] = str(m["date"]); info["written"].append("date")
            if m.get("tracknumber"):
                audio["tracknumber"] = str(m["tracknumber"]); info["written"].append("tracknumber")
            if m.get("albumartist"):
                audio["albumartist"] = str(m["albumartist"]); info["written"].append("albumartist")
            if add_cover:
                pic = Picture(); pic.type = 3; pic.mime = cover_mime; pic.data = cover
                audio.clear_pictures(); audio.add_picture(pic)
                info["written"].append("cover")
            audio.save()
            return True, info

        if ext in (".m4a", ".mp4", ".aac"):
            from mutagen.mp4 import MP4, MP4Cover
            audio = MP4(str(path))
            if audio.tags is None:
                audio.add_tags()
            mp4map = {"artist": "\xa9ART", "title": "\xa9nam", "album": "\xa9alb",
                      "date": "\xa9day", "genre": "\xa9gen", "albumartist": "aART"}
            for field, key in mp4map.items():
                if m.get(field):
                    audio[key] = [str(m[field])]; info["written"].append(field)
            if m.get("tracknumber"):
                try:
                    audio["trkn"] = [(int(str(m["tracknumber"]).split("/")[0]), 0)]
                    info["written"].append("tracknumber")
                except Exception:
                    pass
            if add_cover:
                fmt = MP4Cover.FORMAT_PNG if "png" in (cover_mime or "") else MP4Cover.FORMAT_JPEG
                audio["covr"] = [MP4Cover(cover, imageformat=fmt)]
                info["written"].append("cover")
            audio.save()
            return True, info

        return False, {"written": [], "skipped": [], "error": "format non géré : %s" % ext}
    except Exception as e:
        return False, {"written": [], "skipped": [], "error": str(e)[:120]}


def find_ffmpeg():
    """Cherche ffmpeg : PATH, dossier de l'app, emplacements usuels macOS et Windows."""
    import shutil as _sh
    import sys as _sys
    p = _sh.which("ffmpeg")
    if p:
        return p
    here = os.path.dirname(os.path.abspath(__file__))
    base = getattr(_sys, "_MEIPASS", here)
    candidates = [
        os.path.join(base, "ffmpeg.exe"), os.path.join(base, "ffmpeg"),
        os.path.join(here, "ffmpeg.exe"), os.path.join(here, "ffmpeg"),
        "/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg", "/usr/bin/ffmpeg",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def deep_integrity_check(path, ffmpeg_path, timeout=300, check_clipping=False):
    """Décode via ffmpeg : décodage interrompu, erreurs structurelles, troncature,
    et (si check_clipping) échantillons hors-échelle. severity ∈ {ok, critical}."""
    import subprocess
    try:
        try:
            from mutagen import File as MFile
            mf = MFile(path)
            announced = getattr(mf.info, "length", 0) if mf else 0
        except Exception:
            announced = 0
        if check_clipping:
            # PCM mono FLOAT : les échantillons hors-échelle survivent (en int16 ils
            # seraient écrasés à ±1.0, détruisant la preuve de corruption).
            args = [ffmpeg_path, "-hide_banner", "-v", "error", "-i", str(path),
                    "-f", "f32le", "-ac", "1", "-ar", str(SLIDING_SAMPLE_RATE), "-"]
        else:
            args = [ffmpeg_path, "-hide_banner", "-v", "error", "-stats",
                    "-i", str(path), "-f", "null", "-"]
        result = subprocess.run(args, capture_output=True, timeout=timeout, **_quiet_run())
        stderr_text = result.stderr.decode("utf-8", errors="replace")
        severity = "ok"
        errors = []
        n_crit = sum(1 for l in stderr_text.splitlines()
                     if any(p.search(l) for p in CRITICAL_PATTERNS))
        if result.returncode != 0:
            severity = "critical"
            errors.append("Décodage interrompu (code %d)." % result.returncode)
        if n_crit >= CRIT_ERROR_MIN:
            severity = "critical"
            errors.append("%d erreur(s) de décodage structurelles (trames cassées)." % n_crit)
        decoded_dur = None
        if check_clipping:
            num_samples = len(result.stdout) // 4
            if num_samples > 0:
                decoded_dur = num_samples / SLIDING_SAMPLE_RATE
        else:
            matches = re.findall(r"time=(\d+):(\d+):([\d.]+)", stderr_text)
            if matches:
                h, m, s = matches[-1]
                decoded_dur = int(h) * 3600 + int(m) * 60 + float(s)
        if announced > 1 and decoded_dur and decoded_dur > 0:
            ratio = decoded_dur / announced
            if ratio < 0.90:
                severity = "critical"
                errors.append("Troncature : décodage arrêté à %.1fs sur %.1fs "
                              "annoncées (%.0f%%)." % (decoded_dur, announced, ratio * 100))
        if check_clipping and len(result.stdout) > 0:
            is_corrupt, msg = _oor_verdict(result.stdout)
            if is_corrupt:
                severity = "critical"
                errors.append(msg)
            elif msg:
                errors.append(msg)
        return {"severity": severity, "errors": errors}
    except subprocess.TimeoutExpired:
        return {"severity": "critical",
                "errors": ["Timeout après %ds — fichier probablement gravement corrompu" % timeout]}
    except Exception as e:
        return {"severity": "critical", "errors": ["Exception : %s" % e]}


BK_MTIME_TOL = 2.0


def bk_index(root):
    """{ chemin_relatif: (taille, mtime) } pour tous les fichiers, sauf parasites."""
    index = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not is_junk(d)]
        for fn in filenames:
            if is_junk(fn):
                continue
            full = os.path.join(dirpath, fn)
            try:
                st = os.stat(full)
            except OSError:
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            index[rel] = (st.st_size, st.st_mtime)
    return index


def bk_differs(a, b):
    if a[0] != b[0]:
        return True
    return abs(a[1] - b[1]) > BK_MTIME_TOL


_FN_INVALID = __import__("re").compile(r'[*?"<>|]')


def clean_filename_component(s):
    s = (s or "").replace("\n", " ").replace("\r", " ")
    s = s.replace("/", ", ").replace("\\", ", ")
    s = s.replace(":", " -")
    s = _FN_INVALID.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def _rn_strip_artist_prefix(artist, title):
    if artist and title and title.lower().startswith(("%s - " % artist).lower()):
        return title[len(artist) + 3:].strip()
    return title


def build_track_filename(artist, title, ext):
    """Construit « Artiste - Titre.ext » nettoyé."""
    a = clean_filename_component(artist)
    t = clean_filename_component(_rn_strip_artist_prefix(artist, title))
    if a and t:
        base = "%s - %s" % (a, t)
    else:
        base = t or a or "Sans titre"
    return base[:200] + (ext or "")


def _xml_escape_attr(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def _xml_unescape(s):
    return (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&apos;", "'"))


def usb_mount_and_volume(usb_path):
    """(mount, volume) pour un chemin sous /Volumes/<nom>/… ; sinon (chemin, basename)."""
    parts = os.path.normpath(usb_path).split(os.sep)
    if "Volumes" in parts:
        i = parts.index("Volumes")
        if i + 1 < len(parts):
            mount = os.sep.join(parts[:i + 2]) or os.sep
            return mount, parts[i + 1]
    return usb_path, os.path.basename(os.path.normpath(usb_path))


def physical_to_nml_dir(file_path, mount):
    """Dossier d'un fichier -> DIR Traktor (« /:a/:b/: »)."""
    rel = os.path.relpath(os.path.dirname(file_path), mount)
    parts = [p for p in rel.split(os.sep) if p not in ("", ".")]
    return "/:" + "".join(p + "/:" for p in parts)


def nml_index_locations(nml_text, volume):
    """Index { (dir_nfc, file_nfc) : (dir_raw, file_raw) } pour un volume."""
    import unicodedata
    idx = {}
    loc_re = re.compile(
        r'<LOCATION DIR="([^"]*)" FILE="([^"]*)" VOLUME="' + re.escape(volume) + r'"')
    for m in loc_re.finditer(nml_text):
        dir_raw, file_raw = m.group(1), m.group(2)
        key = (unicodedata.normalize("NFC", _xml_unescape(dir_raw)),
               unicodedata.normalize("NFC", _xml_unescape(file_raw)))
        idx[key] = (dir_raw, file_raw)
    return idx


def nml_rewrite_file(nml_text, dir_raw, old_file_raw, volume, new_file):
    """Remplace l'attribut FILE de la LOCATION ciblée (match exact unique).
    Retourne (texte, n_match). n_match != 1 => on ne touche à rien."""
    needle = '<LOCATION DIR="%s" FILE="%s" VOLUME="%s"' % (dir_raw, old_file_raw, volume)
    n = nml_text.count(needle)
    if n != 1:
        return nml_text, n
    repl = '<LOCATION DIR="%s" FILE="%s" VOLUME="%s"' % (dir_raw, _xml_escape_attr(new_file), volume)
    return nml_text.replace(needle, repl), 1


def _bk_safe_name(name):
    import re as _re
    return _re.sub(r'[<>:"/\\|?*]', "_", name).strip() or "playlist"


def bk_parse_traktor_playlist_tree(nml_path):
    """Parse l'arbre de playlists Traktor en préservant la hiérarchie de dossiers.
    Retourne (playlists, ok) où playlists = [{folders, name, tracks:[rel...]}].
    rel = chemin relatif au volume (ex. 'TRACK BASE/fichier.mp3')."""
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse(str(nml_path))
        root = tree.getroot()
    except Exception:
        return [], False

    def key_to_rel(key):
        if not key:
            return ""
        parts = key.split("/:")
        return "/".join(p for p in parts[1:] if p)

    playlists = []

    def walk(node, path):
        ntype = node.get("TYPE")
        name = node.get("NAME") or ""
        if ntype == "FOLDER":
            sub = node.find("SUBNODES")
            if sub is None:
                return
            new_path = path if name in ("$ROOT", "") else path + [name]
            for child in sub.findall("NODE"):
                walk(child, new_path)
        elif ntype == "PLAYLIST":
            pl = node.find("PLAYLIST")
            if pl is None:
                return
            tracks = []
            for entry in pl.findall("ENTRY"):
                pk = entry.find("PRIMARYKEY")
                if pk is not None and pk.get("TYPE") == "TRACK":
                    rel = key_to_rel(pk.get("KEY", ""))
                    if rel:
                        tracks.append(rel)
            if tracks:
                playlists.append({"folders": list(path),
                                  "name": name or "playlist", "tracks": tracks})

    try:
        pls = root.find("PLAYLISTS")
        nodes = pls.findall("NODE") if pls is not None else []
        if not nodes:
            for node in root.iter("NODE"):
                if node.get("NAME") == "$ROOT":
                    nodes = [node]
                    break
        for node in nodes:
            walk(node, [])
    except Exception:
        return playlists, bool(playlists)
    return playlists, True


def bk_find_collection_nml(root):
    """Cherche collection.nml sur la clé : racine, puis 1 et 2 niveaux en dessous."""
    direct = os.path.join(root, "collection.nml")
    if os.path.isfile(direct):
        return direct
    import glob
    for pat in ("*/collection.nml", "*/*/collection.nml"):
        hits = glob.glob(os.path.join(root, pat))
        if hits:
            return hits[0]
    return None


def bk_copy(src, dst):
    import shutil as _sh
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    _sh.copy2(src, dst)


def bk_supports_hardlinks(dest_dir):
    """True si la destination supporte les liens physiques (HFS+/APFS), False
    sur exFAT/FAT32 — détermine le mode de sauvegarde versionnée."""
    try:
        os.makedirs(dest_dir, exist_ok=True)
        import tempfile as _tf
        with _tf.TemporaryDirectory(dir=str(dest_dir)) as td:
            src = os.path.join(td, "s.tmp")
            dst = os.path.join(td, "d.tmp")
            with open(src, "w") as f:
                f.write("x")
            os.link(src, dst)
            return True
    except (OSError, NotImplementedError):
        return False


def bk_latest_snapshot(backup_root):
    """Dernier snapshot daté présent dans le dossier de sauvegarde, ou None."""
    import glob
    snaps = sorted(p for p in glob.glob(os.path.join(backup_root, "snapshot_*"))
                   if os.path.isdir(p))
    return snaps[-1] if snaps else None


def fix_duplicates_via_playlists(nml_text, mount, volume, groups, master_choices,
                                 backup_dir, usb_root, log=None):
    """Corrige les doublons SANS casser les liens playlist. Pour chaque groupe,
    toute référence (PRIMARYKEY) d'une copie est réécrite vers le master dans la
    section PLAYLISTS ; les copies sont déplacées vers backup_dir (réversible).
    La section COLLECTION n'est pas touchée (les copies deviennent « missing »
    → Remove Missing dans Traktor). Retourne (new_nml_text, stats)."""
    import unicodedata
    import shutil
    idx = nml_index_locations(nml_text, volume)

    def nml_key(path):
        try:
            d = physical_to_nml_dir(path, mount)
            k = (unicodedata.normalize("NFC", d),
                 unicodedata.normalize("NFC", os.path.basename(path)))
            raw = idx.get(k)
            if not raw:
                return None
            dir_raw, file_raw = raw
            return "%s%s%s" % (volume, dir_raw, file_raw)
        except Exception:
            return None

    def move_to_backup(path):
        try:
            rel = os.path.relpath(path, usb_root)
        except Exception:
            rel = os.path.basename(path)
        target = os.path.join(backup_dir, rel)
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.move(path, target)
            return True
        except Exception as e:
            if log:
                log("   ✗ Déplacement impossible : %s — %s" % (os.path.basename(path), e))
            return False

    new_text = nml_text
    n_repointed = n_groups = n_moved = 0
    moved = []

    for key, group in groups.items():
        master_path = master_choices.get(key) or ""
        master_key = nml_key(master_path) if master_path not in ("", ".") else None
        if master_key is None:
            in_coll = [t for t in group if nml_key(t["path"]) is not None]
            if not in_coll:
                # Aucune version dans la collection : groupe hors playlists.
                master = select_master(group)
                for t in group:
                    if t["path"] == master["path"]:
                        continue
                    if move_to_backup(t["path"]):
                        n_moved += 1
                        moved.append(t["path"])
                continue
            master = select_master(in_coll)
            master_path = master["path"]
            master_key = nml_key(master_path)
            if log:
                log("   ⚠ Master remplacé (le choisi était hors collection) : %s"
                    % os.path.basename(master_path))

        n_groups += 1
        for t in group:
            p = t["path"]
            if p == master_path:
                continue
            ckey = nml_key(p)
            if ckey and ckey != master_key:
                needle = 'KEY="%s"' % ckey
                cnt = new_text.count(needle)
                if cnt:
                    new_text = new_text.replace(needle, 'KEY="%s"' % master_key)
                    n_repointed += cnt
            if move_to_backup(p):
                n_moved += 1
                moved.append(p)

    return new_text, {"n_repointed": n_repointed, "n_groups": n_groups,
                      "n_moved": n_moved, "moved_files": moved}


def restore_from_backup(backup_dir, usb_root, log=None):
    """Restaure les fichiers depuis backup_dir vers leur emplacement d'origine.
    Si l'extension a changé entretemps, supprime le fichier au nouveau suffixe.
    Retourne {n_restored, n_failed}."""
    import shutil
    import glob
    n_restored = n_failed = 0
    for dirpath, dirnames, filenames in os.walk(backup_dir):
        for name in filenames:
            f = os.path.join(dirpath, name)
            try:
                rel = os.path.relpath(f, backup_dir)
                original = os.path.join(usb_root, rel)
                os.makedirs(os.path.dirname(original), exist_ok=True)
                stem = os.path.splitext(os.path.basename(original))[0]
                oext = os.path.splitext(original)[1].lower()
                for sib in glob.glob(os.path.join(os.path.dirname(original), stem + ".*")):
                    if os.path.splitext(sib)[1].lower() != oext:
                        try:
                            os.unlink(sib)
                        except Exception:
                            pass
                shutil.copy2(f, original)
                n_restored += 1
            except Exception as e:
                n_failed += 1
                if log:
                    log("   ✗ Échec restauration : %s — %s" % (f, e))
    return {"n_restored": n_restored, "n_failed": n_failed}


class Core:
    def __init__(self):
        self.music_folder = ""
        self.usb_root = ""
        self.acoustid_key = ""
        self.lang = "en"
        self.last_vault_nml_hash = ""
        self.tracks = []
        self._scan_cache = {}
        self._acoustid_cache = {}
        self._enrich_cache = {}
        self._audiofp_cache = {}
        self._integ_cache = {}
        self._last_dup_groups = []
        self._load_config()
        self._load_scan_cache()
        self._load_acoustid_cache()
        self._load_enrich_cache()
        self._load_audiofp_cache()
        self._load_integ_cache()
        self._load_backup_log()

    # ----- état / config -----
    def _config_path(self):
        d = os.path.join(os.path.expanduser("~"), ".djhelper")
        return os.path.join(d, "config.json")

    def _load_config(self):
        try:
            import json
            with open(self._config_path(), encoding="utf-8") as f:
                data = json.load(f)
            self.music_folder = (data.get("music_folder") or "").strip()
            self.usb_root = (data.get("usb_root") or "").strip()
            self.acoustid_key = (data.get("acoustid_key") or "").strip()
            self.lang = (data.get("lang") or "en").strip() or "en"
            self.last_vault_nml_hash = data.get("last_vault_nml_hash") or ""
        except Exception:
            pass

    def _save_config(self):
        try:
            import json
            p = self._config_path()
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"music_folder": self.music_folder,
                           "usb_root": self.usb_root,
                           "acoustid_key": self.acoustid_key,
                           "lang": getattr(self, "lang", "en"),
                           "last_vault_nml_hash": getattr(self, "last_vault_nml_hash", "")},
                          f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def set_lang(self, lang):
        self.lang = "fr" if (lang or "").strip().lower() == "fr" else "en"
        self._save_config()
        return {"ok": True, "lang": self.lang}

    def set_acoustid_key(self, key):
        self.acoustid_key = (key or "").strip()
        self._save_config()
        return {"ok": True}

    # ----- cache AcoustID (clé relative au dossier, validité = taille) -----
    def _acoustid_cache_path(self):
        return os.path.join(os.path.expanduser("~"), ".djhelper", "acoustid_cache.json")

    def _load_acoustid_cache(self):
        self._acoustid_cache = {}
        try:
            import json
            with open(self._acoustid_cache_path(), encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._acoustid_cache = data
        except Exception:
            self._acoustid_cache = {}

    def _save_acoustid_cache(self):
        try:
            import json
            p = self._acoustid_cache_path()
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self._acoustid_cache, f, ensure_ascii=False)
        except Exception:
            pass

    # ----- cache enrichissement (stocke le lookup AcoustID par fichier) -----
    def _enrich_cache_path(self):
        return os.path.join(os.path.expanduser("~"), ".djhelper", "enrich_cache.json")

    def _load_enrich_cache(self):
        self._enrich_cache = {}
        try:
            import json
            with open(self._enrich_cache_path(), encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._enrich_cache = data
        except Exception:
            self._enrich_cache = {}

    def _save_enrich_cache(self):
        try:
            import json
            p = self._enrich_cache_path()
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self._enrich_cache, f, ensure_ascii=False)
        except Exception:
            pass

    def _enrich_get_cached(self, path):
        try:
            rel = os.path.relpath(path, self.music_folder)
        except Exception:
            rel = path
        ent = self._enrich_cache.get(rel)
        if not ent:
            return None
        lk = ent.get("lk")
        if isinstance(lk, dict) and lk.get("status") == "error":
            return None   # ancienne erreur (SSL/réseau) en cache : on réessaie
        try:
            if ent.get("size") != os.path.getsize(path):
                return None
        except Exception:
            return None
        return ent

    def _enrich_store(self, path, lk):
        # Ne jamais cacher un échec réseau/SSL (status "error") : sinon l'erreur
        # est rejouée indéfiniment sans nouvelle requête. On ne cache que les
        # lookups aboutis (ok / no_match).
        if isinstance(lk, dict) and lk.get("status") == "error":
            return
        try:
            rel = os.path.relpath(path, self.music_folder)
            self._enrich_cache[rel] = {"lk": lk, "size": os.path.getsize(path)}
        except Exception:
            pass

    # ----- cache empreintes audio raw (pour détection de doublons par le son) -----
    def _audiofp_cache_path(self):
        return os.path.join(os.path.expanduser("~"), ".djhelper", "audiofp_cache.json")

    def _load_audiofp_cache(self):
        self._audiofp_cache = {}
        try:
            import json
            with open(self._audiofp_cache_path(), encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._audiofp_cache = data
        except Exception:
            self._audiofp_cache = {}

    def _save_audiofp_cache(self):
        try:
            import json
            p = self._audiofp_cache_path()
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self._audiofp_cache, f, ensure_ascii=False)
        except Exception:
            pass

    # ----- cache de scan (tags lus, invalidés par taille+date) -----
    def _scan_cache_path(self):
        return os.path.join(os.path.expanduser("~"), ".djhelper", "scan_cache.json")

    def _load_scan_cache(self):
        self._scan_cache = {}
        try:
            import json
            with open(self._scan_cache_path(), encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._scan_cache = data
        except Exception:
            self._scan_cache = {}

    def _save_scan_cache(self):
        try:
            import json
            p = self._scan_cache_path()
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self._scan_cache, f)
        except Exception:
            pass

    def _read_tags_cached(self, path):
        try:
            st = os.stat(path)
            sig = [st.st_size, int(st.st_mtime)]
        except OSError:
            return self._read_tags(path)
        ent = self._scan_cache.get(path)
        if ent and ent.get("sig") == sig:
            return {"artist": ent["artist"], "title": ent["title"],
                    "bitrate": ent["bitrate"], "duration": ent["duration"]}
        tags = self._read_tags(path)
        self._scan_cache[path] = {"sig": sig, "artist": tags["artist"],
                                  "title": tags["title"], "bitrate": tags["bitrate"],
                                  "duration": tags["duration"]}
        return tags

    def set_music_folder(self, path):
        self.music_folder = (path or "").strip()
        self.tracks = []
        self._save_config()
        return {"ok": True, "path": self.music_folder}

    def set_usb_root(self, path):
        self.usb_root = (path or "").strip()
        self._save_config()
        return {"ok": True, "path": self.usb_root,
                "valid": bool(self.usb_root and os.path.isdir(self.usb_root))}

    def _sync_source(self):
        """Source à synchroniser : la racine de la clé si définie, sinon le dossier audio."""
        if self.usb_root and os.path.isdir(self.usb_root):
            return self.usb_root
        return self.music_folder

    def reveal_file(self, path):
        """Ouvre le fichier dans le gestionnaire de fichiers et le sélectionne si
        possible. macOS : Finder ; Windows : Explorateur ; Linux : dossier parent.
        Repli sur le dossier parent si le fichier exact est introuvable."""
        import sys
        import subprocess
        try:
            if not path:
                return {"ok": False, "error": "Chemin vide"}
            exists = os.path.exists(path)
            folder = os.path.dirname(path)
            if sys.platform == "darwin":
                if exists:
                    subprocess.Popen(["/usr/bin/open", "-R", path])
                elif os.path.isdir(folder):
                    subprocess.Popen(["/usr/bin/open", folder])
                else:
                    return {"ok": False, "error": "Introuvable : " + path}
            elif sys.platform.startswith("win"):
                if exists:
                    subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
                elif os.path.isdir(folder):
                    subprocess.Popen(["explorer", os.path.normpath(folder)])
                else:
                    return {"ok": False, "error": "Introuvable : " + path}
            else:
                target = folder if os.path.isdir(folder) else path
                subprocess.Popen(["xdg-open", target])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)[:150]}

    def compute_status(self):
        """État global de l'app (réplique du statut Tkinter) : renvoie le pire
        niveau parmi les vérifications + le détail de chacune."""
        items = []
        usb = (self.usb_root or "").strip()
        if usb and os.path.isdir(usb):
            items.append({"label": "Racine de la clé", "level": "ok",
                          "detail": usb, "nav": "home"})
        elif usb:
            items.append({"label": "Racine de la clé", "level": "error",
                          "detail": "Chemin renseigné mais introuvable (clé débranchée ?)",
                          "nav": "home"})
        else:
            items.append({"label": "Racine de la clé", "level": "warning",
                          "detail": "Non définie", "nav": "home"})
        if self.tracks:
            items.append({"label": "Bibliothèque indexée", "level": "ok",
                          "detail": "%d fichiers" % len(self.tracks), "nav": "home"})
        else:
            items.append({"label": "Bibliothèque indexée", "level": "warning",
                          "detail": "Pas encore scannée", "nav": "home"})
        ff = find_ffmpeg()
        if ff:
            items.append({"label": "ffmpeg", "level": "ok", "detail": ff, "nav": "home"})
        else:
            items.append({"label": "ffmpeg", "level": "warning",
                          "detail": "Non installé — analyse approfondie indisponible",
                          "nav": "home"})
        fp = find_fpcalc()
        if fp:
            items.append({"label": "fpcalc", "level": "ok", "detail": fp, "nav": "home"})
        else:
            items.append({"label": "fpcalc", "level": "warning",
                          "detail": "Non installé — doublons par empreinte et AcoustID indisponibles",
                          "nav": "home"})
        if (self.acoustid_key or "").strip():
            items.append({"label": "Clé AcoustID", "level": "ok",
                          "detail": "Configurée", "nav": "home"})
        else:
            items.append({"label": "Clé AcoustID", "level": "warning",
                          "detail": "Non configurée — enrichissement et vérification du contenu indisponibles",
                          "nav": "home"})
        if any(i["level"] == "error" for i in items):
            level = "error"
        elif any(i["level"] == "warning" for i in items):
            level = "warning"
        else:
            level = "ok"
        return {"level": level, "items": items}

    # ===== Journal des sauvegardes (date + état de référence par type) =====
    BACKUP_KINDS = [
        ("spare", "Clé de secours"),
        ("structure", "Sauvegarde de structure"),
        ("m3u", "Coffre-fort de playlists"),
        ("full", "Sauvegarde complète"),
    ]

    def _backup_log_path(self):
        return os.path.join(os.path.expanduser("~"), ".djhelper", "backups_log.json")

    def _load_backup_log(self):
        self._backup_log = {}
        try:
            import json
            with open(self._backup_log_path(), encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._backup_log = data
        except Exception:
            self._backup_log = {}

    def _save_backup_log(self):
        try:
            import json
            p = self._backup_log_path()
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self._backup_log, f, ensure_ascii=False)
        except Exception:
            pass

    def _backup_ref(self):
        """Signe compact de la bibliothèque (nombre de fichiers + taille totale).
        Sert à détecter qu'une sauvegarde n'est plus à jour."""
        if self.tracks:
            return {"count": len(self.tracks),
                    "size": sum(t.get("size", 0) or 0 for t in self.tracks)}
        # repli : compter les fichiers du dossier audio sans lire les tags
        n = 0
        size = 0
        try:
            for p in self._list_audio_paths():
                n += 1
                try:
                    size += os.path.getsize(p)
                except OSError:
                    pass
        except Exception:
            pass
        return {"count": n, "size": size}

    def _playlist_tree_hash(self):
        """Empreinte de la STRUCTURE des playlists Traktor (noms + contenu),
        pour détecter une réorganisation dans Traktor même sans changement de
        fichiers. None si la clé/collection.nml est indisponible. Mise en cache
        par (mtime, taille) du nml pour ne pas re-parser à chaque accueil."""
        import hashlib
        usb = (self.usb_root or "").strip()
        if not usb or not os.path.isdir(usb):
            return None
        nml = bk_find_collection_nml(usb)
        if not nml:
            return None
        try:
            st = os.stat(nml)
            key = (st.st_mtime_ns, st.st_size)
            cached = getattr(self, "_ptree_cache", None)
            if cached and cached[0] == key:
                return cached[1]
            playlists, ok = bk_parse_traktor_playlist_tree(nml)
            if not ok:
                return None
            parts = []
            for pl in sorted(playlists, key=lambda p: p.get("name", "")):
                parts.append(pl.get("name", ""))
                parts.extend(pl.get("tracks", []))
            h = hashlib.sha1("\n".join(parts).encode("utf-8", "replace")).hexdigest()
            self._ptree_cache = (key, h)
            return h
        except Exception:
            return None

    def _backup_log_record(self, kind):
        """Enregistre qu'une sauvegarde vient d'être effectuée avec succès."""
        import datetime
        try:
            self._backup_log[kind] = {
                "last": datetime.datetime.now().isoformat(timespec="seconds"),
                "ref": self._backup_ref(),
                "ptree": self._playlist_tree_hash()}
            self._save_backup_log()
        except Exception:
            pass

    def backups_status(self):
        """Pour chaque type de sauvegarde : jamais faite / à jour / à refaire."""
        cur = self._backup_ref()
        cur_ptree = self._playlist_tree_hash()
        out = []
        for key, label in self.BACKUP_KINDS:
            ent = (getattr(self, "_backup_log", {}) or {}).get(key)
            if not ent:
                out.append({"key": key, "label": label, "state": "none",
                            "last": None})
                continue
            ref = ent.get("ref") or {}
            stale = (ref.get("count") != cur["count"]
                     or ref.get("size") != cur["size"])
            # réorganisation de playlists dans Traktor (structure), même sans
            # changement de fichiers — vérifiable seulement si clé branchée et
            # empreinte enregistrée à la dernière sauvegarde
            if not stale and cur_ptree and ent.get("ptree") and ent["ptree"] != cur_ptree:
                stale = True
            out.append({"key": key, "label": label,
                        "state": "stale" if stale else "ok",
                        "last": ent.get("last")})
        if any(o["state"] == "none" for o in out):
            level = "warning"
        elif any(o["state"] == "stale" for o in out):
            level = "warning"
        else:
            level = "ok"
        return {"level": level, "items": out}

    def home_stats(self):
        """Agrège les indicateurs de l'accueil. Les 4 premiers sont dérivés du
        scan (gratuits) ; corrompus et son≠tags sont lus dans les caches (dernier
        résultat connu, jamais recalculés ici)."""
        LOSSLESS = {"wav", "aiff", "aif", "flac", "alac"}
        LOW_TH = 256  # kbps : en dessous = qualité perfectible (formats compressés only)
        tracks = self.tracks
        count = len(tracks)
        total_size = sum(t.get("size", 0) or 0 for t in tracks)
        by_format = {}
        low_q = 0
        missing = 0
        for t in tracks:
            e = (t.get("ext") or "?").lower()
            by_format[e] = by_format.get(e, 0) + 1
            br = t.get("bitrate") or 0
            if e not in LOSSLESS and 0 < br < LOW_TH and br <= 1000:
                low_q += 1
            if not t.get("has_tags"):
                missing += 1
        fmt_sorted = sorted(by_format.items(), key=lambda kv: -kv[1])

        # corrompus : depuis le cache d'intégrité
        ic = getattr(self, "_integ_cache", {}) or {}
        integ_analyzed = len(ic)
        integ_bad = sum(1 for v in ic.values() if v.get("severity") not in (None, "ok"))
        integ_state = ("none" if integ_analyzed == 0
                       else "stale" if integ_analyzed < count
                       else "ok")
        # son ≠ tags : depuis le cache AcoustID
        ac = getattr(self, "_acoustid_cache", {}) or {}
        ac_analyzed = len(ac)
        ac_mismatch = sum(1 for v in ac.values() if v.get("verdict") == "mismatch")
        ac_state = ("none" if ac_analyzed == 0
                    else "stale" if ac_analyzed < count
                    else "ok")

        return {
            "count": count,
            "total_size": total_size, "total_size_h": human_size(total_size),
            "by_format": dict(fmt_sorted),
            "formats_h": " · ".join("%s %d" % (k.upper(), v) for k, v in fmt_sorted[:4]),
            "n_formats": len(by_format),
            "low_quality": low_q, "low_quality_th": LOW_TH,
            "missing_tags": missing,
            "integ": {"state": integ_state, "bad": integ_bad, "analyzed": integ_analyzed},
            "mismatch": {"state": ac_state, "bad": ac_mismatch, "analyzed": ac_analyzed},
        }

    def get_state(self):
        free = None
        total = None
        if self.music_folder and os.path.isdir(self.music_folder):
            try:
                du = shutil.disk_usage(self.music_folder)
                free = human_size(du.free)
                total = human_size(du.total)
            except Exception:
                pass
        return {
            "music_folder": self.music_folder,
            "configured": bool(self.music_folder and os.path.isdir(self.music_folder)),
            "usb_root": self.usb_root,
            "usb_configured": bool(self.usb_root and os.path.isdir(self.usb_root)),
            "acoustid_key": self.acoustid_key,
            "lang": getattr(self, "lang", "en"),
            "fpcalc": find_fpcalc() or "",
            "ffmpeg": find_ffmpeg() or "",
            "free": free,
            "total": total,
            "count": len(self.tracks),
        }

    # ----- scan bibliothèque -----
    def _build_track(self, path, name):
        ext = os.path.splitext(name)[1].lower()
        stem = os.path.splitext(name)[0]
        tags = self._read_tags_cached(path)
        raw_a, raw_t = tags["artist"], tags["title"]

        fa, ft = parse_filename(stem)
        has_tags = bool(raw_a and raw_t)
        art2 = _prefer_readable(raw_a, fa)
        tit2 = _prefer_readable(raw_t, ft)
        if art2 != raw_a or tit2 != raw_t:
            has_tags = False
        artist = art2 or fa or ""
        title = tit2 or ft or ""

        if artist and title:
            key_title = _rn_strip_artist_prefix(artist, title) or title
            key = normalize_string("%s %s" % (artist, key_title), keep_versions=True)
        else:
            key = normalize_string(stem, keep_versions=True)

        try:
            size = os.path.getsize(path)
        except Exception:
            size = 0

        return {
            "path": path, "name": name, "ext": ext.lstrip("."),
            "artist": artist, "title": title, "normalized_key": key,
            "match_candidates": match_candidates(artist, title),
            "has_tags": has_tags, "bitrate": tags["bitrate"],
            "duration": tags["duration"], "duration_h": fmt_duration(tags["duration"]),
            "size": size, "size_h": human_size(size),
        }

    def _list_audio_paths(self):
        d = self.music_folder
        if not (d and os.path.isdir(d)):
            return None
        out = []
        for entry in os.scandir(d):
            try:
                if not entry.is_file():
                    continue
            except Exception:
                continue
            if is_junk(entry.name):
                continue
            if os.path.splitext(entry.name)[1].lower() in SUPPORTED:
                out.append((entry.path, entry.name))
        return out

    # --- scan en lots (pour barre de progression) ---
    def scan_begin(self):
        paths = self._list_audio_paths()
        if paths is None:
            self._scan_paths = []
            return {"ok": False, "error": "Dossier introuvable", "total": 0}
        self._scan_paths = paths
        self._scan_done = 0
        self.tracks = []
        return {"ok": True, "total": len(paths)}

    def scan_step(self, count=150):
        paths = getattr(self, "_scan_paths", [])
        start = getattr(self, "_scan_done", 0)
        end = min(start + count, len(paths))
        for i in range(start, end):
            self.tracks.append(self._build_track(paths[i][0], paths[i][1]))
        self._scan_done = end
        finished = end >= len(paths)
        if finished:
            self.tracks.sort(key=lambda t: (t["artist"].lower(), t["title"].lower()))
            mf = self.music_folder
            scanned = set(p for p, _ in paths)
            self._scan_cache = {p: e for p, e in self._scan_cache.items()
                                if p in scanned or not (mf and p.startswith(mf))}
            self._save_scan_cache()
        return {"done": end, "total": len(paths), "finished": finished}

    def scan_library(self):
        begin = self.scan_begin()
        if not begin.get("ok"):
            return {"ok": False, "error": begin.get("error", ""), "tracks": [], "count": 0}
        while not self.scan_step(500)["finished"]:
            pass
        return {"ok": True, "count": len(self.tracks), "tracks": self.tracks}

    def _read_tags(self, path):
        """artist/title BRUTS (par format, comme le Tkinter) + bitrate/durée."""
        info = {"artist": "", "title": "", "bitrate": None, "duration": None}
        try:
            from mutagen import File as MFile
            mf = MFile(path)
            if mf is not None and getattr(mf, "info", None) is not None:
                info["duration"] = getattr(mf.info, "length", None)
                br = getattr(mf.info, "bitrate", 0) or 0
                info["bitrate"] = int(br / 1000) if br else None
        except Exception:
            pass
        a, t = _read_artist_title(path)
        info["artist"] = a or ""
        info["title"] = t or ""
        return info

    # ----- doublons (porté du Tkinter : detect_duplicates + select_master) -----
    def find_duplicates(self):
        # toujours re-scanner : détecte les fichiers ajoutés/retirés depuis
        # le dernier scan (le cache de tags garde l'opération rapide)
        res = self.scan_library()
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error", "Scan impossible"),
                    "groups": [], "n_groups": 0}

        groups = {}
        for t in self.tracks:
            key = t.get("normalized_key", "")
            # Ignorer les fichiers non identifiés (sans artiste/titre déduit)
            if not key or not (t["artist"] and t["title"]):
                continue
            groups.setdefault(key, []).append(t)

        dups = []
        for key, items in groups.items():
            if len(items) < 2:
                continue
            master = select_master(items)
            rest = sorted([v for v in items if v is not master],
                          key=lambda x: -(x["bitrate"] or 0))
            ordered = [master] + rest
            for v in ordered:
                v["keep"] = (v is master)
            dups.append({
                "artist": master["artist"],
                "title": master["title"],
                "n": len(items),
                "versions": ordered,
            })

        dups.sort(key=lambda g: (g["artist"].lower(), g["title"].lower()))
        self._last_dup_groups = dups
        return {"ok": True, "groups": dups, "n_groups": len(dups)}

    # ----- résolution des doublons (repointage playlists + backup réversible) -----
    def _dup_usb(self):
        usb = (self.usb_root or "").strip()
        if usb and os.path.isdir(usb):
            return usb
        return ""

    def orphan_tracks(self):
        """Morceaux de la bibliothèque référencés dans AUCUNE playlist Traktor.
        Nécessite collection.nml sur la clé. Comparaison par nom de fichier
        (fiable pour une TRACK BASE plate à noms uniques)."""
        usb = (self.usb_root or "").strip()
        if not usb or not os.path.isdir(usb):
            return {"ok": False, "error": "Racine de la clé non définie ou introuvable."}
        nml = bk_find_collection_nml(usb)
        if not nml:
            return {"ok": False, "error": "collection.nml introuvable sur la clé."}
        try:
            playlists, ok = bk_parse_traktor_playlist_tree(nml)
        except Exception as e:
            return {"ok": False, "error": "Lecture des playlists impossible : %s" % str(e)[:100]}
        if not ok:
            return {"ok": False, "error": "Aucune playlist lisible dans collection.nml."}
        in_pl = set()
        for pl in playlists:
            for rel in pl.get("tracks", []):
                base = os.path.basename(rel).lower()
                if base:
                    in_pl.add(base)
        res = self.scan_library()   # re-scan frais : prend en compte les fichiers ajoutés
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error", "Scan impossible")}
        orphans = [{"name": t["name"], "path": t["path"]}
                   for t in self.tracks
                   if os.path.basename(t["path"]).lower() not in in_pl]
        orphans.sort(key=lambda x: x["name"].lower())
        self._last_orphans = orphans
        return {"ok": True, "n_playlists": len(playlists),
                "n_in_playlist": len(in_pl), "n_total": len(self.tracks),
                "n_orphans": len(orphans), "orphans": orphans}

    def set_dup_master(self, path):
        """Choix manuel du master : dans le groupe contenant `path`, marque cette
        version comme celle à garder (keep=True) et les autres à False."""
        for g in getattr(self, "_last_dup_groups", []):
            vers = g.get("versions", [])
            if any(v.get("path") == path for v in vers):
                for v in vers:
                    v["keep"] = (v.get("path") == path)
                return {"ok": True}
        return {"ok": False, "error": "Version introuvable"}

    def resolve_duplicates(self):
        """Repointe les playlists Traktor vers le master dans collection.nml puis
        déplace les copies en trop vers un backup horodaté sur la clé. Réversible."""
        import datetime
        usb = self._dup_usb()
        if not usb:
            return {"ok": False, "error": "Configure la racine de ta clé (onglet Synchro) : "
                                          "indispensable pour repointer les playlists."}
        dup = self.find_duplicates() if not getattr(self, "_last_dup_groups", None) else None
        if dup is not None and not dup.get("ok"):
            return {"ok": False, "error": dup.get("error", "Scan impossible")}
        groups_list = self._last_dup_groups
        if not groups_list:
            return {"ok": False, "error": "Aucun doublon à corriger."}
        mount, volume = usb_mount_and_volume(usb)
        nml_path = bk_find_collection_nml(mount) or bk_find_collection_nml(usb)
        if not nml_path or not os.path.isfile(nml_path):
            return {"ok": False, "error": "collection.nml introuvable sur la clé : "
                                          "impossible de repointer les playlists."}
        groups, master_choices = {}, {}
        for i, g in enumerate(groups_list):
            key = str(i)
            versions = g["versions"]
            groups[key] = versions
            master = next((v for v in versions if v.get("keep")), None) or select_master(versions)
            master_choices[key] = master["path"]
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(usb, "_doublons_backup_%s" % ts)
        try:
            with open(nml_path, encoding="utf-8") as f:
                nml_text = f.read()
        except Exception as e:
            return {"ok": False, "error": "Lecture collection.nml impossible : %s" % e}
        nml_bak = (nml_path[:-4] if nml_path.lower().endswith(".nml") else nml_path) \
            + "_%s.nml.bak" % ts
        try:
            with open(nml_bak, "w", encoding="utf-8") as f:
                f.write(nml_text)
        except Exception as e:
            return {"ok": False, "error": "Sauvegarde collection.nml impossible : %s" % e}
        new_text, stats = fix_duplicates_via_playlists(
            nml_text, mount, volume, groups, master_choices, backup_dir, usb)
        try:
            tmp = nml_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(new_text)
            os.replace(tmp, nml_path)
        except Exception as e:
            return {"ok": False, "error": "Écriture collection.nml impossible : %s" % e}
        self.tracks = []  # fichiers déplacés : forcer un vrai re-scan disque au prochain appel
        return {"ok": True, "n_repointed": stats["n_repointed"], "n_moved": stats["n_moved"],
                "n_groups": stats["n_groups"], "nml_backup": os.path.basename(nml_bak),
                "backup_dir": os.path.basename(backup_dir)}

    def dup_backup_info(self):
        """Présence et poids cumulé des backups de doublons sur la clé."""
        import glob
        usb = self._dup_usb()
        if not usb:
            return {"ok": True, "count": 0, "bytes": 0}
        backups = [b for b in glob.glob(os.path.join(usb, "_doublons_backup_*"))
                   if os.path.isdir(b)]
        total = 0
        for b in backups:
            for dirpath, dirnames, filenames in os.walk(b):
                for fn in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, fn))
                    except Exception:
                        pass
        return {"ok": True, "count": len(backups), "bytes": total}

    def restore_duplicates(self):
        """Restaure les fichiers depuis le dernier backup de doublons."""
        import glob
        usb = self._dup_usb()
        if not usb:
            return {"ok": False, "error": "Racine de la clé non configurée."}
        backups = sorted((b for b in glob.glob(os.path.join(usb, "_doublons_backup_*"))
                          if os.path.isdir(b)), reverse=True)
        if not backups:
            return {"ok": False, "error": "Aucun backup trouvé sur la clé."}
        res = restore_from_backup(backups[0], usb)
        self.tracks = []  # fichiers restaurés : forcer un vrai re-scan disque
        return {"ok": True, "n_restored": res["n_restored"], "n_failed": res["n_failed"],
                "backup_dir": os.path.basename(backups[0])}

    def clean_dup_backups(self):
        """Supprime tous les backups de doublons (libère l'espace, irréversible)."""
        import glob
        import shutil
        usb = self._dup_usb()
        if not usb:
            return {"ok": False, "error": "Racine de la clé non configurée."}
        backups = [b for b in glob.glob(os.path.join(usb, "_doublons_backup_*"))
                   if os.path.isdir(b)]
        if not backups:
            return {"ok": False, "error": "Aucun backup à supprimer."}
        removed, freed = 0, 0
        for b in backups:
            for dirpath, dirnames, filenames in os.walk(b):
                for fn in filenames:
                    try:
                        freed += os.path.getsize(os.path.join(dirpath, fn))
                    except Exception:
                        pass
            try:
                shutil.rmtree(b)
                removed += 1
            except Exception:
                pass
        return {"ok": True, "removed": removed, "freed": freed}

    # ----- détection de doublons par EMPREINTE AUDIO (le son, pas les tags) -----
    def _audiofp_get_cached(self, path):
        try:
            rel = os.path.relpath(path, self.music_folder)
        except Exception:
            rel = path
        ent = self._audiofp_cache.get(rel)
        if not ent:
            return None
        try:
            if ent.get("size") != os.path.getsize(path):
                return None
        except Exception:
            return None
        return ent

    def _audiofp_store(self, path, fp, dur):
        try:
            rel = os.path.relpath(path, self.music_folder)
            self._audiofp_cache[rel] = {"size": os.path.getsize(path), "dur": dur, "fp": fp}
        except Exception:
            pass

    def audiodup_begin(self, threshold=0.85):
        fpcalc = find_fpcalc()
        if not fpcalc:
            return {"ok": False, "total": 0,
                    "error": "fpcalc introuvable — installe-le depuis la carte Configuration (accueil)."}
        res = self.scan_library()  # métadonnées (tags, bitrate, taille) pour l'affichage
        if not res.get("ok"):
            return {"ok": False, "total": 0, "error": res.get("error", "Scan impossible")}
        self._adup_fpcalc = fpcalc
        self._adup_threshold = float(threshold)
        self._adup_paths = [t["path"] for t in self.tracks]
        self._adup_track_by_path = {t["path"]: t for t in self.tracks}
        self._adup_data = {}   # path -> {"fp":[ints], "dur":float}
        self._adup_i = 0
        self._adup_failed = 0
        return {"ok": True, "total": len(self._adup_paths)}

    def audiodup_cancel(self):
        """Interruption : conserve les empreintes déjà calculées (cache) pour que
        la prochaine analyse reparte de là."""
        self._save_audiofp_cache()
        return {"ok": True}

    def audiodup_step(self, count=8):
        import concurrent.futures
        paths = self._adup_paths
        start = self._adup_i
        end = min(start + count, len(paths))
        batch = paths[start:end]
        to_calc = []
        for p in batch:
            ent = self._audiofp_get_cached(p)
            if ent is not None and ent.get("fp"):
                self._adup_data[p] = {"fp": ent["fp"], "dur": ent.get("dur") or 0.0}
            else:
                to_calc.append(p)
        if to_calc:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                futs = {ex.submit(acoustid_fingerprint_raw, p, self._adup_fpcalc): p
                        for p in to_calc}
                for fut in concurrent.futures.as_completed(futs):
                    p = futs[fut]
                    try:
                        fp, dur = fut.result()
                    except Exception:
                        fp, dur = None, None
                    if fp:
                        self._adup_data[p] = {"fp": fp, "dur": dur or 0.0}
                        self._audiofp_store(p, fp, dur or 0.0)
                    else:
                        self._adup_failed += 1
        self._adup_i = end
        finished = end >= len(paths)
        if finished:
            self._save_audiofp_cache()
        return {"done": end, "total": len(paths), "finished": finished, "result": None}

    def audiodup_finalize(self):
        """Phase d'appariement, séparée du calcul des empreintes pour ne pas figer
        l'UI « à 100 % » : appelée explicitement après la dernière empreinte."""
        result = self._audiodup_match()
        result["n_failed"] = self._adup_failed
        return result

    def _audiodup_match(self, dur_tol=2.0, max_offset=8):
        """Apparie les fichiers par similarité d'empreinte. Pré-filtre serré par
        durée (deux copies du même morceau ont la même durée) + court-circuit à
        l'offset 0 pour éviter de tester tous les décalages sur chaque paire."""
        import numpy as np
        items = [(p, d["fp"], d.get("dur") or 0.0)
                 for p, d in self._adup_data.items() if d.get("fp")]
        n = len(items)
        if n < 2:
            return {"ok": True, "groups": [], "n_groups": 0}
        arrs = [np.array(fp, dtype=np.int64).astype(np.uint32) for _, fp, _ in items]
        durs = [d for _, _, d in items]
        th = self._adup_threshold
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        order = sorted(range(n), key=lambda i: durs[i])
        pair_sim = {}
        for a in range(n):
            i = order[a]
            ai = arrs[i]
            for b in range(a + 1, n):
                j = order[b]
                if durs[j] - durs[i] > dur_tol:
                    break
                aj = arrs[j]
                m = min(len(ai), len(aj))
                if m < 40:
                    continue
                # court-circuit : similarité à offset 0 (un seul calcul)
                x = np.bitwise_xor(ai[:m], aj[:m])
                sim0 = 1.0 - _fp_popcount(x) / (32.0 * m)
                if sim0 >= th:
                    s = sim0
                elif sim0 < 0.55:
                    continue  # sons clairement différents : inutile de tester les décalages
                else:
                    s = fp_similarity(ai, aj, max_offset=max_offset)
                if s >= th:
                    union(i, j)
                    pair_sim[(min(i, j), max(i, j))] = s

        comp = {}
        for i in range(n):
            comp.setdefault(find(i), []).append(i)

        groups = []
        for members in comp.values():
            if len(members) < 2:
                continue
            versions = []
            for idx in members:
                t = self._adup_track_by_path.get(items[idx][0])
                if t:
                    versions.append(t)
            if len(versions) < 2:
                continue
            master = select_master(versions)
            rest = sorted([v for v in versions if v is not master],
                          key=lambda x: -(x["bitrate"] or 0))
            ordered = [master] + rest
            for v in ordered:
                v["keep"] = (v is master)
            sims = [s for (i, j), s in pair_sim.items() if i in members and j in members]
            score = round(min(sims), 3) if sims else th
            groups.append({"artist": master.get("artist", ""),
                           "title": master.get("title", ""),
                           "n": len(versions), "versions": ordered, "score": score})
        groups.sort(key=lambda g: (g["artist"].lower(), g["title"].lower()))
        # mémorise pour permettre la résolution sur ces groupes
        self._last_dup_groups = groups
        return {"ok": True, "groups": groups, "n_groups": len(groups)}

    # ----- intégrité (lecture seule) : mode rapide ou approfondi (ffmpeg) -----
    def check_integrity(self, mode="quick"):
        if True:
            res = self.scan_library()   # re-scan frais
            if not res.get("ok"):
                return {"ok": False, "error": res.get("error", "Scan impossible"),
                        "items": [], "n": 0, "n_critical": 0, "n_warning": 0, "total": 0}

        ffmpeg = None
        if mode == "deep":
            ffmpeg = find_ffmpeg()
            if not ffmpeg:
                return {"ok": False,
                        "error": "ffmpeg introuvable — installe-le depuis la carte Configuration "
                                 "(accueil) pour l'analyse approfondie.",
                        "items": [], "n": 0, "n_critical": 0, "n_warning": 0, "total": 0}

        items = []
        for t in self.tracks:
            if mode == "deep":
                r = deep_integrity_check(t["path"], ffmpeg, check_clipping=True)
            else:
                r = quick_integrity_check(t["path"])
            if r["severity"] != "ok":
                items.append({
                    "name": t["name"],
                    "path": t["path"],
                    "ext": t["ext"],
                    "severity": r["severity"],
                    "errors": r["errors"],
                })
        order = {"critical": 0, "warning": 1}
        items.sort(key=lambda x: (order.get(x["severity"], 2), x["name"].lower()))
        n_crit = sum(1 for i in items if i["severity"] == "critical")
        n_warn = sum(1 for i in items if i["severity"] == "warning")
        return {"ok": True, "items": items, "n": len(items),
                "n_critical": n_crit, "n_warning": n_warn, "total": len(self.tracks)}

    # --- intégrité en lots (barre de progression) ---
    def integ_begin(self, mode="quick", workers=4):
        res = self.scan_library()   # re-scan frais : prend les fichiers ajoutés
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error", "Scan impossible"), "total": 0}
        self._integ_mode = mode
        self._integ_idx = 0
        self._integ_items = []
        self._integ_ffmpeg = None
        try:
            self._integ_workers = max(1, min(16, int(workers)))
        except Exception:
            self._integ_workers = 4
        if mode == "deep":
            ff = find_ffmpeg()
            if not ff:
                return {"ok": False,
                        "error": "ffmpeg introuvable — installe-le depuis la carte Configuration "
                                 "(accueil) pour l'analyse approfondie.", "total": 0}
            self._integ_ffmpeg = ff
            try:
                import numpy  # noqa: F401
            except Exception:
                return {"ok": False,
                        "error": "numpy requis pour l'analyse approfondie "
                                 "(pip install numpy).", "total": 0}
        return {"ok": True, "total": len(self.tracks)}

    def integ_step(self, count=40):
        import concurrent.futures
        tracks = self.tracks
        start = self._integ_idx
        end = min(start + count, len(tracks))
        batch = tracks[start:end]
        if self._integ_mode == "deep":
            results = {}
            to_check = []
            for t in batch:
                c = self._integ_get_cached(t["path"])
                if c is not None:
                    results[t["path"]] = c
                else:
                    to_check.append(t)
            if to_check:
                with concurrent.futures.ThreadPoolExecutor(
                        max_workers=getattr(self, "_integ_workers", 4)) as ex:
                    futs = {ex.submit(deep_integrity_check, t["path"],
                                      self._integ_ffmpeg, check_clipping=True): t
                            for t in to_check}
                    for fut in concurrent.futures.as_completed(futs):
                        t = futs[fut]
                        try:
                            r = fut.result()
                        except Exception as e:
                            r = {"severity": "critical", "errors": ["Exception : %s" % e]}
                        results[t["path"]] = r
                        self._integ_store(t["path"], r)
            for t in batch:
                r = results.get(t["path"], {"severity": "ok", "errors": []})
                if r["severity"] != "ok":
                    self._integ_items.append({
                        "name": t["name"], "path": t["path"], "ext": t["ext"],
                        "severity": r["severity"], "errors": r["errors"]})
        else:
            for t in batch:
                r = quick_integrity_check(t["path"])
                self._integ_store(t["path"], r, mode="quick")
                if r["severity"] != "ok":
                    self._integ_items.append({
                        "name": t["name"], "path": t["path"], "ext": t["ext"],
                        "severity": r["severity"], "errors": r["errors"]})
        self._integ_idx = end
        finished = end >= len(tracks)
        result = None
        if finished:
            self._save_integ_cache()
            items = self._integ_items
            order = {"critical": 0, "warning": 1}
            items.sort(key=lambda x: (order.get(x["severity"], 2), x["name"].lower()))
            result = {"ok": True, "items": items, "n": len(items),
                      "n_critical": sum(1 for i in items if i["severity"] == "critical"),
                      "n_warning": sum(1 for i in items if i["severity"] == "warning"),
                      "total": len(tracks)}
        return {"done": end, "total": len(tracks), "finished": finished, "result": result}

    def integ_cancel(self):
        """Interruption de l'analyse : conserve les résultats déjà calculés (cache)."""
        if getattr(self, "_integ_mode", "") == "deep":
            self._save_integ_cache()
        return {"ok": True}

    # ----- cache des résultats d'intégrité approfondie (décodage coûteux) -----
    def _integ_cache_path(self):
        return os.path.join(os.path.expanduser("~"), ".djhelper", "integrity_cache.json")

    def _load_integ_cache(self):
        self._integ_cache = {}
        try:
            import json
            with open(self._integ_cache_path(), encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._integ_cache = data
        except Exception:
            self._integ_cache = {}

    def _save_integ_cache(self):
        try:
            import json
            p = self._integ_cache_path()
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self._integ_cache, f, ensure_ascii=False)
        except Exception:
            pass

    def _integ_sig(self, path):
        st = os.stat(path)
        return [st.st_size, int(st.st_mtime)]

    def _integ_get_cached(self, path):
        try:
            rel = os.path.relpath(path, self.music_folder)
        except Exception:
            rel = path
        ent = self._integ_cache.get(rel)
        if not ent:
            return None
        try:
            if ent.get("sig") != self._integ_sig(path):
                return None
        except Exception:
            return None
        if ent.get("mode", "deep") != "deep":
            return None   # un résultat "rapide" ne vaut pas une analyse approfondie
        return {"severity": ent.get("severity", "ok"), "errors": ent.get("errors", [])}

    def _integ_store(self, path, r, mode="deep"):
        try:
            rel = os.path.relpath(path, self.music_folder)
            sig = self._integ_sig(path)
            ent = self._integ_cache.get(rel)
            if (mode == "quick" and ent and ent.get("mode", "deep") == "deep"
                    and ent.get("sig") == sig):
                return  # ne pas remplacer un résultat approfondi encore valide
            self._integ_cache[rel] = {"sig": sig, "severity": r["severity"],
                                      "errors": r["errors"], "mode": mode}
        except Exception:
            pass

    # --- AcoustID : le son correspond-il aux tags ? (en ligne, en lots) ---
    def _acoustid_get_cached(self, path):
        try:
            rel = os.path.relpath(path, self.music_folder)
        except Exception:
            rel = path
        ent = self._acoustid_cache.get(rel)
        if not ent:
            return None
        try:
            if ent.get("size") != os.path.getsize(path):
                return None
        except Exception:
            return None
        return ent

    def _acoustid_store(self, path, res):
        try:
            rel = os.path.relpath(path, self.music_folder)
            r = dict(res)
            r["size"] = os.path.getsize(path)
            self._acoustid_cache[rel] = r
        except Exception:
            pass

    def acoustid_begin(self):
        audio = self.music_folder
        if not (audio and os.path.isdir(audio)):
            return {"ok": False, "error": "Dossier audio introuvable", "total": 0}
        key = (self.acoustid_key or "").strip()
        if not key:
            return {"ok": False, "total": 0,
                    "error": "Clé AcoustID manquante. Renseigne-la sur l'accueil, "
                             "dans Configuration (gratuite sur acoustid.org), et clique "
                             "sur Enregistrer."}
        fpcalc = find_fpcalc()
        if not fpcalc:
            return {"ok": False, "total": 0,
                    "error": "fpcalc introuvable — installe Chromaprint depuis la "
                             "carte Configuration (accueil)."}
        paths = []
        for dirpath, dirnames, filenames in os.walk(audio):
            dirnames[:] = [d for d in dirnames if not is_junk(d)]
            for fn in filenames:
                if is_junk(fn):
                    continue
                if os.path.splitext(fn)[1].lower() in SUPPORTED:
                    paths.append(os.path.join(dirpath, fn))
        self._ac_paths = paths
        self._ac_key = key
        self._ac_fpcalc = fpcalc
        self._ac_i = 0
        self._ac_mismatches = []
        self._ac_match = self._ac_unident = self._ac_error = 0
        return {"ok": True, "total": len(paths)}

    def acoustid_step(self, count=3):
        import time
        paths = self._ac_paths
        start = self._ac_i
        end = min(start + count, len(paths))
        for i in range(start, end):
            p = paths[i]
            res = self._acoustid_get_cached(p)
            if res is None:
                tags = self._read_tags(p)
                artist = tags["artist"]
                fp, dur = acoustid_fingerprint(p, self._ac_fpcalc)
                if not fp:
                    res = {"verdict": "error", "tag_artist": artist or "", "id_artist": "",
                           "id_title": "", "score": 0.0, "error": "empreinte impossible"}
                else:
                    lk = acoustid_lookup(fp, dur, self._ac_key)
                    if lk["status"] == "error":
                        res = {"verdict": "error", "tag_artist": artist or "", "id_artist": "",
                               "id_title": "", "score": 0.0, "error": lk.get("error", "")}
                    else:
                        v, ia, it = acoustid_verdict(artist or "", lk["matches"])
                        top = lk["matches"][0][0] if lk["matches"] else 0.0
                        res = {"verdict": v, "tag_artist": artist or "", "id_artist": ia,
                               "id_title": it, "score": round(top, 2), "error": ""}
                    time.sleep(0.34)  # limite AcoustID : 3 requêtes/seconde
                self._acoustid_store(p, res)
            v = res.get("verdict")
            if v == "mismatch":
                self._ac_mismatches.append({
                    "name": os.path.basename(p), "path": p,
                    "tag_artist": res.get("tag_artist", ""),
                    "id_artist": res.get("id_artist", ""),
                    "id_title": res.get("id_title", ""), "score": res.get("score", 0.0)})
            elif v == "match":
                self._ac_match += 1
            elif v == "error":
                self._ac_error += 1
            else:
                self._ac_unident += 1
        self._ac_i = end
        finished = end >= len(paths)
        result = None
        if finished:
            self._save_acoustid_cache()
            result = {"ok": True, "mismatches": self._ac_mismatches,
                      "n_mismatch": len(self._ac_mismatches), "n_match": self._ac_match,
                      "n_unident": self._ac_unident, "n_error": self._ac_error,
                      "total": len(paths)}
        return {"done": end, "total": len(paths), "finished": finished, "result": result}

    # --- Enrichissement des tags via AcoustID → MusicBrainz → pochette ---
    def enrich_begin(self):
        audio = self.music_folder
        if not (audio and os.path.isdir(audio)):
            return {"ok": False, "error": "Dossier audio introuvable", "total": 0}
        key = (self.acoustid_key or "").strip()
        if not key:
            return {"ok": False, "total": 0,
                    "error": "Clé AcoustID manquante (onglet Intégrité)."}
        fpcalc = find_fpcalc()
        if not fpcalc:
            return {"ok": False, "total": 0,
                    "error": "fpcalc introuvable — installe-le depuis la carte Configuration (accueil)."}
        paths = []
        for dirpath, dirnames, filenames in os.walk(audio):
            dirnames[:] = [d for d in dirnames if not is_junk(d)]
            for fn in filenames:
                if is_junk(fn):
                    continue
                if os.path.splitext(fn)[1].lower() in SUPPORTED:
                    paths.append(os.path.join(dirpath, fn))
        self._en_paths = paths
        self._en_key = key
        self._en_fpcalc = fpcalc
        self._en_i = 0
        self._en_proposals = []
        self._en_unident_list = []
        self._en_api_error = ""
        self._en_unident = self._en_error = self._en_ok = 0
        self._en_cancel = False
        return {"ok": True, "total": len(paths)}

    def vault_check(self):
        """La structure Traktor (collection.nml) a-t-elle changé depuis la
        dernière génération du coffre-fort M3U ? Appelé à la fermeture."""
        root = (self.usb_root or "").strip()
        if not root or not os.path.isdir(root):
            return {"changed": False}
        cur = nml_hash(root)
        changed = bool(cur) and cur != getattr(self, "last_vault_nml_hash", "")
        return {"changed": changed}

    def enrich_cancel(self):
        self._en_cancel = True
        return {"ok": True}

    def enrich_step(self, count=6):
        import time, concurrent.futures
        if getattr(self, "_en_cancel", False):
            self._save_enrich_cache()
            return {"ok": True, "cancelled": True, "done": self._en_i,
                    "total": len(self._en_paths), "finished": True,
                    "proposals": self._en_proposals,
                    "unident_list": self._en_unident_list,
                    "n_proposed": len(self._en_proposals), "n_unident": self._en_unident,
                    "n_error": self._en_error, "n_already_ok": self._en_ok,
                    "api_error": getattr(self, "_en_api_error", "")}
        paths = self._en_paths
        start = self._en_i
        end = min(start + count, len(paths))
        batch = paths[start:end]
        # 1) empreintes fpcalc en parallèle (partie locale, sans réseau)
        need_fp = [p for p in batch
                   if not isinstance((self._enrich_get_cached(p) or {}).get("lk"), dict)]
        fps = {}
        if need_fp:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                futs = {ex.submit(acoustid_fingerprint, p, self._en_fpcalc): p
                        for p in need_fp}
                for fut in concurrent.futures.as_completed(futs):
                    q = futs[fut]
                    try:
                        fps[q] = fut.result()
                    except Exception:
                        fps[q] = (None, None)
        # 2) traitement séquentiel (lookup AcoustID limité à ~3/s côté serveur)
        for p in batch:
            try:
                tags = self._read_tags(p)
                cur_artist, cur_title = tags["artist"], tags["title"]
                cached = self._enrich_get_cached(p)
                if cached is not None and isinstance(cached.get("lk"), dict):
                    fp_ok, lk = True, cached["lk"]
                else:
                    fp, dur = fps.get(p, (None, None))
                    fp_ok = bool(fp)
                    if fp_ok:
                        lk = acoustid_identify(fp, dur, self._en_key)
                        time.sleep(0.34)
                        self._enrich_store(p, lk)
                    else:
                        lk = None
                if not fp_ok:
                    self._en_error += 1
                    continue
                if lk.get("status") == "ok" and lk.get("candidates"):
                    best = lk["candidates"][0]
                    if best["score"] >= 0.5 and (best["artist"] or best["title"]):
                        chosen_rg, ordered = choose_release_group(best["releasegroups"])
                        protected = has_version_marker(cur_title)
                        prop_artist = best["artist"]
                        prop_title = "" if protected else best["title"]
                        artist_diff = bool(prop_artist) and _tag_norm(prop_artist) != _tag_norm(cur_artist)
                        title_diff = bool(prop_title) and _tag_norm(prop_title) != _tag_norm(cur_title)
                        if not (artist_diff or title_diff):
                            self._en_ok += 1
                            continue
                        albums = [{"id": rg["id"], "title": rg["title"], "type": rg.get("type", "")}
                                  for rg in ordered if rg.get("id")]
                        self._en_proposals.append({
                            "path": p, "name": os.path.basename(p),
                            "cur_artist": cur_artist or "", "cur_title": cur_title or "",
                            "prop_artist": prop_artist, "prop_title": prop_title,
                            "title_protected": protected, "score": round(best["score"], 2),
                            "cover_present": _has_embedded_cover(p),
                            "albums": albums,
                            "chosen_id": (chosen_rg["id"] if chosen_rg else ""),
                            "chosen_title": (chosen_rg["title"] if chosen_rg else "")})
                    else:
                        self._en_unident += 1
                        self._en_unident_list.append({"name": os.path.basename(p), "path": p})
                else:
                    self._en_unident += 1
                    self._en_unident_list.append({"name": os.path.basename(p), "path": p})
                    if isinstance(lk, dict) and lk.get("status") == "error" and lk.get("error"):
                        self._en_api_error = lk.get("error")
            except Exception:
                self._en_error += 1
        self._en_i = end
        finished = end >= len(paths)
        result = None
        if finished:
            self._save_enrich_cache()
            result = {"ok": True, "proposals": self._en_proposals,
                      "unident_list": self._en_unident_list,
                      "n_proposed": len(self._en_proposals), "n_unident": self._en_unident,
                      "n_error": self._en_error, "n_already_ok": self._en_ok,
                      "api_error": getattr(self, "_en_api_error", ""),
                      "total": len(paths)}
        return {"done": end, "total": len(paths), "finished": finished, "result": result}

    def enrich_apply(self, selection):
        """selection : [{path, artist, title, album, album_id, cover_present}].
        Récupère date (MusicBrainz) + pochette (Cover Art) puis écrit les tags."""
        import time
        ok = fail = covers = 0
        details = []
        for sel in (selection or []):
            p = sel.get("path")
            meta = {"artist": sel.get("artist", ""), "title": sel.get("title", ""),
                    "album": sel.get("album", ""), "albumartist": sel.get("artist", ""),
                    "date": ""}
            rg_id = sel.get("album_id") or ""
            try:
                if rg_id:
                    meta["date"] = mb_releasegroup_date(rg_id)
                    time.sleep(1.0)  # MusicBrainz : 1 req/s
                cover = cover_mime = None
                if rg_id and not sel.get("cover_present"):
                    cb, mime = caa_front_cover(rg_id)
                    time.sleep(1.0)  # Cover Art Archive
                    if cb:
                        cover, cover_mime = cb, mime
                        covers += 1
                success, info = write_full_tags(
                    p, meta, cover=cover, cover_mime=cover_mime or "image/jpeg",
                    protect_version=True)
                if success:
                    ok += 1
                    self._scan_cache.pop(p, None)  # forcer relecture au prochain scan
                else:
                    fail += 1
                    details.append({"name": os.path.basename(p),
                                    "error": info.get("error", "échec")})
            except Exception as e:
                fail += 1
                details.append({"name": os.path.basename(p), "error": str(e)[:80]})
        self._save_scan_cache()
        return {"ok": True, "n_ok": ok, "n_fail": fail, "n_covers": covers,
                "details": details}

    # --- Vérifier un dossier d'import (anti-doublon en amont, par le son) ---
    def import_check_begin(self, folder):
        if not (folder and os.path.isdir(folder)):
            return {"ok": False, "error": "Dossier d'import introuvable", "total": 0}
        base = self.music_folder
        if not (base and os.path.isdir(base)):
            return {"ok": False, "total": 0,
                    "error": "Dossier de musique (base) introuvable. Définis-le sur l'accueil."}
        key = (self.acoustid_key or "").strip()
        if not key:
            return {"ok": False, "total": 0,
                    "error": "Clé AcoustID manquante (onglet Intégrité)."}
        fpcalc = find_fpcalc()
        if not fpcalc:
            return {"ok": False, "total": 0,
                    "error": "fpcalc introuvable — installe-le depuis la carte Configuration (accueil)."}
        self.scan_library()  # indexer la base à laquelle on compare
        files = []
        for dirpath, dirnames, filenames in os.walk(folder):
            dirnames[:] = [d for d in dirnames if d != "_DOUBLONS" and not is_junk(d)]
            for fn in filenames:
                if is_junk(fn):
                    continue
                if os.path.splitext(fn)[1].lower() in SUPPORTED:
                    files.append(os.path.join(dirpath, fn))
        if not files:
            return {"ok": False, "total": 0,
                    "error": "Aucun fichier audio dans ce dossier."}
        self._imp_files = files
        self._imp_folder = folder
        self._imp_key = key
        self._imp_fpcalc = fpcalc
        self._imp_i = 0
        self._imp_results = []
        self._imp_dup = self._imp_new = self._imp_unknown = 0
        return {"ok": True, "total": len(files)}

    def import_check_step(self, count=3):
        import time
        files = self._imp_files
        start = self._imp_i
        end = min(start + count, len(files))
        folder_res = os.path.realpath(self._imp_folder)
        for i in range(start, end):
            f = files[i]
            fp, dur = acoustid_fingerprint(f, self._imp_fpcalc)
            cands = []
            if fp:
                res = acoustid_identify(fp, dur, self._imp_key)
                time.sleep(0.34)
                cands = res.get("candidates") or []
            if not cands:
                self._imp_results.append({"name": os.path.basename(f), "path": f,
                                          "status": "inconnu", "ident": "", "base": "", "score": ""})
                self._imp_unknown += 1
                continue
            artist = cands[0].get("artist", "")
            title = cands[0].get("title", "")
            ident = ("%s - %s" % (artist, title)).strip(" -")
            match, score = self.find_match(artist, title)
            is_dup, base_name = False, ""
            if match and score >= 85:
                mp = match.get("path", "")
                try:
                    in_import = os.path.realpath(mp).startswith(folder_res + os.sep)
                except Exception:
                    in_import = (mp == f)
                if not in_import:
                    is_dup, base_name = True, os.path.basename(mp)
            if is_dup:
                self._imp_dup += 1
                self._imp_results.append({"name": os.path.basename(f), "path": f,
                                          "status": "doublon", "ident": ident,
                                          "base": base_name, "score": score})
            else:
                self._imp_new += 1
                self._imp_results.append({"name": os.path.basename(f), "path": f,
                                          "status": "nouveau", "ident": ident,
                                          "base": "", "score": score})
        self._imp_i = end
        finished = end >= len(files)
        result = None
        if finished:
            order = {"doublon": 0, "inconnu": 1, "nouveau": 2}
            results = sorted(self._imp_results, key=lambda r: order[r["status"]])
            for r in results:
                r["checked_default"] = (r["status"] == "doublon")
            result = {"ok": True, "results": results, "n_dup": self._imp_dup,
                      "n_new": self._imp_new, "n_unknown": self._imp_unknown,
                      "total": len(files)}
        return {"done": end, "total": len(files), "finished": finished, "result": result}

    def import_discard(self, paths):
        """Déplace les fichiers donnés dans {dossier}/_DOUBLONS/ (ne supprime rien,
        n'écrase jamais : collision → suffixe incrémental)."""
        import shutil
        folder = getattr(self, "_imp_folder", "")
        if not folder:
            return {"ok": False, "error": "Aucun dossier d'import actif."}
        dest = os.path.join(folder, "_DOUBLONS")
        try:
            os.makedirs(dest, exist_ok=True)
        except Exception as e:
            return {"ok": False, "error": "Impossible de créer _DOUBLONS/ : %s" % e}
        moved = 0
        errors = []
        for src in (paths or []):
            if not src or not os.path.isfile(src):
                continue
            base = os.path.basename(src)
            target = os.path.join(dest, base)
            if os.path.exists(target):
                stem, suf = os.path.splitext(base)
                k = 2
                while os.path.exists(os.path.join(dest, "%s (%d)%s" % (stem, k, suf))):
                    k += 1
                target = os.path.join(dest, "%s (%d)%s" % (stem, k, suf))
            try:
                shutil.move(src, target)
                moved += 1
            except Exception as e:
                errors.append("%s : %s" % (base, str(e)[:60]))
        return {"ok": True, "moved": moved, "errors": errors}

    # ----- tags (diagnostic, lecture seule) -----
    def check_tags(self):
        res = self.scan_library()   # re-scan frais : prend les fichiers ajoutés
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error", "Scan impossible"),
                    "items": [], "total": 0, "n_ok": 0, "n_fix": 0, "n_lost": 0}

        tracks = self.tracks
        with_tags = [t for t in tracks if t["has_tags"]]
        inferable = [t for t in tracks
                     if not t["has_tags"] and t["artist"] and t["title"]]
        lost = [t for t in tracks
                if not t["has_tags"] and not (t["artist"] and t["title"])]

        items = [{"name": t["name"], "artist": t["artist"], "title": t["title"]}
                 for t in inferable]
        items.sort(key=lambda x: x["name"].lower())
        lost_list = [{"name": t["name"], "path": t["path"]} for t in lost]
        lost_list.sort(key=lambda x: x["name"].lower())
        return {"ok": True, "total": len(tracks),
                "n_ok": len(with_tags), "n_fix": len(inferable), "n_lost": len(lost),
                "items": items, "lost_list": lost_list}

    def apply_retag(self):
        """Écrit artiste/titre (déduits du nom) dans les fichiers corrigeables.
        Action : modifie les fichiers. Retourne le nombre retaggué/échoué."""
        if not self.tracks:
            res = self.scan_library()
            if not res.get("ok"):
                return {"ok": False, "error": res.get("error", "Scan impossible"),
                        "n_retagged": 0, "n_failed": 0}
        n_ok = 0
        n_fail = 0
        for t in self.tracks:
            if not t["has_tags"] and t["artist"] and t["title"]:
                if write_tags(t["path"], t["artist"], t["title"]):
                    t["has_tags"] = True
                    self._scan_cache.pop(t["path"], None)  # forcer relecture au prochain scan
                    n_ok += 1
                else:
                    n_fail += 1
        if n_ok:
            self._save_scan_cache()
        return {"ok": True, "n_retagged": n_ok, "n_failed": n_fail}

    # ----- importer / comparaison de playlist (lecture seule) -----
    def find_match(self, artist, title, threshold=85):
        """Meilleur (track, score) de la bibliothèque pour (artist, title).
        score = min(similarité artiste, similarité titre) — porté du Tkinter."""
        from rapidfuzz import fuzz
        q_artist = normalize_string(artist or "")
        q_title = match_title_key(artist, title)
        if not q_artist or not q_title:
            return None, 0
        best = None
        best_score = -1
        for t in self.tracks:
            for ca, ct in t.get("match_candidates", ()):
                if not ca or not ct:
                    continue
                sa = fuzz.token_set_ratio(q_artist, ca)
                st = fuzz.token_sort_ratio(q_title, ct)
                score = sa if sa < st else st
                if score > best_score:
                    best_score = score
                    best = t
        return best, int(best_score)

    def _best_match_both(self, a, t, threshold):
        """Teste les deux sens (Artiste - Titre / Titre - Artiste) et garde le meilleur."""
        m1 = self.find_match(a, t, threshold)
        if a and t:
            m2 = self.find_match(t, a, threshold)
            if m2[1] > m1[1]:
                return m2
        return m1

    @staticmethod
    def _parse_playlist(text):
        entries = []
        for raw in (text or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            a, t = parse_filename(line)
            if a and t:
                entries.append((a, t))
            else:
                entries.append(("", line))
        return entries

    def compare_playlist(self, text, threshold=85):
        if True:
            res = self.scan_library()   # re-scan frais
            if not res.get("ok"):
                return {"ok": False, "error": res.get("error", "Scan impossible"),
                        "found": [], "review": [], "missing": [],
                        "n_total": 0, "n_found": 0, "n_review": 0, "n_missing": 0}

        review_floor = max(65, threshold - 15)
        entries = self._parse_playlist(text)
        found, review, missing = [], [], []
        for a, t in entries:
            label = (a + " - " + t) if a else t
            local, score = self._best_match_both(a, t, threshold)
            if local and score >= threshold:
                found.append({"query": label, "local": local["name"], "score": score})
            elif local and score >= review_floor:
                review.append({"query": label, "local": local["name"], "score": score})
            else:
                missing.append({"query": label})
        return {"ok": True, "n_total": len(entries),
                "n_found": len(found), "n_review": len(review), "n_missing": len(missing),
                "found": found, "review": review, "missing": missing}

    # --- comparaison playlist en lots (barre de progression) ---
    def compare_begin(self, text, threshold=85):
        res = self.scan_library()   # re-scan frais : prend en compte les fichiers ajoutés
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error", "Scan impossible"), "total": 0}
        self._cmp_entries = self._parse_playlist(text)
        self._cmp_threshold = threshold
        self._cmp_idx = 0
        self._cmp_found, self._cmp_review, self._cmp_missing = [], [], []
        return {"ok": True, "total": len(self._cmp_entries)}

    def compare_step(self, count=25):
        entries = self._cmp_entries
        threshold = self._cmp_threshold
        review_floor = max(65, threshold - 15)
        start = self._cmp_idx
        end = min(start + count, len(entries))
        for i in range(start, end):
            a, t = entries[i]
            label = (a + " - " + t) if a else t
            local, score = self._best_match_both(a, t, threshold)
            if local and score >= threshold:
                self._cmp_found.append({"query": label, "local": local["name"],
                                        "path": local.get("path"), "score": score})
            elif local and score >= review_floor:
                self._cmp_review.append({"query": label, "local": local["name"], "score": score})
            else:
                self._cmp_missing.append({"query": label})
        self._cmp_idx = end
        finished = end >= len(entries)
        result = None
        if finished:
            result = {"ok": True, "n_total": len(entries),
                      "n_found": len(self._cmp_found), "n_review": len(self._cmp_review),
                      "n_missing": len(self._cmp_missing), "found": self._cmp_found,
                      "review": self._cmp_review, "missing": self._cmp_missing}
        return {"done": end, "total": len(entries), "finished": finished, "result": result}

    def export_found_m3u(self, dest):
        """Écrit un .m3u des morceaux trouvés (importable dans Traktor)."""
        found = getattr(self, "_cmp_found", [])
        if not found:
            return {"ok": False, "error": "Lance d'abord une comparaison."}
        if not dest or not os.path.isdir(dest):
            return {"ok": False, "error": "Dossier de destination introuvable."}
        lines = ["#EXTM3U"]
        n = 0
        for f in found:
            p = f.get("path")
            if p:
                lines.append(p)
                n += 1
        path = os.path.join(dest, "playlist_trouves.m3u")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
        except Exception as e:
            return {"ok": False, "error": str(e)[:150]}
        return {"ok": True, "path": path, "n": n}

    def export_missing_txt(self, dest):
        """Écrit la liste des morceaux manquants, un par ligne (.txt)."""
        missing = getattr(self, "_cmp_missing", [])
        if not missing:
            return {"ok": False, "error": "Aucun manquant (ou comparaison non lancée)."}
        if not dest or not os.path.isdir(dest):
            return {"ok": False, "error": "Dossier de destination introuvable."}
        path = os.path.join(dest, "morceaux_manquants.txt")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(m.get("query", "") for m in missing) + "\n")
        except Exception as e:
            return {"ok": False, "error": str(e)[:150]}
        return {"ok": True, "path": path, "n": len(missing)}

    # ----- synchro : clone du dossier audio vers une clé de secours -----
    def plan_sync(self, spare):
        """Dry-run : ce qui serait copié / supprimé pour rendre spare identique à la source."""
        master = self._sync_source()
        if not (master and os.path.isdir(master)):
            return {"ok": False, "error": "Source introuvable"}
        if not spare or not os.path.isdir(spare):
            return {"ok": False, "error": "Clé de secours introuvable"}
        if os.path.abspath(spare) == os.path.abspath(master):
            return {"ok": False, "error": "La clé de secours doit être différente du dossier principal"}
        idx_m = bk_index(master)
        idx_s = bk_index(spare)
        to_copy, copy_bytes = [], 0
        for rel, meta_m in idx_m.items():
            meta_s = idx_s.get(rel)
            if meta_s is None or bk_differs(meta_m, meta_s):
                to_copy.append(rel)
                copy_bytes += meta_m[0]
        to_delete = [rel for rel in idx_s if rel not in idx_m]
        return {"ok": True, "spare": spare,
                "to_copy": sorted(to_copy), "to_delete": sorted(to_delete),
                "n_copy": len(to_copy), "n_delete": len(to_delete),
                "copy_bytes": copy_bytes, "copy_h": human_size(copy_bytes)}

    def apply_sync(self, spare):
        """Applique le clone (copie + suppression). Action destructive sur la spare."""
        master = self._sync_source()
        plan = self.plan_sync(spare)
        if not plan.get("ok"):
            return plan
        n_copied = n_deleted = n_failed = 0
        for rel in plan["to_copy"]:
            try:
                bk_copy(os.path.join(master, rel), os.path.join(spare, rel))
                n_copied += 1
            except Exception:
                n_failed += 1
        for rel in plan["to_delete"]:
            try:
                os.unlink(os.path.join(spare, rel))
                n_deleted += 1
            except OSError:
                n_failed += 1
        for dirpath, dirnames, filenames in os.walk(spare, topdown=False):
            if os.path.abspath(dirpath) == os.path.abspath(spare):
                continue
            try:
                if not os.listdir(dirpath):
                    os.rmdir(dirpath)
            except OSError:
                pass
        return {"ok": True, "n_copied": n_copied, "n_deleted": n_deleted, "n_failed": n_failed}

    # --- synchro en lots (barre de progression) ---
    def sync_apply_begin(self, spare):
        plan = self.plan_sync(spare)
        if not plan.get("ok"):
            return plan
        self._sync_spare = spare
        self._sync_copy = plan["to_copy"]
        self._sync_delete = plan["to_delete"]
        self._sync_ci = 0
        self._sync_copied = self._sync_deleted = self._sync_failed = 0
        return {"ok": True, "total": len(plan["to_copy"]) + len(plan["to_delete"])}

    def sync_apply_step(self, count=50):
        master = self._sync_source()
        spare = self._sync_spare
        ncopy = len(self._sync_copy)
        ndel = len(self._sync_delete)
        i = self._sync_ci
        end = min(i + count, ncopy + ndel)
        for j in range(i, end):
            if j < ncopy:
                rel = self._sync_copy[j]
                try:
                    bk_copy(os.path.join(master, rel), os.path.join(spare, rel))
                    self._sync_copied += 1
                except Exception:
                    self._sync_failed += 1
            else:
                rel = self._sync_delete[j - ncopy]
                try:
                    os.unlink(os.path.join(spare, rel))
                    self._sync_deleted += 1
                except OSError:
                    self._sync_failed += 1
        self._sync_ci = end
        finished = end >= (ncopy + ndel)
        result = None
        if finished:
            for dirpath, dirnames, filenames in os.walk(spare, topdown=False):
                if os.path.abspath(dirpath) == os.path.abspath(spare):
                    continue
                try:
                    if not os.listdir(dirpath):
                        os.rmdir(dirpath)
                except OSError:
                    pass
            result = {"ok": True, "n_copied": self._sync_copied,
                      "n_deleted": self._sync_deleted, "n_failed": self._sync_failed}
            self._backup_log_record("spare")
        return {"done": end, "total": ncopy + ndel, "finished": finished, "result": result}

    # --- sauvegarde complète versionnée (hardlink Time Machine, ou archive) ---
    def full_backup_begin(self, dest):
        import datetime
        src = self._sync_source()
        if not (src and os.path.isdir(src)):
            return {"ok": False, "total": 0,
                    "error": "Source introuvable (définis le dossier ou la clé)."}
        if not dest:
            return {"ok": False, "total": 0, "error": "Choisis un dossier de sauvegarde."}
        try:
            if os.path.realpath(dest) == os.path.realpath(src):
                return {"ok": False, "total": 0,
                        "error": "La destination ne peut pas être la source."}
        except Exception:
            pass
        os.makedirs(dest, exist_ok=True)
        hardlink = bk_supports_hardlinks(dest)
        idx_m = bk_index(src)
        self._fb_src = src
        self._fb_dest = dest
        self._fb_mode = "hardlink" if hardlink else "archive"
        self._fb_items = list(idx_m.items())
        self._fb_i = 0
        self._fb_copied = self._fb_linked = self._fb_archived = 0
        self._fb_extra = []
        if hardlink:
            prev = bk_latest_snapshot(dest)
            self._fb_prev = prev
            self._fb_prev_index = bk_index(prev) if prev else {}
            stamp = datetime.datetime.now().strftime("snapshot_%Y-%m-%d_%H%M%S")
            snap = os.path.join(dest, stamp)
            n = 1
            while os.path.exists(snap):
                snap = os.path.join(dest, "%s_%d" % (stamp, n))
                n += 1
            self._fb_snap = snap
        else:
            current = os.path.join(dest, "courant")
            os.makedirs(current, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
            self._fb_current = current
            self._fb_archive = os.path.join(dest, "archive", stamp)
            self._fb_idx_c = bk_index(current)
            self._fb_extra = [rel for rel in self._fb_idx_c if rel not in idx_m]
        self._fb_total = len(self._fb_items) + len(self._fb_extra)
        return {"ok": True, "total": self._fb_total, "mode": self._fb_mode}

    def full_backup_step(self, count=40):
        items = self._fb_items
        nm = len(items)
        extra = self._fb_extra
        total = nm + len(extra)
        end = min(self._fb_i + count, total)
        for i in range(self._fb_i, end):
            if i < nm:
                rel, meta_m = items[i]
                if self._fb_mode == "hardlink":
                    dst = os.path.join(self._fb_snap, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    pm = self._fb_prev_index.get(rel)
                    if self._fb_prev and pm is not None and not bk_differs(meta_m, pm):
                        try:
                            os.link(os.path.join(self._fb_prev, rel), dst)
                            self._fb_linked += 1
                        except OSError:
                            bk_copy(os.path.join(self._fb_src, rel), dst)
                            self._fb_copied += 1
                    else:
                        bk_copy(os.path.join(self._fb_src, rel), dst)
                        self._fb_copied += 1
                else:
                    meta_c = self._fb_idx_c.get(rel)
                    if meta_c is None or bk_differs(meta_m, meta_c):
                        if meta_c is not None:
                            bk_copy(os.path.join(self._fb_current, rel),
                                    os.path.join(self._fb_archive, rel))
                            self._fb_archived += 1
                        bk_copy(os.path.join(self._fb_src, rel),
                                os.path.join(self._fb_current, rel))
                        self._fb_copied += 1
            else:
                rel = extra[i - nm]
                bk_copy(os.path.join(self._fb_current, rel),
                        os.path.join(self._fb_archive, rel))
                self._fb_archived += 1
                try:
                    os.unlink(os.path.join(self._fb_current, rel))
                except OSError:
                    pass
        self._fb_i = end
        finished = end >= total
        result = None
        if finished:
            if self._fb_mode == "archive":
                for dirpath, dirnames, filenames in os.walk(self._fb_current, topdown=False):
                    if os.path.abspath(dirpath) == os.path.abspath(self._fb_current):
                        continue
                    try:
                        if not os.listdir(dirpath):
                            os.rmdir(dirpath)
                    except OSError:
                        pass
                try:
                    if os.path.isdir(self._fb_archive) and not os.listdir(self._fb_archive):
                        os.rmdir(self._fb_archive)
                except OSError:
                    pass
                result = {"ok": True, "mode": "archive", "current": self._fb_current,
                          "copied": self._fb_copied, "archived": self._fb_archived,
                          "total": nm}
            else:
                result = {"ok": True, "mode": "hardlink", "snapshot": self._fb_snap,
                          "copied": self._fb_copied, "linked": self._fb_linked,
                          "total": nm}
            self._backup_log_record("full")
        return {"done": end, "total": total, "finished": finished, "result": result}

    # --- sauvegarde de structure (manifeste + collection.nml) ---
    def export_structure_begin(self, dest_root):
        import datetime
        src = self._sync_source()
        if not (src and os.path.isdir(src)):
            return {"ok": False, "error": "Source introuvable", "total": 0}
        if not (dest_root and os.path.isdir(dest_root)):
            return {"ok": False, "error": "Dossier de destination introuvable", "total": 0}
        stamp = datetime.datetime.now().strftime("struct_backup_%Y-%m-%d_%H%M%S")
        out = os.path.join(dest_root, stamp)
        try:
            os.makedirs(out, exist_ok=True)
        except Exception as e:
            return {"ok": False, "error": str(e), "total": 0}
        paths = []
        for dirpath, dirnames, filenames in os.walk(src):
            dirnames[:] = [d for d in dirnames if not is_junk(d)]
            for fn in filenames:
                if is_junk(fn):
                    continue
                if os.path.splitext(fn)[1].lower() in SUPPORTED:
                    paths.append(os.path.join(dirpath, fn))
        self._struct_src = src
        self._struct_out = out
        self._struct_stamp = stamp
        self._struct_paths = paths
        self._struct_entries = []
        self._struct_idx = 0
        return {"ok": True, "total": len(paths), "out_dir": out}

    def export_structure_step(self, count=80):
        import json, csv, datetime
        src = self._struct_src
        paths = self._struct_paths
        start = self._struct_idx
        end = min(start + count, len(paths))
        for i in range(start, end):
            p = paths[i]
            name = os.path.basename(p)
            rel = os.path.relpath(p, src).replace(os.sep, "/")
            tags = self._read_tags(p)
            artist, title = tags["artist"], tags["title"]
            if not (artist and title):
                fa, ft = parse_filename(os.path.splitext(name)[0])
                artist = artist or fa or ""
                title = title or ft or os.path.splitext(name)[0]
            try:
                size = os.path.getsize(p)
            except Exception:
                size = 0
            self._struct_entries.append({
                "rel_path": rel, "artist": artist, "title": title,
                "size": size, "duration": round(tags["duration"], 1),
                "folder": os.path.dirname(rel)})
        self._struct_idx = end
        finished = end >= len(paths)
        result = None
        if finished:
            out = self._struct_out
            entries = self._struct_entries
            try:
                with open(os.path.join(out, "manifeste.json"), "w", encoding="utf-8") as f:
                    json.dump({"source": src, "generated": self._struct_stamp,
                               "count": len(entries), "entries": entries},
                              f, ensure_ascii=False, indent=2)
                with open(os.path.join(out, "manifeste.csv"), "w", encoding="utf-8-sig", newline="") as f:
                    w = csv.writer(f, delimiter=";")
                    w.writerow(["Dossier", "Chemin relatif", "Artiste", "Titre",
                                "Taille (octets)", "Durée (s)"])
                    for e in entries:
                        w.writerow([e["folder"], e["rel_path"], e["artist"],
                                    e["title"], e["size"], e["duration"]])
            except Exception as e:
                return {"done": end, "total": len(paths), "finished": True,
                        "result": {"ok": False, "error": str(e)}}
            nml = bk_find_collection_nml(src)
            nml_copied = False
            if nml:
                try:
                    import shutil as _sh
                    _sh.copy2(nml, os.path.join(out, "collection.nml"))
                    nml_copied = True
                except OSError:
                    pass
            result = {"ok": True, "out_dir": out, "tracks": len(entries),
                      "nml_copied": nml_copied}
            self._backup_log_record("structure")
        return {"done": end, "total": len(paths), "finished": finished, "result": result}

    # --- coffre-fort de playlists : export M3U miroir de collection.nml ---
    def m3u_begin(self):
        import json, datetime, shutil as _sh
        if getattr(self, "_m3u_running", False):
            return {"ok": False, "error": "Génération déjà en cours…", "total": 0}
        root = self._sync_source()
        if not (root and os.path.isdir(root)):
            return {"ok": False, "error": "Source introuvable. Définis la racine de la clé.", "total": 0}
        nml = bk_find_collection_nml(root)
        if nml is None:
            return {"ok": False, "total": 0,
                    "error": "collection.nml introuvable. Définis la racine de la clé "
                             "(le dossier qui contient collection.nml)."}
        playlists, ok = bk_parse_traktor_playlist_tree(nml)
        if not ok:
            return {"ok": False, "error": "Lecture de collection.nml impossible.", "total": 0}
        m3u_root = os.path.join(root, "M3U")
        try:
            os.makedirs(m3u_root, exist_ok=True)
        except Exception as e:
            return {"ok": False, "error": str(e), "total": 0}
        nml_backup = None
        try:
            bak_dir = os.path.join(m3u_root, "_nml_backup")
            os.makedirs(bak_dir, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
            nml_backup = os.path.join(bak_dir, "collection_%s.nml" % stamp)
            _sh.copy2(nml, nml_backup)
        except OSError:
            nml_backup = None
        old_manifest = set()
        try:
            mf = os.path.join(m3u_root, ".vault_manifest.json")
            if os.path.isfile(mf):
                with open(mf, encoding="utf-8") as f:
                    old_manifest = set(json.load(f))
        except Exception:
            old_manifest = set()
        self._m3u_root_src = root
        self._m3u_root = m3u_root
        self._m3u_playlists = playlists
        self._m3u_idx = 0
        self._m3u_produced = set()
        self._m3u_written = 0
        self._m3u_missing = 0
        self._m3u_meta = {}
        self._m3u_old_manifest = old_manifest
        self._m3u_nml_backup = nml_backup
        self._m3u_running = True
        return {"ok": True, "total": len(playlists)}

    def _m3u_get_meta(self, rel):
        if rel in self._m3u_meta:
            return self._m3u_meta[rel]
        p = os.path.join(self._m3u_root_src, rel)
        dur, artist, title = 0, "", ""
        try:
            tags = self._read_tags(p)
            artist, title = tags["artist"], tags["title"]
            dur = int(round(tags["duration"] or 0))
        except Exception:
            pass
        if not (artist and title):
            fa, ft = parse_filename(os.path.splitext(os.path.basename(rel))[0])
            artist = artist or fa or ""
            title = title or ft or os.path.splitext(os.path.basename(rel))[0]
        self._m3u_meta[rel] = (dur, artist, title)
        return self._m3u_meta[rel]

    def m3u_step(self, count=8):
        import json, unicodedata
        root = self._m3u_root_src
        m3u_root = self._m3u_root
        playlists = self._m3u_playlists
        start = self._m3u_idx
        end = min(start + count, len(playlists))
        for i in range(start, end):
            pl = playlists[i]
            folders = [_bk_safe_name(x) for x in pl["folders"]]
            pl_dir = os.path.join(m3u_root, *folders) if folders else m3u_root
            os.makedirs(pl_dir, exist_ok=True)
            m3u_file = os.path.join(pl_dir, _bk_safe_name(pl["name"]) + ".m3u")
            rel_key = os.path.relpath(m3u_file, m3u_root).replace(os.sep, "/")
            self._m3u_produced.add(rel_key)
            lines = ["#EXTM3U"]
            for rel in pl["tracks"]:
                abs_p = os.path.join(root, rel)
                dur, artist, title = self._m3u_get_meta(rel)
                lines.append(("#EXTINF:%d,%s - %s" % (dur, artist, title)).rstrip(" -"))
                lines.append(abs_p)
                if not os.path.exists(abs_p):
                    self._m3u_missing += 1
            with open(m3u_file, "w", encoding="utf-8-sig") as f:
                f.write("\n".join(lines) + "\n")
            self._m3u_written += 1
        self._m3u_idx = end
        finished = end >= len(playlists)
        result = None
        if finished:
            # mémoriser l'état de collection.nml : sert à détecter les
            # changements de structure à la fermeture de l'app
            try:
                self.last_vault_nml_hash = nml_hash((self.usb_root or "").strip())
                self._save_config()
            except Exception:
                pass
            produced = self._m3u_produced
            # Nettoyage absolu : le dossier M3U appartient au coffre-fort. Tout
            # .m3u qui ne correspond plus à une playlist actuelle est supprimé
            # (couvre aussi les fichiers antérieurs au manifest).
            produced_norm = {unicodedata.normalize("NFC", x) for x in produced}
            n_orphans = 0
            for dirpath, dirnames, filenames in os.walk(m3u_root):
                parts = dirpath.split(os.sep)
                if "_nml_backup" in parts or "IMPORTS" in parts:
                    continue
                for fn in filenames:
                    if not fn.endswith(".m3u"):
                        continue
                    full = os.path.join(dirpath, fn)
                    rel = unicodedata.normalize(
                        "NFC", os.path.relpath(full, m3u_root).replace(os.sep, "/"))
                    if rel not in produced_norm:
                        try:
                            os.unlink(full)
                            n_orphans += 1
                        except OSError:
                            pass
            for dirpath, dirnames, filenames in os.walk(m3u_root, topdown=False):
                parts = dirpath.split(os.sep)
                if "_nml_backup" in parts or "IMPORTS" in parts:
                    continue
                if os.path.abspath(dirpath) == os.path.abspath(m3u_root):
                    continue
                try:
                    if not os.listdir(dirpath):
                        os.rmdir(dirpath)
                except OSError:
                    pass
            try:
                with open(os.path.join(m3u_root, ".vault_manifest.json"), "w",
                          encoding="utf-8") as f:
                    json.dump(sorted(unicodedata.normalize("NFC", x) for x in produced),
                              f, ensure_ascii=False)
            except OSError:
                pass
            result = {"ok": True, "playlists": self._m3u_written,
                      "missing": self._m3u_missing, "orphans": n_orphans,
                      "nml_backup": self._m3u_nml_backup, "m3u_root": m3u_root}
            self._m3u_running = False
            self._backup_log_record("m3u")
        return {"done": end, "total": len(playlists), "finished": finished, "result": result}

    # --- renommage des fichiers d'après les tags (+ maj collection.nml) ---
    def _rename_setup(self):
        audio = self.music_folder
        usb = self.usb_root if (self.usb_root and os.path.isdir(self.usb_root)) else audio
        mount, volume = usb_mount_and_volume(usb)
        nml_path = bk_find_collection_nml(mount) or bk_find_collection_nml(usb)
        return audio, mount, volume, nml_path

    def rename_scan_begin(self):
        audio, mount, volume, nml_path = self._rename_setup()
        if not (audio and os.path.isdir(audio)):
            return {"ok": False, "error": "Dossier audio introuvable", "total": 0}
        idx = {}
        if nml_path and os.path.isfile(nml_path):
            try:
                with open(nml_path, encoding="utf-8", newline="") as f:
                    idx = nml_index_locations(f.read(), volume)
            except Exception:
                idx = {}
        paths = []
        for dirpath, dirnames, filenames in os.walk(audio):
            dirnames[:] = [d for d in dirnames if not is_junk(d)]
            for fn in filenames:
                if is_junk(fn):
                    continue
                if os.path.splitext(fn)[1].lower() in SUPPORTED:
                    paths.append(os.path.join(dirpath, fn))
        self._rn_paths = paths
        self._rn_idx = idx
        self._rn_mount = mount
        self._rn_nml_path = nml_path
        self._rn_i = 0
        self._rn_rows = []
        self._rn_already = 0
        self._rn_notags = 0
        self._rn_seen = {}
        return {"ok": True, "total": len(paths), "has_nml": bool(nml_path)}

    def rename_scan_step(self, count=120):
        import unicodedata
        paths = self._rn_paths
        start = self._rn_i
        end = min(start + count, len(paths))
        for i in range(start, end):
            p = paths[i]
            name = os.path.basename(p)
            ext = os.path.splitext(name)[1]
            tags = self._read_tags(p)
            artist, title = tags["artist"], tags["title"]
            if not (artist or title):
                self._rn_notags += 1
                continue
            new = build_track_filename(artist, title, ext)
            if unicodedata.normalize("NFC", new) == unicodedata.normalize("NFC", name):
                self._rn_already += 1
                continue
            d = os.path.dirname(p)
            taken = self._rn_seen.setdefault(d, set())
            base, e = os.path.splitext(new)
            cand, k = new, 2
            while cand.lower() in taken:
                cand = "%s (%d)%s" % (base, k, e)
                k += 1
            taken.add(cand.lower())
            new = cand
            try:
                dir_t = physical_to_nml_dir(p, self._rn_mount)
            except Exception:
                dir_t = None
            key = ((unicodedata.normalize("NFC", dir_t), unicodedata.normalize("NFC", name))
                   if dir_t is not None else None)
            in_nml = key in self._rn_idx if key else False
            dir_raw, file_raw = self._rn_idx.get(key, ("", "")) if in_nml else ("", "")
            try:
                disp = os.path.relpath(d, self._rn_mount)
            except Exception:
                disp = os.path.basename(d)
            self._rn_rows.append({"path": p, "old_name": name, "new_name": new,
                                  "in_nml": in_nml, "dir_raw": dir_raw,
                                  "file_raw": file_raw, "dir_display": disp})
        self._rn_i = end
        finished = end >= len(paths)
        result = None
        if finished:
            result = {"ok": True, "rows": self._rn_rows, "n_rename": len(self._rn_rows),
                      "n_already": self._rn_already, "n_no_tags": self._rn_notags,
                      "has_nml": bool(self._rn_nml_path)}
        return {"done": end, "total": len(paths), "finished": finished, "result": result}

    def rename_apply_begin(self, selection):
        if not selection:
            return {"ok": False, "error": "Aucune ligne sélectionnée", "total": 0}
        audio, mount, volume, nml_path = self._rename_setup()
        nml_text = None
        nml_backup = None
        if nml_path and os.path.isfile(nml_path):
            import datetime, shutil as _sh
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nml_backup = nml_path + ".backup_" + ts
            try:
                _sh.copy2(nml_path, nml_backup)
                with open(nml_path, encoding="utf-8", newline="") as f:
                    nml_text = f.read()
            except Exception as e:
                return {"ok": False, "error": "Sauvegarde de collection.nml impossible : %s" % e,
                        "total": 0}
        self._ra_sel = selection
        self._ra_volume = volume
        self._ra_nml_path = nml_path
        self._ra_nml_text = nml_text
        self._ra_nml_backup = nml_backup
        self._ra_i = 0
        self._ra_ok = self._ra_fail = self._ra_nmlupd = 0
        return {"ok": True, "total": len(selection), "nml_backup": nml_backup}

    def rename_apply_step(self, count=40):
        sel = self._ra_sel
        start = self._ra_i
        end = min(start + count, len(sel))
        for i in range(start, end):
            data = sel[i]
            p = data["path"]
            new_name = data["new_name"]
            target = os.path.join(os.path.dirname(p), new_name)
            if os.path.exists(target):
                self._ra_fail += 1
                continue
            try:
                os.rename(p, target)
                self._ra_ok += 1
                if data.get("in_nml") and self._ra_nml_text is not None:
                    self._ra_nml_text, n = nml_rewrite_file(
                        self._ra_nml_text, data.get("dir_raw", ""), data.get("file_raw", ""),
                        self._ra_volume, new_name)
                    if n == 1:
                        self._ra_nmlupd += 1
            except Exception:
                self._ra_fail += 1
        self._ra_i = end
        finished = end >= len(sel)
        result = None
        if finished:
            if self._ra_nml_text is not None and self._ra_nml_path:
                try:
                    tmp = self._ra_nml_path + ".tmp"
                    with open(tmp, "w", encoding="utf-8", newline="") as f:
                        f.write(self._ra_nml_text)
                    os.replace(tmp, self._ra_nml_path)
                except Exception as e:
                    return {"done": end, "total": len(sel), "finished": True,
                            "result": {"ok": False,
                                       "error": "Fichiers renommés mais écriture de collection.nml "
                                                "échouée : %s. Restaure la sauvegarde." % e,
                                       "n_renamed": self._ra_ok, "n_nml": self._ra_nmlupd,
                                       "n_failed": self._ra_fail}}
            result = {"ok": True, "n_renamed": self._ra_ok, "n_nml": self._ra_nmlupd,
                      "n_failed": self._ra_fail, "nml_backup": self._ra_nml_backup}
        return {"done": end, "total": len(sel), "finished": finished, "result": result}
