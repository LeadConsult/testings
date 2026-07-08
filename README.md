# Ground Truth — Business Intelligence Baseline

A small Flask app implementing the 5-tool Business Intelligence Baseline System:

1. **Daily Revenue & Expense Log** — margin auto-calculated per transaction
2. **Daily Lead Tracker** — conversion rate auto-calculated
3. **Daily Work Log** — Lead Consult vs. Oatslead hour split
4. **Weekly Review** — fixed expenses + legal/institutional milestone notes
5. **Weekly Summary** — everything above rolled into one auto-built snapshot, with two fields you fill in by hand (evidence gap closed, account balance)

All money figures are stored as plain numbers and displayed in Naira (₦). One shared password protects the whole app for your team — there are no individual accounts.

---

## 1. Run it locally first

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` — the default password is `changeme123` (change this before going live — see below).

## 2. Environment variables

Set these before deploying anywhere real:

| Variable | Purpose | Example |
|---|---|---|
| `SECRET_KEY` | Signs login sessions. Use a long random string. | `openssl rand -hex 32` |
| `TEAM_PASSWORD` | The single shared password everyone on the team uses to log in. | `Ledger2026!` |
| `DATABASE_URL` | Optional. Defaults to a local SQLite file. Set this if you move to Postgres (see note below). | `postgresql://...` |
| `PORT` | Optional, only used when running `python app.py` directly. | `5000` |

## 3. Deploying so your team can access it online

The easiest free/cheap options for a small Flask + SQLite app:

### Option A — Render.com (recommended, simplest)
1. Push this folder to a GitHub repo.
2. On Render: **New → Web Service**, connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add the environment variables from the table above under **Environment**.
6. **Important:** Render's free web services have an *ephemeral filesystem* — the SQLite database will be wiped on every redeploy or restart. To keep your data:
   - Add a **Render Persistent Disk** (small paid add-on) mounted at `/opt/render/project/src/instance`, **or**
   - Switch to Render's free **PostgreSQL** add-on and set `DATABASE_URL` to the connection string it gives you (the app already supports this — no code changes needed, just install `psycopg2-binary` too).

### Option B — Railway or Fly.io
Same idea as Render: connect the repo, set the same environment variables, and attach a persistent volume (or their managed Postgres) for the same reason as above.

### Option C — PythonAnywhere
Good if you want something that doesn't sleep and keeps its filesystem by default (their disk is persistent), which sidesteps the SQLite concern entirely. Upload the folder, create a virtualenv, install `requirements.txt`, and point their WSGI config at `app.app`.

**Bottom line:** wherever you deploy, make sure the disk holding the `instance/bi_baseline.db` file is *persistent*, or switch `DATABASE_URL` to a real Postgres add-on. This is the one thing that will silently lose your team's data if skipped.

## 4. Changing the team password later
Just update the `TEAM_PASSWORD` environment variable on your host and restart the app. Everyone already logged in stays logged in (sessions last 30 days); new logins need the new password.

## 5. Backing up your data
The whole business lives in `instance/bi_baseline.db` (SQLite) unless you've switched to Postgres. Download/copy that file periodically, or set up your host's automatic backup feature if using Postgres.

## Project structure
```
app.py              — routes for all 5 tools + dashboard + login
models.py            — database tables
utils.py              — week-range and currency helpers
config.py            — reads SECRET_KEY / TEAM_PASSWORD / DATABASE_URL from env
templates/            — one HTML page per tool
static/css/style.css  — the whole visual design
```
