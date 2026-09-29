# Phase 9 — Namespaces, secrets & Postgres

[← Phase 8](08-first-image.md) · [Guide home](../../AWS_K8S_DEPLOYMENT.md) · Next: [Phase 10 →](10-app-ingress-tls.md)

**Goal:** namespaces and settings in place, every password generated and stored safely, and a running Postgres with one database each for the app and Airflow.
**Time:** ~40 minutes.

---

## Step 9.1 — Create the namespaces and config manifests

**Where:** 🪟 Windows (VS Code)

**`k8s/00-namespaces.yaml`**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: sysdesign
---
apiVersion: v1
kind: Namespace
metadata:
  name: jenkins
---
apiVersion: v1
kind: Namespace
metadata:
  name: airflow
```

**`k8s/10-config.yaml`**: non-secret app settings, injected as environment variables. The same ConfigMap also goes into `airflow`, because Airflow's task pods run the app image (for seeding and clearsessions) and need the same settings.
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sysdesign-config
  namespace: sysdesign
data:
  DEBUG: "False"
  ALLOWED_HOSTS: sysdesignquest.duckdns.org,localhost
  CSRF_TRUSTED_ORIGINS: https://sysdesignquest.duckdns.org
  SECURE_SSL_REDIRECT: "True"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: sysdesign-config
  namespace: airflow
data:
  DEBUG: "False"
  ALLOWED_HOSTS: sysdesignquest.duckdns.org,localhost
  CSRF_TRUSTED_ORIGINS: https://sysdesignquest.duckdns.org
  SECURE_SSL_REDIRECT: "True"
```
`localhost` is in `ALLOWED_HOSTS` for the Kubernetes health checks (Phase 10), which send `Host: localhost`. It's harmless publicly: Traefik only routes requests for `sysdesignquest.duckdns.org` to the app. Values like `"False"` are quoted because ConfigMap values must be strings.

- [ ] Both files created, hostname filled in

---

## Step 9.2 — Create the Postgres manifest

**Where:** 🪟 Windows → **`k8s/20-postgres.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: sysdesign
spec:
  selector:
    app: postgres
  ports:
    - name: postgres
      port: 5432
      targetPort: postgres
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: sysdesign
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:17        # pinned: 18 changed the data directory layout
          env:
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-superuser
                  key: password
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          ports:
            - name: postgres
              containerPort: 5432
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "postgres"]
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              memory: 1Gi
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

How it fits together:
- **Service `postgres`** gives the database a stable DNS name: `postgres.sysdesign.svc.cluster.local` (or just `postgres` from inside the `sysdesign` namespace). It routes to pods labelled `app: postgres`.
- **StatefulSet** runs exactly one pod, always named `postgres-0`, and gives it a persistent disk from `volumeClaimTemplates`. The PVC `data-postgres-0` survives pod restarts and even deleting the StatefulSet.
- **`POSTGRES_PASSWORD` from a Secret**: the password is never in the file.
- **`PGDATA` subfolder**: Postgres refuses to initialize in a directory that isn't empty, and some volumes contain a `lost+found` folder. A subfolder avoids that.
- **`readinessProbe`**: the pod counts as Ready only once Postgres accepts connections.

- [ ] File created

---

## Step 9.3 — Commit, push and pull

**Where:** 🪟 Windows
```powershell
git add k8s/00-namespaces.yaml k8s/10-config.yaml k8s/20-postgres.yaml
git commit -m "Add namespaces, app config and Postgres manifests"
git push
```

**Where:** 🐧 VM
```bash
cd ~/sysdesign && git pull
```

- [ ] VM has the files (`ls k8s/`)

---

## Step 9.4 — Generate every password, once

**Where:** 🐧 VM

```bash
umask 077
cat > ~/.sysdesign-secrets <<EOF
PG_SUPER_PASS=$(openssl rand -hex 24)
APP_DB_PASS=$(openssl rand -hex 24)
AIRFLOW_DB_PASS=$(openssl rand -hex 24)
DJANGO_SECRET_KEY=$(openssl rand -hex 48)
AIRFLOW_FERNET_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
AIRFLOW_API_SECRET=$(openssl rand -hex 32)
AIRFLOW_JWT_SECRET=$(openssl rand -hex 32)
AIRFLOW_ADMIN_PASS=$(openssl rand -hex 12)
EOF
```

What each value is for:

| Variable | Used by |
|---|---|
| `PG_SUPER_PASS` | Postgres `postgres` superuser. Admin tasks only; apps never use it |
| `APP_DB_PASS` | The `sysdesign` DB role the app connects as |
| `AIRFLOW_DB_PASS` | The `airflow` DB role (Airflow's metadata DB) |
| `DJANGO_SECRET_KEY` | Django signing (sessions, CSRF tokens). Changing it logs everyone out |
| `AIRFLOW_FERNET_KEY` | Encrypts connection passwords stored in Airflow's DB. Must be 32 bytes, URL-safe base64 |
| `AIRFLOW_API_SECRET`, `AIRFLOW_JWT_SECRET` | Airflow 3 API server session signing / API tokens |
| `AIRFLOW_ADMIN_PASS` | Your Airflow UI `admin` login |

Notes:
- `umask 077` makes the file readable by you only.
- Hex passwords contain only `0-9a-f`, so they never need escaping inside a `postgresql://user:pass@host/db` URL.
- The `$(…)` parts run **now**, and the file stores the resulting values.

