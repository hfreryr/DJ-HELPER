// app.js — relie l'UI à la logique Python via window.pywebview.api

let API = null;
let scannedOnce = false;
let dupShown = false;
let scanning = false;
let lastFix = 0;
let integMode = 'quick';
let spareFolder = '';
let lastPlan = null;

function $(id){ return document.getElementById(id); }

// ---------- navigation ----------
const items = document.querySelectorAll('.nav-item');
const views = {
  home: $('view-home'),
  import: $('view-import'),
  orphans: $('view-orphans'),
  tags: $('view-tags'),
  dup:  $('view-dup'),
  integ: $('view-integ'),
  sync: $('view-sync'),
  soon: $('view-soon'),
};
function showView(v, name){
  Object.values(views).forEach(s => s.classList.remove('show'));
  (views[v] || views.home).classList.add('show');
  if (v === 'soon' && name) $('soon-title').textContent = name;
  if (v === 'sync') renderSyncSource();
  if (v === 'home') refreshHome();
  if (v === 'dup' && scannedOnce && !dupShown) scanDuplicates();
  if (v === 'integ') updateIntegAckeyHint();
  document.querySelector('.main').scrollTop = 0;
}
items.forEach(it => it.addEventListener('click', () => {
  items.forEach(i => i.classList.remove('active'));
  it.classList.add('active');
  showView(it.dataset.view, it.dataset.name);
}));
function navTo(v){
  items.forEach(i => i.classList.toggle('active', i.dataset.view === v));
  showView(v);
}
document.querySelectorAll('[data-go]').forEach(el => el.addEventListener('click', () => {
  navTo(el.dataset.go);
}));

// ---------- accueil ----------
// ---------- progression ----------
function showSpinner(loadingId, text){
  const el = $(loadingId);
  el.innerHTML = '<span class="spinner"></span>' + (text || '');
  el.style.display = 'block';
}
function showProgress(loadingId, label){
  const el = $(loadingId);
  el.innerHTML = '<div class="pbar"><div class="pfill"></div></div><div class="plabel"></div>';
  el.style.display = 'block';
  setProgress(loadingId, 0, 0, label);
}
function setProgress(loadingId, done, total, label){
  const el = $(loadingId); if (!el) return;
  const pct = total ? Math.round(done * 100 / total) : 0;
  const fill = el.querySelector('.pfill');
  const lab = el.querySelector('.plabel');
  if (fill) fill.style.width = pct + '%';
  if (lab) lab.textContent = (label ? label + ' ' : '') + pct + ' %';
}
// Boucle générique : begin() -> {ok,total} ; step(n) -> {done,total,finished,result}
async function runChunked(loadingId, label, beginFn, stepFn, chunk){
  const begin = await beginFn();
  if (!begin || begin.ok === false) return begin;       // erreur (ex. ffmpeg, dossier)
  showProgress(loadingId, label);
  let last = null;
  do {
    last = await stepFn(chunk);
    setProgress(loadingId, last.done, last.total, label);
  } while (!last.finished);
  $(loadingId).style.display = 'none';
  return last.result ? last.result : last;
}

async function refreshHome(){
  if (!API) return;
  const st = await API.get_state();
  if (st.configured){
    $('home-setup').style.display = 'none';
    $('home-dash').style.display = 'block';
    $('dash-sub').textContent = folderName(st.music_folder)
      + (st.free ? ' · ' + st.free + ' libres' : '');
    $('tile-free').textContent = st.free || '—';
    $('tile-free-meta').textContent = st.total ? ('sur ' + st.total) : '';
    $('tile-count').textContent = st.count ? format(st.count) : '…';
    $('cfg-music').textContent = st.music_folder || '—';
    const cu = $('cfg-usb');
    if (st.usb_configured){
      cu.textContent = st.usb_root;
      cu.classList.remove('missing');
      $('cfg-usb-btn').textContent = 'Modifier';
    } else {
      cu.textContent = 'Non définie — requise pour doublons, synchro et sauvegarde';
      cu.classList.add('missing');
      $('cfg-usb-btn').textContent = 'Définir';
    }
    const setTool = (id, path) => {
      const el = $(id);
      if (!el) return;
      if (path){ el.innerHTML = '<span class="ac-ok">✓</span> ' + esc(path); el.classList.remove('missing'); }
      else { el.innerHTML = '⚠️ non détecté — voir l\'info-bulle pour l\'installer'; el.classList.add('missing'); }
    };
    setTool('cfg-ffmpeg', st.ffmpeg);
    setTool('cfg-fpcalc', st.fpcalc);
    loadAcoustidKey();
    updateHomeTiles();
    updateBackups();
    scanLibrary();   // re-scan disque à chaque affichage de l'accueil (prend les ajouts/suppressions)
  } else {
    $('home-setup').style.display = 'block';
    $('home-dash').style.display = 'none';
  }
  refreshStatus();
}

async function pickFolder(){
  if (!API) return;
  const res = await API.pick_music_folder();
  if (res && res.ok){
    $('chk-music-mk').textContent = '✓';
    $('chk-music-mk').className = 'mk ok';
    $('chk-music-path').textContent = res.path;
    scannedOnce = false; dupShown = false;
    await refreshHome();
  }
}

async function scanLibrary(){
  if (!API) return;
  if (scanning) return;   // évite les scans concurrents (rescan auto + action)
  scanning = true;
  try {
    const begin = await API.scan_begin();
    if (!begin || !begin.ok) return;
    scannedOnce = true;
    const total = begin.total || 0;
    let done = 0;
    while (done < total){
      const r = await API.scan_step(400);
      done = r.done;
      $('tile-count').textContent = Math.round(done * 100 / total) + ' %';
      if (r.finished) break;
    }
    $('tile-count').textContent = format(total);
    const d = await API.find_duplicates();
    if (d && d.ok){
      $('tile-dup').textContent = format(d.n_groups);
      $('tile-dup').style.color = d.n_groups ? 'var(--warning)' : 'var(--success)';
    }
    updateHomeTiles();
  } finally {
    scanning = false;
  }
}

// ---------- doublons ----------
let dupGroups = [];

function filterDuplicates(){
  const q = ($('dup-filter').value || '').toLowerCase().trim();
  if (!q){ renderDuplicates(dupGroups); return; }
  const f = dupGroups.filter(g =>
    (g.artist || '').toLowerCase().includes(q) ||
    (g.title || '').toLowerCase().includes(q) ||
    g.versions.some(v => (v.name || '').toLowerCase().includes(q)));
  renderDuplicates(f);
}

async function scanDuplicates(){
  if (!API) return;
  $('dup-empty').style.display = 'none';
  $('dup-list').innerHTML = '';
  $('dup-loading').style.display = 'block';
  $('btn-scan-dup').disabled = true;
  const res = await API.find_duplicates();
  $('dup-loading').style.display = 'none';
  $('btn-scan-dup').disabled = false;
  if (!res || !res.ok){
    $('dup-empty').textContent = (res && res.error)
      ? res.error : "Choisis d'abord ton dossier sur l'accueil.";
    $('dup-empty').style.display = 'block';
    $('dup-count').textContent = '—';
    return;
  }
  renderDuplicates(res.groups);
  dupGroups = res.groups;
  $('dup-filter').value = '';
  $('dup-filter').style.display = res.groups.length ? '' : 'none';
  dupShown = true;
  const filesConcerned = res.groups.reduce((a, g) => a + g.versions.length, 0);
  $('dup-count').textContent = res.n_groups
    ? (res.n_groups + ' groupe' + (res.n_groups > 1 ? 's' : '') + ' · ' + filesConcerned + ' fichiers')
    : 'Aucun doublon';
  $('dup-actions').style.display = 'block';
  $('btn-dup-fix').disabled = !res.groups.length;
  $('dup-confirm').style.display = 'none';
  $('dup-fix-count').textContent = '';
  loadDupBackupInfo();
}

let audioStop = false;

