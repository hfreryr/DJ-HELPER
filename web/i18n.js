// i18n.js — traduction FR -> EN. Le HTML reste la source française ;
// quand LANG === 'en', les nœuds texte connus sont traduits au chargement,
// et un MutationObserver traduit les contenus insérés dynamiquement
// (rendus JS et messages du moteur Python).
let LANG = 'en';   // défaut anglais ; écrasé par la config au démarrage

const I18N_EN = {
  // --- sidebar ---
  "Accueil": "Home",
  "Bibliothèque": "Library",
  "Tags": "Tags",
  "Importer": "Import",
  "Hors playlist": "No playlist",
  "Contrôle": "Checks",
  "Doublons": "Duplicates",
  "Intégrité": "Integrity",
  "Synchro": "Sync",
  "Statut": "Status",
  "Une app pensée par un DJ, pour les DJ": "An app made by a DJ, for DJs",
  // --- mise en route ---
  "Mise en route": "Getting started",
  "Choisis ton": "Pick your",
  "dossier audio": "audio folder",
  "pour commencer. Tu définiras ensuite la": "to get started. You'll then set your",
  "racine de ta clé": "USB stick root",
  "(pour les doublons et la synchro) depuis l'accueil.": "(for duplicates and sync) from the home tab.",
  "Dossier des fichiers audio": "Audio files folder",
  "à définir": "not set",
  "Choisir le dossier": "Choose folder",
  "Prêt à mixer": "Ready to mix",
  "Re-scanner": "Re-scan",
  // --- accueil : tuiles ---
  "Ta bibliothèque": "Your library",
  "Morceaux": "Tracks",
  "dans ton dossier": "in your folder",
  "Taille totale": "Total size",
  "sur le disque": "on disk",
  "Espace libre": "Free space",
  "Formats": "Formats",
  "Santé de la collection": "Collection health",
  "groupes détectés": "groups found",
  "Fichiers corrompus": "Corrupted files",
  "non analysé": "not analyzed",
  "Tags manquants": "Missing tags",
  "sans artiste ou titre": "no artist or title",
  "Faible qualité": "Low quality",
  "Son ≠ tags": "Audio ≠ tags",
  "non vérifié": "not checked",
  "Sauvegardes": "Backups",
  "Configuration": "Settings",
  // --- configuration ---
  "Dossier audio": "Audio folder",
  "Le dossier de tes fichiers musicaux (ex.": "The folder with your music files (e.g.",
  "). Sert au scan, aux tags, à la détection de doublons.": "). Used for scanning, tags and duplicate detection.",
  "Modifier": "Change",
  "Racine de la clé": "USB stick root",
  "Le dossier qui contient": "The folder containing",
  "Définir": "Set",
  "Clé AcoustID": "AcoustID key",
  "Enregistrer": "Save",
  "Obtenir une clé": "Get a key",
  "Clé AcoustID enregistrée": "AcoustID key saved",
  "Outils système": "System tools",
  "Décodeur audio, requis pour l'": "Audio decoder, required for the",
  "analyse approfondie": "deep analysis",
  "d'intégrité.": "integrity mode.",
  ": dans le Terminal,": ": in Terminal,",
  "en PowerShell, ou télécharge sur": "in PowerShell, or download from",
  "et ajoute le dossier": "and add the folder",
  "au PATH.": "to your PATH.",
  "(Debian/Ubuntu) ou l'équivalent de ta distribution.": "(Debian/Ubuntu) or your distribution's equivalent.",
  "Empreinte acoustique (Chromaprint), requis pour la": "Acoustic fingerprint (Chromaprint), required for",
  "détection de doublons par le son": "audio-based duplicate detection",
  "et la": "and",
  "vérification AcoustID": "AcoustID verification",
  "(le binaire": "(the",
  "est inclus).": "binary is included).",
  ": télécharge Chromaprint sur": ": download Chromaprint from",
  ", décompresse, et ajoute le dossier contenant": ", unzip, and add the folder containing",
  "Langue": "Language",
  "Langue de l'interface": "Interface language",
  // --- importer ---
  "Comparer une playlist": "Compare a playlist",
  "Vois ce que tu as déjà sur ta clé et ce qu'il te manque": "See what you already have on your stick and what's missing",
  "Analyser la playlist": "Analyze playlist",
  "Trouvés": "Found",
  "déjà sur ta clé": "already on your stick",
  "À vérifier": "To review",
  "correspondance incertaine": "uncertain match",
  "Manquants": "Missing",
  "à récupérer": "to get",
  "Générer le M3U des trouvés": "Generate M3U of found tracks",
  "Exporter les manquants (.txt)": "Export missing (.txt)",
  "Comparaison à ta bibliothèque…": "Comparing to your library…",
  "Vérifier un dossier d'import": "Check an import folder",
  "Choisir un dossier à vérifier": "Choose a folder to check",
  "Tout cocher": "Check all",
  "Tout décocher": "Uncheck all",
  "Écarter les cochés → _DOUBLONS/": "Move checked → _DOUBLONS/",
  "Identification des fichiers d'import…": "Identifying import files…",
  // --- hors playlist ---
  "Morceaux dans aucune playlist": "Tracks in no playlist",
  "Compare ta bibliothèque aux playlists de": "Compares your library to the playlists in",
  "Repère les morceaux jamais classés dans une playlist": "Finds tracks never added to any playlist",
  "Analyser": "Analyze",
  // --- tags ---
  "Tags & nommage": "Tags & naming",
  "Déduire les tags depuis le nom": "Infer tags from filenames",
  "Scanner": "Scan",
  "Modifier les tags": "Write tags",
  "Annuler": "Cancel",
  "Confirmer": "Confirm",
  "Bien taggés": "Well tagged",
  "À corriger": "To fix",
  "Non identifiables": "Unidentifiable",
  "Lecture des tags…": "Reading tags…",
  "Enrichir les tags via AcoustID": "Enrich tags via AcoustID",
  "Retrouve les tags officiels associés à tes fichiers audio": "Find the official tags for your audio files",
  "Identifier": "Identify",
  "Appliquer la sélection": "Apply selection",
  "Identification en ligne…": "Identifying online…",
  "Renommer les fichiers d'après les tags": "Rename files from tags",
  "Renommer la sélection": "Rename selection",
  "Analyse…": "Analyzing…",
  // --- doublons ---
  "Repérer les doublons": "Find duplicates",
  "Repère les doublons présents dans tes fichiers audio": "Finds duplicate tracks among your audio files",
  "Définir la racine": "Set the root",
  "Par titre": "By title",
  "Par empreinte": "By fingerprint",
  ": compare le": ": compares the",
  "son": "sound",
  "Arrêter": "Stop",
  "Lecture de tes fichiers…": "Reading your files…",
  "Corriger les doublons": "Fix duplicates",
  "(réversible, rien n'est supprimé) et sauvegarde": "(reversible, nothing is deleted) and backs up",
  "Restaurer le dernier backup": "Restore last backup",
  "Vider les backups": "Clear backups",
  // --- intégrité ---
  "Vérifier tes fichiers": "Check your files",
  "Détecter les fichiers corrompus": "Detect corrupted files",
  "Repère les fichiers audio cassés, tronqués ou illisibles": "Finds broken, truncated or unreadable audio files",
  "Rapide": "Quick",
  "Approfondi": "Deep",
  "Fichiers analysés en parallèle": "Files analyzed in parallel",
  "Lancer l'analyse": "Run analysis",
  "Vérifier le contenu audio (AcoustID)": "Verify audio content (AcoustID)",
  "Le son de ton fichier correspond-il à ses tags ?": "Does your file's audio match its tags?",
  "Vérifier le contenu": "Verify content",
  // --- synchro ---
  "Sauvegarde & synchronisation": "Backup & sync",
  "Source à synchroniser": "Source to sync",
  ") pour cloner la clé entière.": ") to clone the whole stick.",
  "Ton dossier audio": "Your audio folder",
  "Réinitialiser": "Reset",
  "Racine de la clé…": "USB stick root…",
  "Synchroniser la clé de secours": "Sync the spare stick",
  "Aucun dossier choisi": "No folder selected",
  "Choisir": "Choose",
  "Synchroniser": "Sync",
  "Comparaison des deux dossiers…": "Comparing the two folders…",
  "Sauvegarde de structure": "Structure backup",
  "s'il est présent. Léger, lisible, non destructif.": "if present. Light, readable, non-destructive.",
  "Choisir un dossier": "Choose a folder",
  "Sauvegarder la structure": "Back up structure",
  "Indexation…": "Indexing…",
  "Coffre-fort de playlists": "Playlist vault",
  "Lit": "Reads",
  "et génère dans": "and generates in",
  "un arbre de playlists": "a playlist tree of",
  "Exporte tes playlists Traktor en fichiers M3U lisibles": "Exports your Traktor playlists as readable M3U files",
  "Générer les M3U": "Generate M3U files",
  "Lecture de collection.nml…": "Reading collection.nml…",
  "Sauvegarde complète": "Full backup",
  "Sauvegarder tout": "Back up everything",
  "Sauvegarde en cours…": "Backing up…",
  "À venir": "Coming soon",
  "Cet onglet n'est pas encore branché": "This tab is not wired up yet",
  // --- dynamiques fréquents (JS + moteur) ---
  "Analyse en cours…": "Analyzing…",
  "Identification…": "Identifying…",
  "Erreur": "Error",
  "Dossier audio introuvable": "Audio folder not found",
  "Clé AcoustID manquante (onglet Intégrité).": "AcoustID key missing (Integrity tab).",
  "fpcalc introuvable — installe-le depuis la carte Configuration (accueil).": "fpcalc not found — install it from the Settings card (home).",
  "Racine de la clé non définie ou introuvable.": "USB stick root not set or not found.",
  "collection.nml introuvable sur la clé.": "collection.nml not found on the stick.",
  "Aucune playlist lisible dans collection.nml.": "No readable playlist in collection.nml.",
  "Lance d'abord une comparaison.": "Run a comparison first.",
  "Aucun manquant (ou comparaison non lancée).": "Nothing missing (or comparison not run).",
  "Dossier de destination introuvable.": "Destination folder not found.",
  "Chemin vide": "Empty path",
  "Fichier introuvable": "File not found",
};


