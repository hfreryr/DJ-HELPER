# Sécurité de DJ Helper

## Signaler une faille

Merci de **ne pas ouvrir d'issue publique**. Utilise le formulaire privé de
GitHub : onglet **Security → Report a vulnerability** de ce dépôt
(« Private vulnerability reporting »).

Indique la version (visible en bas de la barre latérale), le système
(macOS / Windows) et les étapes pour reproduire. Réponse visée sous 7 jours ;
correctif publié dans une nouvelle version, avec mention dans les notes de
release une fois les utilisateurs protégés.

## Versions prises en charge

Seule la **dernière version** reçoit des correctifs. L'application vérifie au
démarrage (une fois par jour, désactivable dans l'accueil) si une version plus
récente existe ; elle ne télécharge et n'installe rien d'elle-même.

## Vérifier un téléchargement

Chaque release publie :

- `SHA256SUMS` — `sha256sum -c SHA256SUMS` (macOS : `shasum -a 256 -c SHA256SUMS`) ;
- une **attestation de provenance** Sigstore, qui prouve que le zip a été
  construit par le workflow de ce dépôt :

  ```
  gh attestation verify DJHelper-macos.zip -R hfreryr/dj-helper
  ```

## Ce que fait l'application (surface d'attaque)

- **Fichiers** : lit ta bibliothèque et ta clé ; n'écrit `collection.nml`
  qu'après une sauvegarde, par écriture atomique, et refuse tout NML contenant
  un DOCTYPE ou des entités XML.
- **Réseau** : https uniquement — AcoustID / MusicBrainz / Discogs / Bandcamp
  (identification et tags), API GitHub (version). Aucune télémétrie.
- **Serveur local** : l'écoute audio passe par un serveur lié à `127.0.0.1`,
  protégé par un jeton aléatoire, limité aux fichiers de ta bibliothèque.
- **Outils externes** : `ffmpeg` et `fpcalc` sont fournis (empreintes SHA-256
  vérifiées au build) et appelés sans shell ; ffmpeg n'accepte que les
  protocoles `file` et `pipe`.
- **Interface** : politique de sécurité du contenu (CSP) interdisant scripts
  et ressources externes.
- **Données privées** : `~/.djhelper` en 700, fichiers en 600.

## Chaîne de build

Actions GitHub épinglées par empreinte de commit ; dépendances Python figées
avec leurs sommes (`requirements-build.lock`, installé avec
`--require-hashes`) ; Python et binaires externes en versions exactes ;
mises à jour proposées par Dependabot.