async function scanDuplicatesAudio(){
  if (!API) return;
  $('dup-empty').style.display = 'none';
  $('dup-list').innerHTML = '';
  $('btn-scan-dup').disabled = true;
  audioStop = false;
  const begin = await API.audiodup_begin();
  if (!begin || !begin.ok){
    $('dup-empty').textContent = (begin && begin.error) ? begin.error : 'Erreur';
    $('dup-empty').style.display = 'block';
    $('dup-count').textContent = '—';
    $('btn-scan-dup').disabled = false;
    return;
  }
  $('btn-dup-stop').style.display = '';
  showProgress('dup-loading', 'Empreintes audio…');
  let last = null;
  do {
    if (audioStop){
      await API.audiodup_cancel();
      $('dup-loading').style.display = 'none';
      $('btn-dup-stop').style.display = 'none';
      $('btn-scan-dup').disabled = false;
      $('dup-count').textContent = 'Analyse interrompue — les empreintes déjà calculées sont conservées.';
      return;
    }
    last = await API.audiodup_step(8);
    setProgress('dup-loading', last.done, last.total, 'Empreintes audio…');
  } while (!last.finished);
  // Phase 2 : appariement (séparée pour ne pas figer la barre à 100%)
  $('btn-dup-stop').style.display = 'none';
  showSpinner('dup-loading', 'Comparaison des empreintes…');
  const res = await API.audiodup_finalize();
  $('dup-loading').style.display = 'none';
  $('btn-scan-dup').disabled = false;
  if (!res || !res.ok){
    $('dup-empty').textContent = (res && res.error) ? res.error : 'Erreur';
    $('dup-empty').style.display = 'block';
    return;
  }
  renderDuplicates(res.groups);
  dupGroups = res.groups;
  $('dup-filter').value = '';
  $('dup-filter').style.display = res.groups.length ? '' : 'none';
  dupShown = true;
  const files = res.groups.reduce((a, g) => a + g.versions.length, 0);
  let note = res.n_groups
    ? (res.n_groups + ' groupe' + (res.n_groups > 1 ? 's' : '') + ' · ' + files + ' fichiers (par le son)')
    : 'Aucun doublon par le son';
  if (res.n_failed) note += ' · ' + res.n_failed + ' non analysé(s)';
  $('dup-count').textContent = note;
  $('dup-actions').style.display = 'block';
  $('btn-dup-fix').disabled = !res.groups.length;
  $('dup-confirm').style.display = 'none';
  $('dup-fix-count').textContent = '';
  loadDupBackupInfo();
}

// --- résolution des doublons ---
let dupConfirmAction = '';
function humanSize(b){
  if (b >= 1073741824) return (b / 1073741824).toFixed(1) + ' Go';
  if (b >= 1048576) return Math.round(b / 1048576) + ' Mo';
  return Math.round(b / 1024) + ' Ko';
}

async function loadDupBackupInfo(){
  if (!API) return;
  const info = await API.dup_backup_info();
  if (info && info.ok && info.count){
    $('dup-backup-row').style.display = 'flex';
    $('dup-backup-info').textContent = info.count + ' sauvegarde(s) de doublons sur la clé · ' + humanSize(info.bytes);
  } else {
    $('dup-backup-row').style.display = 'none';
  }
}

async function askFixDuplicates(){
  if (!dupGroups.length){ $('dup-fix-count').textContent = 'Aucun doublon à corriger.'; return; }
  const st = await API.get_state();
  if (!st.usb_configured){ $('dup-needs-usb').style.display = 'flex'; return; }
  $('dup-needs-usb').style.display = 'none';
  dupConfirmAction = 'fix';
  const copies = dupGroups.reduce((a, g) => a + (g.versions.length - 1), 0);
  $('dup-confirm-text').textContent = 'Corriger ' + copies + ' copie(s) sur ' + dupGroups.length
    + ' groupe(s) ? Les playlists seront repointées vers la version gardée et les copies déplacées '
    + 'vers un backup réversible. collection.nml est sauvegardé avant.';
  $('dup-confirm').style.display = 'flex';
}

function askCleanBackups(){
  dupConfirmAction = 'clean';
  $('dup-confirm-text').textContent = 'Supprimer définitivement les backups de doublons ? '
    + 'Les copies écartées seront perdues (la version gardée reste). Irréversible.';
  $('dup-confirm').style.display = 'flex';
}

async function onDupConfirm(){
  $('dup-confirm').style.display = 'none';
  if (dupConfirmAction === 'fix') return doFixDuplicates();
  if (dupConfirmAction === 'clean') return doCleanBackups();
}

async function doFixDuplicates(){
  $('btn-dup-fix').disabled = true;
  $('dup-fix-count').textContent = 'Correction en cours…';
  const r = await API.resolve_duplicates();
  if (!r || !r.ok){
    $('dup-fix-count').textContent = (r && r.error) ? r.error : 'Erreur';
    $('btn-dup-fix').disabled = false;
    return;
  }
  $('dup-fix-count').textContent = r.n_repointed + ' référence(s) repointée(s) · ' + r.n_moved
    + ' copie(s) au backup. Fais « Remove Missing Tracks » dans Traktor.';
  await scanDuplicates();
  loadDupBackupInfo();
}

async function restoreDup(){
  $('btn-dup-restore').disabled = true;
  const r = await API.restore_duplicates();
  $('btn-dup-restore').disabled = false;
  if (!r || !r.ok){ $('dup-backup-info').textContent = (r && r.error) ? r.error : 'Erreur'; return; }
  $('dup-backup-info').textContent = r.n_restored + ' fichier(s) restauré(s)'
    + (r.n_failed ? (' · ' + r.n_failed + ' échec(s)') : '');
  await scanDuplicates();
}

async function doCleanBackups(){
  const r = await API.clean_dup_backups();
  if (!r || !r.ok){ $('dup-backup-info').textContent = (r && r.error) ? r.error : 'Erreur'; return; }
  $('dup-backup-info').textContent = r.removed + ' backup(s) supprimé(s) · ' + humanSize(r.freed) + ' libéré(s)';
  loadDupBackupInfo();
}

function renderDuplicates(groups){
  const root = $('dup-list');
  if (!groups.length){
    root.innerHTML = '<div class="empty">Aucun doublon détecté dans ce dossier. 👌</div>';
    return;
  }
  root.innerHTML = groups.map(g => {
    const sc = (g.score != null)
      ? ' <span>· ' + Math.round(g.score * 100) + '% identique</span>' : '';
    const head = '<div class="dup-head"><div class="title">'
      + esc(g.artist || '—') + ' — ' + esc(g.title)
      + ' <span>· ' + g.n + ' versions</span>' + sc + '</div></div>';
    const rows = g.versions.map(v => {
      const meta = [v.ext.toUpperCase(),
        v.bitrate ? (v.bitrate + ' kbps') : null,
        v.duration_h || null, v.size_h].filter(Boolean).join(' · ');
      if (v.keep){
        return '<div class="ver best" data-path="' + esc(v.path) + '">'
          + '<svg class="mark" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2"><path d="M5 12l4 4 10-10"/></svg>'
          + '<div><div class="fname">' + esc(v.name) + '</div><div class="fmeta">' + esc(meta) + '</div></div>'
          + '<span class="keep">À garder</span></div>';
      }
      return '<div class="ver dim choose" data-path="' + esc(v.path) + '" title="Cliquer pour garder cette version à la place">'
        + '<span class="radio-dot"></span>'
        + '<div><div class="fname">' + esc(v.name) + '</div><div class="fmeta">' + esc(meta) + '</div></div>'
        + '<span class="choose-lbl">Garder celle-ci</span></div>';
    }).join('');
    return '<div class="dup-group">' + head + rows + '</div>';
  }).join('');
  root.querySelectorAll('.ver.choose[data-path]').forEach(el =>
    el.addEventListener('click', () => chooseMaster(el.dataset.path)));
}

async function chooseMaster(path){
  if (!path || !API) return;
  for (const g of dupGroups){
    if (g.versions.some(v => v.path === path)){
      g.versions.forEach(v => { v.keep = (v.path === path); });
      break;
    }
  }
  await API.set_dup_master(path);
  filterDuplicates();   // re-render en respectant le filtre courant
}

// ---------- utils ----------
function format(n){ return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '\u00a0'); }
function folderName(p){ if(!p) return ''; const parts = p.replace(/[\\/]+$/,'').split(/[\\/]/); return parts[parts.length-1] || p; }
function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

// ---------- intégrité ----------
let integStop = false;

