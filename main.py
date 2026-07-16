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
        self.core = Core()
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
        self.core.set_music_folder(path)
        return {"ok": True, "path": path}

    def pick_usb_root(self):
        try:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not res:
            return {"ok": False, "cancelled": True}
        path = res[0] if isinstance(res, (list, tuple)) else res
        return self.core.set_usb_root(path)

    def reset_usb_root(self):
        return self.core.set_usb_root("")

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
        return self.core.export_found_m3u(dest)

    def export_missing_txt(self):
        try:
            res = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not res:
            return {"ok": False, "cancelled": True}
        dest = res[0] if isinstance(res, (list, tuple)) else res
        return self.core.export_missing_txt(dest)

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
        return self.core.full_backup_begin(dest)

    def full_backup_step(self, count=40):
        return self.core.full_backup_step(count)

    def export_structure_begin(self, dest):
        return self.core.export_structure_begin(dest)
    def export_structure_step(self, count=80):
        return self.core.export_structure_step(count)

    def m3u_begin(self):
        return self.core.m3u_begin()

    def m3u_step(self, count=8):
        return self.core.m3u_step(count)

    def rename_scan_begin(self):
        return self.core.rename_scan_begin()

    def rename_scan_step(self, count=120):
        return self.core.rename_scan_step(count)

    def rename_apply_begin(self, selection):
        return self.core.rename_apply_begin(selection)

    def rename_apply_step(self, count=40):
        return self.core.rename_apply_step(count)

    # --- état / données ---
    def get_state(self):
        return self.core.get_state()

    def compute_status(self):
        return self.core.compute_status()

    def reveal_file(self, path):
        return self.core.reveal_file(path)

    def home_stats(self):
        return self.core.home_stats()

    def backups_status(self):
        return self.core.backups_status()

    def scan_library(self):
        return self.core.scan_library()

    def scan_begin(self):
        return self.core.scan_begin()

    def scan_step(self, count=150):
        return self.core.scan_step(count)

    def find_duplicates(self):
        return self.core.find_duplicates()

    def resolve_duplicates(self):
        return self.core.resolve_duplicates()

    def set_dup_master(self, path):
        return self.core.set_dup_master(path)

    def orphan_tracks(self):
        return self.core.orphan_tracks()

    def dup_backup_info(self):
        return self.core.dup_backup_info()

    def restore_duplicates(self):
        return self.core.restore_duplicates()

    def clean_dup_backups(self):
        return self.core.clean_dup_backups()

    def audiodup_begin(self, threshold=0.85):
        return self.core.audiodup_begin(threshold)

    def audiodup_step(self, count=8):
        return self.core.audiodup_step(count)

    def audiodup_finalize(self):
        return self.core.audiodup_finalize()

    def audiodup_cancel(self):
        return self.core.audiodup_cancel()

    def check_integrity(self, mode="quick"):
        return self.core.check_integrity(mode)

    def integ_begin(self, mode="quick", workers=4):
        return self.core.integ_begin(mode, workers)

    def integ_step(self, count=40):
        return self.core.integ_step(count)

    def integ_cancel(self):
        return self.core.integ_cancel()

    def set_acoustid_key(self, key):
        return self.core.set_acoustid_key(key)

    def set_lang(self, lang):
        return self.core.set_lang(lang)

    def acoustid_begin(self):
        return self.core.acoustid_begin()

    def acoustid_step(self, count=3):
        return self.core.acoustid_step(count)

    def enrich_begin(self):
        return self.core.enrich_begin()

    def enrich_step(self, count=3):
        return self.core.enrich_step(count)

    def enrich_apply(self, selection):
        return self.core.enrich_apply(selection)

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
        return self.core.import_check_begin(folder)

    def import_check_step(self, count=3):
        return self.core.import_check_step(count)

    def import_discard(self, paths):
        return self.core.import_discard(paths)

    def check_tags(self):
        return self.core.check_tags()

    def apply_retag(self):
        return self.core.apply_retag()

    def compare_playlist(self, text):
        return self.core.compare_playlist(text)

    def compare_begin(self, text, threshold=85):
        return self.core.compare_begin(text, threshold)

    def compare_step(self, count=25):
        return self.core.compare_step(count)

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
        return self.core.plan_sync(spare)

    def apply_sync(self, spare):
        return self.core.apply_sync(spare)

    def sync_apply_begin(self, spare):
        return self.core.sync_apply_begin(spare)

    def sync_apply_step(self, count=50):
        return self.core.sync_apply_step(count)


def main():
    api = Api()
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
    webview.start(debug=bool(os.environ.get("DJHELPER_DEBUG")))


if __name__ == "__main__":
    main()