// --- lot 2 : textes dynamiques exacts (rendus JS / moteur) ---
Object.assign(I18N_EN, {
  "Non définie — requise pour doublons, synchro et sauvegarde": "Not set — required for duplicates, sync and backup",
  "Aucun doublon": "No duplicates",
  "Analyse interrompue — les empreintes déjà calculées sont conservées.": "Analysis stopped — fingerprints already computed are kept.",
  "Comparaison des empreintes…": "Comparing fingerprints…",
  "Aucun doublon par le son": "No audio duplicates",
  "Aucun doublon à corriger.": "No duplicates to fix.",
  "Aucun doublon détecté dans ce dossier. 👌": "No duplicates found in this folder. 👌",
  "À garder": "Keep",
  "Garder celle-ci": "Keep this one",
  "Analyse approfondie…": "Deep analysis…",
  "Analyse interrompue — les fichiers déjà vérifiés sont conservés en cache.": "Analysis stopped — files already checked are kept in cache.",
  "Aucun problème détecté. Ta bibliothèque est saine. 👌": "No issues found. Your library is healthy. 👌",
  "Tous tes fichiers sont déjà bien taggés. Rien à faire. 👌": "All your files are already well tagged. Nothing to do. 👌",
  "Aucun fichier audio trouvé.": "No audio files found.",
  "Manquants — à récupérer": "Missing — to get",
  "À vérifier — correspondance incertaine": "To review — uncertain match",
  "Tous les morceaux de cette playlist sont déjà sur ta clé. 👌": "Every track in this playlist is already on your stick. 👌",
  "À faire": "To do",
  "À jour": "Up to date",
  "À mettre à jour": "To update",
  "à refaire": "to redo",
  "incohérences": "inconsistencies",
  "fpcalc non détecté — voir Configuration sur l’accueil": "fpcalc not detected — see Settings on the home tab",
  "Clé enregistrée": "Key saved",
  "Non identifié": "Not identified",
  "Titre protégé (remix/edit) — non modifié": "Protected title (remix/edit) — left unchanged",
  "Écriture…": "Writing…",
  "Génération…": "Generating…",
  "Ta clé de secours est déjà à jour. Rien à synchroniser. 👌": "Your spare stick is already up to date. Nothing to sync. 👌",
  "Les suppressions sont définitives.": "Deletions are permanent.",
  "Tout est prêt": "All set",
  "Vérifications à faire": "Checks needed",
  "Problème détecté": "Problem detected",
  "État du système": "System status",
  "Choisis d'abord ton dossier sur l'accueil.": "Choose your folder on the home tab first.",
  "Échec": "Failed",
  "Cette opération écrit dans tes fichiers.": "This operation writes to your files.",
  "Chemin du fichier manquant.": "Missing file path.",
  "Impossible de localiser le fichier.": "Could not locate the file.",
  "Impossible de localiser le fichier :": "Could not locate the file:",
  "Coche au moins un fichier à écarter.": "Check at least one file to move aside.",
  "Cliquer pour localiser le fichier": "Click to locate the file",
  "Cliquer pour garder cette version à la place": "Click to keep this version instead",
  "Aucun : tous tes morceaux sont dans au moins une playlist. 👌": "None: every track is in at least one playlist. 👌",
  "supprimé": "deleted",
  "Supprimer définitivement les backups de doublons ? Les copies écartées seront perdues (la version gardée reste). Irréversible.": "Permanently delete the duplicate backups? The set-aside copies will be lost (the kept version stays). Irreversible.",
});