async function scanIntegrity(){
  if (!API) return;
  $('integ-empty').style.display = 'none';
  $('integ-list').innerHTML = '';
  $('btn-scan-integ').disabled = true;
  integStop = false;
  const isDeep = (integMode === 'deep');
  const chunk = isDeep ? Math.max(8, parseInt($('integ-workers').value) || 4) : 80;
  const label = isDeep ? 'Analyse approfondie…' : 'Analyse…';
  const begin = await API.integ_begin(integMode, parseInt($('integ-workers').value) || 4);
  if (!begin || !begin.ok){
    $('btn-scan-integ').disabled = false;
    $('integ-empty').textContent = (begin && begin.error)
      ? begin.error : "Choisis d'abord ton dossier sur l'accueil.";
    $('integ-empty').style.display = 'block';
    $('integ-count').textContent = '—';
    return;
  }
  if (isDeep) $('btn-integ-stop').style.display = '';
  showProgress('integ-loading', label);
  let last = null;
  do {
    if (integStop){
      await API.integ_cancel();
      $('integ-loading').style.display = 'none';
      $('btn-integ-stop').style.display = 'none';
      $('btn-scan-integ').disabled = false;
      $('integ-count').textContent = 'Analyse interrompue — les fichiers déjà vérifiés sont conservés en cache.';
      return;
    }
    last = await API.integ_step(chunk);
    setProgress('integ-loading', last.done, last.total, label);
  } while (!last.finished);
  $('integ-loading').style.display = 'none';
  $('btn-integ-stop').style.display = 'none';
  $('btn-scan-integ').disabled = false;
  const res = last.result;
  if (!res || !res.ok){
    $('integ-empty').textContent = (res && res.error) ? res.error : 'Erreur';
    $('integ-empty').style.display = 'block';
    $('integ-count').textContent = '—';
    return;
  }
  renderIntegrity(res);
  // tuile accueil
  const tnum = $('tile-integ'), tmeta = $('tile-integ-meta');
  if (tnum){
    tnum.textContent = res.n;
    tnum.style.color = res.n ? 'var(--error)' : 'var(--success)';
    tmeta.textContent = res.n ? 'fichiers à vérifier' : 'tout est sain';
  }
}

function renderIntegrity(res){
  const root = $('integ-list');
  const parts = [];
  if (res.n_critical) parts.push(res.n_critical + ' critique' + (res.n_critical > 1 ? 's' : ''));
  if (res.n_warning) parts.push(res.n_warning + ' à vérifier');
  $('integ-count').textContent = res.n
    ? (parts.join(' · ') + ' sur ' + res.total + ' fichiers')
    : (res.total + ' fichiers analysés');
  if (!res.items.length){
    root.innerHTML = '<div class="integ-ok">Aucun problème détecté. Ta bibliothèque est saine. 👌</div>';
    return;
  }
  root.innerHTML = res.items.map(it => {
    const label = it.severity === 'critical' ? 'Critique' : 'À vérifier';
    return '<div class="integ-row">'
      + '<span class="sev ' + it.severity + '">' + label + '</span>'
      + '<div><div class="fname">' + esc(it.name) + '</div>'
      + '<div class="ferr">' + esc(it.errors.join(' · ')) + '</div></div></div>';
  }).join('');
}

// ---------- tags ----------
async function scanTags(){
  if (!API) return;
  $('tags-empty').style.display = 'none';
  $('tags-preview').innerHTML = '';
  $('tags-counters').style.display = 'none';
  $('tags-loading').style.display = 'block';
  $('btn-scan-tags').disabled = true;
  const res = await API.check_tags();
  $('tags-loading').style.display = 'none';
  $('btn-scan-tags').disabled = false;
  if (!res || !res.ok){
    $('tags-empty').textContent = (res && res.error)
      ? res.error : "Choisis d'abord ton dossier sur l'accueil.";
    $('tags-empty').style.display = 'block';
    $('tags-count').textContent = '—';
    return;
  }
  renderTags(res);
}

function renderTags(res){
  $('tags-counters').style.display = 'grid';
  $('tags-ok').textContent = format(res.n_ok);
  $('tags-fix').textContent = format(res.n_fix);
  $('tags-lost').textContent = format(res.n_lost);
  $('tags-count').textContent = res.total + ' fichiers analysés';

  // bouton « Modifier les tags » visible seulement s'il y a des corrigeables
  lastFix = res.n_fix;
  $('btn-apply-retag').style.display = res.n_fix > 0 ? '' : 'none';
  $('retag-confirm').style.display = 'none';

  const root = $('tags-preview');
  let html = '';
  if (res.items.length){
    const head = '<div class="tag-row head"><div>Fichier</div><div>Artiste proposé</div><div>Titre proposé</div></div>';
    const rows = res.items.map(it =>
      '<div class="tag-row"><div class="fn">' + esc(it.name) + '</div>'
      + '<div>' + esc(it.artist) + '</div><div>' + esc(it.title) + '</div></div>'
    ).join('');
    html += '<div class="tag-preview-head">'
      + res.n_fix + ' fichier(s) peuvent être corrigés automatiquement à partir de leur nom (aperçu des valeurs proposées) :</div>'
      + '<div class="tag-table">' + head + rows + '</div>';
  }
  const lost = res.lost_list || [];
  tagsLost = lost;
  $('tile-lost').classList.toggle('clickable', lost.length > 0);
  $('tile-lost').style.cursor = lost.length ? 'pointer' : '';
  $('tags-lost-list').style.display = 'none';
  $('tags-lost-list').innerHTML = '';
  if (!html){
    let msg;
    if (res.total === 0) msg = 'Aucun fichier audio trouvé.';
    else msg = 'Tous tes fichiers sont déjà bien taggés. Rien à faire. 👌';
    root.innerHTML = '<div class="empty">' + esc(msg) + '</div>';
    return;
  }
  root.innerHTML = html;
}

function toggleTagsLost(){
  if (!tagsLost.length) return;
  const box = $('tags-lost-list');
  if (box.style.display !== 'none'){ box.style.display = 'none'; return; }
  box.innerHTML = '<div class="unident-head">Non identifiables — à taguer ou renommer à la main '
    + '<span style="color:var(--text-3);font-weight:400;">(clique un fichier pour le localiser)</span></div>'
    + tagsLost.map((u, i) => '<div class="unident-item" data-i="' + i + '">' + esc(u.name) + '</div>').join('');
  box.querySelectorAll('.unident-item[data-i]').forEach(el =>
    el.addEventListener('click', () => {
      const u = tagsLost[parseInt(el.dataset.i)];
      revealFile(u && u.path);
    }));
  box.style.display = 'block';
}

function askRetagConfirm(){
  $('btn-apply-retag').style.display = 'none';
  $('retag-confirm-text').textContent =
    'Modifier les tags de ' + lastFix + ' fichier(s) à partir de leur nom\u00a0? '
    + 'Cette opération écrit dans tes fichiers.';
  $('retag-confirm').style.display = 'flex';
}

function cancelRetag(){
  $('retag-confirm').style.display = 'none';
  $('btn-apply-retag').style.display = lastFix > 0 ? '' : 'none';
}

async function applyRetag(){
  if (!API) return;
  $('retag-confirm').style.display = 'none';
  $('tags-loading').style.display = 'block';
  $('btn-scan-tags').disabled = true;
  const res = await API.apply_retag();
  $('btn-scan-tags').disabled = false;
  if (!res || !res.ok){
    $('tags-loading').style.display = 'none';
    return;
  }
  await scanTags();   // rafraîchit compteurs + aperçu (remet tags-loading à none)
  const note = res.n_retagged + ' fichier(s) modifié(s)'
    + (res.n_failed ? ' · ' + res.n_failed + ' échec(s)' : '');
  const el = document.createElement('div');
  el.className = 'tag-preview-head';
  el.style.color = res.n_failed ? 'var(--warning)' : 'var(--success)';
  el.textContent = note;
  $('tags-preview').prepend(el);
}

// ---------- importer ----------
async function comparePlaylist(){
  if (!API) return;
  const text = $('import-text').value || '';
  if (!text.trim()){
    $('import-count').textContent = 'Colle d\u2019abord une liste de morceaux';
    return;
  }
  $('import-results').innerHTML = '';
  $('import-counters').style.display = 'none';
  $('btn-compare').disabled = true;
  const res = await runChunked('import-loading', 'Comparaison…',
    () => API.compare_begin(text), (n) => API.compare_step(n), 25);
  $('btn-compare').disabled = false;
  if (!res || !res.ok){
    $('import-count').textContent = (res && res.error)
      ? res.error : "Choisis d'abord ton dossier sur l'accueil.";
    return;
  }
  renderImport(res);
}

