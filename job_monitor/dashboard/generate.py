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

<footer>Data refreshes every ~10 minutes via a scheduled GitHub Actions run.</footer>

<script>
const JOBS = __JOBS_JSON__;
const NOTIFICATIONS = __NOTIF_JSON__;
const COMPANIES = __COMPANIES_JSON__;

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


def render(conn, output_path):
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

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