// Fragments : remplacés en sous-chaîne dans les textes assemblés (nombres, chemins).
// Appliqués du plus long au plus court pour éviter les collisions.
const I18N_FRAGMENTS = [
  ["Non identifiables — à taguer ou renommer à la main", "Unidentifiable — tag or rename manually"],
  ["Non identifiés — à taguer à la main", "Not identified — tag manually"],
  ["(clique un morceau pour le localiser)", "(click a track to locate it)"],
  ["(clique un fichier pour le localiser)", "(click a file to locate it)"],
  [" fichier(s) déplacé(s) dans _DOUBLONS/ — rien n'est supprimé", " file(s) moved to _DOUBLONS/ — nothing deleted"],
  [" vers un backup réversible. collection.nml est sauvegardé avant.", " to a reversible backup. collection.nml is backed up first."],
  [". Irréversible — une sauvegarde du .nml est faite avant.", ". Irreversible — the .nml is backed up first."],
  [" sauvegarde(s) de doublons sur la clé · ", " duplicate backup(s) on the stick · "],
  [" supprimé(s) sur la clé de secours. ", " deleted on the spare stick. "],
  ["À copier vers la clé de secours (", "To copy to the spare stick ("],
  ["À supprimer de la clé de secours (", "To delete from the spare stick ("],
  [" morceau(x) dans aucune playlist ▸", " track(s) in no playlist ▸"],
  ["⚠ AcoustID a refusé la requête : ", "⚠ AcoustID rejected the request: "],
  [" référence(s) repointée(s) · ", " reference(s) repointed · "],
  ["Écrire les tags officiels de ", "Write official tags for "],
  ["Synchronisation terminée — ", "Sync complete — "],
  [" pochette(s) ajoutée(s)", " cover(s) added"],
  [" backup(s) supprimé(s) · ", " backup(s) deleted · "],
  [" playlist(s) exportée(s)", " playlist(s) exported"],
  [" corrections proposées", " corrections proposed"],
  [" correction proposée", " correction proposed"],
  ["Modifier les tags de ", "Write tags for "],
  [" fichier(s) restauré(s)", " file(s) restored"],
  [" fichier(s) modifié(s)", " file(s) modified"],
  [" fichier(s) tagués · ", " file(s) tagged · "],
  [" déjà bien taggés", " already well tagged"],
  [" non identifiés ▸", " not identified ▸"],
  [" · 0 non identifié", " · 0 not identified"],
  ["fichiers à vérifier", "files to check"],
  [" fichiers analysés", " files analyzed"],
  [" morceaux analysés", " tracks analyzed"],
  [" déjà au format", " already formatted"],
  ["Dossier choisi : ", "Chosen folder: "],
  ["Snapshot créé · ", "Snapshot created · "],
  ["Miroir à jour · ", "Mirror updated · "],
  ["Clé entière : ", "Whole stick: "],
  [" à renommer · ", " to rename · "],
  [" à supprimer · ", " to delete · "],
  [" à copier · ", " to copy · "],
  [" copié(s), ", " copied, "],
  [" copié(s) · ", " copied · "],
  [" supprimé(s)", " deleted"],
  [" archivé(s)", " archived"],
  [" renommé(s)", " renamed"],
  ["Identifié : ", "Identified: "],
  ["M3U créé (", "M3U created ("],
  ["Liste créée (", "List created ("],
  [" morceaux) : ", " tracks): "],
  [" manquants) : ", " missing): "],
  ["Terminé : ", "Done: "],
  [" fichier(s) · ", " file(s) · "],
  [" fichier(s)", " file(s)"],
  [" libéré(s)", " freed"],
  [" lié(s)", " linked"],
  [" à vérifier", " to review"],
  [" erreurs", " errors"],
  ["Taggé ", "Tagged "],
].sort((a, b) => b[0].length - a[0].length);