function renderImport(res){
  $('import-counters').style.display = 'grid';
  $('imp-found').textContent = format(res.n_found);
  $('imp-review').textContent = format(res.n_review);
  $('imp-missing').textContent = format(res.n_missing);
  $('import-count').textContent = res.n_total + ' morceaux analysés';
  // barre d'exports : M3U des trouvés + liste des manquants
  $('import-exports').style.display = 'flex';
  $('btn-export-m3u').disabled = !res.n_found;
  $('btn-export-missing').disabled = !res.n_missing;
  $('import-export-msg').style.display = 'none';

  const root = $('import-results');
  let html = '';
  if (res.missing.length){
    html += '<div class="imp-section"><h3>Manquants — à récupérer</h3>'
      + res.missing.map(m => '<div class="imp-row"><span class="q">' + esc(m.query) + '</span></div>').join('')
      + '</div>';
  }
  if (res.review.length){
    html += '<div class="imp-section"><h3>À vérifier — correspondance incertaine</h3>'
      + res.review.map(r => '<div class="imp-row"><span class="q">' + esc(r.query)
        + '</span><span class="m">≈ ' + esc(r.local) + ' <b>' + r.score + '%</b></span></div>').join('')
      + '</div>';
  }
  if (!res.missing.length && !res.review.length){
    html = '<div class="empty">Tous les morceaux de cette playlist sont déjà sur ta clé. 👌</div>';
  }
  root.innerHTML = html;
}

async function updateBackups(){
  if (!API) return;
  let s;
  try { s = await API.backups_status(); } catch (e) { return; }
  if (!s || !s.items) return;
  const MAP = {
    none:  { txt: 'À faire',            col: 'var(--text-3)' },
    ok:    { txt: 'À jour',             col: 'var(--success)' },
    stale: { txt: 'À mettre à jour',    col: 'var(--warning)' },
  };
  const fmtDate = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return '';
    return 'le ' + String(d.getDate()).padStart(2,'0') + '/'
      + String(d.getMonth()+1).padStart(2,'0') + '/' + d.getFullYear();
  };
  $('bk-list').innerHTML = s.items.map(it => {
    const m = MAP[it.state] || MAP.none;
    return '<div class="tile clickable bk-tile" data-go="sync">'
      + '<div class="lab"><span class="bk-dot" style="background:' + m.col + '"></span> ' + esc(it.label) + '</div>'
      + '<div class="bk-state" style="color:' + m.col + '">' + m.txt + '</div>'
      + '<div class="meta">' + (it.last ? fmtDate(it.last) : '—') + '</div>'
      + '</div>';
  }).join('');
  $('bk-list').querySelectorAll('.bk-tile').forEach(r =>
    r.addEventListener('click', () => navTo('sync')));
}

// ---------- AcoustID (vérifier le contenu) ----------
async function updateHomeTiles(){
  if (!API) return;
  let s;
  try { s = await API.home_stats(); } catch (e) { return; }
  if (!s) return;
  $('tile-size').textContent = s.total_size_h || '—';
  $('tile-formats').textContent = s.n_formats || '—';
  $('tile-formats-meta').textContent = s.formats_h || '—';
  const lq = $('tile-lowq');
  lq.textContent = s.low_quality;
  lq.style.color = s.low_quality ? 'var(--warning)' : 'var(--success)';
  $('tile-lowq-meta').textContent = '< ' + s.low_quality_th + ' kbps';
  const mt = $('tile-missing');
  mt.textContent = s.missing_tags;
  mt.style.color = s.missing_tags ? 'var(--warning)' : 'var(--success)';
  const ig = $('tile-integ'), igm = $('tile-integ-meta');
  if (s.integ.state === 'none'){ ig.textContent = '—'; ig.style.color = 'var(--text-3)'; igm.textContent = 'non analysé'; }
  else { ig.textContent = s.integ.bad; ig.style.color = s.integ.bad ? 'var(--error)' : 'var(--success)';
         igm.textContent = s.integ.state === 'stale' ? 'à refaire' : (s.integ.bad ? 'à vérifier' : 'tout est sain'); }
  const mm = $('tile-mismatch'), mmm = $('tile-mismatch-meta');
  if (s.mismatch.state === 'none'){ mm.textContent = '—'; mm.style.color = 'var(--text-3)'; mmm.textContent = 'non vérifié'; }
  else { mm.textContent = s.mismatch.bad; mm.style.color = s.mismatch.bad ? 'var(--error)' : 'var(--success)';
         mmm.textContent = s.mismatch.state === 'stale' ? 'à refaire' : (s.mismatch.bad ? 'incohérences' : 'tout concorde'); }
}

async function updateIntegAckeyHint(){
  if (!API) return;
  const st = await API.get_state();
  const hasKey = !!(st.acoustid_key || '').trim();
  const h = $('ackey-missing-hint');
  if (h) h.style.display = hasKey ? 'none' : 'block';
  if (!st.fpcalc) $('acoustid-count').textContent = 'fpcalc non détecté — voir Configuration sur l’accueil';
}

function setAckeyMode(hasKey){
  const row = $('ackey-row'), set = $('ackey-set');
  if (!row || !set) return;
  row.style.display = hasKey ? 'none' : '';
  set.style.display = hasKey ? 'flex' : 'none';
}

async function loadAcoustidKey(){
  if (!API) return;
  const st = await API.get_state();
  const inp = $('acoustid-key');
  if (inp && st.acoustid_key !== undefined) inp.value = st.acoustid_key || '';
  setAckeyMode(!!(st.acoustid_key || '').trim());
  if (!st.fpcalc){
    $('acoustid-count').textContent = 'fpcalc non détecté — voir Configuration sur l’accueil';
  }
}

async function saveAcoustidKey(){
  if (!API) return;
  const v = ($('acoustid-key').value || '').trim();
  await API.set_acoustid_key(v);
  $('acoustid-count').textContent = v ? 'Clé enregistrée' : '—';
  setAckeyMode(!!v);
}

async function checkAcoustid(){
  if (!API) return;
  $('acoustid-results').innerHTML = '';
  $('btn-acoustid').disabled = true;
  const res = await runChunked('acoustid-loading', 'Identification…',
    () => API.acoustid_begin(), (n) => API.acoustid_step(n), 3);
  $('btn-acoustid').disabled = false;
  if (!res || !res.ok){
    $('acoustid-count').textContent = (res && res.error) ? res.error : 'Erreur';
    return;
  }
  let note = res.n_mismatch + ' divergence' + (res.n_mismatch > 1 ? 's' : '')
    + ' · ' + res.n_match + ' conformes';
  if (res.n_unident) note += ' · ' + res.n_unident + ' non identifiés';
  if (res.n_error) note += ' · ' + res.n_error + ' erreurs';
  $('acoustid-count').textContent = note;
  if (!res.mismatches.length){
    $('acoustid-results').innerHTML = '<div class="empty" style="color:var(--success)">Aucune divergence : le son correspond aux tags. 👌</div>';
    return;
  }
  $('acoustid-results').innerHTML = res.mismatches.map(m =>
    '<div class="ac-row"><div class="f">' + esc(m.name) + '</div>'
    + '<div class="d">Taggé <b>' + esc(m.tag_artist || '—') + '</b> · identifié : '
    + esc(m.id_artist || '?') + (m.id_title ? ' – ' + esc(m.id_title) : '')
    + ' (score ' + m.score + ')</div></div>').join('');
}

// ---------- enrichissement des tags (AcoustID → MusicBrainz) ----------
let enrichProps = [];
let enrichUnident = [];
let tagsLost = [];
function _tagNorm(s){ return (s||'').replace(/\s+/g,' ').trim().toLowerCase(); }

async function enrichScan(){
  if (!API) return;
  $('enrich-results').style.display = 'none';
  $('enrich-confirm').style.display = 'none';
  $('btn-enrich').disabled = true;
  $('btn-enrich-stop').style.display = '';
  const res = await runChunked('enrich-loading', 'Identification…',
    () => API.enrich_begin(), (n) => API.enrich_step(n), 6);
  $('btn-enrich').disabled = false;
  $('btn-enrich-stop').style.display = 'none';
  if (!res || !res.ok){
    $('enrich-count').textContent = (res && res.error) ? res.error : 'Erreur';
    return;
  }
  let note = (res.cancelled ? 'Analyse interrompue — résultats partiels · ' : '')
    + res.n_proposed + ' correction' + (res.n_proposed > 1 ? 's' : '')
    + ' proposée' + (res.n_proposed > 1 ? 's' : '') + ' · ' + res.n_already_ok + ' déjà bien taggés';
  if (res.n_error) note += ' · ' + res.n_error + ' erreurs';
  enrichUnident = res.unident_list || [];
  if (res.api_error){
    const isSSL = /SSL|CERTIFICATE_VERIFY|certificate verify/i.test(res.api_error);
    const advice = isSSL
      ? ' — problème de <b>certificats SSL</b>, pas ta clé. Lance <code>/Applications/Python\\ 3.12/Install\\ Certificates.command</code> (ou <code>pip3.12 install certifi</code>), puis relance.'
      : ' — vérifie ta clé (une clé d\u2019<b>application</b> est requise, pas une clé de compte).';
    $('enrich-count').innerHTML = '<span style="color:var(--error);font-weight:600;">⚠ AcoustID a refusé la requête : '
      + esc(res.api_error) + '</span>' + advice;
    $('enrich-unident-list').style.display = 'none';
    return;
  }
  $('enrich-count').innerHTML = esc(note)
    + (res.n_unident
       ? ' · <span class="num-link" id="enrich-unident-link">' + res.n_unident + ' non identifiés ▸</span>'
       : ' · 0 non identifié');
  const ubox = $('enrich-unident-list');
  ubox.style.display = 'none';
  ubox.innerHTML = '';
  enrichProps = res.proposals || [];
  if (!enrichProps.length){ $('enrich-table').innerHTML = ''; return; }
  renderEnrich(enrichProps);
  $('enrich-results').style.display = 'block';
}

