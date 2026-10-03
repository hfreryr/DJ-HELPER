"""Tests de non-régression des garde-fous « données » de DJ Helper.

Chaque test reproduit un scénario de perte ou de corruption trouvé à l'audit
v1.5.15 : on ne doit jamais perdre un morceau, une référence de playlist ou
la sauvegarde de collection.nml.

Lancement :  python3 -m pytest -q tests
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core  # noqa: E402

HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n<NML VERSION="19">'


def _nml(collection, playlist_keys):
    entries = "".join(
        '<ENTRY><PRIMARYKEY TYPE="TRACK" KEY="%s"></PRIMARYKEY></ENTRY>\n' % k
        for k in playlist_keys)
    return (HEAD + '<COLLECTION ENTRIES="%d">\n%s</COLLECTION>'
            '<PLAYLISTS><NODE TYPE="FOLDER" NAME="$ROOT"><SUBNODES COUNT="1">\n'
            '<NODE TYPE="PLAYLIST" NAME="P"><PLAYLIST ENTRIES="%d" TYPE="LIST" UUID="u">\n'
            '%s</PLAYLIST></NODE></SUBNODES></NODE></PLAYLISTS></NML>\n'
            % (len(collection), "".join(collection), len(playlist_keys), entries))


def _entry(d, f, vol, info='<INFO GENRE="House"></INFO>'):
    return ('<ENTRY TITLE="t" ARTIST="a"><LOCATION DIR="%s" FILE="%s" VOLUME="%s" '
            'VOLUMEID="x"></LOCATION>%s</ENTRY>\n' % (d, f, vol, info))


def _touch(path, data=b"x" * 100):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def _bare_core(**attrs):
    c = core.Core.__new__(core.Core)
    c.tracks = []
    c.usb_root = ""
    c.music_folder = ""
    for k, v in attrs.items():
        setattr(c, k, v)
    return c


# --------------------------------------------------------------- doublons
@pytest.fixture
def dup_usb(tmp_path):
    usb = tmp_path / "FRASANDISK"
    for n in ("Song.mp3", "Song.flac", "Song (1).mp3"):
        _touch(str(usb / "Music" / "A" / n))
    nml = usb / "Traktor" / "collection.nml"
    os.makedirs(nml.parent)
    nml.write_text(_nml(
        [_entry("/:Music/:A/:", "Song.mp3", "FRASANDISK"),
         _entry("/:Music/:A/:", "Song.flac", "FRASANDISK"),
         _entry("/:Music/:A/:", "Song.flac", "T:"),
         _entry("/:Music/:A/:", "Song (1).mp3", "FRASANDISK")],
        ["FRASANDISK/:Music/:A/:Song.flac", "T:/:Music/:A/:Song.flac",
         "FRASANDISK/:Music/:A/:Song (1).mp3"]), encoding="utf-8")
    return str(usb), str(nml)


def _group(usb):
    p = lambda n: os.path.join(usb, "Music", "A", n)
    return [{"path": p("Song.mp3"), "ext": "mp3", "bitrate": 320, "size": 100, "name": "Song.mp3"},
            {"path": p("Song.flac"), "ext": "flac", "bitrate": 900, "size": 100, "name": "Song.flac"},
            {"path": p("Song (1).mp3"), "ext": "mp3", "bitrate": 320, "size": 100,
             "name": "Song (1).mp3"}]


def test_dup_repoints_every_volume_and_moves_after_nml(dup_usb):
    usb, nml = dup_usb
    c = _bare_core(usb_root=usb)
    c._dup_usb = lambda: usb
    c._last_dup_groups = [{"versions": [dict(v, keep=(i == 0)) for i, v in enumerate(_group(usb))]}]
    r = c.resolve_duplicates()
    assert r["ok"] and r["n_repointed"] == 3 and r["n_moved"] == 2
    txt = open(nml, encoding="utf-8").read()
    assert txt.count('KEY="FRASANDISK/:Music/:A/:Song.mp3"') == 3
    assert "Song.flac\"></PRIMARYKEY>" not in txt
    assert os.path.exists(os.path.join(usb, "Music", "A", "Song.mp3"))
    # filet de sécurité : sauvegarde faite avant l'écriture
    assert os.listdir(core.nml_backup_dir(nml))


def test_dup_plan_touches_nothing_on_disk(dup_usb):
    usb, _nml_path = dup_usb
    text = open(_nml_path, encoding="utf-8").read()
    g = {"0": _group(usb)}
    new, st = core.fix_duplicates_via_playlists(
        text, usb, "FRASANDISK", g, {"0": g["0"][0]["path"]}, "", usb)
    assert sorted(os.path.basename(p) for p in st["to_move"]) == ["Song (1).mp3", "Song.flac"]
    assert st["kept_back"] == []
    # préparation pure : aucun fichier déplacé, nml sur disque inchangé
    assert all(os.path.exists(v["path"]) for v in g["0"])
    assert open(_nml_path, encoding="utf-8").read() == text


def test_restore_never_deletes_existing_file(dup_usb):
    usb, _ = dup_usb
    c = _bare_core(usb_root=usb)
    c._dup_usb = lambda: usb
    c._last_dup_groups = [{"versions": [dict(v, keep=(i == 0)) for i, v in enumerate(_group(usb))]}]
    c.resolve_duplicates()
    flac = os.path.join(usb, "Music", "A", "Song.flac")
    _touch(flac, b"NEW")                                   # un fichier a repris ce nom
    r = c.restore_duplicates()
    assert r["n_restored"] == 1 and r["n_conflict"] == 1
    assert open(flac, "rb").read() == b"NEW"
    assert os.path.exists(os.path.join(usb, "Music", "A", "Song.mp3"))


def test_dup_key_keeps_version_info():
    k = lambda t: core.normalize_string(t, keep_versions=True)
    assert k("Song (Extended Mix)") != k("Song")
    assert k("Song [Extended Mix]") != k("Song")
    assert k("Song (Live Video)") != k("Song")
    assert k("Song (Official Video)") == k("Song")
    assert k("Song (feat. X)") == k("Song")
    assert k("Song (Original Mix)") == k("Song")
    assert k("Song (1)") == k("Song")
    assert core.normalize_string("Røyksopp Œuvre Straße") == "royksopp oeuvre strasse"


# --------------------------------------------------------------- synchro
@pytest.fixture
def sync_dirs(tmp_path):
    m, s = tmp_path / "master", tmp_path / "spare"
    t = time.time()
    _touch(str(m / "A" / "Song.mp3"), b"1" * 10)
    _touch(str(s / "A" / "song.mp3"), b"1" * 10)            # casse différente
    _touch(str(m / "A" / "dst.mp3"), b"3" * 10)
    _touch(str(s / "A" / "dst.mp3"), b"3" * 10)
    _touch(str(s / "A" / "extra.mp3"), b"x")
    for p, ts in ((m / "A" / "Song.mp3", t), (s / "A" / "song.mp3", t),
                  (m / "A" / "dst.mp3", t), (s / "A" / "dst.mp3", t + 3600)):
        os.utime(str(p), (ts, ts))
    c = _bare_core()
    c._sync_source = lambda: str(m)
    c._backup_log_record = lambda kind: None
    return c, str(m), str(s), tmp_path


def test_sync_case_rename_instead_of_copy_delete(sync_dirs):
    c, m, s, _ = sync_dirs
    p = c.plan_sync(s)
    assert p["to_copy"] == []                      # DST (+1 h pile) = identique
    assert p["to_delete"] == ["A/extra.mp3"]
    assert p["to_rename"] == [["A/song.mp3", "A/Song.mp3"]]
    assert c.sync_apply_begin(s)["ok"]
    res = c.sync_apply_step(50)["result"]
    assert res["n_renamed"] == 1 and res["n_deleted"] == 1
    assert sorted(os.listdir(os.path.join(s, "A"))) == ["Song.mp3", "dst.mp3"]


def test_sync_and_backup_refuse_overlap(sync_dirs):
    c, m, s, root = sync_dirs
    os.makedirs(os.path.join(m, "sub"))
    for target in (os.path.join(m, "sub"), str(root), m):
        assert not c.plan_sync(target)["ok"]
        assert not c.full_backup_begin(target)["ok"]
    assert not core.paths_overlap(m, m + "2")


# --------------------------------------------------------------- renommage
@pytest.fixture
def rename_usb(tmp_path):
    usb = tmp_path / "KEY"
    _touch(str(usb / "Music" / "113 - tonton.mp3"))
    _touch(str(usb / "Music" / "R&B track.mp3"))
    nml = usb / "Traktor" / "collection.nml"
    os.makedirs(nml.parent)
    nml.write_text(_nml(
        [_entry("/:Music/:", "113 - tonton.mp3", "KEY"),
         _entry("/:Music/:", "113 - tonton.mp3", "T:"),
         _entry("/:Music/:", "R&amp;B track.mp3", "KEY")],
        ["KEY/:Music/:113 - tonton.mp3", "T:/:Music/:113 - tonton.mp3",
         "KEY/:Music/:R&amp;B track.mp3"]), encoding="utf-8")
    c = _bare_core()
    c._rename_setup = lambda: (str(usb / "Music"), str(usb), "KEY", str(nml))
    return c, str(usb), str(nml)


def test_rename_updates_locations_and_playlist_keys(rename_usb):
    c, usb, nml = rename_usb
    music = os.path.join(usb, "Music")
    assert c.rename_apply_begin([
        {"path": os.path.join(music, "113 - tonton.mp3"), "new_name": "113 - Tonton du bled.mp3"},
        {"path": os.path.join(music, "R&B track.mp3"), "new_name": "R&B - Track.mp3"}])["ok"]
    res = c.rename_apply_step(40)["result"]
    assert res["n_renamed"] == 2 and res["n_refs"] == 3
    txt = open(nml, encoding="utf-8").read()
    assert "113 - tonton.mp3" not in txt
    assert txt.count("113 - Tonton du bled.mp3") == 4
    assert txt.count("R&amp;B - Track.mp3") == 2
    assert core.nml_dangling_refs(txt) == []


def test_rename_rolls_back_when_nml_write_fails(rename_usb, monkeypatch):
    c, usb, nml = rename_usb
    src = os.path.join(usb, "Music", "R&B track.mp3")
    c.rename_apply_begin([{"path": src, "new_name": "RB.mp3"}])

    def boom(path, text):
        raise OSError("disque plein")
    monkeypatch.setattr(core, "nml_write_atomic", boom)
    res = c.rename_apply_step(40)["result"]
    assert not res["ok"]
    assert os.path.exists(src)                      # renommage annulé
    assert "R&amp;B track.mp3" in open(nml, encoding="utf-8").read()


def test_rename_case_only(rename_usb):
    c, usb, nml = rename_usb
    src = os.path.join(usb, "Music", "113 - tonton.mp3")
    c.rename_apply_begin([{"path": src, "new_name": "113 - Tonton.mp3"}])
    res = c.rename_apply_step(40)["result"]
    assert res["ok"] and res["n_renamed"] == 1
    assert "113 - Tonton.mp3" in os.listdir(os.path.join(usb, "Music"))


def test_dangling_refs_detects_case_renames():
    t = ('<LOCATION DIR="/:M/:" FILE="Song.mp3" VOLUME="K"></LOCATION>'
         '<PRIMARYKEY TYPE="TRACK" KEY="K/:M/:song.mp3"></PRIMARYKEY>'
         '<PRIMARYKEY TYPE="TRACK" KEY="K/:M/:gone.mp3"></PRIMARYKEY>'
         '<PRIMARYKEY TYPE="TRACK" KEY="K/:M/:Song.mp3"></PRIMARYKEY>')
    assert core.nml_dangling_refs(t) == [("K/:M/:song.mp3", "K/:M/:Song.mp3"),
                                         ("K/:M/:gone.mp3", None)]


# --------------------------------------------------------------- validation (nml)
def test_review_write_keeps_comment_and_refuses_bad_year(tmp_path):
    usb = tmp_path / "KEY"
    nml = usb / "Traktor" / "collection.nml"
    os.makedirs(nml.parent)
    nml.write_text(_nml([_entry("/:Music/:", "a.mp3", "KEY",
                                '<INFO GENRE="House" COMMENT="perso &amp; co"/>')],
                        []), encoding="utf-8", newline="")
    c = _bare_core(usb_root=str(usb))
    c._review_nml_path = lambda: str(nml)
    c._review_backup_nml = lambda p: None
    ok, err = c._review_write_nml("KEY/:Music/:a.mp3", {"genre": "Techno", "mark": "Club"})
    assert ok, err
    txt = open(nml, encoding="utf-8").read()
    assert 'GENRE="Techno"' in txt and "Club" in txt and "perso &amp; co" in txt
    ok, err = c._review_write_nml("KEY/:Music/:a.mp3", {"year": "19x5"})
    assert not ok and "année" in err


def test_nml_write_atomic_refuses_broken_xml(tmp_path):
    p = tmp_path / "collection.nml"
    p.write_text(HEAD + "</NML>", encoding="utf-8")
    with pytest.raises(Exception):
        core.nml_write_atomic(str(p), HEAD + "<COLLECTION>")
    assert p.read_text(encoding="utf-8") == HEAD + "</NML>"


# --------------------------------------------------------------- divers
def test_json_save_atomic_and_quarantine(tmp_path):
    p = str(tmp_path / "c.json")
    core.json_save_atomic(p, {"a": 1})
    assert open(p).read() == '{"a": 1}'
    open(p, "w").write("{cassé")
    core.json_quarantine(p)
    assert not os.path.exists(p)
    assert any(f.startswith("c.json.corrupt-") for f in os.listdir(tmp_path))


def test_title_cleanup_keeps_real_titles():
    f = core.rv_clean_title_proposal
    assert f("Nena - 99 Luftballons", "Nena") == "99 Luftballons"
    assert f("Love - 2 Become 1") is None
    assert f("Best Of 2010 - 07 Titanium", "David Guetta") == "Titanium"
    assert f("Song [Dirty]") is None


def test_enrichment_refuses_empty_normalised_names():
    assert core.enr_find_year("東京", "★") == (None, None)


def test_bk_differs_dst_tolerance():
    assert not core.bk_differs((10, 1000.0), (10, 4600.0))
    assert not core.bk_differs((10, 1000.0), (10, 1001.5))
    assert core.bk_differs((10, 1000.0), (10, 2000.0))
    assert core.bk_differs((10, 1000.0), (11, 1000.0))


def test_sync_folder_case_difference_does_not_loop(tmp_path):
    m, s = tmp_path / "master", tmp_path / "spare"
    _touch(str(m / "Techno" / "x.mp3"), b"1")
    _touch(str(s / "techno" / "x.mp3"), b"1")
    t = time.time()
    for p in (m / "Techno" / "x.mp3", s / "techno" / "x.mp3"):
        os.utime(str(p), (t, t))
    c = _bare_core()
    c._sync_source = lambda: str(m)
    p = c.plan_sync(str(s))
    assert p["to_rename"] == [] and p["to_copy"] == [] and p["to_delete"] == []


def test_compilation_prefix():
    f = core._strip_compilation_prefix
    assert f("Now 80 - 12 Take On Me") == "Take On Me"
    assert f("Hits - 07 Song") == "Song"
    assert f("Nena - 99 Luftballons") == "Nena - 99 Luftballons"
    assert f("Love - 2 Become 1") == "Love - 2 Become 1"


def test_learn_artist_uses_lookup_key_and_keeps_mirror(tmp_path, monkeypatch):
    import json
    usb = tmp_path / "KEY"
    os.makedirs(usb)
    (usb / "DJHELPER_MEMOIRE.json").write_text(
        json.dumps({"kavinsky": {"genres": {"Synthwave": 3}, "source": "user"}}), encoding="utf-8")
    c = _bare_core(usb_root=str(usb))
    local = tmp_path / "home" / "artist_genres.json"
    c._review_artist_table_path = lambda: str(local)
    c._review_learn_artist("Daft Punk", "French touch")
    table = json.loads(local.read_text(encoding="utf-8"))
    assert "daftpunk" in table and "kavinsky" in table      # miroir préservé
    mirror = json.loads((usb / "DJHELPER_MEMOIRE.json").read_text(encoding="utf-8"))
    assert "kavinsky" in mirror and "daftpunk" in mirror