// Règles regex pour les motifs avec nombres imbriqués
const I18N_REGEX = [
  [/^sur (\d+) \((\d+) playlists\)$/, "of $1 ($2 playlists)"],
  [/^(\d+) fichier\(s\) peuvent être corrigés automatiquement à partir de leur nom \(aperçu des valeurs proposées\) :$/,
   "$1 file(s) can be fixed automatically from their names (preview of proposed values):"],
];


// --- lot 3 : info-bulles, sous-titres de cartes, placeholders ---
Object.assign(I18N_EN, {
  "Les deux dossiers dont DJ Helper a besoin. Modifiables à tout moment.": "The two folders DJ Helper needs. Changeable at any time.",
  "— la racine de ta clé. Requis pour corriger les doublons, synchroniser et sauvegarder.": "— your USB stick root. Required to fix duplicates, sync and back up.",
  "Clé gratuite pour identifier tes fichiers en ligne (vérification son↔tags, enrichissement des tags). Obtiens-la sur": "Free key to identify your files online (audio↔tags verification, tag enrichment). Get it at",
  "→ « Register a new application », puis colle la clé ici. Sans elle, seule la détection de doublons par empreinte locale fonctionne.": "→ “Register a new application”, then paste the key here. Without it, only local fingerprint duplicate detection works.",
  "(si « brew » est inconnu, installe Homebrew depuis brew.sh).": "(if “brew” is unknown, install Homebrew from brew.sh).",
  "Compare une playlist externe à ta bibliothèque, ou contrôle un dossier de téléchargements": "Compare an external playlist to your library, or check a downloads folder",
  "Une playlist Spotify, YouTube, Apple Music… ? Convertis-la en texte via TuneMyMusic, puis colle les titres ci-dessous — un par ligne, au format « Artiste - Titre ».": "A Spotify, YouTube or Apple Music playlist? Convert it to text with TuneMyMusic, then paste the titles below — one per line, as “Artist - Title”.",
  "Identifie chaque fichier du dossier par son empreinte acoustique (et non par ses tags, souvent faux sur des téléchargements), puis le compare à ta bibliothèque. Les doublons peuvent être écartés dans un sous-dossier": "Identifies each file in the folder by its acoustic fingerprint (not its tags, often wrong on downloads), then compares it to your library. Duplicates can be moved aside into a subfolder",
  "— rien n'est supprimé. Nécessite la clé AcoustID (onglet Intégrité) et": "— nothing is deleted. Requires the AcoustID key (Integrity tab) and",
  "Avant d'intégrer de nouveaux fichiers à ta banque, repère ce que tu as déjà pour éviter les doublons": "Before adding new files to your bank, spot what you already have to avoid duplicates",
  "⚠ Les « non identifiés » (inconnus d'AcoustID) ne sont pas pré-cochés : l'un d'eux peut être un doublon que l'empreinte n'a pas reconnu. Vérifie-les à la main avant de verser dans ta banque.": "⚠ “Not identified” files (unknown to AcoustID) are not pre-checked: one of them may be a duplicate the fingerprint missed. Check them manually before adding them to your bank.",
  "Repère les morceaux de ta bibliothèque qui ne sont dans aucune playlist": "Finds the tracks in your library that are in no playlist",
  "(Traktor) et liste les morceaux qui ne sont dans aucune playlist. Nécessite la clé branchée. Comparaison par nom de fichier.": "(Traktor) and lists the tracks that are in no playlist. Requires the stick to be plugged in. Comparison by file name.",
  "Corrige les métadonnées et les noms de fichiers de ta bibliothèque": "Fix your library's metadata and file names",
  "Compare le nom du fichier (souvent « Artiste - Titre ») aux tags internes et corrige ces derniers s'ils sont vides ou erronés. Aperçu avant d'appliquer.": "Compares the file name (usually “Artist - Title”) to the embedded tags and fixes them when empty or wrong. Preview before applying.",
  "Lit le nom de chaque fichier et corrige les tags artiste/titre en conséquence": "Reads each file's name and fixes the artist/title tags accordingly",
  "Choisis d'abord ton dossier sur l'accueil, puis lance le scan.": "Choose your folder on the home tab first, then run the scan.",
  "Identifie chaque fichier par son empreinte acoustique et propose les tags officiels (artiste, titre, album) + la pochette manquante via MusicBrainz. Réutilise la clé AcoustID de l'onglet Intégrité. Les titres marqués remix/edit ne sont jamais remplacés. Analyse en ligne (~1 fichier/s, mise en cache).": "Identifies each file by its acoustic fingerprint and proposes the official tags (artist, title, album) plus missing cover art via MusicBrainz. Reuses the AcoustID key from the Integrity tab. Titles marked remix/edit are never replaced. Online analysis (~1 file/s, cached).",
  "Ta collection Traktor est mise à jour en conséquence — cues & beat grids préservés (sauvegarde de": "Your Traktor collection is updated accordingly — cues & beat grids preserved (backup of",
  "faite avant). Nécessite la racine de la clé pour le suivi Traktor.": "made first). Requires the stick root for Traktor tracking.",
  "Grâce à leurs tags, renomme tes fichiers audio au format « Artiste - Titre »": "Uses their tags to rename your audio files as “Artist - Title”",
  "Deux fichiers identiques gaspillent de la place et encombrent tes playlists. Cet onglet les repère et te laisse garder la meilleure version, puis corriger sans rien supprimer.": "Two identical files waste space and clutter your playlists. This tab finds them, lets you keep the best version, then fixes everything without deleting anything.",
  "⚠️ Racine de la clé non définie — indispensable pour repointer tes playlists Traktor lors de la correction.": "⚠️ USB stick root not set — required to repoint your Traktor playlists during the fix.",
  ": compare artiste + titre des tags. Instantané, sans outil externe. Rate les doublons mal taggés ou orthographiés différemment.": ": compares tag artist + title. Instant, no external tool. Misses badly tagged or differently spelled duplicates.",
  "réel. Attrape ce que « par titre » rate, et ne confond jamais un remix avec l'original. Plus lente (décode tout, puis met en cache). Nécessite": "itself. Catches what “by title” misses, and never confuses a remix with the original. Slower (decodes everything, then caches). Requires",
  "Repointe tes playlists Traktor vers la version gardée, déplace les copies vers": "Repoints your Traktor playlists to the kept version, moves the copies to",
  ". Ensuite, dans Traktor : « Remove Missing Tracks ». Nécessite la racine de ta clé (onglet Synchro).": ". Then, in Traktor: “Remove Missing Tracks”. Requires your stick root (Sync tab).",
  "Contrôle l'intégrité technique de tes fichiers et la cohérence entre le son et les tags": "Checks your files' technical integrity and the consistency between audio and tags",
  "Repère les fichiers dont l'audio est cassé, tronqué ou illisible — ceux qui risquent de planter ou de couper en plein set.": "Finds files whose audio is broken, truncated or unreadable — the ones that may crash or cut out mid-set.",
  ": vérifie l'en-tête et la structure du fichier. Instantané, sans décodage.": ": checks the file header and structure. Instant, no decoding.",
  ": décode entièrement l'audio via ffmpeg pour repérer les fichiers qui s'ouvrent mais sont corrompus ou tronqués en profondeur. Bien plus lent — résultats mis en cache ensuite.": ": fully decodes the audio with ffmpeg to find files that open but are deeply corrupted or truncated. Much slower — results are cached afterwards.",
  "Nombre de fichiers décodés simultanément. Plus élevé = plus rapide, mais plus gourmand en CPU. 4 est un bon compromis ; monte à 8 sur une machine puissante.": "Number of files decoded at once. Higher = faster but more CPU-hungry. 4 is a good compromise; go up to 8 on a powerful machine.",
  "Choisis d'abord ton dossier sur l'accueil, puis lance l'analyse.": "Choose your folder on the home tab first, then run the analysis.",
  "Analyse des fichiers… (peut prendre un moment sur une grosse bibliothèque)": "Analyzing files… (can take a while on a large library)",
  "Calcule l'empreinte acoustique de chaque fichier (Chromaprint /": "Computes each file's acoustic fingerprint (Chromaprint /",
  ") et l'identifie en ligne via AcoustID, puis compare au tag artiste. Nécessite une clé AcoustID gratuite et": ") and identifies it online via AcoustID, then compares it to the artist tag. Requires a free AcoustID key and",
  "installé. Analyse en ligne : comptez ~1 fichier/seconde (mis en cache ensuite).": "installed. Online analysis: expect ~1 file/second (cached afterwards).",
  "⚠ Clé AcoustID non configurée — définis-la sur l'accueil (Configuration) pour activer la vérification.": "⚠ AcoustID key not set — define it on the home tab (Settings) to enable verification.",
  "Protège ta bibliothèque : clone vers une clé de secours, sauvegardes datées et export des playlists": "Protect your library: clone to a spare stick, dated backups and playlist export",
  "Par défaut, seul ton dossier audio est cloné. Définis la racine de la clé (le dossier qui contient": "By default, only your audio folder is cloned. Set the stick root (the folder containing",
  "Génère un manifeste daté (inventaire complet : artiste, titre, durée, arborescence) et copie": "Generates a dated manifest (full inventory: artist, title, duration, tree) and copies",
  "Stocke ta collection en sécurité dans un dossier de ton choix": "Stores your collection safely in a folder of your choice",
  "(chemins absolus, requis par Traktor à l'import), avec copie horodatée du": "(absolute paths, required by Traktor on import), with a timestamped copy of the",
  ". Nécessite la racine de la clé. Les playlists supprimées dans Traktor sont nettoyées au passage suivant.": ". Requires the stick root. Playlists deleted in Traktor are cleaned up on the next pass.",
  "Sur disque Mac (APFS/HFS+) : snapshots datés façon Time Machine — les fichiers inchangés sont liés, pas recopiés. Sur clé exFAT/FAT32 : miroir « courant » + archive datée des versions remplacées. La 1re passe copie tout ; les suivantes ne traitent que les nouveautés. La destination doit être différente de la source.": "On a Mac disk (APFS/HFS+): dated Time Machine-style snapshots — unchanged files are linked, not recopied. On an exFAT/FAT32 stick: a “current” mirror plus a dated archive of replaced versions. The first pass copies everything; later ones only handle what's new. The destination must differ from the source.",
  "Copie versionnée de tous tes fichiers dans un dossier de ton choix": "Versioned copy of all your files into a folder of your choice",
  "On portera ta logique existante ici, ensemble, écran par écran.": "We'll port your existing logic here, together, screen by screen.",
  "Clé d'application AcoustID": "AcoustID application key",
  "Filtrer les résultats…": "Filter results…",
});