async function revealFile(path){
  if (!path){ alert(t('Chemin du fichier manquant.')); return; }
  if (!API){ return; }
  try {
    const r = await API.reveal_file(path);
    if (r && !r.ok) alert(t('Impossible de localiser le fichier :') + '\n' + (r.error || 'erreur inconnue'));
  } catch (e){
    alert(t('Impossible de localiser le fichier.'));
  }
}

function toggleEnrichUnident(){
  const box = $('enrich-unident-list');
  if (box.style.display !== 'none'){ box.style.display = 'none'; return; }
  box.innerHTML = enrichUnident.map((u, i) =>
    '<div class="unident-item" data-i="' + i + '" title="Cliquer pour localiser le fichier">'
    + esc(u.name) + '</div>').join('')
    || '<div class="unident-item">—</div>';
  box.querySelectorAll('.unident-item[data-i]').forEach(el =>
    el.addEventListener('click', () => {
      const u = enrichUnident[parseInt(el.dataset.i)];
      revealFile(u && u.path);
    }));
  box.style.display = 'block';
}

function renderEnrich(props){
  $('enrich-table').innerHTML = props.map((p, i) => {
    let chg = '';
    if (p.prop_artist && _tagNorm(p.prop_artist) !== _tagNorm(p.cur_artist))
      chg += 'Artiste : <span class="old">' + esc(p.cur_artist || '—') + '</span> → <b>' + esc(p.prop_artist) + '</b>';
    if (p.prop_title && _tagNorm(p.prop_title) !== _tagNorm(p.cur_title)){
      if (chg) chg += '<br>';
      chg += 'Titre : <span class="old">' + esc(p.cur_title || '—') + '</span> → <b>' + esc(p.prop_title) + '</b>';
    }
    const prot = p.title_protected ? '<div class="prot">Titre protégé (remix/edit) — non modifié</div>' : '';
    let sel = '';
    if (p.albums && p.albums.length){
      sel = '<select>' + p.albums.map(a =>
        '<option value="' + esc(a.id) + '"' + (a.id === p.chosen_id ? ' selected' : '') + '>'
        + esc(a.title) + (a.type ? ' (' + esc(a.type) + ')' : '') + '</option>').join('') + '</select>';
    }
    return '<div class="enrich-row" data-idx="' + i + '"><input type="checkbox" checked>'
      + '<div class="body"><div class="f reveal" data-path="' + esc(p.path || '') + '" title="Cliquer pour localiser le fichier">' + esc(p.name) + '</div>'
      + '<div class="chg">' + chg + '</div>' + prot + sel + '</div></div>';
  }).join('');
  $('enrich-table').querySelectorAll('.f.reveal[data-path]').forEach(el =>
    el.addEventListener('click', () => revealFile(el.dataset.path)));
}

function enrichToggleAll(state){
  document.querySelectorAll('#enrich-table input[type=checkbox]').forEach(cb => cb.checked = state);
}

function askApplyEnrich(){
  const n = [...document.querySelectorAll('#enrich-table input[type=checkbox]')].filter(cb => cb.checked).length;
  if (!n){ $('enrich-count').textContent = 'Coche au moins une ligne.'; return; }
  $('enrich-confirm-text').textContent = 'Écrire les tags officiels de ' + n
    + ' fichier(s) et embarquer la pochette manquante ? Les titres remix/edit ne seront pas remplacés.';
  $('enrich-confirm').style.display = 'flex';
}

async function doApplyEnrich(){
  $('enrich-confirm').style.display = 'none';
  const selection = [];
  document.querySelectorAll('#enrich-table .enrich-row').forEach(row => {
    if (!row.querySelector('input[type=checkbox]').checked) return;
    const p = enrichProps[+row.dataset.idx];
    const sel = row.querySelector('select');
    let album_id = p.chosen_id, album = p.chosen_title;
    if (sel){ album_id = sel.value; const a = (p.albums || []).find(x => x.id === album_id); album = a ? a.title : ''; }
    selection.push({path: p.path, artist: p.prop_artist, title: p.prop_title,
                    album, album_id, cover_present: p.cover_present});
  });
  if (!selection.length) return;
  $('btn-enrich-apply').disabled = true;
  showProgress('enrich-loading', 'Écriture…');
  let ok = 0, fail = 0, cov = 0;
  const chunk = 2;
  for (let i = 0; i < selection.length; i += chunk){
    const r = await API.enrich_apply(selection.slice(i, i + chunk));
    if (r && r.ok){ ok += r.n_ok; fail += r.n_fail; cov += r.n_covers; }
    setProgress('enrich-loading', Math.min(i + chunk, selection.length), selection.length, 'Écriture…');
  }
  $('enrich-loading').style.display = 'none';
  $('btn-enrich-apply').disabled = false;
  $('enrich-count').textContent = ok + ' fichier(s) tagués · ' + cov + ' pochette(s) ajoutée(s)'
    + (fail ? (' · ' + fail + ' échec(s)') : '');
  $('enrich-results').style.display = 'none';
  $('enrich-table').innerHTML = '';
}

// ---------- vérifier un dossier d'import ----------
let impResults = [];

async function checkImportFolder(){
  if (!API) return;
  const pick = await API.pick_import_folder();
  if (!pick || !pick.ok) return;  // annulé
  $('impchk-results').style.display = 'none';
  $('impchk-unknown').style.display = 'none';
  $('btn-impchk').disabled = true;
  const res = await runChunked('impchk-loading', 'Identification…',
    () => API.import_check_begin(pick.path), (n) => API.import_check_step(n), 3);
  $('btn-impchk').disabled = false;
  if (!res || !res.ok){
    $('impchk-count').textContent = (res && res.error) ? res.error : 'Erreur';
    return;
  }
  $('impchk-count').textContent = res.total + ' fichier(s) · ' + res.n_dup + ' doublon(s), '
    + res.n_new + ' nouveau(x)' + (res.n_unknown ? (', ' + res.n_unknown + ' non identifié(s)') : '');
  impResults = res.results || [];
  renderImportCheck(impResults);
  $('impchk-results').style.display = 'block';
  $('impchk-unknown').style.display = res.n_unknown ? 'block' : 'none';
}

function renderImportCheck(results){
  const lab = {doublon: 'Doublon', nouveau: 'Nouveau', inconnu: 'Non identifié'};
  const cls = {doublon: 'dup', nouveau: 'new', inconnu: 'unk'};
  $('impchk-table').innerHTML = results.map((r, i) => {
    let d = '';
    if (r.ident) d += 'Identifié : ' + esc(r.ident);
    if (r.base) d += (d ? ' · ' : '') + 'déjà présent : <b>' + esc(r.base) + '</b>'
      + (r.score !== '' ? (' (' + r.score + ')') : '');
    return '<div class="impchk-row" data-idx="' + i + '" data-path="' + esc(r.path) + '">'
      + '<input type="checkbox"' + (r.checked_default ? ' checked' : '') + '>'
      + '<div class="body"><div class="f">' + esc(r.name)
      + '<span class="st ' + cls[r.status] + '">' + lab[r.status] + '</span></div>'
      + (d ? ('<div class="d">' + d + '</div>') : '') + '</div></div>';
  }).join('');
}

function impToggleAll(state){
  document.querySelectorAll('#impchk-table input[type=checkbox]').forEach(cb => cb.checked = state);
}

