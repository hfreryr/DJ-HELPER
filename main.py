"""
main.py — lanceur du socle DJ Helper (web / pywebview).

Lance une fenêtre d'application NATIVE (pas un navigateur) qui affiche web/index.html.
La classe Api expose la logique Python au JavaScript via window.pywebview.api.*

Lancement :  python3 main.py
Prérequis  :  pip install pywebview mutagen rapidfuzz
"""

import os
import sys

import webview

from core import Core


def resource_path(rel):
    """Chemin d'une ressource, compatible exécution normale et bundle PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# Fixe le bundle CA (SSL) avec un chemin absolu fiable, avant tout appel réseau.
try:
    import core as _core_mod
    _ca = resource_path("cacert.pem")
    if os.path.isfile(_ca):
        _core_mod._CA_BUNDLE = _ca
except Exception:
    pass


class Api:
    def __init__(self):
        # « _core » : pywebview n'expose pas les attributs préfixés « _ ». En
        # public, TOUTES les méthodes de Core (non protégées) seraient appelables
        # depuis le JS et parcourues au chargement.
        self._core = Core()
        self._window = None

    def set_window(self, window):
        self._window = window

    # --- dialogues natifs ---
    def pick_music_folder(self):
        try:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not res:
            return {"ok": False, "cancelled": True}
        path = res[0] if isinstance(res, (list, tuple)) else res
        self._core.set_music_folder(path)
        return {"ok": True, "path": path}

    def pick_usb_root(self):
        try:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not res:
            return {"ok": False, "cancelled": True}
        path = res[0] if isinstance(res, (list, tuple)) else res
        return self._core.set_usb_root(path)

    def reset_usb_root(self):
        return self._core.set_usb_root("")

    def pick_struct_dest(self):
        try:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not res:
            return {"ok": False, "cancelled": True}
        path = res[0] if isinstance(res, (list, tuple)) else res
        return {"ok": True, "path": path}

    def export_found_m3u(self):
        try:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not res:
            return {"ok": False, "cancelled": True}
        dest = res[0] if isinstance(res, (list, tuple)) else res
        return self._core.export_found_m3u(dest)

    def export_missing_txt(self):
        try:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not res:
            return {"ok": False, "cancelled": True}
        dest = res[0] if isinstance(res, (list, tuple)) else res
        return self._core.export_missing_txt(dest)

    def pick_full_dest(self):
        try:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not res:
            return {"ok": False, "cancelled": True}
        path = res[0] if isinstance(res, (list, tuple)) else res
        return {"ok": True, "path": path}

    def full_backup_begin(self, dest):
        return self._core.full_backup_begin(dest)

    def full_backup_step(self, count=40):
        return self._core.full_backup_step(count)

    def export_structure_begin(self, dest):
        return self._core.export_structure_begin(dest)
    def export_structure_step(self, count=80):
        return self._core.export_structure_step(count)

    def m3u_begin(self):
        return self._core.m3u_begin()

    def m3u_step(self, count=8):
        return self._core.m3u_step(count)

    def rename_scan_begin(self):
        return self._core.rename_scan_begin()

    def rename_scan_step(self, count=120):
        return self._core.rename_scan_step(count)

    def rename_apply_begin(self, selection):
        return self._core.rename_apply_begin(selection)

    def rename_apply_step(self, count=40):
        return self._core.rename_apply_step(count)

    # --- état / données ---
    def get_state(self):
        return self._core.get_state()

    def compute_status(self):
        return self._core.compute_status()

    def reveal_file(self, path):
        return self._core.reveal_file(path)

    def check_dir_entries(self):
        return self._core.check_dir_entries()

    def playlist_refs_check(self):
        return self._core.playlist_refs_check()

    def playlist_refs_fix(self):
        return self._core.playlist_refs_fix()

    def backups_overview(self):
        return self._core.backups_overview()

    def traktor_backups_clean(self, keep=10):
        return self._core.traktor_backups_clean(keep)

    def home_stats(self):
        return self._core.home_stats()

    def backups_status(self):
        return self._core.backups_status()

    def scan_begin(self):
        return self._core.scan_begin()

    def scan_step(self, count=150):
        return self._core.scan_step(count)

    def find_duplicates(self, store=True):
        return self._core.find_duplicates(bool(store))

    def resolve_duplicates(self):
        return self._core.resolve_duplicates()

    def set_dup_master(self, path):
        return self._core.set_dup_master(path)

    def orphan_tracks(self):
        return self._core.orphan_tracks()

    def orphans_to_traktor(self):
        return self._core.orphans_to_traktor()

    def dup_backup_info(self):
        return self._core.dup_backup_info()

    def restore_duplicates(self):
        return self._core.restore_duplicates()

    def clean_dup_backups(self):
        return self._core.clean_dup_backups()

    def audiodup_begin(self, threshold=0.85):
        return self._core.audiodup_begin(threshold)

    def audiodup_step(self, count=8):
        return self._core.audiodup_step(count)

    def audiodup_finalize(self):
        return self._core.audiodup_finalize()

    def audiodup_cancel(self):
        return self._core.audiodup_cancel()

    def integ_begin(self, mode="quick", workers=4):
        return self._core.integ_begin(mode, workers)

    def integ_step(self, count=40):
        return self._core.integ_step(count)

    def integ_cancel(self):
        return self._core.integ_cancel()

    def set_acoustid_key(self, key):
        return self._core.set_acoustid_key(key)

    def set_lang(self, lang):
        return self._core.set_lang(lang)

    # --- Nettoyer ma bibliothèque (file de validation + enrichissement) ---
    def review_scan(self):
        return self._core.review_scan()

    def review_state(self):
        return self._core.review_state()

    def review_apply(self, item_id, patch=None):
        return self._core.review_apply(item_id, patch)

    def review_skip(self, item_id):
        return self._core.review_skip(item_id)

    def review_approve(self, item_id):
        return self._core.review_approve(item_id)

    def auto_enrich_begin(self):
        return self._core.auto_enrich_begin()

    def auto_enrich_step(self, batch=2):
        return self._core.auto_enrich_step(batch)

    def auto_enrich_stop(self):
        return self._core.auto_enrich_stop()

    def vault_check(self):
        return self._core.vault_check()

    def confirm_quit(self):
        """Fermeture définitive demandée par l'UI (après le choix de l'utilisateur)."""
        self._quit_ok = True
        try:
            self._window.destroy()
        except Exception:
            pass
        return {"ok": True}

    def acoustid_begin(self):
        return self._core.acoustid_begin()

    def acoustid_step(self, count=3):
        return self._core.acoustid_step(count)

    def enrich_begin(self):
        return self._core.enrich_begin()

    def enrich_step(self, count=3):
        return self._core.enrich_step(count)

    def enrich_cancel(self):
        return self._core.enrich_cancel()

    def enrich_apply(self, selection):
        return self._core.enrich_apply(selection)

    def pick_import_folder(self):
        try:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not res:
            return {"ok": False, "cancelled": True}
        path = res[0] if isinstance(res, (list, tuple)) else res
        return {"ok": True, "path": path}

    def import_check_begin(self, folder):
        return self._core.import_check_begin(folder)

    def import_check_step(self, count=3):
        return self._core.import_check_step(count)

    def import_discard(self, paths):
        return self._core.import_discard(paths)

    def check_tags(self):
        return self._core.check_tags()

    def apply_retag(self):
        return self._core.apply_retag()

    def compare_begin(self, text, threshold=85):
        return self._core.compare_begin(text, threshold)

    def compare_step(self, count=25):
        return self._core.compare_step(count)

    # --- synchro ---
    def pick_spare_folder(self):
        try:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not res:
            return {"ok": False, "cancelled": True}
        path = res[0] if isinstance(res, (list, tuple)) else res
        return {"ok": True, "path": path}

    def plan_sync(self, spare):
        return self._core.plan_sync(spare)

    def sync_apply_begin(self, spare):
        return self._core.sync_apply_begin(spare)

    def sync_apply_step(self, count=50):
        return self._core.sync_apply_step(count)


def _guard(fn):
    """Toute exception Python devient {ok: False, error} au lieu d'une promesse
    JS rejetée (bouton bloqué, spinner infini). La trace va sur stderr et dans
    ~/.djhelper/errors.log pour diagnostic."""
    import functools, inspect, traceback

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            tb = traceback.format_exc()
            sys.stderr.write(tb)
            try:
                d = os.path.join(os.path.expanduser("~"), ".djhelper")
                os.makedirs(d, exist_ok=True)
                p = os.path.join(d, "errors.log")
                if os.path.isfile(p) and os.path.getsize(p) > 512 * 1024:
                    os.replace(p, p + ".1")
                import datetime
                with open(p, "a", encoding="utf-8") as f:
                    f.write("== %s %s\n%s\n" % (datetime.datetime.now().isoformat(timespec="seconds"),
                                                fn.__name__, tb))
            except Exception:
                pass
            # « finished » arrête aussi les boucles *_step côté JS
            return {"ok": False, "finished": True,
                    "error": "%s : %s" % (type(e).__name__, str(e)[:300])}
    # pywebview lit les paramètres via getfullargspec (qui ignore __wrapped__)
    wrapper.__signature__ = inspect.signature(fn)
    return wrapper


for _name, _fn in list(vars(Api).items()):
    if callable(_fn) and not _name.startswith("_") and _name != "set_window":
        setattr(Api, _name, _guard(_fn))


def main():
    api = Api()

    def on_closing():
        if getattr(api, "_quit_ok", False):
            return True
        if api._core.m3u_busy():
            return False   # génération en cours : ne pas fermer
        # Le handler « closing » est appelé SUR LE THREAD UI. Y appeler
        # evaluate_js() attend une réponse du moteur web, qui ne peut être
        # rendue que par ce même thread : interblocage (roue arc-en-ciel sur
        # macOS, gel sur Windows) — et seulement quand le coffre a changé,
        # d'où « une fois sur deux ». On ferme donc toujours directement : le
        # contrôle au DÉMARRAGE (app.js) proposera la régénération.
        return True

    window = webview.create_window(
        "DJ Helper",
        resource_path("web/index.html"),
        js_api=api,
        width=1140,
        height=760,
        min_size=(960, 640),
        background_color="#191919",
    )
    api.set_window(window)
    window.events.closing += on_closing
    webview.start(debug=bool(os.environ.get("DJHELPER_DEBUG")))


if __name__ == "__main__":
    main()
