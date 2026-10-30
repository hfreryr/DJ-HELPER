"""Sert web/ et expose la vraie Api (main.py) en HTTP, sur 127.0.0.1, pour les
tests d'interface sans pywebview. Le script tests/ui/bridge.js remplace
window.pywebview.api par des appels POST /api/<méthode>.

Réservé aux tests : n'écoute que sur la boucle locale.
"""
import http.server
import json
import os
import socketserver
import sys
import threading
import types

APP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def start(home, port=0):
    """Lance le serveur dans un thread ; renvoie (url, serveur)."""
    os.environ["HOME"] = home
    os.environ["USERPROFILE"] = home
    os.makedirs(home, exist_ok=True)
    sys.path.insert(0, APP)
    wv = types.ModuleType("webview")
    wv.FOLDER_DIALOG = 20
    sys.modules.setdefault("webview", wv)
    import main  # noqa: E402

    dialog = {"next": None}

    class FakeWin:
        def create_file_dialog(self, *a, **k):
            return [dialog["next"]] if dialog["next"] else None

        def destroy(self):
            pass

        def evaluate_js(self, s):
            pass

    api = main.Api()
    api.set_window(FakeWin())

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=os.path.join(APP, "web"), **k)

        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"[]")
            name = self.path.strip("/").split("/")[-1]
            if name == "__dialog":
                dialog["next"] = body[0]
                out = {"ok": True}
            elif name.startswith("_") or not hasattr(api, name):
                self.send_error(404)
                return
            else:
                out = getattr(api, name)(*body)
            data = json.dumps(out, default=str).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass          # page fermée pendant la réponse : sans importance en test

    class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True

    srv = S(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return "http://127.0.0.1:%d" % srv.server_address[1], srv
