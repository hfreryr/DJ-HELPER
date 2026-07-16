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
