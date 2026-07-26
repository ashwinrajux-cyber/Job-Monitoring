"""
Renders a single self-contained static HTML dashboard (docs/index.html) from
the current DB state. No backend needed - all search/filtering happens
client-side over an embedded JSON payload, so this can be served for free via
GitHub Pages.
"""
import json
from datetime import datetime, timedelta, timezone

from job_monitor.storage import db

IST = timezone(timedelta(hours=5, minutes=30))

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job Monitor Dashboard</title>
<style>
:root {
  color-scheme: light;
  --surface-1: #fcfcfb;
  --page: #f9f9f7;
  --text-primary: #0b0b0b;
  --text-secondary: #52514e;
  --muted: #898781;
  --grid: #e1e0d9;
  --border: rgba(11,11,11,0.10);
  --good: #0ca30c;
  --warning: #fab219;
  --critical: #d03b3b;
  --series-1: #2a78d6;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --surface-1: #1a1a19;
    --page: #0d0d0d;
    --text-primary: #ffffff;
    --text-secondary: #c3c2b7;
    --muted: #898781;
    --grid: #2c2c2a;
    --border: rgba(255,255,255,0.10);
    --good: #0ca30c;
    --warning: #fab219;
    --critical: #e66767;
    --series-1: #3987e5;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-1: #1a1a19;
  --page: #0d0d0d;
  --text-primary: #ffffff;
  --text-secondary: #c3c2b7;
  --muted: #898781;
  --grid: #2c2c2a;
  --border: rgba(255,255,255,0.10);
  --good: #0ca30c;
  --warning: #fab219;
  --critical: #e66767;
  --series-1: #3987e5;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--page);
  color: var(--text-primary);
  padding: 24px;
}
h1 { font-size: 20px; margin: 0 0 4px; }
.subtitle { color: var(--text-secondary); font-size: 13px; margin-bottom: 24px; }
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 28px;
}
.tile {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
}
.tile .value { font-size: 26px; font-weight: 600; line-height: 1.2; }
.tile .label { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
.tile.accent .value { color: var(--series-1); }
.tile.crit .value { color: var(--critical); }
section {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 20px;
}
section h2 { font-size: 15px; margin: 0 0 12px; }
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.filters input, .filters select {
  background: var(--page);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
}
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--grid);
  white-space: nowrap;
}
th { color: var(--text-secondary); font-weight: 500; font-size: 12px; }
tr:last-child td { border-bottom: none; }
a { color: var(--series-1); text-decoration: none; }
a:hover { text-decoration: underline; }
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border);
}
.badge.ok { color: var(--good); }
.badge.error { color: var(--critical); }
.badge.never_run { color: var(--muted); }
.empty { color: var(--muted); font-size: 13px; padding: 12px 0; }
footer { color: var(--muted); font-size: 12px; margin-top: 8px; }
.manage-note {
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--page);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
  line-height: 1.5;
}
.manage-note code {
  background: var(--border);
  border-radius: 4px;
  padding: 1px 5px;
}
.token-row { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.token-row input { flex: 1; min-width: 220px; }
.muted-text { font-size: 12px; color: var(--muted); }
.btn {
  background: var(--page);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
}
.btn:hover { border-color: var(--series-1); }
.btn-ghost { opacity: 0.7; }
.btn-primary { background: var(--series-1); color: white; border-color: var(--series-1); font-weight: 500; }
.btn-danger { color: var(--critical); }
.add-form { margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--grid); }
.add-form h3 { font-size: 13px; margin: 0 0 10px; color: var(--text-secondary); }
.save-row { display: flex; align-items: center; gap: 12px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--grid); }
input[type="checkbox"] { width: 16px; height: 16px; }
</style>
</head>
<body>
<h1>Job Monitor Dashboard</h1>
<div class="subtitle">Generated __GENERATED_AT__</div>

<div class="stats">
  <div class="tile"><div class="value">__TOTAL_COMPANIES__</div><div class="label">Companies monitored</div></div>
  <div class="tile accent"><div class="value">__ACTIVE_COMPANIES__</div><div class="label">Healthy right now</div></div>
  <div class="tile __ERROR_CLASS__"><div class="value">__ERROR_COMPANIES__</div><div class="label">Companies with errors</div></div>
  <div class="tile"><div class="value">__LAST_SUCCESS__</div><div class="label">Last successful check</div></div>
  <div class="tile accent"><div class="value">__TOTAL_JOBS__</div><div class="label">Matching jobs detected (all-time)</div></div>
  <div class="tile accent"><div class="value">__TOTAL_NOTIFIED__</div><div class="label">Notifications sent</div></div>
</div>