async function discardImport(){
  const rows = [...document.querySelectorAll('#impchk-table .impchk-row')];
  const paths = rows.filter(r => r.querySelector('input[type=checkbox]').checked).map(r => r.dataset.path);
  if (!paths.length){ $('impchk-count').textContent = 'Coche au moins un fichier à écarter.'; return; }
  $('btn-impchk-discard').disabled = true;
  const r = await API.import_discard(paths);
  $('btn-impchk-discard').disabled = false;
  if (!r || !r.ok){ $('impchk-count').textContent = (r && r.error) ? r.error : 'Erreur'; return; }
  rows.forEach(row => { if (row.querySelector('input[type=checkbox]').checked) row.remove(); });
  $('impchk-count').textContent = r.moved + " fichier(s) déplacé(s) dans _DOUBLONS/ — rien n'est supprimé"
    + (r.errors && r.errors.length ? (' · ' + r.errors.length + ' échec(s)') : '');
}

// ---------- renommage ----------
let renameRows = [];

async function renameScan(){
  if (!API) return;
  $('btn-rename-scan').disabled = true;
  $('btn-rename-apply').style.display = 'none';
  $('rename-confirm').style.display = 'none';
  $('rename-results').style.display = 'none';
  const res = await runChunked('rename-loading', 'Analyse…',
    () => API.rename_scan_begin(), (n) => API.rename_scan_step(n), 120);
  $('btn-rename-scan').disabled = false;
  if (!res || !res.ok){
    $('rename-count').textContent = (res && res.error) ? res.error : "Choisis d'abord ton dossier sur l'accueil.";
    return;
  }
  renameRows = (res.rows || []).map(r => Object.assign({}, r, {_checked: true}));
  let note = res.n_rename + ' à renommer · ' + res.n_already + ' déjà au format';
  if (res.n_no_tags) note += ' · ' + res.n_no_tags + ' sans tags';
  if (!res.has_nml) note += ' · ⚠ sans suivi Traktor';
  $('rename-count').textContent = note;
  if (renameRows.length){
    renderRenameTable();
    $('rename-results').style.display = 'block';
    $('btn-rename-apply').style.display = '';
  }
}

function renderRenameTable(){
  const root = $('rename-table');
  root.innerHTML = renameRows.map((r, i) =>
    '<div class="rn-row">'
    + '<input type="checkbox" data-i="' + i + '" ' + (r._checked ? 'checked' : '') + '>'
    + '<span class="rn-old" title="' + esc(r.old_name) + '">' + esc(r.old_name) + '</span>'
    + '<span class="rn-new" title="' + esc(r.new_name) + '">' + esc(r.new_name) + '</span>'
    + '<span class="rn-track ' + (r.in_nml ? 'yes' : 'no') + '">' + (r.in_nml ? 'Suivi' : 'Hors NML') + '</span>'
    + '</div>').join('');
  root.querySelectorAll('input[type=checkbox]').forEach(cb => cb.addEventListener('change', () => {
    renameRows[+cb.dataset.i]._checked = cb.checked;
  }));
}

function renameCheckAll(state){
  renameRows.forEach(r => r._checked = state);
  $('rename-table').querySelectorAll('input[type=checkbox]').forEach(cb => { cb.checked = state; });
}

function askRenameConfirm(){
  const sel = renameRows.filter(r => r._checked);
  if (!sel.length){ $('rename-count').textContent = 'Coche au moins une ligne.'; return; }
  $('btn-rename-apply').style.display = 'none';
  const nNml = sel.filter(r => r.in_nml).length;
  $('rename-confirm-text').textContent =
    'Renommer ' + sel.length + ' fichier(s)'
    + (nNml ? ' · ' + nNml + ' suivi(s) dans collection.nml (mis à jour)' : '')
    + '. Irréversible — une sauvegarde du .nml est faite avant.';
  $('rename-confirm').style.display = 'flex';
}

function cancelRename(){
  $('rename-confirm').style.display = 'none';
  if (renameRows.length) $('btn-rename-apply').style.display = '';
}

async function applyRename(){
  const sel = renameRows.filter(r => r._checked).map(r => ({
    path: r.path, new_name: r.new_name, in_nml: r.in_nml,
    dir_raw: r.dir_raw, file_raw: r.file_raw }));
  if (!sel.length) return;
  $('rename-confirm').style.display = 'none';
  const res = await runChunked('rename-loading', 'Renommage…',
    () => API.rename_apply_begin(sel), (n) => API.rename_apply_step(n), 40);
  if (!res || !res.ok){
    $('rename-count').textContent = (res && res.error) ? res.error : 'Erreur';
    return;
  }
  let note = res.n_renamed + ' renommé(s)';
  if (res.n_nml) note += ' · ' + res.n_nml + ' entrée(s) Traktor maj';
  if (res.n_failed) note += ' · ' + res.n_failed + ' échec(s)';
  $('rename-count').textContent = note;
  $('rename-results').style.display = 'none';
  renameRows = [];
}

// ---------- synchro ----------
let structDest = '';

async function renderSyncSource(){
  if (!API) return;
  const st = await API.get_state();
  if (st.usb_configured){
    $('src-path').textContent = 'Clé entière : ' + st.usb_root;
    $('btn-reset-usb').style.display = '';
  } else {
    $('src-path').textContent = 'Ton dossier audio' + (st.music_folder ? ' (' + folderName(st.music_folder) + ')' : '');
    $('btn-reset-usb').style.display = 'none';
  }
}

async function pickUsbRoot(){
  if (!API) return;
  const res = await API.pick_usb_root();
  if (res && res.ok){
    await renderSyncSource();
    // un changement de source invalide le plan en cours
    lastPlan = null; $('btn-sync-apply').style.display = 'none';
    $('sync-results').innerHTML = ''; $('sync-count').textContent = '—';
  }
}

async function resetUsbRoot(){
  if (!API) return;
  await API.reset_usb_root();
  await renderSyncSource();
  lastPlan = null; $('btn-sync-apply').style.display = 'none';
  $('sync-results').innerHTML = ''; $('sync-count').textContent = '—';
}

async function pickStructDest(){
  if (!API) return;
  const res = await API.pick_struct_dest();
  if (res && res.ok){
    structDest = res.path;
    $('struct-dest').textContent = 'Dossier choisi : ' + res.path;
    $('btn-pick-struct').textContent = 'Modifier';
    $('btn-export-struct').disabled = false;
  }
}

async function exportStructure(){
  if (!API || !structDest) return;
  $('btn-export-struct').disabled = true;
  const res = await runChunked('struct-loading', 'Indexation…',
    () => API.export_structure_begin(structDest), (n) => API.export_structure_step(n), 80);
  $('btn-export-struct').disabled = false;
  if (!res || !res.ok){
    $('struct-count').textContent = (res && res.error) ? res.error : 'Erreur';
    return;
  }
  $('struct-count').textContent = res.tracks + ' piste(s) · '
    + (res.nml_copied ? 'collection.nml inclus' : 'sans collection.nml');
}

// ---------- sauvegarde complète ----------
let fullDest = '';

async function pickFullDest(){
  if (!API) return;
  const res = await API.pick_full_dest();
  if (res && res.ok){
    fullDest = res.path;
    $('full-dest').textContent = 'Dossier choisi : ' + res.path;
    $('btn-pick-full').textContent = 'Modifier';
    $('btn-full-backup').disabled = false;
  }
}

async function runFullBackup(){
  if (!API || !fullDest) return;
  $('btn-full-backup').disabled = true;
  const res = await runChunked('full-loading', 'Sauvegarde…',
    () => API.full_backup_begin(fullDest), (n) => API.full_backup_step(n), 40);
  $('btn-full-backup').disabled = false;
  if (!res || !res.ok){
    $('full-count').textContent = (res && res.error) ? res.error : 'Erreur';
    return;
  }
  if (res.mode === 'hardlink')
    $('full-count').textContent = 'Snapshot créé · ' + res.copied + ' copié(s), ' + res.linked + ' lié(s)';
  else
    $('full-count').textContent = 'Miroir à jour · ' + res.copied + ' copié(s), ' + res.archived + ' archivé(s)';
}

async function generateM3u(){
  if (!API) return;  $('btn-m3u').disabled = true;
  const res = await runChunked('m3u-loading', 'Génération…',
    () => API.m3u_begin(), (n) => API.m3u_step(n), 8);
  $('btn-m3u').disabled = false;
  if (!res || !res.ok){
    $('m3u-count').textContent = (res && res.error) ? res.error : 'Erreur';
    return;
  }
  let note = res.playlists + ' playlist(s) exportée(s)';
  if (res.orphans) note += ' · ' + res.orphans + ' supprimée(s)';
  if (res.missing) note += ' · ' + res.missing + ' fichier(s) manquant(s)';
  $('m3u-count').textContent = note;
}

