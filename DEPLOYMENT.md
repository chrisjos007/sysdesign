# Deployment Guide — SysDesign Quest

This document describes how to deploy SysDesign Quest to production with PostgreSQL as the database, using a zero-cost hosting stack. The Django project package is `config` (`config/settings.py`, `config.wsgi`).

## 1. Architecture

| Component | Service | Role |
|---|---|---|
| Application server | Render (Web Service) | Runs Django via Gunicorn, serves static assets via WhiteNoise |
| Database | Neon | Managed PostgreSQL |
| Source control | GitHub | Render deploys directly from a connected repository |

**Why this combination:** both Render and Neon offer free tiers with no credit card requirement. Render's own managed Postgres add-on auto-deletes after 30 days of the free trial; Neon's free tier has no fixed expiry and instead scales compute to zero when idle, which avoids that data-loss trap while keeping cost at zero indefinitely.

**Known limitations of this stack:**
- Render's free web service spins down after 15 minutes of inactivity; the next request triggers a cold start (30–60 seconds).
- Neon's free compute scales to zero after 5 minutes of inactivity, adding a comparable cold-start delay on first query.
- Render's free tier is capped at 750 instance-hours/month, 512MB RAM, 0.1 vCPU.
- Neon's free tier is capped at 0.5GB storage and 100 compute-hours/month.

This is acceptable for a personal project or portfolio deployment with light, intermittent traffic. It is not suitable for a workload that requires consistent low-latency availability — see Section 6 for alternatives without the sleep/cold-start behavior.

## 2. Code changes (completed)

The following changes have already been applied to this repository to make it deployable:

