"""Chaque appel window.pywebview.api.X du front doit exister dans la classe Api.
Bug historique : review_scan absent de main.py -> 'is not a function' (v1.1.0-v1.3.2)."""
import re, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_front_calls_are_exposed():
    js = open(os.path.join(HERE, "web", "app.js"), encoding="utf-8").read()
    calls = set(re.findall(r'API\.([a-zA-Z_0-9]+)\s*\(', js))
    api = set(re.findall(r'    def ([a-zA-Z_0-9]+)\(',
                         open(os.path.join(HERE, "main.py"), encoding="utf-8").read()))
    missing = calls - api
    assert not missing, "Méthodes appelées par le front mais absentes d'Api: %s" % sorted(missing)

if __name__ == "__main__":
    test_front_calls_are_exposed()
    print("surface API front/back cohérente ✅")