async function pickSpare(){
  if (!API) return;
  const res = await API.pick_spare_folder();
  if (res && res.ok){
    spareFolder = res.path;
    $('spare-path').textContent = res.path;
    $('btn-sync-plan').disabled = false;
    $('btn-sync-apply').style.display = 'none';
    $('sync-results').innerHTML = '';
    $('sync-count').textContent = '—';
    lastPlan = null;
  }
}

async function planSync(){
  if (!API || !spareFolder) return;
  $('sync-results').innerHTML = '';
  $('btn-sync-apply').style.display = 'none';
  $('sync-confirm').style.display = 'none';
  showSpinner('sync-loading', 'Comparaison des deux dossiers…');
  $('btn-sync-plan').disabled = true;
  const res = await API.plan_sync(spareFolder);
  $('sync-loading').style.display = 'none';
  $('btn-sync-plan').disabled = false;
  if (!res || !res.ok){
    $('sync-count').textContent = (res && res.error) ? res.error : 'Erreur';
    return;
  }
  lastPlan = res;
  renderSyncPlan(res);
}

function renderSyncPlan(res){
  $('sync-count').textContent = res.n_copy + ' à copier · ' + res.n_delete + ' à supprimer · ' + res.copy_h;
  const root = $('sync-results');
  if (res.n_copy === 0 && res.n_delete === 0){
    root.innerHTML = '<div class="empty">Ta clé de secours est déjà à jour. Rien à synchroniser. 👌</div>';
    $('btn-sync-apply').style.display = 'none';
    return;
  }
  let html = '';
  if (res.n_copy){
    const list = res.to_copy.slice(0, 200).map(f => '<div class="imp-row"><span class="q">' + esc(f) + '</span></div>').join('');
    html += '<div class="imp-section"><h3>À copier vers la clé de secours (' + res.n_copy + ')</h3>' + list
      + (res.n_copy > 200 ? '<div class="empty">… et ' + (res.n_copy - 200) + ' autres</div>' : '') + '</div>';
  }
  if (res.n_delete){
    const list = res.to_delete.slice(0, 200).map(f => '<div class="imp-row"><span class="q">' + esc(f) + '</span><span class="m"><b>supprimé</b></span></div>').join('');
    html += '<div class="imp-section"><h3>À supprimer de la clé de secours (' + res.n_delete + ')</h3>' + list
      + (res.n_delete > 200 ? '<div class="empty">… et ' + (res.n_delete - 200) + ' autres</div>' : '') + '</div>';
  }
  root.innerHTML = html;
  $('btn-sync-apply').style.display = '';
}

function askSyncConfirm(){
  if (!lastPlan) return;
  $('btn-sync-apply').style.display = 'none';
  $('sync-confirm-text').textContent =
    'Synchroniser\u00a0: ' + lastPlan.n_copy + ' fichier(s) copié(s) et '
    + lastPlan.n_delete + ' supprimé(s) sur la clé de secours. '
    + 'Les suppressions sont définitives.';
  $('sync-confirm').style.display = 'flex';
}

function cancelSync(){
  $('sync-confirm').style.display = 'none';
  $('btn-sync-apply').style.display = lastPlan ? '' : 'none';
}

async function applySync(){
  if (!API || !spareFolder) return;
  $('sync-confirm').style.display = 'none';
  $('btn-sync-plan').disabled = true;
  const res = await runChunked('sync-loading', 'Synchronisation…',
    () => API.sync_apply_begin(spareFolder), (n) => API.sync_apply_step(n), 40);
  $('btn-sync-plan').disabled = false;
  $('btn-sync-apply').style.display = 'none';
  lastPlan = null;
  if (!res || !res.ok){
    $('sync-count').textContent = (res && res.error) ? res.error : 'Erreur';
    return;
  }
  const note = res.n_copied + ' copié(s) · ' + res.n_deleted + ' supprimé(s)'
    + (res.n_failed ? ' · ' + res.n_failed + ' échec(s)' : '');
  $('sync-count').textContent = 'Terminé : ' + note;
  $('sync-results').innerHTML = '<div class="empty" style="color:'
    + (res.n_failed ? 'var(--warning)' : 'var(--success)') + '">Synchronisation terminée — ' + esc(note) + '</div>';
}

// ---------- boutons ----------
$('btn-pick').addEventListener('click', pickFolder);
$('btn-rescan').addEventListener('click', () => { scannedOnce = false; dupShown = false; scanLibrary(); });
let dupMethod = 'title';
document.querySelectorAll('#dup-method .seg-btn').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#dup-method .seg-btn').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  dupMethod = b.dataset.method;
}));
$('btn-scan-dup').addEventListener('click', () => {
  if (dupMethod === 'audio') scanDuplicatesAudio(); else scanDuplicates();
});
$('btn-dup-stop').addEventListener('click', () => { audioStop = true; });
$('dup-filter').addEventListener('input', filterDuplicates);
$('btn-dup-fix').addEventListener('click', askFixDuplicates);
$('cfg-music-btn').addEventListener('click', async () => {
  const r = await API.pick_music_folder();
  if (r && r.ok){ scannedOnce = false; dupShown = false; await refreshHome(); }
});
$('cfg-usb-btn').addEventListener('click', async () => {
  const r = await API.pick_usb_root();
  if (r && r.ok) await refreshHome();
});
$('btn-dup-setusb').addEventListener('click', async () => {
  const r = await API.pick_usb_root();
  if (r && r.ok){ $('dup-needs-usb').style.display = 'none'; await refreshHome(); }
});
$('btn-dup-no').addEventListener('click', () => { $('dup-confirm').style.display = 'none'; });
$('btn-dup-yes').addEventListener('click', onDupConfirm);
$('btn-dup-restore').addEventListener('click', restoreDup);
$('btn-dup-clean').addEventListener('click', askCleanBackups);
$('btn-scan-integ').addEventListener('click', scanIntegrity);
$('btn-integ-stop').addEventListener('click', () => { integStop = true; });
$('btn-save-ackey').addEventListener('click', saveAcoustidKey);
$('ackey-edit').addEventListener('click', () => setAckeyMode(false));
$('btn-acoustid').addEventListener('click', checkAcoustid);
$('btn-enrich').addEventListener('click', enrichScan);
$('btn-enrich-stop').addEventListener('click', () => { if (API) API.enrich_cancel(); });
$('enrich-count').addEventListener('click', (e) => {
  if (e.target && e.target.closest && e.target.closest('#enrich-unident-link')) toggleEnrichUnident();
});
$('btn-enrich-all').addEventListener('click', () => enrichToggleAll(true));
$('btn-enrich-none').addEventListener('click', () => enrichToggleAll(false));
$('btn-enrich-apply').addEventListener('click', askApplyEnrich);
$('btn-enrich-yes').addEventListener('click', doApplyEnrich);
$('btn-enrich-no').addEventListener('click', () => { $('enrich-confirm').style.display = 'none'; });
$('btn-impchk').addEventListener('click', checkImportFolder);
$('btn-impchk-all').addEventListener('click', () => impToggleAll(true));
$('btn-impchk-none').addEventListener('click', () => impToggleAll(false));
$('btn-impchk-discard').addEventListener('click', discardImport);
$('btn-scan-tags').addEventListener('click', scanTags);
$('tile-lost').addEventListener('click', toggleTagsLost);
$('btn-apply-retag').addEventListener('click', askRetagConfirm);
$('btn-retag-yes').addEventListener('click', applyRetag);
$('btn-retag-no').addEventListener('click', cancelRetag);
// renommage
$('btn-rename-scan').addEventListener('click', renameScan);
$('btn-rename-apply').addEventListener('click', askRenameConfirm);
$('btn-rename-yes').addEventListener('click', applyRename);
$('btn-rename-no').addEventListener('click', cancelRename);
$('btn-rn-all').addEventListener('click', () => renameCheckAll(true));
$('btn-rn-none').addEventListener('click', () => renameCheckAll(false));
$('btn-compare').addEventListener('click', comparePlaylist);
let orphansData = [];
async function scanOrphans(){
  if (!API) return;
  $('btn-orphans').disabled = true;
  $('orphans-count').textContent = 'Analyse…';
  $('orphans-list').style.display = 'none';
  const res = await API.orphan_tracks();
  $('btn-orphans').disabled = false;
  if (!res || !res.ok){
    $('orphans-count').textContent = (res && res.error) ? res.error : 'Erreur';
    return;
  }
  orphansData = res.orphans || [];
  if (!res.n_orphans){
    $('orphans-count').innerHTML = '<span style="color:var(--success)">Aucun : tous tes morceaux sont dans au moins une playlist. 👌</span>';
    return;
  }
  $('orphans-count').innerHTML = '<span class="num-link" id="orphans-link">'
    + res.n_orphans + ' morceau(x) dans aucune playlist ▸</span>'
    + ' <span style="color:var(--text-3)">sur ' + res.n_total + ' (' + res.n_playlists + ' playlists)</span>';
  $('orphans-link').onclick = () => {
    const box = $('orphans-list');
    if (box.style.display !== 'none'){ box.style.display = 'none'; return; }
    box.innerHTML = '<div class="unident-head">Dans aucune playlist '
      + '<span style="color:var(--text-3);font-weight:400;">(clique un morceau pour le localiser)</span></div>'
      + orphansData.map((u, i) => '<div class="unident-item" data-i="' + i + '">' + esc(u.name) + '</div>').join('');
    box.querySelectorAll('.unident-item[data-i]').forEach(el =>
      el.addEventListener('click', () => { const u = orphansData[parseInt(el.dataset.i)]; revealFile(u && u.path); }));
    box.style.display = 'block';
  };
}
$('btn-orphans').addEventListener('click', scanOrphans);
$('btn-export-m3u').addEventListener('click', async () => {
  const msg = $('import-export-msg');
  const r = await API.export_found_m3u();
  if (r && r.ok){ msg.textContent = 'M3U créé (' + r.n + ' morceaux) : ' + r.path; msg.style.display = ''; }
  else if (r && !r.cancelled){ msg.textContent = (r && r.error) || 'Échec'; msg.style.display = ''; }
});
$('btn-export-missing').addEventListener('click', async () => {
  const msg = $('import-export-msg');
  const r = await API.export_missing_txt();
  if (r && r.ok){ msg.textContent = 'Liste créée (' + r.n + ' manquants) : ' + r.path; msg.style.display = ''; }
  else if (r && !r.cancelled){ msg.textContent = (r && r.error) || 'Échec'; msg.style.display = ''; }
});
// synchro
$('btn-pick-spare').addEventListener('click', pickSpare);
$('btn-pick-usb').addEventListener('click', pickUsbRoot);
$('btn-reset-usb').addEventListener('click', resetUsbRoot);
$('btn-pick-struct').addEventListener('click', pickStructDest);
$('btn-pick-full').addEventListener('click', pickFullDest);
$('btn-full-backup').addEventListener('click', runFullBackup);
$('btn-export-struct').addEventListener('click', exportStructure);
$('btn-m3u').addEventListener('click', generateM3u);
$('btn-sync-plan').addEventListener('click', planSync);
$('btn-sync-apply').addEventListener('click', askSyncConfirm);
$('btn-sync-yes').addEventListener('click', applySync);
$('btn-sync-no').addEventListener('click', cancelSync);
// mode intégrité (rapide / approfondi)
document.querySelectorAll('#integ-mode .seg-btn').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#integ-mode .seg-btn').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  integMode = b.dataset.mode;
  $('integ-deep-opts').style.display = (integMode === 'deep') ? 'flex' : 'none';
}));