// --- lot 3b : messages du moteur (core.py) ---
Object.assign(I18N_EN, {
  "Aucun backup trouvé sur la clé.": "No backup found on the stick.",
  "Aucun backup à supprimer.": "No backup to delete.",
  "Aucun dossier d'import actif.": "No active import folder.",
  "Aucun fichier audio dans ce dossier.": "No audio files in this folder.",
  "Aucune ligne sélectionnée": "No line selected",
  "Bibliothèque indexée": "Library indexed",
  "Chemin renseigné mais introuvable (clé débranchée ?)": "Path set but not found (stick unplugged?)",
  "Choisis un dossier de sauvegarde.": "Choose a backup folder.",
  "Clé de secours introuvable": "Spare stick not found",
  "Configurée": "Configured",
  "Dossier d'import introuvable": "Import folder not found",
  "Dossier de musique (base) introuvable. Définis-le sur l'accueil.": "Music folder (base) not found. Set it on the home tab.",
  "Dossier introuvable": "Folder not found",
  "La clé de secours doit être différente du dossier principal": "The spare stick must differ from the main folder",
  "La destination ne peut pas être la source.": "The destination cannot be the source.",
  "Lecture de collection.nml impossible.": "Could not read collection.nml.",
  "Non configurée — enrichissement et vérification du contenu indisponibles": "Not set — enrichment and content verification unavailable",
  "Non installé — analyse approfondie indisponible": "Not installed — deep analysis unavailable",
  "Non installé — doublons par empreinte et AcoustID indisponibles": "Not installed — fingerprint duplicates and AcoustID unavailable",
  "Pas encore scannée": "Not scanned yet",
  "Racine de la clé non configurée.": "USB stick root not set.",
  "Source introuvable": "Source not found",
  "Source introuvable (définis le dossier ou la clé).": "Source not found (set the folder or the stick).",
  "Source introuvable. Définis la racine de la clé.": "Source not found. Set the stick root.",
  "Version introuvable": "Version not found",
});
// Fragments moteur (messages avec chemins/valeurs interpolés)
I18N_FRAGMENTS.push(
  ["Clé AcoustID manquante. Renseigne-la sur l'accueil, ", "AcoustID key missing. Set it on the home tab, "],
  ["Configure la racine de ta clé (onglet Synchro) : ", "Set your stick root (Sync tab): "],
  ["Fichiers renommés mais écriture de collection.nml ", "Files renamed but writing collection.nml "],
  ["Impossible de créer _DOUBLONS/ : ", "Could not create _DOUBLONS/: "],
  ["Introuvable : ", "Not found: "],
  ["Lecture des playlists impossible : ", "Could not read playlists: "],
  ["Sauvegarde de collection.nml impossible : ", "Could not back up collection.nml: "],
  ["Écriture collection.nml impossible : ", "Could not write collection.nml: "],
  ["collection.nml introuvable sur la clé : ", "collection.nml not found on the stick: "],
  ["collection.nml introuvable. Définis la racine de la clé ", "collection.nml not found. Set the stick root "],
  ["ffmpeg introuvable — installe-le depuis la carte Configuration ", "ffmpeg not found — install it from the Settings card "],
  ["fpcalc introuvable — installe Chromaprint depuis la ", "fpcalc not found — install Chromaprint from the "],
  ["format non géré : ", "unsupported format: "]
);
I18N_FRAGMENTS.sort((a, b) => b[0].length - a[0].length);

