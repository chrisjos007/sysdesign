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

This is acceptable for a personal project or portfolio deployment with light, intermittent traffic. It is not suitable for a workload that requires consistent low-latency availability — see Section 5 for alternatives without the sleep/cold-start behavior.

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

# Against production PostgreSQL — run locally with DATABASE_URL pointed at Neon
# (Render's free tier has no Shell tab; see Section 7)
python manage.py loaddata data.json
```
If `data.json` does not already include the seeded content (because it was excluded or the dump predates a content update), run `seed_content` and `seed_games` first, then `loaddata` to restore user and progress records on top.

## 4. Deployment procedure: Render + Neon

1. **Provision the database.** Sign up at neon.tech (GitHub login, no card required), create a project, and copy the pooled connection string (`postgresql://user:pass@host/db?sslmode=require`).
2. **Push the repository to GitHub.** `venv/` and `db.sqlite3` are excluded via `.gitignore`, so the pushed repository remains small.
3. **Create the web service on Render.** Sign up (no card required) → New → Web Service → connect the repository.
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - Start Command: `gunicorn config.wsgi --log-file -`
   - Instance type: Free
   - **Both fields must be set explicitly in the Render dashboard.** Render's free tier does not reliably read the repository's `Procfile` — if the Start Command field is left blank, Render falls back to a generic auto-detected guess (`gunicorn app:app`), which fails with `ModuleNotFoundError: No module named 'app'` since this project's WSGI module is `config.wsgi`. Separately, Render's Pre-Deploy Command feature (the mechanism that would otherwise run migrations, corresponding to the `release:` line in `Procfile`) is only available on paid plans, so `migrate` is appended to the Build Command instead on the free tier.
4. **Set environment variables** on the Render service:
   - `SECRET_KEY` — a freshly generated value (`python -c "import secrets; print(secrets.token_urlsafe(50))"`), not the development key committed in the repository.
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = the assigned Render hostname (e.g. `your-app.onrender.com`)
   - `DATABASE_URL` = the Neon connection string from step 1