<section>
  <h2>Recently discovered openings</h2>
  <div class="filters">
    <input id="f-company" placeholder="Company">
    <input id="f-role" placeholder="Role / title">
    <input id="f-location" placeholder="Location">
    <input id="f-experience" placeholder="Experience">
    <input id="f-date" type="date">
  </div>
  <div class="table-wrap">
    <table id="jobs-table">
      <thead><tr>
        <th>Detected</th><th>Company</th><th>Role</th><th>Location</th>
        <th>Type</th><th>Experience</th><th>Category</th><th>Apply</th><th>Notified</th>
      </tr></thead>
      <tbody></tbody>
    </table>
    <div class="empty" id="jobs-empty" style="display:none">No jobs match these filters yet.</div>
  </div>
</section>

<section>
  <h2>Notification history</h2>
  <div class="table-wrap">
    <table id="notif-table">
      <thead><tr><th>Sent</th><th>Company</th><th>Role</th><th>Status</th></tr></thead>
      <tbody></tbody>
    </table>
    <div class="empty" id="notif-empty" style="display:none">No notifications sent yet.</div>
  </div>
</section>

<section>
  <h2>Monitoring status per company</h2>
  <div class="table-wrap">
    <table id="companies-table">
      <thead><tr>
        <th>Company</th><th>Source</th><th>Status</th><th>Last checked</th><th>Last success</th><th>Last error</th>
      </tr></thead>
      <tbody></tbody>
    </table>
  </div>
</section>

<section>
  <h2>Manage companies</h2>
  <div class="manage-note">
    Changes save directly to this project's GitHub repo (<code>companies.json</code>) and take
    effect on the next run (within ~10 minutes). To enable saving, paste a GitHub token below -
    a <b>fine-grained personal access token</b> scoped to just this repo with
    <b>Contents: Read and write</b> permission (create one at
    <a href="https://github.com/settings/tokens?type=beta" target="_blank" rel="noopener">github.com/settings/tokens</a>).
    It's stored only in this browser (localStorage) and used only for direct calls to GitHub's
    API - it is never embedded in this page or sent anywhere else.
  </div>
  <div class="token-row">
    <input id="gh-token" type="password" placeholder="GitHub token (Contents: read/write)">
    <button id="token-save" class="btn">Save token</button>
    <button id="token-clear" class="btn btn-ghost">Clear</button>
    <span id="token-status" class="muted-text"></span>
  </div>

  <div class="table-wrap">
    <table id="manage-table">
      <thead><tr><th>Enabled</th><th>Name</th><th>Source</th><th>Career page</th><th></th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <div class="add-form">
    <h3>Add a company</h3>
    <div class="filters">
      <input id="add-name" placeholder="Company name">
      <select id="add-source">
        <option value="greenhouse">greenhouse</option>
        <option value="lever">lever</option>
        <option value="ashby">ashby</option>
        <option value="smartrecruiters">smartrecruiters</option>
        <option value="workday">workday</option>
        <option value="generic_html">generic_html</option>
      </select>
      <input id="add-identifier" placeholder="Identifier (see hint below)" style="flex: 2; min-width: 260px;">
      <input id="add-career-page" placeholder="Career page URL" style="flex: 2; min-width: 220px;">
    </div>
    <div class="muted-text" id="add-hint">Board token / slug, e.g. "openai"</div>
    <button id="add-btn" class="btn" style="margin-top: 10px;">+ Add to list</button>
  </div>

  <div class="save-row">
    <button id="save-btn" class="btn btn-primary">Save changes to GitHub</button>
    <span id="save-status" class="muted-text"></span>
  </div>
</section>

<footer>Data refreshes every ~10 minutes via a scheduled GitHub Actions run.</footer>

<script>
const JOBS = __JOBS_JSON__;
const NOTIFICATIONS = __NOTIF_JSON__;
const COMPANIES = __COMPANIES_JSON__;
const COMPANIES_CONFIG = __COMPANIES_CONFIG_JSON__;
const REPO = 'ashwinrajux-cyber/Job-Monitoring';
const TOKEN_KEY = 'jobmonitor_gh_token';
let DRAFT = JSON.parse(JSON.stringify(COMPANIES_CONFIG));