function t(s){
  return (LANG === 'en' && Object.prototype.hasOwnProperty.call(I18N_EN, s)) ? I18N_EN[s] : s;
}

function _translateTextNode(node){
  const raw = node.nodeValue;
  if (!raw) return;
  const s = raw.trim();
  if (!s) return;
  if (Object.prototype.hasOwnProperty.call(I18N_EN, s)){
    node.nodeValue = raw.replace(s, I18N_EN[s]);
    return;
  }
  let out = raw, changed = false;
  for (const [fr, en] of I18N_REGEX){
    const m = out.trim().match(fr);
    if (m){ out = out.replace(out.trim(), out.trim().replace(fr, en)); changed = true; }
  }
  for (const [fr, en] of I18N_FRAGMENTS){
    if (out.includes(fr)){ out = out.split(fr).join(en); changed = true; }
  }
  if (changed) node.nodeValue = out;
}

function translateDom(root){
  if (LANG !== 'en') return;
  const target = root || document.body;
  const walker = document.createTreeWalker(target, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach(_translateTextNode);
  (target.querySelectorAll ? target.querySelectorAll('[title],[placeholder]') : []).forEach(el => {
    ['title', 'placeholder'].forEach(a => {
      const v = el.getAttribute && el.getAttribute(a);
      if (v && Object.prototype.hasOwnProperty.call(I18N_EN, v.trim())){
        el.setAttribute(a, I18N_EN[v.trim()]);
      }
    });
  });
}

let _i18nObserver = null;
function startI18nObserver(){
  if (LANG !== 'en' || _i18nObserver) return;
  _i18nObserver = new MutationObserver(muts => {
    muts.forEach(m => {
      if (m.type === 'characterData'){ _translateTextNode(m.target); return; }
      m.addedNodes.forEach(n => {
        if (n.nodeType === 3) _translateTextNode(n);
        else if (n.nodeType === 1) translateDom(n);
      });
    });
  });
  _i18nObserver.observe(document.body, {childList: true, subtree: true, characterData: true});
}
