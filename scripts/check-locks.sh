#!/usr/bin/env bash
# Vérifie que chaque *.lock correspond encore à son .in : on rejoue la commande
# notée en tête du lock (uv garde les versions déjà figées si elles conviennent)
# et on compare. Échoue si un .in, une contrainte ou une proposition Dependabot
# a changé sans régénération du lock.
#   Corriger : relancer la commande indiquée en tête du lock concerné.
set -euo pipefail
cd "$(dirname "$0")/.."
status=0
tmp=$(mktemp -d)
for lock in requirements-build.lock requirements-dev.lock requirements-semgrep.lock; do
  cmd=$(sed -n '2p' "$lock" | sed 's/^#\s*//')
  case "$cmd" in "uv pip compile "*) ;; *) echo "$lock : en-tête uv introuvable"; status=1; continue;; esac
  cp "$lock" "$tmp/$lock"
  # même commande, sortie vers la copie (préférences = versions actuelles)
  eval "${cmd/-o $lock/-o $tmp/$lock} -q"
  if ! diff -q <(grep -v '^#' "$lock") <(grep -v '^#' "$tmp/$lock") >/dev/null; then
    echo "::error file=$lock::$lock n'est plus à jour. Relancer : $cmd"
    diff <(grep -v '^#' "$lock") <(grep -v '^#' "$tmp/$lock") | head -20 || true
    status=1
  else
    echo "$lock : à jour"
  fi
done
exit $status