// ---------- Statut (bas de sidebar) ----------
let statusItems = [];
const STATUS_LABEL = { ok: 'Tout est prêt', warning: 'Vérifications à faire', error: 'Problème détecté' };
const STATUS_COL = { ok: 'var(--success)', warning: 'var(--warning)', error: 'var(--error)' };

async function refreshStatus(){
  if (!API) return;
  let s;
  try { s = await API.compute_status(); } catch (e) { return; }
  if (!s) return;
  statusItems = s.items || [];
  const dot = $('conn-dot');
  dot.classList.remove('ok', 'warning', 'error', 'on');
  dot.classList.add(s.level);
  $('conn-label').textContent = STATUS_LABEL[s.level] || 'Statut';
}

function toggleStatusPopup(){
  const p = $('status-popup');
  if (p.style.display !== 'none'){ p.style.display = 'none'; return; }
  const rows = statusItems.map(it => {
    const col = STATUS_COL[it.level] || 'var(--text-3)';
    return '<div class="status-item" data-nav="' + esc(it.nav || '') + '">'
      + '<span class="si-dot" style="background:' + col + '"></span>'
      + '<div><div class="si-lab">' + esc(it.label) + '</div>'
      + '<div class="si-det">' + esc(it.detail) + '</div></div></div>';
  }).join('');
  p.innerHTML = '<div class="sp-title">État du système</div>' + rows;
  p.querySelectorAll('.status-item').forEach(el => el.addEventListener('click', () => {
    const nav = el.dataset.nav;
    p.style.display = 'none';
    if (nav) showView(nav);
  }));
  p.style.display = 'block';
}

$('status-btn').addEventListener('click', (e) => { e.stopPropagation(); toggleStatusPopup(); });
document.addEventListener('click', (e) => {
  const p = $('status-popup');
  if (p.style.display !== 'none' && !p.contains(e.target)
      && !$('status-btn').contains(e.target)){
    p.style.display = 'none';
  }
});
setInterval(() => { if (API) refreshStatus(); }, 5000);

// ---------- démarrage : attendre l'API pywebview ----------
async function boot(){
  API = window.pywebview.api;
  // langue : lue depuis la config AVANT tout rendu (défaut anglais)
  try {
    const st = await API.get_state();
    LANG = (st && st.lang === 'fr') ? 'fr' : 'en';
  } catch (e){ LANG = 'en'; }
  translateDom();
  startI18nObserver();
  const fr = $('btn-lang-fr'), en = $('btn-lang-en');
  fr.classList.toggle('active', LANG === 'fr');
  en.classList.toggle('active', LANG === 'en');
  fr.addEventListener('click', async () => { await API.set_lang('fr'); location.reload(); });
  en.addEventListener('click', async () => { await API.set_lang('en'); location.reload(); });
  refreshHome();
  try {
    const v = await API.vault_check();
    if (v && v.changed) showVaultPrompt('start');
  } catch (e){}
}
if (window.pywebview && window.pywebview.api){
  boot();
} else {
  window.addEventListener('pywebviewready', boot);
}


// ---------- fermeture : coffre-fort M3U à jour ? ----------
let vaultMode = 'quit';
function showVaultPrompt(mode){
  vaultMode = mode || 'quit';
  const box = $('vault-modal');
  box.querySelector('.modal-text').textContent = (vaultMode === 'quit')
    ? 'Ta collection Traktor a changé depuis la dernière sauvegarde du coffre-fort (playlists, classement ou cues). Régénérer le coffre-fort M3U maintenant avant de quitter ?'
    : 'Ta collection Traktor a changé depuis la dernière sauvegarde du coffre-fort (playlists, classement ou cues). Régénérer le coffre-fort M3U maintenant ?';
  $('btn-vq-skip').textContent = (vaultMode === 'quit') ? 'Quitter sans régénérer' : 'Plus tard';
  $('btn-vq-regen').textContent = (vaultMode === 'quit') ? 'Régénérer et quitter' : 'Régénérer';
  ['btn-vq-cancel','btn-vq-skip','btn-vq-regen'].forEach(id => $(id).disabled = false);
  $('btn-vq-cancel').style.display = (vaultMode === 'quit') ? '' : 'none';
  box.style.display = 'flex';
  $('vault-progress').style.display = 'none';
  translateDom(box);
}
$('btn-vq-cancel').addEventListener('click', () => {
  $('vault-modal').style.display = 'none';
});
$('btn-vq-skip').addEventListener('click', () => {
  if (vaultMode === 'quit'){ if (API) API.confirm_quit(); }
  else $('vault-modal').style.display = 'none';
});
$('btn-vq-regen').addEventListener('click', async () => {
  if (!API) return;
  ['btn-vq-cancel','btn-vq-skip','btn-vq-regen'].forEach(id => $(id).disabled = true);
  const prog = $('vault-progress');
  prog.style.display = '';
  prog.textContent = t('Lecture de collection.nml…');
  try {
    const begin = await API.m3u_begin();
    if (!begin || !begin.ok){
      prog.textContent = (begin && begin.error) || t('Échec');
      ['btn-vq-cancel','btn-vq-skip','btn-vq-regen'].forEach(id => $(id).disabled = false);
      return;
    }
    const total = begin.total || 0;
    let done = 0;
    while (done < total){
      const r = await API.m3u_step(8);
      done = r.done;
      prog.textContent = t('Génération…') + ' ' + Math.round(done * 100 / Math.max(total, 1)) + ' %';
      if (r.finished) break;
    }
    prog.textContent = t('Terminé : ') + t('coffre-fort à jour');
  } catch (e){}
  if (vaultMode === 'quit') API.confirm_quit();
  else setTimeout(() => { $('vault-modal').style.display = 'none'; }, 1200);
});
