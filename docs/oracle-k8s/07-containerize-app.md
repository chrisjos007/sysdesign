# Phase 7 — Containerize the app

[← Phase 6](06-cert-manager.md) · [Guide home](../../ORACLE_K8S_DEPLOYMENT.md) · Next: [Phase 8 →](08-first-image.md)

**Goal:** Django works correctly behind an HTTPS proxy, and the app builds into a small, secret-free container image that you've tested locally.
**Time:** ~45 minutes. All work in this phase is on 🪟 Windows.

---

## Step 7.1 — Teach Django about the TLS proxy

**Why:** in the cluster, HTTPS ends at Traefik, and Django receives plain HTTP. Django's CSRF protection compares the browser's `Origin: https://sysdesignquest.duckdns.org` with what it thinks the request is (`http://…`). They don't match, so **every form POST, including login, fails with "403 CSRF verification failed"**. Render's proxy has the same effect. If Render logins ever fail that way, this change fixes them too.

**Where:** 🪟 Windows → open `config/settings.py`

Find this block (around line 38):
```python
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()
]
```

Directly **below** it, add:
```python

# TLS terminates at the reverse proxy (Traefik on k8s, Render's edge), which
# sets X-Forwarded-Proto; trust it so request.is_secure() and the CSRF origin
# check see https.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]

SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
```

What each line does:

| Setting | Effect |
|---|---|
| `SECURE_PROXY_SSL_HEADER` | "If the proxy says `X-Forwarded-Proto: https`, treat the request as HTTPS." Safe only when a proxy always sets that header. Traefik does, and a NetworkPolicy (Phase 10) makes Traefik the only way in |
| `CSRF_TRUSTED_ORIGINS` | Extra origins allowed to POST, read from an env var, e.g. `https://sysdesignquest.duckdns.org` |
| `SECURE_SSL_REDIRECT` | Redirects `http://` → `https://`. Off by default so local dev and Render are unchanged; the cluster turns it on via env |
| `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` | Browsers only send these cookies over HTTPS in production (`DEBUG=False`) |

**Check local dev still works:**
```powershell
.\venv\Scripts\python manage.py check
.\venv\Scripts\python manage.py runserver
```
Open http://127.0.0.1:8000, log in, and click around. Everything behaves as before, because `DEBUG` defaults to `True` locally. Stop the server with **Ctrl+C**.

- [ ] Settings added; `check` passes; local login still works

---

## Step 7.2 — Write the Dockerfile

**Where:** 🪟 Windows → create **`Dockerfile`** at the repo root (no extension)

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
RUN useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
# Static files are baked into the image; no DB is needed for collectstatic.
RUN SECRET_KEY=collectstatic-only DEBUG=False python manage.py collectstatic --noinput

