# Job Monitor

Continuously watches a list of companies' official hiring channels for new
Product Design / UX openings and pushes a phone notification the moment a
match is found. Runs for free on GitHub Actions (every 10 minutes, 24/7,
independent of your laptop) and publishes a searchable dashboard via GitHub
Pages.

## How it works

- **Sources**: Greenhouse, Lever, Ashby, SmartRecruiters and Workday all
  expose public JSON job-board APIs — this reads those directly (reliable,
  structured data). A generic HTML fallback scraper exists for companies on
  none of those, but it's best-effort (see `job_monitor/scrapers/generic_html.py`).
  **LinkedIn is intentionally not scraped** — it's against LinkedIn's Terms of
  Service and gets IPs blocked quickly. If a target company only posts to
  LinkedIn, watch their own careers page/ATS instead.
- **Filtering**: `job_monitor/config/roles.json` defines keyword categories.
  Only `product_design_ux` is enabled today; UX Researcher, Product Manager,
  Design Manager, Visual/Service/Motion Designer are pre-defined but disabled —
  flip `"enabled": true` on any of them any time, no code changes needed.
- **Dedup**: every job is keyed by `(company, external_id)` in SQLite
  (`data/jobs.db`). A job notifies exactly once, ever.
- **First-time baseline**: the first time a company is scraped, its currently
  open matching jobs are stored silently (not notified) — otherwise you'd get
  flooded with alerts for jobs that have been open for months. Only jobs that
  appear *after* that baseline trigger a push.
- **Reliability**: each company is scraped independently — one company
  erroring (site down, API changed) never blocks the others, and it's
  automatically retried on the next 10-minute cycle. Per-company status/last
  error is visible on the dashboard.

## Repo layout

```
job_monitor/
  config/companies.json   # your company list — edit this
  config/roles.json        # role keyword categories — edit to add/enable categories
  scrapers/                 # one module per ATS + generic HTML fallback
  filters/match.py           # title -> category matching
  storage/db.py               # SQLite schema + dedup logic
  notify/telegram.py             # push notification sender
  dashboard/generate.py          # renders docs/index.html
  main.py                          # one full monitoring cycle
data/jobs.db                # SQLite DB (committed so state survives between runs)
docs/index.html              # generated dashboard (served by GitHub Pages)
.github/workflows/monitor.yml # the cron job that runs everything every 10 min
```

## Already verified working

I ran the pipeline live against 5 example companies during setup: Airbnb
(Greenhouse), Notion (Ashby), Visa (SmartRecruiters), Salesforce (Workday),
and Rippling (Lever). Real Product Design / UX jobs were correctly found,
matched, and stored — e.g. Notion's "Product Designer" and Salesforce's "Sr
Product Designer" and "Senior Product Designer - Design Systems". Lever
briefly returned errors for every board while testing (an external outage,
not a code issue — the same Lever scraper successfully parsed real data
earlier in the same session). Notifications now go through Telegram (see
setup step 2) instead of ntfy — switched after initial testing since Telegram
is official, free, has no ToS risk, and keeps a permanent chat history for
free. The current `data/jobs.db` and `docs/index.html` in this repo are real
output from that earlier test run — replace `config/companies.json` with your
real list whenever you're ready and the next run picks it up automatically.

## Setup steps (do these in order)

### 1. Push this to GitHub

You'll need a GitHub account. From this folder:

```bash
git add -A
git commit -m "Initial job monitor"
```

Then create an empty repo on github.com (New repository → do NOT initialize
with a README), and:

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

(Tell me your GitHub username/repo name if you'd like me to drive this instead —
I can install the `gh` CLI and run it here once you `gh auth login`.)

### 2. Set up Telegram notifications

Notifications go through the official, free Telegram Bot API — no ToS risk,
no app to install beyond Telegram itself.

1. In Telegram, message **@BotFather** → send `/newbot` → give it a name and
   a username (must end in `bot`, e.g. `my_job_alerts_bot`). It replies with a
   **bot token** (looks like `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`).
2. Open a chat with your new bot (search its username) and send it any
   message, e.g. "hi" — bots can't message you first, so this step is
   required once.