- **`requirements.txt`** — added `dj-database-url`, `psycopg[binary]`, `gunicorn`, `whitenoise`.
- **`config/settings.py`**:
  - `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` are now read from environment variables, with safe defaults preserved for local development (running with no environment variables set behaves exactly as before).
  - `DATABASES` is configured via `dj_database_url.config(...)`, defaulting to the existing `db.sqlite3` file locally and switching to PostgreSQL automatically once a `DATABASE_URL` environment variable is set.
  - `whitenoise.middleware.WhiteNoiseMiddleware` was added to `MIDDLEWARE`, immediately after `SecurityMiddleware`, to serve static files directly from the application server without a separate static file host.
  - `STATIC_ROOT` and a `STORAGES['staticfiles']` entry (WhiteNoise's compressed manifest storage) were added so `collectstatic` has a destination and static assets are served with cache-busting hashes and gzip/brotli compression in production.
  - A pre-existing defect was also corrected: `settings.py` was missing `DEFAULT_AUTO_FIELD` (the file was truncated mid-comment). This has been restored to `django.db.models.BigAutoField`, matching Django's `startproject` default. This was not causing failures — Django silently falls back to `AutoField` — but is worth noting as a fix made alongside the deployment work.
- **`Procfile`** (repository root):
  ```
  web: gunicorn config.wsgi --log-file -
  release: python manage.py migrate
  ```
- **`.gitignore`** (repository root) — the repository previously had none; `venv/`, `__pycache__/`, `db.sqlite3`, `db.sqlite3-journal*`, `staticfiles/`, and `.env` are now excluded so the pushed repository stays minimal.

None of these changes alter local development behavior: `python manage.py runserver` continues to work unmodified, using SQLite and the existing development secret key.

## 3. Database migration to PostgreSQL

Two paths are available, depending on whether existing local data should be preserved.

**Option A — clean initialization.** The management commands `seed_content` and `seed_games` are idempotent and fully rebuild the application's reference content (books, chapters, concepts, quizzes, and games) from scratch. Running `migrate`, `seed_content`, and `seed_games` against a fresh Postgres database is the simplest path, at the cost of discarding any existing user accounts and progress data (XP, levels, streaks, badges) stored in the local SQLite database.

**Option B — carry over existing data.** To preserve existing users and progress:
```bash
# Locally, against the current SQLite database
python manage.py dumpdata --natural-foreign --natural-primary \
  -e contenttypes -e auth.Permission -e sessions > data.json

# After deploying, against PostgreSQL (e.g. via Render's Shell tab)
python manage.py loaddata data.json
```
If `data.json` does not already include the seeded content (because it was excluded or the dump predates a content update), run `seed_content` and `seed_games` first, then `loaddata` to restore user and progress records on top.

## 4. Deployment procedure: Render + Neon

1. **Provision the database.** Sign up at neon.tech (GitHub login, no card required), create a project, and copy the pooled connection string (`postgresql://user:pass@host/db?sslmode=require`).
2. **Push the repository to GitHub.** `venv/` and `db.sqlite3` are excluded via `.gitignore`, so the pushed repository remains small.
3. **Create the web service on Render.** Sign up (no card required) → New → Web Service → connect the repository.
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - Start Command: `gunicorn config.wsgi --log-file -`
   - Instance type: Free
   - Note: migrations run via the `release` line in `Procfile`; confirm Render's current plan supports release-phase commands on the free tier, or add `python manage.py migrate` to the build command as a fallback.
4. **Set environment variables** on the Render service:
   - `SECRET_KEY` — a freshly generated value (`python -c "import secrets; print(secrets.token_urlsafe(50))"`), not the development key committed in the repository.
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = the assigned Render hostname (e.g. `your-app.onrender.com`)
   - `DATABASE_URL` = the Neon connection string from step 1
5. **Deploy.** Render installs dependencies, runs `collectstatic`, applies migrations, and starts Gunicorn.
6. **Seed the database** once, via Render's Shell tab: `python manage.py seed_content && python manage.py seed_games`, followed by `loaddata data.json` if carrying over existing data per Section 3.
7. **Verify.** Visit the assigned hostname. The first request after deployment or a period of inactivity will be slow (cold start); subsequent requests will be normal.

## 5. Alternative hosting options

If the sleep behavior or resource caps of the Render/Neon stack are not acceptable, the following alternatives were evaluated:

| Option | Cost | Considerations |
|---|---|---|
| **Railway** | Free, credit-based ($5 credit the first month, ~$1/month thereafter) | No card required to start; the web service and database draw from the same credit pool and pause once it is exhausted for the month |
| **PythonAnywhere** (free web app tier) + Neon (Postgres) | Free | No sleep/cold-start behavior, but limited to 100 CPU-seconds/day and outbound network access is restricted to an allowlist — a direct connection to an external Postgres host may be blocked and should be validated before committing to this path; the built-in free database is MySQL, not Postgres |
| **Oracle Cloud "Always Free" compute instance** (self-managed Django + PostgreSQL via Nginx, Gunicorn, and systemd) | Free, no sleep, no monthly hour cap | The only evaluated option with genuinely always-on availability at zero cost. Trade-offs: signup requires a credit card for identity verification (not billed under normal use), ARM instance capacity is frequently unavailable in high-demand regions, and Oracle reduced the Always Free Ampere A1 allocation from 4 OCPU/24GB to 2 OCPU/12GB in mid-2026 without prior notice. Requires ongoing server administration (OS patching, process supervision, firewall configuration) rather than a managed platform |

**Recommendation:** Render + Neon is the lowest-effort path for a personal or portfolio deployment and is the configuration this guide targets. If continuous availability is required and self-administration is acceptable, the Oracle Cloud Always Free instance is the only option in this comparison with no idle penalty — budget significantly more setup time than the Render/Neon path.

## 6. Production hardening checklist

- Confirm `DEBUG=False` and `ALLOWED_HOSTS` is set correctly in the production environment; Django returns HTTP 400 for any host not in this list.
- Set `SECURE_SSL_REDIRECT = True`, `SESSION_COOKIE_SECURE = True`, and `CSRF_COOKIE_SECURE = True` once HTTPS is confirmed to be working (Render provisions HTTPS automatically).
- Confirm a freshly generated `SECRET_KEY` is set via environment variable in production. The application falls back to the development key committed in the repository if this variable is unset, which is not safe for a public deployment.
- Establish a periodic backup or branch-export routine for the Neon database, as the free tier does not include a long-term backup guarantee.
