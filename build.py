#!/usr/bin/env python3
"""Build script: generates dist/index.html and dist/calendar/index.html.

RA data and notes are stored in GitLab at runtime — this script only
bakes in the calendar fallback data and the static HTML shell.

Usage:
    python build.py
"""
import json, os, re
from datetime import date

CURRENT_VER      = "May 2025"
UPGRADE_VER      = "November 2025"
UPGRADE_PRD_DATE = "2026-04-11"
UPGRADE_PRD_DISP = "April 11, 2026"
ENVS = ["PRD", "PSUP", "PSUP2", "REL", "TST", "POC", "MST", "PSUPLB", "MAP", "CVTST", "RPT", "SHD"]

BASE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(BASE, "dist")

def get_category(ra_type):
    if ra_type == "Licensing Change": return "licensing"
    if ra_type == "Special Update":  return "su"
    return "other"

def parse_prd_date(title):
    m = re.search(r'for PRD (?:on|by)\s+(\d{1,2})-(\d{1,2})-(\d{2,4})', title, re.IGNORECASE)
    if not m: return None
    month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if year < 100: year += 2000
    try: return date(year, month, day).isoformat()
    except ValueError: return None

def annotate(raw):
    result = []
    for ra in raw:
        r = dict(ra)
        r["cat"] = get_category(r["type"])
        r["prd_from_title"] = parse_prd_date(r["title"]) if r["type"] == "Special Update" else None
        result.append(r)
    return result

def build():
    os.makedirs(os.path.join(DIST, "calendar"), exist_ok=True)

    env_json = json.dumps(ENVS)

    # ── index.html — no data baked in, loads from GitLab at runtime ──────────
    html = (INDEX_TEMPLATE
            .replace("__ENVS__",             env_json)
            .replace("__CURRENT_VER__",      CURRENT_VER)
            .replace("__UPGRADE_VER__",      UPGRADE_VER)
            .replace("__UPGRADE_PRD_DATE__", UPGRADE_PRD_DATE)
            .replace("__UPGRADE_PRD_DISP__", UPGRADE_PRD_DISP))
    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    # ── calendar/index.html — bakes in current data as fallback, then fetches
    #    from GitLab on load for live data
    with open(os.path.join(BASE, "ra_data.json"), encoding="utf-8") as f:
        cal_data = annotate(json.load(f))
    today = date.today().isoformat()
    with open(os.path.join(BASE, "calendar_template.html"), encoding="utf-8") as f:
        cal = f.read()
    cal = (cal
           .replace("__RA_DATA__", json.dumps(cal_data))
           .replace("__TODAY__",   today)
           .replace('href="/"',         'href="../"')
           .replace('href="/calendar"', 'href="../calendar/"')
           .replace('const RA_DATA',    'let RA_DATA')
           .replace('</body>', CALENDAR_GL_SHIM + '\n</body>'))
    with open(os.path.join(DIST, "calendar", "index.html"), "w", encoding="utf-8") as f:
        f.write(cal)

    print(f"Built -> dist/")

# Injected into the calendar page to refresh data from GitLab silently
CALENDAR_GL_SHIM = """<script>
(async function() {
  try {
    const cfg = JSON.parse(localStorage.getItem('ra_gl_cfg') || 'null');
    if (!cfg) return;
    const r = await fetch(
      cfg.base + '/api/v4/projects/' + encodeURIComponent(cfg.project) +
      '/repository/files/' + encodeURIComponent('ra_data.json') + '/raw?ref=main',
      { headers: { 'PRIVATE-TOKEN': cfg.token } }
    );
    if (r.ok) { RA_DATA = await r.json(); init(); }
  } catch(e) { /* silent — baked-in data already rendered */ }
})();
</script>"""

