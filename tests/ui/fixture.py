"""Fabrique une fausse clé Traktor (fichiers audio + collection.nml) pour les
tests d'interface. Aucune donnée réelle : deux tonalités de 2 s copiées sous
des noms variés (accents, remix, doublon, fichiers sans tags, liens cassés).

    build(dossier) -> chemin de la racine de la clé
"""
import html
import os
import random
import shutil

from mutagen.id3 import ID3, TCON, TIT2, TPE1

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

TRACKS = [  # artiste, titre, genre, année, basse qualité, tags présents
    ("Daft Punk", "One More Time", "French touch", 2000, 0, 1),
    ("Daft Punk", "One More Time (Extended Mix)", "French touch", 2000, 0, 1),
    ("113", "Tonton du bled", "Rap/Hip-hop", 1999, 0, 1),
    ("50 Cent", "In Da Club", "Rap/Hip-hop", 2003, 1, 1),
    ("Røyksopp", "Eple", "Electro chill", 2001, 0, 1),
    ("Étienne de Crécy", "Prix Choc", "French touch", 2004, 0, 1),
    ("Chic", "Le Freak (Dimitri From Paris Remix)", "Disco/Funk/Soul", 1978, 0, 1),
    ("Mylène Farmer", "Sans contrefaçon (The Magician Remix)", "Pop", 1987, 0, 1),
    ("Joe Dassin", "L'été indien", "Chanson FR", 1975, 1, 1),
    ("Boney M.", "Daddy Cool", "Disco/Funk/Soul", 1976, 0, 1),
    ("Amelie Lens", "In My Mind", "Techno", 2019, 0, 1),
    ("Charlotte de Witte", "Doppler", "Techno dark", 2020, 0, 1),
    ("Indira Paganotto", "Akelarre", "Techno hard", 2021, 0, 1),
    ("Kölsch", "Grey", "Techno melodic", 2015, 0, 1),
    ("Bon Entendeur", "Le Temps est bon", "House", 2019, 0, 1),
    ("Saint Germain", "Rose Rouge", "Electro chill", 2000, 0, 1),
    ("Jain", "Makeba", "Pop", 2015, 1, 1),
    ("Max Richter", "On the Nature of Daylight", "Classique", 2004, 0, 1),
    ("Avicii, Aloe Blacc", "Wake Me Up", "EDM/Big room", 2013, 1, 1),
    ("Queen", "Another One Bites the Dust", "Rock", 1980, 0, 1),
    ("Kavinsky", "Nightcall", "Synthwave", 2010, 0, 1),
    ("Inconnu", "", None, None, 0, 0),
    ("", "Track 07", None, None, 1, 0),
]


def build(base):
    rnd = random.Random(1)
    root = os.path.join(base, "Volumes", "FRASANDISK")
    music = os.path.join(root, "Music")
    shutil.rmtree(os.path.join(base, "Volumes"), ignore_errors=True)
    os.makedirs(music)
    os.makedirs(os.path.join(root, "Traktor"))
    hi = os.path.join(ASSETS, "tone320.mp3")
    lo = os.path.join(ASSETS, "tone128.mp3")
    tracks = list(TRACKS)
    for i in range(20):
        tracks.append(("Artiste %02d" % i, "Morceau numéro %d" % i,
                       rnd.choice(["House", "Techno", "Pop", "Rap/Hip-hop"]),
                       2000 + i % 24, i % 7 == 0, 1))
    files = []
    for a, t, g, y, low, tags in tracks:
        name = ("%s - %s.mp3" % (a, t)) if a and t else ((t or a or "piste") + ".mp3")
        name = name.replace("/", ", ")
        p = os.path.join(music, name)
        shutil.copy(lo if low else hi, p)
        if tags:
            id3 = ID3()
            id3.add(TPE1(encoding=3, text=a))
            id3.add(TIT2(encoding=3, text=t))
            if g:
                id3.add(TCON(encoding=3, text=g))
            id3.save(p)
        files.append((name, a, t, g, y))
    # doublon « copie système »
    shutil.copy(os.path.join(music, "Daft Punk - One More Time.mp3"),
                os.path.join(music, "Daft Punk - One More Time (1).mp3"))

    e = lambda s: html.escape(s, quote=True)  # noqa: E731
    ents, keys = [], []
    for name, a, t, g, y in files:
        info = '<INFO BITRATE="320000" %s %s RANKING="153"></INFO>' % (
            ('GENRE="%s"' % e(g)) if g else "", ('RELEASE_DATE="%d/1/1"' % y) if y else "")
        ents.append('<ENTRY ARTIST="%s" TITLE="%s"><LOCATION DIR="/:Music/:" FILE="%s" '
                    'VOLUME="FRASANDISK" VOLUMEID="x"></LOCATION>%s</ENTRY>' % (e(a), e(t), e(name), info))
        keys.append("FRASANDISK/:Music/:" + e(name))

    def pl(name, ks):
        return ('<NODE TYPE="PLAYLIST" NAME="%s"><PLAYLIST ENTRIES="%d" TYPE="LIST" UUID="u%d">%s'
                '</PLAYLIST></NODE>' % (e(name), len(ks), len(name),
                                        "".join('<ENTRY><PRIMARYKEY TYPE="TRACK" KEY="%s">'
                                                '</PRIMARYKEY></ENTRY>' % k for k in ks)))
    dangling = ["FRASANDISK/:Music/:Disparu - Fantôme.mp3"]
    nodes = [pl("COCKTAIL", keys[:8]), pl("TECHNO", keys[10:14] + dangling),
             '<NODE TYPE="FOLDER" NAME="GENRES"><SUBNODES COUNT="1">%s</SUBNODES></NODE>'
             % pl("House", keys[14:16])]
    nml = ('<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n<NML VERSION="19">'
           '<HEAD COMPANY="www.native-instruments.com" PROGRAM="Traktor"></HEAD>'
           '<COLLECTION ENTRIES="%d">%s</COLLECTION><PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT">'
           '<SUBNODES COUNT="%d">%s</SUBNODES></NODE></PLAYLISTS></NML>\n'
           % (len(ents), "\n".join(ents), len(nodes), "".join(nodes)))
    with open(os.path.join(root, "Traktor", "collection.nml"), "w", encoding="utf-8") as f:
        f.write(nml)
    return root