5. **Deploy.** Render installs dependencies, runs `collectstatic`, applies migrations, and starts Gunicorn.
6. **Seed the database** once, from your local machine with `DATABASE_URL` pointed at the Neon connection string (Render's free tier has no Shell tab — see Section 7): `python manage.py seed_content && python manage.py seed_games`, followed by `loaddata data.json` if carrying over existing data per Section 3.
7. **Verify.** Visit the assigned hostname. The first request after deployment or a period of inactivity will be slow (cold start); subsequent requests will be normal.

## 5. Alternative hosting options

If the sleep behavior or resource caps of the Render/Neon stack are not acceptable, the following alternatives were evaluated:

| Option | Cost | Considerations |
|---|---|---|
| **Railway** | Free, credit-based ($5 credit the first month, ~$1/month thereafter) | No card required to start; the web service and database draw from the same credit pool and pause once it is exhausted for the month |
| **PythonAnywhere** (free web app tier) + Neon (Postgres) | Free | No sleep/cold-start behavior, but limited to 100 CPU-seconds/day and outbound network access is restricted to an allowlist — a direct connection to an external Postgres host may be blocked and should be validated before committing to this path; the built-in free database is MySQL, not Postgres |
| **Oracle Cloud "Always Free" compute instance** (self-managed Django + PostgreSQL via Nginx, Gunicorn, and systemd) | Free, no sleep, no monthly hour cap | The only evaluated option with genuinely always-on availability at zero cost. Trade-offs: signup requires a credit card for identity verification (not billed under normal use), ARM instance capacity is frequently unavailable in high-demand regions, and Oracle reduced the Always Free Ampere A1 allocation from 4 OCPU/24GB to 2 OCPU/12GB in mid-2026 without prior notice. Requires ongoing server administration (OS patching, process supervision, firewall configuration) rather than a managed platform |

**Recommendation:** Render + Neon is the lowest-effort path for a personal or portfolio deployment and is the configuration this guide targets. If continuous availability is required and self-administration is acceptable, the Oracle Cloud Always Free instance is the only option in this comparison with no idle penalty — budget significantly more setup time than the Render/Neon path.

## 6. Managing content and data in production

Render's free tier has no Shell tab, so there is no interactive console attached to the running production instance. Any `manage.py` command must instead be run either from a local machine pointed at the Neon database, or through the Django admin UI. Both are described below.

**6.1 Running management commands against Neon from a local machine.** This is the primary route for anything not exposed through the admin UI (seeding, one-off data fixes, `dumpdata`/`loaddata`, `createsuperuser`). Set `DATABASE_URL` in the local shell session to the Neon connection string before running a command, so the command operates on production data instead of the local `db.sqlite3`:
```powershell
$env:DATABASE_URL = "postgresql://user:pass@host/db?sslmode=require"   # Neon connection string
python manage.py seed_content
python manage.py seed_games
```
(On cmd.exe use `set DATABASE_URL=...`; on macOS/Linux use `export DATABASE_URL=...`.) Because this only sets the variable for the current terminal session, subsequent `runserver` calls in a fresh terminal continue to use local SQLite as normal. `seed_content` and `seed_games` are idempotent — they update existing rows rather than duplicating them, so they are safe to re-run against Neon after any change to the underlying data in `learn/management/commands/seed_content.py` or `seed_games.py`.

**6.2 Adding or editing content going forward.** The book/chapter/concept/quiz/game data is defined in code (`seed_content.py`, `seed_games.py`), not entered ad hoc — this is the intended source of truth. To add new content:
1. Edit the relevant `seed_*.py` command locally.
2. Test it against local SQLite first (`python manage.py seed_content && python manage.py seed_games`, then verify in `runserver`).
3. Commit and push the change to GitHub — Render will redeploy automatically.
4. Re-run the seed commands against Neon per 6.1 so the new content reaches production immediately, rather than waiting for it to be picked up incidentally (the seed commands are not run automatically on every deploy — only `migrate` is, via the Build Command).

**6.3 Django admin for occasional or one-off edits.** Once a superuser exists, `/admin/` on the deployed site provides a full CRUD interface for every registered model (see `learn/admin.py`) without needing local access to the database at all — useful for quick fixes (correcting a typo in a quiz question, adjusting XP values) but not a practical way to manage bulk content.

**6.4 Bulk content export/import.** For moving a large batch of data between environments (e.g. syncing production back down to a local copy for debugging), `dumpdata`/`loaddata` work the same way as described in Section 3, with `DATABASE_URL` pointed at Neon for the production side of the operation.

## 7. Production hardening checklist

- Confirm `DEBUG=False` and `ALLOWED_HOSTS` is set correctly in the production environment; Django returns HTTP 400 for any host not in this list.
- Set `SECURE_SSL_REDIRECT = True`, `SESSION_COOKIE_SECURE = True`, and `CSRF_COOKIE_SECURE = True` once HTTPS is confirmed to be working (Render provisions HTTPS automatically).
- Confirm a freshly generated `SECRET_KEY` is set via environment variable in production. The application falls back to the development key committed in the repository if this variable is unset, which is not safe for a public deployment.
- Establish a periodic backup or branch-export routine for the Neon database, as the free tier does not include a long-term backup guarantee.


---

## 8. Deploying on Oracle Cloud Free Tier (Always Free VM)

Oracle Cloud's Always Free tier includes a permanent ARM-based Ampere A1 compute instance (up to 4 OCPU, 24 GB RAM across free instances) with 200 GB block storage. Unlike Render's free tier, this VM never sleeps — there is no cold-start penalty. The trade-off is that you manage the OS, Nginx, PostgreSQL, SSL, and deployments yourself.

**Estimated setup time:** 45–90 minutes for a first-time deployment.

### 8.1 Provision the VM

1. Sign up at cloud.oracle.com (requires a valid credit card for identity verification; the Always Free resources are never charged unless you manually upgrade to Pay As You Go).
2. Navigate to **Compute → Instances → Create Instance**.
3. Choose an **Always Free-eligible shape:**
   - Shape: `VM.Standard.A1.Flex` (ARM/Ampere)
   - OCPU: 1–4, RAM: 6–24 GB — all free within the Always Free quota
   - A single instance with 2 OCPU and 12 GB RAM is a reasonable choice.
4. Image: **Ubuntu 22.04 (aarch64)**.
5. Under **Networking**, confirm a public IP address is assigned and note the subnet.
6. **SSH key pair:** generate or upload a public key. Download the private key — you will need it to connect.
7. Create the instance and wait for it to reach Running state. Note the **Public IP address**.

### 8.2 Open firewall ports

OCI has two layers of firewall: the VCN Security List and the OS-level iptables/nftables. Both must allow traffic.

**In the OCI Console:**
1. Go to the instance's VCN → Security Lists → Default Security List.
2. Add **Ingress rules** for:
   - TCP port 80 (HTTP), source `0.0.0.0/0`
   - TCP port 443 (HTTPS), source `0.0.0.0/0`

**On the VM itself** (Ubuntu's iptables blocks these by default):
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

### 8.3 Initial server setup

SSH into the instance:
```bash
ssh -i /path/to/private_key.pem ubuntu@<PUBLIC_IP>
```

Update packages and install dependencies:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib nginx certbot python3-certbot-nginx \
    netfilter-persistent git
```

### 8.4 Set up PostgreSQL

```bash
sudo -u postgres psql <<'SQL'
CREATE DATABASE sysdesign_quest;
CREATE USER sysdesign_user WITH PASSWORD 'choose-a-strong-password';
ALTER ROLE sysdesign_user SET client_encoding TO 'utf8';
ALTER ROLE sysdesign_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE sysdesign_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE sysdesign_quest TO sysdesign_user;
SQL
```

The `DATABASE_URL` for this local PostgreSQL instance will be:
```
postgresql://sysdesign_user:choose-a-strong-password@localhost/sysdesign_quest
```

No external Neon account is needed — PostgreSQL runs on the same VM.

### 8.5 Deploy the application

```bash
# Clone the repository
cd /srv
sudo git clone https://github.com/<your-username>/sysdesign_quest.git
sudo chown -R ubuntu:ubuntu sysdesign_quest
cd sysdesign_quest

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables for the current shell
export SECRET_KEY="$(python -c "import secrets; print(secrets.token_urlsafe(50))")"
export DEBUG=False
export ALLOWED_HOSTS="<PUBLIC_IP>,<your-domain.com>"
export DATABASE_URL="postgresql://sysdesign_user:choose-a-strong-password@localhost/sysdesign_quest"

# Collect static files and run migrations
python manage.py collectstatic --noinput
python manage.py migrate

# Seed content
python manage.py seed_content
python manage.py seed_games

# Create a superuser
python manage.py createsuperuser
```

### 8.6 Configure Gunicorn as a systemd service

Create `/etc/systemd/system/sysdesign_quest.service`:
```ini
[Unit]
Description=SysDesign Quest Gunicorn daemon
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/srv/sysdesign_quest
Environment="SECRET_KEY=<your-generated-secret-key>"
Environment="DEBUG=False"
Environment="ALLOWED_HOSTS=<PUBLIC_IP>,<your-domain.com>"
Environment="DATABASE_URL=postgresql://sysdesign_user:choose-a-strong-password@localhost/sysdesign_quest"
ExecStart=/srv/sysdesign_quest/venv/bin/gunicorn \
    --workers 2 \
    --bind unix:/run/sysdesign_quest.sock \
    config.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sysdesign_quest
sudo systemctl start sysdesign_quest
sudo systemctl status sysdesign_quest   # confirm it is active (running)
```

### 8.7 Configure Nginx

Create `/etc/nginx/sites-available/sysdesign_quest`:
```nginx
server {
    listen 80;
    server_name <PUBLIC_IP> <your-domain.com>;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        root /srv/sysdesign_quest;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/sysdesign_quest.sock;
    }
}
```

Enable the site and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/sysdesign_quest /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Visit `http://<PUBLIC_IP>` — the application should be reachable over HTTP.

### 8.8 Enable HTTPS with Let's Encrypt (requires a domain name)

A domain name is required for a free Let's Encrypt certificate. Point an `A` record at the VM's public IP, then:
```bash
sudo certbot --nginx -d your-domain.com
```

Certbot modifies the Nginx config automatically and sets up a cron job for certificate renewal. After this step, add the HTTPS-hardening settings to `settings.py` per Section 7, and update `ALLOWED_HOSTS` in the systemd service to use only the domain name.

### 8.9 Deploying updates

Because there is no CI/CD pipeline in this setup, updates are deployed manually:
```bash
cd /srv/sysdesign_quest
git pull
source venv/bin/activate
pip install -r requirements.txt          # if requirements changed
python manage.py collectstatic --noinput # if static files changed
python manage.py migrate                 # if migrations were added
sudo systemctl restart sysdesign_quest
```

Alternatively, wrap this in a shell script and invoke it over SSH from a GitHub Actions workflow for automated deploys on push to `main`.

### 8.10 Known limitations of this stack

- **Self-managed:** OS security patches, PostgreSQL backups, and certificate renewals are your responsibility. `unattended-upgrades` can handle OS patches automatically; set it up immediately after provisioning.
- **Single-instance PostgreSQL:** no managed backup guarantee. Schedule `pg_dump` via cron and push dumps to OCI Object Storage (also free in the Always Free tier) or any off-site location.
- **ARM architecture:** the A1 shape is aarch64. All packages in `requirements.txt` have ARM Linux wheels on PyPI, so this is not a problem in practice — but any dependency that ships only x86 native extensions would fail to install.
- **Ephemeral public IP:** the free tier assigns an ephemeral public IP that can change if you stop and start the instance. Reserve a static IP (OCI calls it a Reserved Public IP) to avoid this — also free within the Always Free quota.
