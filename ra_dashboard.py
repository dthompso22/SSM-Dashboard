from flask import Flask, jsonify, request
import json
import os
import re
from datetime import datetime, date

app = Flask(__name__)

CURRENT_VER      = "May 2025"
UPGRADE_VER      = "November 2025"
UPGRADE_PRD_DATE = "2026-04-11"
UPGRADE_PRD_DISP = "April 11, 2026"

NOTES_FILE        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ra_notes.json")
RA_DATA_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ra_data.json")
CALENDAR_TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calendar_template.html")

def load_ra_data():
    with open(RA_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

ENVS = ["PRD", "PSUP", "PSUP2", "REL", "TST", "POC", "MST", "PSUPLB", "MAP", "CVTST", "RPT", "SHD"]

def get_category(ra_type):
    if ra_type == "Licensing Change":
        return "licensing"
    elif ra_type == "Special Update":
        return "su"
    else:
        return "other"

def parse_prd_date(title):
    """Extract PRD date from SU titles like 'for PRD on 3-4-26' or 'for PRD by 12-31-2025'.
    Returns ISO date string (YYYY-MM-DD) or None."""
    m = re.search(r'for PRD (?:on|by)\s+(\d{1,2})-(\d{1,2})-(\d{2,4})', title, re.IGNORECASE)
    if not m:
        return None
    month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if year < 100:
        year += 2000
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None

def load_notes():
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_notes(data):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@app.route("/api/notes", methods=["GET"])
def api_get_notes():
    return jsonify(load_notes())

@app.route("/api/notes/<int:pkg_id>", methods=["POST"])
def api_save_notes(pkg_id):
    notes = load_notes()
    payload = request.get_json(force=True)
    key = str(pkg_id)
    if key not in notes:
        notes[key] = {}
    notes[key].update(payload)
    notes[key]["last_updated"] = datetime.now().isoformat(timespec="seconds")
    save_notes(notes)
    return jsonify({"status": "ok", "last_updated": notes[key]["last_updated"]})

HTML_TEMPLATE = r"""<!DOCTYPE html>
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

  /* ── Layout ── */
  main { max-width: 1400px; margin: 0 auto; padding: 20px 20px 60px; display: flex; flex-direction: column; gap: 24px; }

  /* ── Section header ── */
  .section-hdr {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 0 4px 8px;
    border-bottom: 2px solid #1a2b4a;
    margin-bottom: 0;
  }
  .section-hdr h2 {
    font-size: 15px;
    font-weight: 700;
    color: #1a2b4a;
    letter-spacing: .1px;
  }
  .section-cnt {
    background: #1a2b4a;
    color: #fff;
    font-size: 11px;
    font-weight: 700;
    padding: 1px 8px;
    border-radius: 10px;
  }
  .ver-chip {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    vertical-align: middle;
  }
  .ver-chip-current { background: #dbeafe; color: #1e40af; }
  .ver-chip-upgrade { background: #fef3c7; color: #92400e; }
  .upg-date-note {
    font-size: 11px;
    color: #6b7280;
    font-weight: 400;
    margin-left: 4px;
  }

  /* ── Card ── */
  .card {
    background: #fff;
    border-radius: 0 0 10px 10px;
    box-shadow: 0 1px 5px rgba(0,0,0,.07), 0 3px 12px rgba(0,0,0,.05);
    overflow: clip;
  }

  /* ── Table ── */
  table { width: 100%; border-collapse: collapse; }
  thead th {
    background: #f7f8fb;
    color: #4a5568;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .6px;
    padding: 9px 12px;
    text-align: left;
    border-bottom: 1px solid #e2e6ee;
    white-space: nowrap;
    position: sticky;
    top: 56px;
    z-index: 10;
  }

  tbody tr.ra-row {
    cursor: pointer;
    border-bottom: 1px solid #edf0f5;
    transition: background .1s;
  }
  tbody tr.ra-row:hover { background: #f5f7fb; }
  tbody tr.ra-row.open  { background: #eef2fa; }
  tbody td {
    padding: 9px 12px;
    vertical-align: middle;
  }

  /* column widths */
  .col-ra     { width: 90px;  white-space: nowrap; }
  .col-title  { min-width: 220px; }
  .col-owner  { width: 120px; white-space: nowrap; }
  .col-created{ width: 90px;  white-space: nowrap; }
  .col-prd    { width: 100px; white-space: nowrap; }
  .col-envs   { width: 180px; }
  .col-notes  { width: 170px; }
  .col-save   { width: 58px;  text-align: center; }

  .ra-link {
    color: #1a6bc5; text-decoration: none;
    font-weight: 600; font-size: 13px;
  }
  .ra-link:hover { text-decoration: underline; }

  /* Past-due warning icon */
  .pastdue-icon {
    display: inline-block;
    font-size: 13px;
    margin-left: 5px;
    cursor: default;
    vertical-align: middle;
    line-height: 1;
  }

  .type-tag { font-size: 10px; color: #9ca3af; font-style: italic; }
  .owner-name { font-size: 12px; color: #374151; }
  .prd-preview { font-size: 12px; color: #374151; }
  .prd-default { font-size: 12px; color: #92400e; font-style: italic; }
  .prd-pastdue { font-size: 12px; color: #dc2626; font-weight: 600; }

  /* ── Env pills (Non-PRDs column) ── */
  .env-pills { display: flex; flex-wrap: wrap; gap: 3px; }
  .ep {
    display: inline-block;
    font-size: 9px; font-weight: 700;
    padding: 2px 5px; border-radius: 3px;
    line-height: 1.3; white-space: nowrap;
  }
  .ep-done    { background: #d1fae5; color: #065f46; }
  .ep-pending { background: #fef9c3; color: #78350f; }
  .ep-failed  { background: #fee2e2; color: #7f1d1d; }
  .no-envs    { font-size: 11px; color: #d1d5db; }

  /* ── Notes preview ── */
  .notes-preview {
    font-size: 12px; color: #64748b;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    max-width: 160px;
  }

  /* ── Save indicator ── */
  .save-ind {
    font-size: 11px; font-weight: 600; color: #16a34a;
    opacity: 0; transition: opacity .3s; white-space: nowrap;
  }
  .save-ind.show { opacity: 1; }

  /* ── Expand row ── */
  tr.expand-row { display: none; }
  tr.expand-row.open { display: table-row; }
  tr.expand-row td {
    background: #f0f4fc;
    border-bottom: 2px solid #c7d2e8;
    padding: 16px 18px 20px;
  }
  .expand-inner {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px 28px;
  }
  .env-section h4, .notes-section h4 {
    font-size: 10px; font-weight: 700;
    text-transform: uppercase; color: #4a5568;
    letter-spacing: .6px; margin-bottom: 8px;
  }
  .env-grid { display: flex; flex-wrap: wrap; gap: 6px; }
  .env-item {
    display: flex; align-items: center; gap: 5px;
    background: #fff; border: 1px solid #d4dae8;
    border-radius: 5px; padding: 4px 8px;
    min-width: 148px; flex: 0 0 auto;
  }
  .env-item label {
    font-size: 10px; font-weight: 700; color: #4a5568;
    width: 50px; flex-shrink: 0;
  }
  .env-item input[type="date"] {
    border: none; background: transparent;
    font-size: 11px; color: #1a1a2e;
    outline: none; cursor: pointer; flex: 1; min-width: 0;
  }
  .env-item input[type="checkbox"] {
    accent-color: #1a6bc5; width: 13px; height: 13px;
    cursor: pointer; flex-shrink: 0;
  }
  .env-item.done-env { background: #f0fdf4; border-color: #86efac; }
  .env-item.done-env label { color: #16a34a; }

  .notes-section { display: flex; flex-direction: column; gap: 5px; }
  .notes-section textarea {
    width: 100%; height: 80px;
    border: 1px solid #c7d2e6; border-radius: 5px;
    padding: 7px 9px; font-size: 13px; font-family: inherit;
    resize: vertical; color: #1a1a2e; background: #fff;
    outline: none; transition: border-color .15s;
  }
  .notes-section textarea:focus { border-color: #1a6bc5; box-shadow: 0 0 0 2px rgba(26,107,197,.15); }

  .expand-footer {
    grid-column: 1 / -1;
    display: flex; align-items: center; justify-content: space-between;
    margin-top: 2px;
  }
  .last-updated { font-size: 10px; color: #8a96a8; font-style: italic; }

  /* empty */
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
  <div style="display:flex;gap:4px;">
    <a class="nav-link active" href="/">RA Tracker</a>
    <a class="nav-link" href="/calendar">Calendar</a>
  </div>
  <div class="meta">
    <div id="header-counts"></div>
    <div style="margin-top:2px;">Epic Systems</div>
  </div>
</header>

<main>

  <!-- Special Updates — Current Version -->
  <div>
    <div class="section-hdr">
      <h2>Special Updates <span class="ver-chip ver-chip-current">__CURRENT_VER__</span></h2>
      <span class="section-cnt" id="cnt-su-current">0</span>
    </div>
    <div class="card">
      <table>
        <thead><tr>
          <th class="col-ra">RA #</th>
          <th class="col-title">Title</th>
          <th class="col-owner">Primary Owner</th>
          <th class="col-created">Created</th>
          <th class="col-prd">PRD Date</th>
          <th class="col-envs">Non-PRDs Installed</th>
          <th class="col-notes">Notes</th>
          <th class="col-save"></th>
        </tr></thead>
        <tbody id="tbody-su-current"></tbody>
      </table>
    </div>
  </div>

  <!-- Special Updates — Upgrade Version -->
  <div>
    <div class="section-hdr">
      <h2>Special Updates <span class="ver-chip ver-chip-upgrade">__UPGRADE_VER__</span>
        <span class="upg-date-note">&#8594; PRD with upgrade &middot; __UPGRADE_PRD_DISP__</span>
      </h2>
      <span class="section-cnt" id="cnt-su-upgrade">0</span>
    </div>
    <div class="card">
      <table>
        <thead><tr>
          <th class="col-ra">RA #</th>
          <th class="col-title">Title</th>
          <th class="col-owner">Primary Owner</th>
          <th class="col-created">Created</th>
          <th class="col-prd">PRD Date</th>
          <th class="col-envs">Non-PRDs Installed</th>
          <th class="col-notes">Notes</th>
          <th class="col-save"></th>
        </tr></thead>
        <tbody id="tbody-su-upgrade"></tbody>
      </table>
    </div>
  </div>

  <!-- Licensing -->
  <div>
    <div class="section-hdr">
      <h2>Licensing</h2>
      <span class="section-cnt" id="cnt-licensing">0</span>
    </div>
    <div class="card">
      <table>
        <thead><tr>
          <th class="col-ra">RA #</th>
          <th class="col-title">Title</th>
          <th class="col-owner">Primary Owner</th>
          <th class="col-created">Created</th>
          <th class="col-prd">PRD Date</th>
          <th class="col-envs">Non-PRDs Installed</th>
          <th class="col-notes">Notes</th>
          <th class="col-save"></th>
        </tr></thead>
        <tbody id="tbody-licensing"></tbody>
      </table>
    </div>
  </div>

  <!-- Other -->
  <div>
    <div class="section-hdr">
      <h2>Other</h2>
      <span class="section-cnt" id="cnt-other">0</span>
    </div>
    <div class="card">
      <table>
        <thead><tr>
          <th class="col-ra">RA #</th>
          <th class="col-title">Title / Type</th>
          <th class="col-owner">Primary Owner</th>
          <th class="col-created">Created</th>
          <th class="col-prd">PRD Date</th>
          <th class="col-envs">Non-PRDs Installed</th>
          <th class="col-notes">Notes</th>
          <th class="col-save"></th>
        </tr></thead>
        <tbody id="tbody-other"></tbody>
      </table>
    </div>
  </div>

</main>

<script>
const RA_DATA         = __RA_DATA__;
const ENVS            = __ENVS__;
const CURRENT_VER     = "__CURRENT_VER__";
const UPGRADE_VER     = "__UPGRADE_VER__";
const UPGRADE_PRD_DATE = "__UPGRADE_PRD_DATE__";
const TODAY           = "__TODAY__";

// ── Helpers ───────────────────────────────────────────────────────────────────
function sherlockUrl(pkgId) {
  return `https://sherlock.epic.com/default.aspx?view=ra/home#cid=618&id=${pkgId}&rv=0`;
}

function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// "THOMPSON, DAVID" → "David Thompson"
function formatOwner(name) {
  if (!name) return '—';
  const parts = name.split(', ');
  if (parts.length === 2) {
    const last  = parts[0].charAt(0).toUpperCase() + parts[0].slice(1).toLowerCase();
    const first = parts[1].charAt(0).toUpperCase() + parts[1].slice(1).toLowerCase();
    return first + ' ' + last;
  }
  return name;
}

// Build compact env pills from ra.envs dict
function envPillsHtml(envs) {
  if (!envs || Object.keys(envs).length === 0) {
    return '<span class="no-envs">—</span>';
  }
  return Object.entries(envs).map(([name, status]) => {
    const cls = status === 'done' ? 'ep-done' : status === 'pending' ? 'ep-pending' : 'ep-failed';
    return `<span class="ep ${cls}">${escHtml(name)}</span>`;
  }).join('');
}

// ── State ─────────────────────────────────────────────────────────────────────
let notesData  = {};
let saveTimers = {};

// ── Core row builder ──────────────────────────────────────────────────────────
function appendRA(tbody, ra, defaultPrdDate) {
  const key   = String(ra.pkg_id);
  const saved = notesData[key] || {};

  // PRD date: saved user entry > title-parsed date > section default
  const prdSaved    = saved['env_PRD_date'] || '';
  const prdFallback = ra.prd_from_title || defaultPrdDate || '';
  const prdDisplay  = prdSaved || prdFallback;

  // Past-due: only flag when the title-parsed date exists and is before today
  const isPastDue = ra.prd_from_title && ra.prd_from_title < TODAY && !prdSaved;
  const prdClass  = isPastDue
    ? 'prd-pastdue'
    : (!prdSaved && prdFallback ? 'prd-default' : 'prd-preview');

  const notesPrev  = escHtml(saved.notes || '');
  const ownerFmt   = escHtml(formatOwner(ra.primary_owner));

  const pastDueHtml = isPastDue
    ? `<span class="pastdue-icon" title="PRD date has passed — review to close">&#9888;</span>`
    : '';

  const tr = document.createElement('tr');
  tr.className = 'ra-row';
  tr.id = 'row-' + key;

  tr.innerHTML = `
    <td class="col-ra">
      <a class="ra-link" href="${sherlockUrl(ra.pkg_id)}" target="_blank" rel="noopener"
         onclick="event.stopPropagation()">RA ${ra.ra_num}</a>${pastDueHtml}
    </td>
    <td class="col-title">
      <div style="font-weight:500;line-height:1.35;">${escHtml(ra.title)}</div>
      <div class="type-tag">${escHtml(ra.type)}</div>
    </td>
    <td class="col-owner"><span class="owner-name">${ownerFmt}</span></td>
    <td class="col-created">${ra.created}</td>
    <td class="col-prd"><span class="${prdClass}" id="prd-prev-${key}">${escHtml(prdDisplay)}</span></td>
    <td class="col-envs"><div class="env-pills">${envPillsHtml(ra.envs)}</div></td>
    <td class="col-notes"><div class="notes-preview" id="notes-prev-${key}">${notesPrev}</div></td>
    <td class="col-save"><span class="save-ind" id="save-cell-${key}">Saved &#10003;</span></td>
  `;
  tr.addEventListener('click', () => toggleExpand(key));
  tbody.appendChild(tr);

  // Expand row
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

// ── Build section ─────────────────────────────────────────────────────────────
function buildSection(tbodyId, rows, defaultPrdDate) {
  const tbody = document.getElementById(tbodyId);
  tbody.innerHTML = '';
  if (rows.length === 0) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="8">No records.</td></tr>';
    return;
  }
  rows.forEach(ra => appendRA(tbody, ra, defaultPrdDate || ''));
}

// ── Expand row HTML ───────────────────────────────────────────────────────────
function buildExpandHTML(ra, saved, defaultPrdDate) {
  const key = String(ra.pkg_id);
  // PRD defaults: prefer title-parsed date over section default
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

  const notesVal = escHtml(saved.notes || '');
  const lastUp   = saved.last_updated
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
        <textarea id="notes-${key}" placeholder="Add notes&hellip;">${notesVal}</textarea>
        <div class="expand-footer">
          <span class="last-updated" id="lastupdated-${key}">${lastUp}</span>
          <span class="save-ind" id="save-expand-${key}">Saved &#10003;</span>
        </div>
      </div>
    </div>`;
}

// ── Expand events ─────────────────────────────────────────────────────────────
function wireExpandEvents(key, ra, defaultPrdDate) {
  const prdDefault = ra.prd_from_title || defaultPrdDate || '';
  ENVS.forEach(env => {
    const dateEl = document.getElementById(`envdate-${key}-${env}`);
    const doneEl = document.getElementById(`envdone-${key}-${env}`);
    if (dateEl) {
      dateEl.addEventListener('change', () => {
        updateEnvStyle(key, env);
        scheduleSave(key);
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

// ── Save ──────────────────────────────────────────────────────────────────────
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

  try {
    const resp = await fetch(`/api/notes/${key}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();
    if (!notesData[key]) notesData[key] = {};
    Object.assign(notesData[key], payload);
    notesData[key].last_updated = data.last_updated;
    const lu = document.getElementById('lastupdated-' + key);
    if (lu) lu.textContent = 'Last updated: ' + data.last_updated.replace('T', ' ');
    flashSaved(key);
  } catch (err) { console.error('Save failed', key, err); }
}

function flashSaved(key) {
  ['save-cell-', 'save-expand-'].forEach(prefix => {
    const el = document.getElementById(prefix + key);
    if (!el) return;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 2000);
  });
}

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  try {
    const r = await fetch('/api/notes');
    if (r.ok) notesData = await r.json();
  } catch (e) { console.warn('Could not load notes:', e); }

  const suCurrent = RA_DATA.filter(r => r.cat === 'su' && !r.upgrade_ver);
  const suUpgrade = RA_DATA.filter(r => r.cat === 'su' &&  r.upgrade_ver);
  const licensing = RA_DATA.filter(r => r.cat === 'licensing');
  const other     = RA_DATA.filter(r => r.cat === 'other');

  document.getElementById('cnt-su-current').textContent = suCurrent.length;
  document.getElementById('cnt-su-upgrade').textContent = suUpgrade.length;
  document.getElementById('cnt-licensing').textContent  = licensing.length;
  document.getElementById('cnt-other').textContent      = other.length;
  document.getElementById('header-counts').textContent  =
    `${RA_DATA.length} RAs · ${suCurrent.length + suUpgrade.length} SU · ${licensing.length} Lic · ${other.length} Other`;

  buildSection('tbody-su-current', suCurrent, '');
  buildSection('tbody-su-upgrade', suUpgrade, UPGRADE_PRD_DATE);
  buildSection('tbody-licensing',  licensing,  '');
  buildSection('tbody-other',      other,      '');
}

init();
</script>
</body>
</html>"""

@app.route("/")
def index():
    today_str = date.today().isoformat()
    annotated = []
    for ra in load_ra_data():
        r = dict(ra)
        r["cat"] = get_category(r["type"])
        if r["type"] == "Special Update":
            r["prd_from_title"] = parse_prd_date(r["title"])
        else:
            r["prd_from_title"] = None
        annotated.append(r)

    import json as _json
    ra_json   = _json.dumps(annotated)
    envs_json = _json.dumps(ENVS)

    html = (HTML_TEMPLATE
            .replace("__RA_DATA__", ra_json)
            .replace("__ENVS__", envs_json)
            .replace("__CURRENT_VER__", CURRENT_VER)
            .replace("__UPGRADE_VER__", UPGRADE_VER)
            .replace("__UPGRADE_PRD_DATE__", UPGRADE_PRD_DATE)
            .replace("__UPGRADE_PRD_DISP__", UPGRADE_PRD_DISP)
            .replace("__TODAY__", today_str))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route("/calendar")
def calendar():
    today_str = date.today().isoformat()
    annotated = []
    for ra in load_ra_data():
        r = dict(ra)
        r["cat"] = get_category(r["type"])
        if r["type"] == "Special Update":
            r["prd_from_title"] = parse_prd_date(r["title"])
        else:
            r["prd_from_title"] = None
        annotated.append(r)

    import json as _json
    ra_json = _json.dumps(annotated)

    with open(CALENDAR_TEMPLATE, "r", encoding="utf-8") as f:
        tmpl = f.read()

    html = (tmpl
            .replace("__RA_DATA__", ra_json)
            .replace("__TODAY__", today_str))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)