3. In your browser, visit
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` (replace
   `<YOUR_TOKEN>` with your actual token). You'll see JSON containing
   `"chat":{"id": 123456789, ...}` — that number is your **chat id**.
4. In your GitHub repo: **Settings → Secrets and variables → Actions → New
   repository secret**, add two secrets:
   - `TELEGRAM_BOT_TOKEN` = the token from step 1
   - `TELEGRAM_CHAT_ID` = the number from step 3

### 3. Enable GitHub Pages (for the dashboard)

**Settings → Pages → Source: Deploy from a branch → Branch: `main`, folder:
`/docs` → Save.** Your dashboard will be live at
`https://<your-username>.github.io/<repo-name>/` within a minute or two, and
updates automatically every cycle.

### 4. Confirm the workflow is scheduled

Once pushed, **Actions** tab → you should see "Job Monitor" listed. It runs
every 10 minutes automatically. You can also trigger it manually from there
("Run workflow") to test immediately rather than waiting.

Note: GitHub disables a scheduled workflow after 60 days with zero commits to
the repo — but this workflow commits its own DB/dashboard updates every run,
so that never happens as long as it's running successfully.

### 5. Add your real ~100 companies

Edit `job_monitor/config/companies.json`. Each entry:

```json
{
  "name": "Swiggy",
  "enabled": true,
  "source_type": "greenhouse",
  "identifier": "swiggy",
  "career_page": "https://careers.swiggy.com/"
}
```

`source_type` / `identifier` by ATS:

| ATS | source_type | identifier |
|---|---|---|
| Greenhouse | `greenhouse` | board token, e.g. `boards.greenhouse.io/<this>` |
| Lever | `lever` | company slug, e.g. `jobs.lever.co/<this>` |
| Ashby | `ashby` | job-board name, e.g. `jobs.ashbyhq.com/<this>` |
| SmartRecruiters | `smartrecruiters` | company identifier, e.g. `jobs.smartrecruiters.com/<this>` |
| Workday | `workday` | object: `{"tenant": "...", "wd_host": "wd12", "site": "External_Career_Site"}` (find these 3 values in the company's careers URL, e.g. `https://<tenant>.<wd_host>.myworkdayjobs.com/<site>`) |
| Anything else | `generic_html` | the full career-page URL (best-effort, fragile — see the module docstring) |

To find a company's ATS: open their careers page, open browser dev tools →
Network tab, reload, and look for a request to one of the domains above. Most
mid-size-to-large companies use one of these five.

Set `"enabled": false` on any company to pause monitoring without deleting it.
Scaling to hundreds of entries requires no code changes.

### 6. Test locally any time

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=your-token
export TELEGRAM_CHAT_ID=your-chat-id
python -m job_monitor.main
```

This runs one full cycle against whatever's in `companies.json` right now.
Useful for testing config changes before they go live on the schedule.

## Search & filtering

The dashboard (`docs/index.html`) has live client-side filters over Company,
Role, Location, Experience, and Date detected — no backend needed, works on
the static GitHub Pages copy.

## Managing companies from the dashboard

The dashboard also has a "Manage companies" section to enable/disable, remove,
or add companies without editing `companies.json` by hand. Since the dashboard
is a static page with no backend, it saves changes by calling GitHub's
Contents API directly from your browser, using a token you paste in once:

1. Create a **fine-grained personal access token** at
   `github.com/settings/tokens?type=beta`, scoped to just this repo, with
   **Contents: Read and write** permission. (This is separate from the
   Actions-trigger token used for the cron-job.org integration — that one
   only has Actions permission and won't work here.)
2. Paste it into the "GitHub token" field on the dashboard and click **Save
   token** — it's stored only in your browser's local storage and used only
   for direct calls to `api.github.com`; it's never embedded in the page or
   sent anywhere else.
3. Toggle companies on/off, remove them, or use the "Add a company" form, then
   click **Save changes to GitHub**. The change commits straight to
   `companies.json` and takes effect on the next run (~10 minutes).

Since this dashboard is publicly hosted, anyone can *view* this section, but
only someone with a valid write-scoped token can actually save changes.

## Adding future job categories

Flip `"enabled": true` in `job_monitor/config/roles.json` for UX Researcher,
Product Manager, Design Manager, Visual/Service/Motion Designer — or add a
brand new category object with your own `include_keywords` /
`exclude_keywords`. No other changes needed.
