# Contribuer à DJ Helper

Deux règles passent avant tout le reste :

1. **Jamais de perte de données.** `collection.nml` n'est écrit qu'après une
   sauvegarde, par écriture atomique (`nml_write_atomic`). Aucune suppression
   de fichier audio : on déplace dans un sous-dossier.
2. **Rien n'atteint une release sans contrôles verts** (`checks.yml`).

## Avant de proposer une modification

- [ ] `python -m pytest -q tests` passe ; un bug corrigé = un test ajouté.
- [ ] `bandit -q -r core.py main.py -ll` ne signale rien.
- [ ] Interface modifiée : `python tests/ui/run_ui.py` passe (0 violation axe,
      clavier, zoom 200 %, CSP). Préparer une fois : `cd tests/ui && npm ci`
      puis `python -m playwright install chromium`.
- [ ] Nouveau texte d'interface : traduction ajoutée dans `web/i18n.js`.
- [ ] Nouveau champ : une étiquette (`<label>` ou `aria-label`). Nouveau
      bouton-icône : un nom accessible. Couleur : contraste ≥ 4,5:1.
- [ ] Aucun script inline ni ressource externe (la CSP de `index.html` les bloque).
- [ ] Réseau : https uniquement (`_https_only`), jamais d'URL venue d'une
      réponse distante sans contrôle.
- [ ] Appels externes (ffmpeg, fpcalc) : liste d'arguments, jamais `shell=True` ;
      ffmpeg avec `FFMPEG_SAFE_INPUT`.
- [ ] Release : `APP_VERSION` (web/app.js) **et** `?v=` (index.html) incrémentés.

## Dépendances

| Fichier | Rôle |
|---|---|
| `requirements.txt` | dépendances de l'app (bornes basses) |
| `requirements-build.in` + `build-constraints.txt` → `requirements-build.lock` | ce qui est livré (macOS + Windows), avec sommes |
| `requirements-dev.in` → `requirements-dev.lock` | outils du CI (Linux) |
| `requirements-semgrep.in` → `requirements-semgrep.lock` | Semgrep, isolé |
| `tests/ui/package.json` → `package-lock.json` | axe-core |

Après une modification d'un `.in`, de `requirements.txt` ou des contraintes —
y compris une proposition **Dependabot** — régénérer le lock avec la commande
écrite en 2ᵉ ligne du fichier, puis vérifier : `scripts/check-locks.sh`.
Le CI échoue tant que le lock n'est pas à jour.

Binaires embarqués (ffmpeg, fpcalc) : versions et sommes SHA-256 figées dans
`.github/workflows/build.yml`. Mise à jour = nouvelle URL **et** nouvelle
somme, après lecture des notes de version et CVE.

## Faux positifs des analyseurs

Une alerte Bandit ou Semgrep jugée sans risque s'annote **sur la ligne même**
(`# nosec B310`, `# nosemgrep: <règle>`) avec la **justification en
commentaire sur la ligne précédente**. Jamais d'exclusion globale.

## Veille

`watch.yml` relance tous les contrôles le 3 de chaque mois et ouvre une issue
en cas d'échec. À chaque issue de veille :

- [ ] Faille dans une dépendance : mettre à jour, régénérer le lock, publier.
- [ ] Nouvelle règle Semgrep : corriger, ou annoter avec justification.
- [ ] Une fois par trimestre, vérifier à la main les nouvelles versions de
      ffmpeg et Chromaprint (pas couvertes par Dependabot).

Failles de sécurité : voir [SECURITY.md](SECURITY.md) — jamais en issue publique.