function renderJobs() {
  const company = document.getElementById('f-company').value.toLowerCase();
  const role = document.getElementById('f-role').value.toLowerCase();
  const location = document.getElementById('f-location').value.toLowerCase();
  const experience = document.getElementById('f-experience').value.toLowerCase();
  const date = document.getElementById('f-date').value;

  const rows = JOBS.filter(j => {
    if (company && !(j.company_name || '').toLowerCase().includes(company)) return false;
    if (role && !(j.title || '').toLowerCase().includes(role)) return false;
    if (location && !(j.location || '').toLowerCase().includes(location)) return false;
    if (experience && !(j.experience || '').toLowerCase().includes(experience)) return false;
    if (date && !(j.first_seen_at || '').startsWith(date)) return false;
    return true;
  });

  const tbody = document.querySelector('#jobs-table tbody');
  tbody.innerHTML = rows.map(j => `
    <tr>
      <td>${escapeHtml(formatTs(j.first_seen_at))}</td>
      <td>${escapeHtml(j.company_name || '')}</td>
      <td>${escapeHtml(j.title || '')}</td>
      <td>${escapeHtml(j.location || '—')}</td>
      <td>${escapeHtml(j.employment_type || '—')}</td>
      <td>${escapeHtml(j.experience || '—')}</td>
      <td>${escapeHtml(j.category || '')}</td>
      <td>${j.url ? `<a href="${escapeAttr(j.url)}" target="_blank" rel="noopener">Apply</a>` : '—'}</td>
      <td>${j.notified ? 'Yes' : 'No'}</td>
    </tr>`).join('');
  document.getElementById('jobs-empty').style.display = rows.length ? 'none' : 'block';
}

function renderNotifications() {
  const tbody = document.querySelector('#notif-table tbody');
  tbody.innerHTML = NOTIFICATIONS.map(n => `
    <tr>
      <td>${escapeHtml(formatTs(n.sent_at))}</td>
      <td>${escapeHtml(n.company_name || '')}</td>
      <td>${escapeHtml(n.title || '')}</td>
      <td>${n.success ? '<span class="badge ok">sent</span>' : '<span class="badge error">failed</span>'}</td>
    </tr>`).join('');
  document.getElementById('notif-empty').style.display = NOTIFICATIONS.length ? 'none' : 'block';
}

function renderCompanies() {
  const tbody = document.querySelector('#companies-table tbody');
  tbody.innerHTML = COMPANIES.map(c => `
    <tr>
      <td>${escapeHtml(c.name || '')}</td>
      <td>${escapeHtml(c.source_type || '')}</td>
      <td><span class="badge ${c.status}">${escapeHtml(c.status)}</span></td>
      <td>${escapeHtml(formatTs(c.last_checked_at))}</td>
      <td>${escapeHtml(formatTs(c.last_success_at))}</td>
      <td>${escapeHtml(c.last_error || '—')}</td>
    </tr>`).join('');
}

const IDENTIFIER_HINTS = {
  greenhouse: 'Board token, e.g. "openai" (from boards.greenhouse.io/openai)',
  lever: 'Company slug, e.g. "spotify" (from jobs.lever.co/spotify)',
  ashby: 'Job board name, e.g. "notion" (from jobs.ashbyhq.com/notion)',
  smartrecruiters: 'Company identifier, e.g. "Visa" (from jobs.smartrecruiters.com/Visa)',
  workday: 'JSON object: {"tenant":"acme","wd_host":"wd5","site":"External"}',
  generic_html: 'The full career page URL, e.g. "https://example.com/careers"',
};

function renderManageTable() {
  const tbody = document.querySelector('#manage-table tbody');
  tbody.innerHTML = DRAFT.map((c, i) => `
    <tr>
      <td><input type="checkbox" data-idx="${i}" class="enable-toggle" ${c.enabled ? 'checked' : ''}></td>
      <td>${escapeHtml(c.name || '')}</td>
      <td>${escapeHtml(c.source_type || '')}</td>
      <td>${c.career_page ? `<a href="${escapeAttr(c.career_page)}" target="_blank" rel="noopener">link</a>` : '—'}</td>
      <td><button class="btn btn-danger remove-btn" data-idx="${i}">Remove</button></td>
    </tr>`).join('');

  tbody.querySelectorAll('.enable-toggle').forEach(el =>
    el.addEventListener('change', e => {
      DRAFT[+e.target.dataset.idx].enabled = e.target.checked;
    })
  );
  tbody.querySelectorAll('.remove-btn').forEach(el =>
    el.addEventListener('click', e => {
      const idx = +e.target.dataset.idx;
      if (confirm(`Remove "${DRAFT[idx].name}" from monitoring?`)) {
        DRAFT.splice(idx, 1);
        renderManageTable();
      }
    })
  );
}

function loadToken() {
  const t = localStorage.getItem(TOKEN_KEY);
  document.getElementById('token-status').textContent = t ? 'Token saved in this browser ✓' : 'No token saved';
}

function utf8ToBase64(str) {
  return btoa(unescape(encodeURIComponent(str)));
}