# ── Main tracker HTML template ────────────────────────────────────────────────
INDEX_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SSM Health RA Tracker</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: #f0f2f5;
    color: #1a1a2e;
    font-size: 14px;
  }

  /* ── Sticky nav ── */
  header {
    background: #1a2b4a;
    color: #fff;
    padding: 0 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 56px;
    box-shadow: 0 2px 8px rgba(0,0,0,.35);
    position: sticky;
    top: 0;
    z-index: 100;
  }
  header .brand { display: flex; align-items: center; gap: 12px; }
  header .brand-icon {
    width: 32px; height: 32px;
    background: #e8501a; border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 15px; color: #fff; flex-shrink: 0;
  }
  header h1 { font-size: 17px; font-weight: 600; letter-spacing: .2px; }
  header .subtitle { font-size: 11px; color: #8faecf; margin-top: 1px; }
  header .meta { font-size: 12px; color: #8faecf; text-align: right; }
  .nav-link {
    color: #8faecf; text-decoration: none;
    font-size: 12px; font-weight: 500;
    padding: 5px 12px; border-radius: 5px;
    transition: background .15s, color .15s;
  }
  .nav-link:hover { background: rgba(255,255,255,.1); color: #fff; }
  .nav-link.active { background: rgba(255,255,255,.15); color: #fff; }

  /* ── Header buttons ── */
  .hdr-btn {
    display: flex; align-items: center; gap: 6px;
    border: none; border-radius: 5px;
    color: #fff; font-size: 12px; font-weight: 600;
    padding: 5px 12px; cursor: pointer;
    transition: background .15s, opacity .15s;
    white-space: nowrap;
  }
  .hdr-btn:disabled { opacity: .6; cursor: default; }
  .hdr-btn .spin {
    display: none; width: 12px; height: 12px;
    border: 2px solid rgba(255,255,255,.4);
    border-top-color: #fff; border-radius: 50%;
    animation: spin .7s linear infinite;
  }
  .hdr-btn.loading .spin { display: inline-block; }
  @keyframes spin { to { transform: rotate(360deg); } }

  #refresh-btn { background: #e8501a; }
  #refresh-btn:hover:not(:disabled) { background: #c94315; }

  #sync-btn { background: rgba(255,255,255,.12); }
  #sync-btn:hover:not(:disabled) { background: rgba(255,255,255,.2); }

  /* ── Settings gear ── */
  #cfg-btn {
    background: rgba(255,255,255,.1); border: none; border-radius: 5px;
    color: #8faecf; font-size: 16px; width: 30px; height: 30px;
    cursor: pointer; transition: background .15s, color .15s; line-height: 1;
  }
  #cfg-btn:hover { background: rgba(255,255,255,.2); color: #fff; }

  /* ── Sync status ── */
  .sync-status { font-size: 11px; white-space: nowrap; }
  .status-ok   { color: #86efac; }
  .status-busy { color: #93c5fd; }
  .status-err  { color: #fca5a5; }
  .status-warn { color: #fcd34d; }

  /* ── Config banner ── */
  .cfg-banner {
    background: #fffbeb; border-bottom: 1px solid #fcd34d;
    padding: 8px 28px; font-size: 12px; color: #78350f;
  }
  .cfg-banner a { color: #92400e; font-weight: 600; cursor: pointer; text-decoration: underline; }

  /* ── Config modal ── */
  .cfg-overlay {
    position: fixed; inset: 0;
    background: rgba(0,0,0,.45);
    display: flex; align-items: center; justify-content: center;
    z-index: 500;
  }
  .cfg-modal {
    background: #fff; border-radius: 10px;
    padding: 24px 28px; width: 480px; max-width: 95vw;
    box-shadow: 0 8px 32px rgba(0,0,0,.25);
  }
  .cfg-modal h3 { font-size: 15px; font-weight: 700; color: #1a2b4a; margin-bottom: 6px; }
  .cfg-modal > p { font-size: 12px; color: #6b7280; margin-bottom: 18px; line-height: 1.6; }
  .cfg-field { margin-bottom: 14px; }
  .cfg-field label {
    display: block; font-size: 11px; font-weight: 700;
    color: #374151; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 4px;
  }
  .cfg-field input {
    width: 100%; padding: 7px 10px;
    border: 1px solid #d1d5db; border-radius: 5px;
    font-size: 13px; outline: none; transition: border-color .15s; font-family: inherit;
  }
  .cfg-field input:focus { border-color: #1a6bc5; box-shadow: 0 0 0 2px rgba(26,107,197,.15); }
  .cfg-field small { font-size: 11px; color: #9ca3af; display: block; margin-top: 4px; line-height: 1.4; }
  .cfg-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
  .cfg-actions button {
    padding: 7px 18px; border-radius: 5px; font-size: 13px; font-weight: 600;
    cursor: pointer; border: 1px solid #d1d5db; background: #fff; color: #374151;
    transition: background .15s;
  }
  .cfg-actions button.primary { background: #1a2b4a; color: #fff; border-color: #1a2b4a; }
  .cfg-actions button.primary:hover { background: #243d6a; }
  .cfg-error { font-size: 12px; color: #dc2626; margin-top: 12px; display: none; }

  .hidden { display: none !important; }

  /* ── Layout ── */
  main { max-width: 1400px; margin: 0 auto; padding: 20px 20px 60px; display: flex; flex-direction: column; gap: 24px; }

  /* ── Section header ── */
  .section-hdr {
    display: flex; align-items: baseline; gap: 10px;
    padding: 0 4px 8px; border-bottom: 2px solid #1a2b4a; margin-bottom: 0;
  }
  .section-hdr h2 { font-size: 15px; font-weight: 700; color: #1a2b4a; letter-spacing: .1px; }
  .section-cnt {
    background: #1a2b4a; color: #fff;
    font-size: 11px; font-weight: 700; padding: 1px 8px; border-radius: 10px;
  }
  .ver-chip { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; vertical-align: middle; }
  .ver-chip-current { background: #dbeafe; color: #1e40af; }
  .ver-chip-upgrade { background: #fef3c7; color: #92400e; }
  .upg-date-note { font-size: 11px; color: #6b7280; font-weight: 400; margin-left: 4px; }

  /* ── Card ── */
  .card {
    background: #fff; border-radius: 0 0 10px 10px;
    box-shadow: 0 1px 5px rgba(0,0,0,.07), 0 3px 12px rgba(0,0,0,.05); overflow: clip;
  }

  /* ── Table ── */
  table { width: 100%; border-collapse: collapse; }
  thead th {
    background: #f7f8fb; color: #4a5568; font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .6px; padding: 9px 12px;
    text-align: left; border-bottom: 1px solid #e2e6ee; white-space: nowrap;
    position: sticky; top: 56px; z-index: 10;
  }
  tbody tr.ra-row { cursor: pointer; border-bottom: 1px solid #edf0f5; transition: background .1s; }
  tbody tr.ra-row:hover { background: #f5f7fb; }
  tbody tr.ra-row.open  { background: #eef2fa; }
  tbody td { padding: 9px 12px; vertical-align: middle; }

  .col-ra     { width: 90px;  white-space: nowrap; }
  .col-title  { min-width: 220px; }
  .col-owner  { width: 120px; white-space: nowrap; }
  .col-created{ width: 90px;  white-space: nowrap; }
  .col-prd    { width: 100px; white-space: nowrap; }
  .col-envs   { width: 180px; }
  .col-notes  { width: 170px; }
  .col-save   { width: 58px;  text-align: center; }

  .ra-link { color: #1a6bc5; text-decoration: none; font-weight: 600; font-size: 13px; }
  .ra-link:hover { text-decoration: underline; }
  .pastdue-icon { display: inline-block; font-size: 13px; margin-left: 5px; cursor: default; vertical-align: middle; line-height: 1; }
  .type-tag { font-size: 10px; color: #9ca3af; font-style: italic; }
  .owner-name { font-size: 12px; color: #374151; }
  .prd-preview { font-size: 12px; color: #374151; }
  .prd-default { font-size: 12px; color: #92400e; font-style: italic; }
  .prd-pastdue { font-size: 12px; color: #dc2626; font-weight: 600; }

  .env-pills { display: flex; flex-wrap: wrap; gap: 3px; }
  .ep { display: inline-block; font-size: 9px; font-weight: 700; padding: 2px 5px; border-radius: 3px; line-height: 1.3; white-space: nowrap; }
  .ep-done    { background: #d1fae5; color: #065f46; }
  .ep-pending { background: #fef9c3; color: #78350f; }
  .ep-failed  { background: #fee2e2; color: #7f1d1d; }
  .no-envs    { font-size: 11px; color: #d1d5db; }

  .notes-preview { font-size: 12px; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 160px; }
  .save-ind { font-size: 11px; font-weight: 600; color: #16a34a; opacity: 0; transition: opacity .3s; white-space: nowrap; }
  .save-ind.show { opacity: 1; }

  tr.expand-row { display: none; }
  tr.expand-row.open { display: table-row; }
  tr.expand-row td { background: #f0f4fc; border-bottom: 2px solid #c7d2e8; padding: 16px 18px 20px; }
  .expand-inner { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 28px; }
  .env-section h4, .notes-section h4 {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    color: #4a5568; letter-spacing: .6px; margin-bottom: 8px;
  }
  .env-grid { display: flex; flex-wrap: wrap; gap: 6px; }
  .env-item {
    display: flex; align-items: center; gap: 5px;
    background: #fff; border: 1px solid #d4dae8; border-radius: 5px;
    padding: 4px 8px; min-width: 148px; flex: 0 0 auto;
  }
  .env-item label { font-size: 10px; font-weight: 700; color: #4a5568; width: 50px; flex-shrink: 0; }
  .env-item input[type="date"] { border: none; background: transparent; font-size: 11px; color: #1a1a2e; outline: none; cursor: pointer; flex: 1; min-width: 0; }
  .env-item input[type="checkbox"] { accent-color: #1a6bc5; width: 13px; height: 13px; cursor: pointer; flex-shrink: 0; }
  .env-item.done-env { background: #f0fdf4; border-color: #86efac; }
  .env-item.done-env label { color: #16a34a; }

  .notes-section { display: flex; flex-direction: column; gap: 5px; }
  .notes-section textarea {
    width: 100%; height: 80px; border: 1px solid #c7d2e6; border-radius: 5px;
    padding: 7px 9px; font-size: 13px; font-family: inherit;
    resize: vertical; color: #1a1a2e; background: #fff;
    outline: none; transition: border-color .15s;
  }
  .notes-section textarea:focus { border-color: #1a6bc5; box-shadow: 0 0 0 2px rgba(26,107,197,.15); }

  .expand-footer { grid-column: 1 / -1; display: flex; align-items: center; justify-content: space-between; margin-top: 2px; }
  .last-updated { font-size: 10px; color: #8a96a8; font-style: italic; }
  .empty-row td { text-align: center; color: #9ca3af; padding: 24px; font-style: italic; font-size: 13px; }
</style>
</head>
<body>

<header>
  <div class="brand">
    <div class="brand-icon">RA</div>
    <div>
      <h1>SSM Health RA Tracker</h1>
      <div class="subtitle">Technical Coordinator &mdash; Request Activity Dashboard</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <a class="nav-link active" href="./">RA Tracker</a>
    <a class="nav-link" href="./calendar/">Calendar</a>
    <span id="sync-status" class="sync-status"></span>
    <button id="refresh-btn" class="hdr-btn" onclick="refreshData()">
      <span class="spin"></span>
      <span id="refresh-label">&#8593; Refresh Data</span>
    </button>
    <button id="sync-btn" class="hdr-btn" onclick="syncAll()">
      <span class="spin"></span>
      <span id="sync-label">&#8635; Sync</span>
    </button>
    <button id="cfg-btn" onclick="openCfg()" title="Configure GitLab">&#9881;</button>
  </div>
  <div class="meta">
    <div id="header-counts"></div>
    <div style="margin-top:2px;">Epic Systems</div>
  </div>
</header>

<div id="cfg-banner" class="cfg-banner hidden">
  &#9888; Not connected &mdash; <a onclick="openCfg()">configure GitLab</a> to load RA data and share notes with your team.
</div>

<main>
  <div>
    <div class="section-hdr">
      <h2>Special Updates <span class="ver-chip ver-chip-current">__CURRENT_VER__</span></h2>
      <span class="section-cnt" id="cnt-su-current">0</span>
    </div>
    <div class="card"><table>
      <thead><tr>
        <th class="col-ra">RA #</th><th class="col-title">Title</th>
        <th class="col-owner">Primary Owner</th><th class="col-created">Created</th>
        <th class="col-prd">PRD Date</th><th class="col-envs">Non-PRDs Installed</th>
        <th class="col-notes">Notes</th><th class="col-save"></th>
      </tr></thead>
      <tbody id="tbody-su-current"></tbody>
    </table></div>
  </div>

  <div>
    <div class="section-hdr">
      <h2>Special Updates <span class="ver-chip ver-chip-upgrade">__UPGRADE_VER__</span>
        <span class="upg-date-note">&#8594; PRD with upgrade &middot; __UPGRADE_PRD_DISP__</span>
      </h2>
      <span class="section-cnt" id="cnt-su-upgrade">0</span>
    </div>
    <div class="card"><table>
      <thead><tr>
        <th class="col-ra">RA #</th><th class="col-title">Title</th>
        <th class="col-owner">Primary Owner</th><th class="col-created">Created</th>
        <th class="col-prd">PRD Date</th><th class="col-envs">Non-PRDs Installed</th>
        <th class="col-notes">Notes</th><th class="col-save"></th>
      </tr></thead>
      <tbody id="tbody-su-upgrade"></tbody>
    </table></div>
  </div>

  <div>
    <div class="section-hdr">
      <h2>Licensing</h2>
      <span class="section-cnt" id="cnt-licensing">0</span>
    </div>
    <div class="card"><table>
      <thead><tr>
        <th class="col-ra">RA #</th><th class="col-title">Title</th>
        <th class="col-owner">Primary Owner</th><th class="col-created">Created</th>
        <th class="col-prd">PRD Date</th><th class="col-envs">Non-PRDs Installed</th>
        <th class="col-notes">Notes</th><th class="col-save"></th>
      </tr></thead>
      <tbody id="tbody-licensing"></tbody>
    </table></div>
  </div>

  <div>
    <div class="section-hdr">
      <h2>Other</h2>
      <span class="section-cnt" id="cnt-other">0</span>
    </div>
    <div class="card"><table>
      <thead><tr>
        <th class="col-ra">RA #</th><th class="col-title">Title / Type</th>
        <th class="col-owner">Primary Owner</th><th class="col-created">Created</th>
        <th class="col-prd">PRD Date</th><th class="col-envs">Non-PRDs Installed</th>
        <th class="col-notes">Notes</th><th class="col-save"></th>
      </tr></thead>
      <tbody id="tbody-other"></tbody>
    </table></div>
  </div>
</main>

<!-- ── Settings modal ── -->
<div id="cfg-overlay" class="cfg-overlay hidden" onclick="if(event.target===this)closeCfg()">
  <div class="cfg-modal">
    <h3>&#9881; GitLab Setup</h3>
    <p>RA data and notes are stored in a GitLab project so everyone always sees live data.
       Each person uses their own token but points to the <strong>same project</strong>.</p>
    <div class="cfg-field">
      <label>GitLab URL</label>
      <input id="cfg-base" type="url" value="https://gitlab.epic.com">
    </div>
    <div class="cfg-field">
      <label>Project path or numeric ID</label>
      <input id="cfg-project" placeholder="yourname/ra-dashboard-data">
      <small>Create any GitLab project and paste its path here. Share the same path with your colleague.</small>
    </div>
    <div class="cfg-field">
      <label>Your Personal Access Token</label>
      <input id="cfg-token" type="password" placeholder="glpat-xxxxxxxxxxxxxxxxxxxx">
      <small>GitLab &rarr; Profile &rarr; Access Tokens &rarr; create with <strong>api</strong> scope.
             Each person creates their own token to the shared project.</small>
    </div>
    <div id="cfg-error" class="cfg-error"></div>
    <div class="cfg-actions">
      <button onclick="closeCfg()">Cancel</button>
      <button class="primary" onclick="saveCfg()">Save &amp; Connect</button>
    </div>
  </div>
</div>

<script>
const ENVS             = __ENVS__;
const CURRENT_VER      = "__CURRENT_VER__";
const UPGRADE_VER      = "__UPGRADE_VER__";
const UPGRADE_PRD_DATE = "__UPGRADE_PRD_DATE__";
const TODAY            = new Date().toISOString().slice(0, 10);

// ── Helpers ───────────────────────────────────────────────────────────────────
function sherlockUrl(pkgId) {
  return `https://sherlock.epic.com/default.aspx?view=ra/home#cid=618&id=${pkgId}&rv=0`;
}
function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function formatOwner(name) {
  if (!name) return '\u2014';
  const parts = name.split(', ');
  if (parts.length === 2) {
    const last  = parts[0].charAt(0).toUpperCase() + parts[0].slice(1).toLowerCase();
    const first = parts[1].charAt(0).toUpperCase() + parts[1].slice(1).toLowerCase();
    return first + ' ' + last;
  }
  return name;
}
function envPillsHtml(envs) {
  if (!envs || Object.keys(envs).length === 0) return '<span class="no-envs">\u2014</span>';
  return Object.entries(envs).map(([name, status]) => {
    const cls = status === 'done' ? 'ep-done' : status === 'pending' ? 'ep-pending' : 'ep-failed';
    return `<span class="ep ${cls}">${escHtml(name)}</span>`;
  }).join('');
}

// ── GitLab backend ────────────────────────────────────────────────────────────
const GL_KEY = 'ra_gl_cfg';
function glConfig() {
  try { return JSON.parse(localStorage.getItem(GL_KEY) || 'null'); } catch { return null; }
}
function glSetConfig(cfg) { localStorage.setItem(GL_KEY, JSON.stringify(cfg)); }

function glRepoFileUrl(cfg, filename) {
  return `${cfg.base}/api/v4/projects/${encodeURIComponent(cfg.project)}/repository/files/${encodeURIComponent(filename)}`;
}

async function glFetchFile(cfg, filename) {
  const r = await fetch(glRepoFileUrl(cfg, filename) + '/raw?ref=main', {
    headers: { 'PRIVATE-TOKEN': cfg.token }
  });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`GitLab GET ${filename}: HTTP ${r.status}`);
  return await r.json();
}

async function glPushFile(cfg, filename, content, commitMsg) {
  const url  = glRepoFileUrl(cfg, filename);
  const body = { branch: 'main', content: JSON.stringify(content, null, 2), commit_message: commitMsg };
  const check = await fetch(url + '?ref=main', { headers: { 'PRIVATE-TOKEN': cfg.token } });
  const method = check.ok ? 'PUT' : 'POST';
  const r = await fetch(url, {
    method,
    headers: { 'PRIVATE-TOKEN': cfg.token, 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!r.ok) throw new Error(`GitLab ${method} ${filename}: HTTP ${r.status}`);
}

async function glLoadNotes(cfg)     { return await glFetchFile(cfg, 'ra_notes.json') || {}; }
async function glLoadData(cfg)      { return await glFetchFile(cfg, 'ra_data.json')  || []; }
async function glSaveNotes(cfg, d)  { await glPushFile(cfg, 'ra_notes.json', d, 'Update RA notes'); }
async function glSaveData(cfg, d)   { await glPushFile(cfg, 'ra_data.json',  d, 'Refresh RA data'); }

function setSyncStatus(state) {
  const el = document.getElementById('sync-status');
  if (!el) return;
  const map = {
    synced:       ['\u2713 Synced',     'sync-status status-ok'],
    syncing:      ['Loading\u2026',     'sync-status status-busy'],
    saving:       ['Saving\u2026',      'sync-status status-busy'],
    refreshing:   ['Refreshing\u2026',  'sync-status status-busy'],
    error:        ['\u26a0 Error',      'sync-status status-err'],
    unconfigured: ['Not configured',    'sync-status status-warn'],
  };
  const [text, cls] = map[state] || ['', 'sync-status'];
  el.textContent = text;
  el.className   = cls;
}

// ── State ─────────────────────────────────────────────────────────────────────
let RA_DATA    = [];
let notesData  = {};
let saveTimers = {};

// ── Render ────────────────────────────────────────────────────────────────────
function renderAll() {
  const suCurrent = RA_DATA.filter(r => r.cat === 'su' && !r.upgrade_ver);
  const suUpgrade = RA_DATA.filter(r => r.cat === 'su' &&  r.upgrade_ver);
  const licensing = RA_DATA.filter(r => r.cat === 'licensing');
  const other     = RA_DATA.filter(r => r.cat === 'other');

  document.getElementById('cnt-su-current').textContent = suCurrent.length;
  document.getElementById('cnt-su-upgrade').textContent = suUpgrade.length;
  document.getElementById('cnt-licensing').textContent  = licensing.length;
  document.getElementById('cnt-other').textContent      = other.length;
  document.getElementById('header-counts').textContent  =
    `${RA_DATA.length} RAs \u00b7 ${suCurrent.length + suUpgrade.length} SU \u00b7 ${licensing.length} Lic \u00b7 ${other.length} Other`;

  buildSection('tbody-su-current', suCurrent, '');
  buildSection('tbody-su-upgrade', suUpgrade, UPGRADE_PRD_DATE);
  buildSection('tbody-licensing',  licensing, '');
  buildSection('tbody-other',      other,     '');
}

function showLoadMsg(msg) {
  ['tbody-su-current','tbody-su-upgrade','tbody-licensing','tbody-other'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = `<tr class="empty-row"><td colspan="8">${msg}</td></tr>`;
  });
}

// ── Row builders (unchanged from original) ────────────────────────────────────
function appendRA(tbody, ra, defaultPrdDate) {
  const key   = String(ra.pkg_id);
  const saved = notesData[key] || {};

  const prdSaved    = saved['env_PRD_date'] || '';
  const prdFallback = ra.prd_from_title || defaultPrdDate || '';
  const prdDisplay  = prdSaved || prdFallback;

  const isPastDue = ra.prd_from_title && ra.prd_from_title < TODAY && !prdSaved;
  const prdClass  = isPastDue ? 'prd-pastdue' : (!prdSaved && prdFallback ? 'prd-default' : 'prd-preview');

  const tr = document.createElement('tr');
  tr.className = 'ra-row';
  tr.id = 'row-' + key;
  tr.innerHTML = `
    <td class="col-ra">
      <a class="ra-link" href="${sherlockUrl(ra.pkg_id)}" target="_blank" rel="noopener"
         onclick="event.stopPropagation()">RA ${ra.ra_num}</a>
      ${isPastDue ? '<span class="pastdue-icon" title="PRD date has passed \u2014 review to close">\u26a0</span>' : ''}
    </td>
    <td class="col-title">
      <div style="font-weight:500;line-height:1.35;">${escHtml(ra.title)}</div>
      <div class="type-tag">${escHtml(ra.type)}</div>
    </td>
    <td class="col-owner"><span class="owner-name">${escHtml(formatOwner(ra.primary_owner))}</span></td>
    <td class="col-created">${ra.created}</td>
    <td class="col-prd"><span class="${prdClass}" id="prd-prev-${key}">${escHtml(prdDisplay)}</span></td>
    <td class="col-envs"><div class="env-pills">${envPillsHtml(ra.envs)}</div></td>
    <td class="col-notes"><div class="notes-preview" id="notes-prev-${key}">${escHtml(saved.notes || '')}</div></td>
    <td class="col-save"><span class="save-ind" id="save-cell-${key}">Saved &#10003;</span></td>
  `;
  tr.addEventListener('click', () => toggleExpand(key));
  tbody.appendChild(tr);

  const exTr = document.createElement('tr');
  exTr.className = 'expand-row';
  exTr.id = 'expand-' + key;
  const exTd = document.createElement('td');
  exTd.colSpan = 8;
  exTd.innerHTML = buildExpandHTML(ra, saved, defaultPrdDate);
  exTr.appendChild(exTd);
  tbody.appendChild(exTr);
  wireExpandEvents(key, ra, defaultPrdDate);
}

function buildSection(tbodyId, rows, defaultPrdDate) {
  const tbody = document.getElementById(tbodyId);
  tbody.innerHTML = '';
  if (rows.length === 0) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="8">No records.</td></tr>';
    return;
  }
  rows.forEach(ra => appendRA(tbody, ra, defaultPrdDate || ''));
}

function buildExpandHTML(ra, saved, defaultPrdDate) {
  const key = String(ra.pkg_id);
  const prdDefault = ra.prd_from_title || defaultPrdDate || '';
  let envHtml = '';
  ENVS.forEach(env => {
    const savedDate = saved[`env_${env}_date`] || '';
    const dateVal   = savedDate || (env === 'PRD' && prdDefault ? prdDefault : '');
    const doneVal   = saved[`env_${env}_done`] ? 'checked' : '';
    const doneCls   = saved[`env_${env}_done`] ? ' done-env' : '';
    envHtml += `
      <div class="env-item${doneCls}" id="envitem-${key}-${env}">
        <label>${env}</label>
        <input type="date" id="envdate-${key}-${env}" value="${escHtml(dateVal)}">
        <input type="checkbox" id="envdone-${key}-${env}" ${doneVal}>
      </div>`;
  });
  const lastUp = saved.last_updated
    ? 'Last updated: ' + saved.last_updated.replace('T', ' ')
    : 'Not yet saved';
  return `
    <div class="expand-inner">
      <div class="env-section">
        <h4>Planned Environment Dates</h4>
        <div class="env-grid">${envHtml}</div>
      </div>
      <div class="notes-section">
        <h4>Notes</h4>
        <textarea id="notes-${key}" placeholder="Add notes&hellip;">${escHtml(saved.notes || '')}</textarea>
        <div class="expand-footer">
          <span class="last-updated" id="lastupdated-${key}">${lastUp}</span>
          <span class="save-ind" id="save-expand-${key}">Saved &#10003;</span>
        </div>
      </div>
    </div>`;
}

function wireExpandEvents(key, ra, defaultPrdDate) {
  const prdDefault = ra.prd_from_title || defaultPrdDate || '';
  ENVS.forEach(env => {
    const dateEl = document.getElementById(`envdate-${key}-${env}`);
    const doneEl = document.getElementById(`envdone-${key}-${env}`);
    if (dateEl) {
      dateEl.addEventListener('change', () => {
        updateEnvStyle(key, env); scheduleSave(key);
        if (env === 'PRD') {
          const prev = document.getElementById('prd-prev-' + key);
          if (prev) { prev.textContent = dateEl.value || prdDefault; prev.className = 'prd-preview'; }
        }
      });
    }
    if (doneEl) doneEl.addEventListener('change', () => { updateEnvStyle(key, env); scheduleSave(key); });
  });
  const notesEl = document.getElementById('notes-' + key);
  if (notesEl) {
    notesEl.addEventListener('blur', () => {
      const p = document.getElementById('notes-prev-' + key);
      if (p) p.textContent = notesEl.value;
      scheduleSave(key);
    });
    notesEl.addEventListener('input', () => scheduleSave(key));
  }
}

function updateEnvStyle(key, env) {
  const item   = document.getElementById(`envitem-${key}-${env}`);
  const doneEl = document.getElementById(`envdone-${key}-${env}`);
  if (!item || !doneEl) return;
  item.classList.toggle('done-env', doneEl.checked);
}

function toggleExpand(key) {
  const row = document.getElementById('row-' + key);
  const exp = document.getElementById('expand-' + key);
  if (!row || !exp) return;
  const open = exp.classList.contains('open');
  exp.classList.toggle('open', !open);
  row.classList.toggle('open', !open);
}

// ── Save (notes → GitLab, read-modify-write) ──────────────────────────────────
function scheduleSave(key) {
  if (saveTimers[key]) clearTimeout(saveTimers[key]);
  saveTimers[key] = setTimeout(() => doSave(key), 600);
}

async function doSave(key) {
  const payload = {};
  ENVS.forEach(env => {
    const d = document.getElementById(`envdate-${key}-${env}`);
    const c = document.getElementById(`envdone-${key}-${env}`);
    if (d) payload[`env_${env}_date`] = d.value;
    if (c) payload[`env_${env}_done`] = c.checked;
  });
  const n = document.getElementById('notes-' + key);
  if (n) payload.notes = n.value;

  if (!notesData[key]) notesData[key] = {};
  Object.assign(notesData[key], payload);
  const ts = new Date().toISOString().slice(0, 19);
  notesData[key].last_updated = ts;

  const lu = document.getElementById('lastupdated-' + key);
  if (lu) lu.textContent = 'Last updated: ' + ts.replace('T', ' ');
  flashSaved(key);

  const cfg = glConfig();
  if (!cfg) return;
  setSyncStatus('saving');
  try {
    let remote = {};
    try { remote = await glLoadNotes(cfg); } catch { /* use empty */ }
    remote[key] = notesData[key];
    Object.assign(notesData, remote);
    await glSaveNotes(cfg, remote);
    setSyncStatus('synced');
  } catch(e) {
    setSyncStatus('error');
    console.error('Notes save failed', key, e);
  }
}

function flashSaved(key) {
  ['save-cell-', 'save-expand-'].forEach(prefix => {
    const el = document.getElementById(prefix + key);
    if (!el) return;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 2000);
  });
}

// ── Refresh Data (runs local helper → pushes new data to GitLab) ──────────────
async function refreshData() {
  const cfg = glConfig();
  if (!cfg) { openCfg(); return; }

  const btn   = document.getElementById('refresh-btn');
  const label = document.getElementById('refresh-label');
  btn.disabled = true;
  btn.classList.add('loading');
  label.textContent = 'Refreshing\u2026';
  setSyncStatus('refreshing');

  try {
    // 1. Call local helper (runs Update-RAData.ps1)
    let helperResp;
    try {
      helperResp = await fetch('http://localhost:7474/refresh', { method: 'POST' });
    } catch {
      alert(
        'Could not reach the local RA helper.\n\n' +
        'Run Start-RAHelper.ps1 first, then try again.\n\n' +
        'The helper is a small local server that runs Update-RAData.ps1 ' +
        'and returns fresh data for the site to push to GitLab.'
      );
      setSyncStatus('error');
      return;
    }

    if (!helperResp.ok) {
      const err = await helperResp.json().catch(() => ({}));
      alert('Refresh failed:\n' + (err.error || `HTTP ${helperResp.status}`));
      setSyncStatus('error');
      return;
    }

    const { data, count } = await helperResp.json();

    // 2. Push fresh data to GitLab
    await glSaveData(cfg, data);

    // 3. Update local state and re-render
    RA_DATA = data;
    renderAll();

    label.textContent = `\u2713 ${count} RAs`;
    setSyncStatus('synced');
    setTimeout(() => { label.textContent = '\u2191 Refresh Data'; }, 3000);

  } catch(e) {
    setSyncStatus('error');
    console.error('Refresh failed:', e);
    alert('Refresh failed: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}

// ── Sync (pull latest data + notes from GitLab) ───────────────────────────────
async function syncAll() {
  const cfg = glConfig();
  if (!cfg) { openCfg(); return; }

  const btn   = document.getElementById('sync-btn');
  const label = document.getElementById('sync-label');
  btn.disabled = true;
  btn.classList.add('loading');
  label.textContent = 'Syncing\u2026';
  setSyncStatus('syncing');

  try {
    const [raData, notes] = await Promise.all([glLoadData(cfg), glLoadNotes(cfg)]);
    if (raData.length > 0) RA_DATA = raData;
    Object.assign(notesData, notes);
    renderAll();
    setSyncStatus('synced');
  } catch(e) {
    setSyncStatus('error');
    console.error('Sync failed:', e);
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
    label.textContent = '\u21bb Sync';
  }
}

// ── Settings modal ────────────────────────────────────────────────────────────
function openCfg() {
  const cfg = glConfig() || {};
  document.getElementById('cfg-base').value    = cfg.base    || 'https://gitlab.epic.com';
  document.getElementById('cfg-project').value = cfg.project || '';
  document.getElementById('cfg-token').value   = cfg.token   || '';
  document.getElementById('cfg-error').style.display = 'none';
  document.getElementById('cfg-overlay').classList.remove('hidden');
}
function closeCfg() { document.getElementById('cfg-overlay').classList.add('hidden'); }

async function saveCfg() {
  const cfg = {
    base:    document.getElementById('cfg-base').value.trim().replace(/\/$/, ''),
    project: document.getElementById('cfg-project').value.trim(),
    token:   document.getElementById('cfg-token').value.trim(),
  };
  const errEl = document.getElementById('cfg-error');
  errEl.style.display = 'none';
  if (!cfg.base || !cfg.project || !cfg.token) {
    errEl.textContent = 'All fields are required.';
    errEl.style.display = 'block';
    return;
  }
  glSetConfig(cfg);
  closeCfg();
  document.getElementById('cfg-banner').classList.add('hidden');
  setSyncStatus('syncing');
  try {
    const [raData, notes] = await Promise.all([glLoadData(cfg), glLoadNotes(cfg)]);
    RA_DATA   = raData;
    notesData = notes;
    if (RA_DATA.length > 0) {
      renderAll();
    } else {
      showLoadMsg('No data yet \u2014 click \u2191 Refresh Data to load from Track.');
    }
    setSyncStatus('synced');
  } catch(e) {
    setSyncStatus('error');
    console.error('GitLab connect failed:', e);
    alert(
      'Could not connect to GitLab.\n\nError: ' + e.message +
      '\n\nCheck:\n  \u2022 Token has "api" scope\n  \u2022 Project path is correct\n  \u2022 You are on the Epic network (or VPN)'
    );
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  const cfg = glConfig();
  if (!cfg) {
    setSyncStatus('unconfigured');
    document.getElementById('cfg-banner').classList.remove('hidden');
    showLoadMsg('Configure GitLab (\u2699) to load RA data.');
    return;
  }
  setSyncStatus('syncing');
  try {
    const [raData, notes] = await Promise.all([glLoadData(cfg), glLoadNotes(cfg)]);
    RA_DATA   = raData;
    notesData = notes;
    if (RA_DATA.length > 0) {
      renderAll();
    } else {
      showLoadMsg('No data yet \u2014 click \u2191 Refresh Data to load from Track.');
    }
    setSyncStatus('synced');
  } catch(e) {
    setSyncStatus('error');
    showLoadMsg('Could not load data from GitLab. Check your settings (\u2699) and network.');
    console.error('Init failed:', e);
  }
}

init();
</script>
</body>
</html>"""

if __name__ == "__main__":
    build()