Now add the Gemini key without it appearing on screen or in your shell history:
```bash
read -rsp 'Gemini API key: ' k; echo "GEMINI_API_KEY=$k" >> ~/.sysdesign-secrets; unset k; echo
```

Finally, **copy everything into your password manager** as one secure note, "sysdesign k3s secrets". You'll need these values to rebuild the cluster if the VM is ever lost.
```bash
cat ~/.sysdesign-secrets
```

**Check:**
```bash
ls -l ~/.sysdesign-secrets
wc -l ~/.sysdesign-secrets
```

**Expected:** `-rw-------` and `9` lines.

> ⚠️ Run the `cat > … <<EOF` block **only once**. Running it again generates new passwords that won't match what's already in the cluster. If you need to change one value later, edit that line with `nano ~/.sysdesign-secrets`.

- [ ] Secrets file has 9 lines, mode `-rw-------`, and is copied to your password manager

---

## Step 9.5 — Load the secrets into your shell

**Where:** 🐧 VM

```bash
set -a; source ~/.sysdesign-secrets; set +a
echo "${#APP_DB_PASS}"
```

`set -a` exports every variable the file defines, so the commands below can use them. **Expected:** `48` (the password's length, not the password itself).

> Each new SSH session starts without these variables. Re-run this step whenever a later step uses `$SOMETHING_PASS` in a new session.

- [ ] Prints `48`

---

## Step 9.6 — Apply namespaces and config

**Where:** 🐧 VM

```bash
cd ~/sysdesign
kubectl apply -f k8s/00-namespaces.yaml -f k8s/10-config.yaml
kubectl get ns
kubectl -n sysdesign get configmap sysdesign-config -o yaml
```

**Expected:** namespaces `sysdesign`, `jenkins` and `airflow` exist, and the ConfigMap shows your hostname.

- [ ] Namespaces and ConfigMaps exist

---

## Step 9.7 — Create the secrets in the cluster

**Where:** 🐧 VM (with the variables loaded from Step 9.5)

```bash
kubectl -n sysdesign create secret generic postgres-superuser \
  --from-literal=password="$PG_SUPER_PASS"

for ns in sysdesign airflow; do
  kubectl -n "$ns" create secret generic sysdesign-secrets \
    --from-literal=SECRET_KEY="$DJANGO_SECRET_KEY" \
    --from-literal=DATABASE_URL="postgresql://sysdesign:${APP_DB_PASS}@postgres.sysdesign.svc.cluster.local:5432/sysdesign" \
    --from-literal=GEMINI_API_KEY="$GEMINI_API_KEY" \
    --dry-run=client -o yaml | kubectl apply -f -
done
```

- `DATABASE_URL` uses the **full** DNS name (`postgres.sysdesign.svc.cluster.local`), so the same value works from both the `sysdesign` and `airflow` namespaces.
- `--dry-run=client -o yaml | kubectl apply -f -` generates the Secret and then *applies* it, so re-running the command later updates it instead of failing with "already exists". Use this whenever you rotate a value.

**Check** (shows key names and sizes, not values):
```bash
kubectl -n sysdesign describe secret sysdesign-secrets
kubectl -n airflow get secret sysdesign-secrets
```

**Expected:** `DATABASE_URL`, `GEMINI_API_KEY` and `SECRET_KEY` listed with byte counts; the secret also exists in `airflow`.

To see a value when debugging (be careful where you do this):
```bash
kubectl -n sysdesign get secret sysdesign-secrets -o jsonpath='{.data.DATABASE_URL}' | base64 -d; echo
```

> **Secrets are only base64-encoded, not encrypted.** Anyone with your kubeconfig can read them. That's why the kubeconfig and the VM login must be protected.

- [ ] `postgres-superuser` and `sysdesign-secrets` (×2) exist

---

## Step 9.8 — Start Postgres

**Where:** 🐧 VM

```bash
kubectl apply -f k8s/20-postgres.yaml
kubectl -n sysdesign rollout status statefulset/postgres --timeout=5m
kubectl -n sysdesign get pods,pvc
```

**Expected:**
```
NAME             READY   STATUS    RESTARTS   AGE
pod/postgres-0   1/1     Running   0          40s

NAME                                    STATUS   VOLUME     CAPACITY   ACCESS MODES   STORAGECLASS
persistentvolumeclaim/data-postgres-0   Bound    pvc-…      10Gi       RWO            local-path
```

**If the pod is stuck `Pending`:** `kubectl -n sysdesign describe pod postgres-0` → Events. **If it's `CrashLoopBackOff`:** `kubectl -n sysdesign logs postgres-0`.

- [ ] `postgres-0` Running, PVC Bound

---

## Step 9.9 — Create the app and Airflow databases

**Where:** 🐧 VM (variables loaded)

```bash
kubectl -n sysdesign exec -i postgres-0 -- psql -U postgres -v ON_ERROR_STOP=1 <<SQL
CREATE ROLE sysdesign LOGIN PASSWORD '${APP_DB_PASS}';
CREATE DATABASE sysdesign OWNER sysdesign;
CREATE ROLE airflow LOGIN PASSWORD '${AIRFLOW_DB_PASS}';
CREATE DATABASE airflow OWNER airflow;
SQL
```

- `kubectl exec -i postgres-0 -- psql …` runs `psql` **inside** the Postgres container and feeds it the SQL below. Inside the container, `psql -U postgres` connects over a local socket without a password.
- Each app gets its **own role** that owns **only its own database**. If one credential leaks, the damage stays contained.

**Expected:**
```
CREATE ROLE
CREATE DATABASE
CREATE ROLE
CREATE DATABASE
```

**Check:**
```bash
kubectl -n sysdesign exec postgres-0 -- psql -U postgres -c '\l'
```
The list includes `sysdesign` (owner `sysdesign`) and `airflow` (owner `airflow`).

**Check that the app's credentials really work over the network**, the way the app will connect:
```bash
kubectl -n sysdesign run pgcheck --rm -i --restart=Never --image=postgres:17 \
  --env="DATABASE_URL=postgresql://sysdesign:${APP_DB_PASS}@postgres:5432/sysdesign" \
  -- sh -c 'psql "$DATABASE_URL" -c "select current_user, current_database();"'
```
(The single quotes make `$DATABASE_URL` expand *inside* the pod, not in your VM shell.)

**Expected:** a row `sysdesign | sysdesign`, then `pod "pgcheck" deleted`.

- [ ] Both databases exist; the app role can log in over the network

---

## ✅ Checkpoint

- [ ] `~/.sysdesign-secrets` exists and is backed up in your password manager
- [ ] Namespaces `sysdesign`, `jenkins`, `airflow` exist
- [ ] ConfigMap `sysdesign-config` in `sysdesign` and `airflow`
- [ ] Secrets `postgres-superuser` (sysdesign) and `sysdesign-secrets` (sysdesign + airflow)
- [ ] `postgres-0` Running with a Bound 10 Gi PVC
- [ ] Databases `sysdesign` and `airflow`, each owned by its own role