async function saveToGitHub() {
  const token = localStorage.getItem(TOKEN_KEY);
  const statusEl = document.getElementById('save-status');
  if (!token) {
    statusEl.textContent = 'Enter and save a GitHub token first.';
    return;
  }
  statusEl.textContent = 'Saving...';
  const url = `https://api.github.com/repos/${REPO}/contents/job_monitor/config/companies.json`;
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Accept': 'application/vnd.github+json',
  };
  try {
    const getResp = await fetch(url, {headers});
    if (!getResp.ok) throw new Error(`Couldn't read current file (HTTP ${getResp.status}). Check your token's permissions.`);
    const getData = await getResp.json();

    const content = JSON.stringify(DRAFT, null, 2);
    const putResp = await fetch(url, {
      method: 'PUT',
      headers: {...headers, 'Content-Type': 'application/json'},
      body: JSON.stringify({
        message: 'Update companies.json via dashboard',
        content: utf8ToBase64(content),
        sha: getData.sha,
        branch: 'main',
      }),
    });
    if (!putResp.ok) {
      const err = await putResp.json().catch(() => ({}));
      throw new Error(err.message || `Save failed (HTTP ${putResp.status})`);
    }
    statusEl.textContent = 'Saved! Live on the next run (within ~10 minutes).';
  } catch (e) {
    statusEl.textContent = `Error: ${e.message}`;
  }
}

document.getElementById('token-save').addEventListener('click', () => {
  const val = document.getElementById('gh-token').value.trim();
  if (val) {
    localStorage.setItem(TOKEN_KEY, val);
    document.getElementById('gh-token').value = '';
  }
  loadToken();
});
document.getElementById('token-clear').addEventListener('click', () => {
  localStorage.removeItem(TOKEN_KEY);
  loadToken();
});
document.getElementById('add-source').addEventListener('change', e => {
  document.getElementById('add-hint').textContent = IDENTIFIER_HINTS[e.target.value] || '';
});
document.getElementById('add-btn').addEventListener('click', () => {
  const name = document.getElementById('add-name').value.trim();
  const source_type = document.getElementById('add-source').value;
  const identifierRaw = document.getElementById('add-identifier').value.trim();
  const career_page = document.getElementById('add-career-page').value.trim();
  if (!name || !identifierRaw) {
    alert('Company name and identifier are required.');
    return;
  }
  let identifier = identifierRaw;
  if (source_type === 'workday') {
    try {
      identifier = JSON.parse(identifierRaw);
    } catch (e) {
      alert('For workday, the identifier must be valid JSON, e.g. {"tenant":"acme","wd_host":"wd5","site":"External"}');
      return;
    }
  }
  DRAFT.push({name, enabled: true, source_type, identifier, career_page: career_page || undefined});
  renderManageTable();
  document.getElementById('add-name').value = '';
  document.getElementById('add-identifier').value = '';
  document.getElementById('add-career-page').value = '';
});
document.getElementById('save-btn').addEventListener('click', saveToGitHub);

function formatTs(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString('en-IN', {timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true}) + ' IST';
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

['f-company','f-role','f-location','f-experience','f-date'].forEach(id =>
  document.getElementById(id).addEventListener('input', renderJobs)
);

renderJobs();
renderNotifications();
renderCompanies();
renderManageTable();
loadToken();
</script>
</body>
</html>
"""


def _format_ts(iso):
    """Time-only, IST - this tile refreshes every ~10 minutes so a date is just noise."""
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso).astimezone(IST)
        return dt.strftime("%I:%M %p IST")
    except ValueError:
        return iso


def render(conn, output_path, companies_config=None):
    stats = db.get_stats(conn)
    jobs = db.get_recent_jobs(conn, limit=500)
    notifications = db.get_notification_history(conn, limit=500)
    companies = db.get_company_status(conn)

    html = TEMPLATE
    html = html.replace("__GENERATED_AT__", datetime.now(timezone.utc).astimezone(IST).strftime("%b %d, %I:%M %p IST"))
    html = html.replace("__TOTAL_COMPANIES__", str(stats["total_companies"]))
    html = html.replace("__ACTIVE_COMPANIES__", str(stats["active_companies"]))
    html = html.replace("__ERROR_COMPANIES__", str(stats["error_companies"]))
    html = html.replace("__ERROR_CLASS__", "crit" if stats["error_companies"] else "")
    html = html.replace("__LAST_SUCCESS__", _format_ts(stats["last_success_at"]))
    html = html.replace("__TOTAL_JOBS__", str(stats["total_jobs"]))
    html = html.replace("__TOTAL_NOTIFIED__", str(stats["total_notified"]))
    html = html.replace("__JOBS_JSON__", json.dumps(jobs).replace("</script>", "<\\/script>"))
    html = html.replace("__NOTIF_JSON__", json.dumps(notifications).replace("</script>", "<\\/script>"))
    html = html.replace("__COMPANIES_JSON__", json.dumps(companies).replace("</script>", "<\\/script>"))
    html = html.replace(
        "__COMPANIES_CONFIG_JSON__",
        json.dumps(companies_config or []).replace("</script>", "<\\/script>"),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