USER 10001
EXPOSE 8000
CMD ["gunicorn", "config.wsgi", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", "--threads", "4", \
     "--timeout", "90", \
     "--worker-tmp-dir", "/dev/shm", \
     "--forwarded-allow-ips", "*", \
     "--access-logfile", "-"]
```

Line by line:

| Line | Why |
|---|---|
| `FROM python:3.13-slim` | Same Python as your venv (3.13). Multi-arch, so it works on amd64 and arm64 |
| `PYTHONDONTWRITEBYTECODE=1` | No `.pyc` writes, because the container filesystem will be read-only |
| `PYTHONUNBUFFERED=1` | Logs appear immediately in `kubectl logs` |
| `useradd --uid 10001` | A non-root user. The Kubernetes manifest enforces running as this UID |
| `COPY requirements.txt` then `pip install`, **before** `COPY . .` | Layer caching: dependencies are only reinstalled when `requirements.txt` changes, not on every code change |
| `collectstatic` at build time | WhiteNoise serves static files from the image. The dummy `SECRET_KEY` is only used during this build step |
| `USER 10001` | Everything after this, including the running app, is non-root |
| `--workers 2 --threads 4` | 8 concurrent requests in about 250 MB of memory |
| `--timeout 90` | Gemini calls can take up to 60 s (`learn/llm.py`) |
| `--worker-tmp-dir /dev/shm` | Gunicorn's heartbeat files go to shared memory, since the root filesystem is read-only |
| `--forwarded-allow-ips *` | Trust `X-Forwarded-*` from any source. Safe because only Traefik can reach the pod (NetworkPolicy, Phase 10) |
| `--access-logfile -` | Request logs to stdout, so `kubectl logs` shows them |

- [ ] `Dockerfile` created

---

## Step 7.3 — Write `.dockerignore`

**Where:** 🪟 Windows → create **`.dockerignore`** at the repo root

```
.git
.gitignore
.env
.envrc
venv/
.venv/
**/__pycache__/
**/*.pyc
db.sqlite3*
staticfiles/
.vscode/
.claude/
.impeccable/
.vexp/
*.md
Procfile
Dockerfile
Jenkinsfile
k8s/
jenkins/
airflow/
docs/
file.*
table.csv
testfile.tmp
try.py
```

**Why this matters:** everything not listed here gets copied into the image by `COPY . .`, and the image will be **public**.
- **`.env`** holds your local secrets (including the Gemini key).
- **`db.sqlite3`** holds your local users and data.
- **`venv/`** is huge and Windows-specific.

- [ ] `.dockerignore` created

---

## Step 7.4 — Build the image locally

**Where:** 🪟 Windows (repo root, Docker Desktop running)

```powershell
docker build -t sysdesign-quest:dev .
```

**Expected:** a series of steps ending in `naming to docker.io/library/sysdesign-quest:dev`. The first build takes 1–3 minutes.

**If `collectstatic` fails:** read the error. It's usually a static file referenced in a template that doesn't exist, and it fails the same way locally with `DEBUG=False`.

- [ ] Image built

---

## Step 7.5 — Check nothing secret got in

**Where:** 🪟 Windows

```powershell
docker run --rm sysdesign-quest:dev ls -la /app
docker run --rm sysdesign-quest:dev sh -c "ls -a /app | grep -E '^\.env$|sqlite' || echo CLEAN"
```

**Expected:** the second command prints **`CLEAN`**. The listing shows `config`, `learn`, `manage.py`, `requirements.txt` and `staticfiles`, and no `venv`, `.git` or `.env`.

```powershell
docker images sysdesign-quest:dev
```
The size should be roughly 200–300 MB.

- [ ] Prints `CLEAN`

---

## Step 7.6 — Smoke-test the container

**Where:** 🪟 Windows

```powershell
docker run --rm -p 8000:8000 -e DEBUG=False -e ALLOWED_HOSTS=localhost `
  -e DATABASE_URL=sqlite:////tmp/db.sqlite3 sysdesign-quest:dev `
  sh -c "python manage.py migrate --noinput && exec gunicorn config.wsgi --bind 0.0.0.0:8000"
```

This uses a throwaway SQLite DB in the container's `/tmp`, runs migrations, then starts gunicorn.

**Where:** 🌐 Browser → http://localhost:8000/accounts/login/

**Expected:** the login page renders **with its styling**, which proves WhiteNoise serves the static files baked into the image. Content pages will be empty because this DB has no seed data. That's fine.

Stop the container with **Ctrl+C** in PowerShell.

- [ ] Login page renders with CSS

---

## Step 7.7 — Commit and push

**Where:** 🪟 Windows

```powershell
git add config/settings.py Dockerfile .dockerignore
git commit -m "Containerize app and trust TLS-terminating proxy"
git push
```

Render redeploys as usual and keeps working. It's configured as a Python service and ignores the Dockerfile, and the settings changes are compatible.

- [ ] Pushed; Render deploy still green

---

## ✅ Checkpoint

- [ ] `config/settings.py` has the proxy settings; local dev unchanged
- [ ] Image builds, contains no `.env` / `db.sqlite3`, and serves the login page with CSS
- [ ] Committed and pushed
