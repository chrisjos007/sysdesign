# Phase 10 — App, ingress & HTTPS

[← Phase 9](09-secrets-and-postgres.md) · [Guide home](../../ORACLE_K8S_DEPLOYMENT.md) · Next: [Phase 11 →](11-remote-access.md)

**Goal:** SysDesign Quest live at `https://sysdesignquest.duckdns.org` with a trusted certificate, data in Postgres, and the web pod locked down by network policies.
**Time:** ~60 minutes.

---

## Step 10.1 — Create the web manifest

**Where:** 🪟 Windows → **`k8s/30-web.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: sysdesign
spec:
  selector:
    app: web
  ports:
    - name: http
      port: 80
      targetPort: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: sysdesign
spec:
  replicas: 1
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0      # keep the old pod serving until the new one is Ready
      maxSurge: 1
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      # The code runner executes learner-submitted Python in this pod; don't
      # hand it a Kubernetes API token.
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: web
          image: ghcr.io/chrisjos007/sysdesign-quest:latest   # Jenkins pins a commit tag on each deploy
          imagePullPolicy: Always
          ports:
            - name: http
              containerPort: 8000
          envFrom:
            - configMapRef:
                name: sysdesign-config
            - secretRef:
                name: sysdesign-secrets
          readinessProbe:
            httpGet:
              path: /accounts/login/
              port: http
              httpHeaders:
                # Probes hit the pod IP; without these Django answers 400
                # (DisallowedHost) or 301 (SECURE_SSL_REDIRECT).
                - name: Host
                  value: sysdesignquest.duckdns.org
                - name: X-Forwarded-Proto
                  value: https
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 5
          livenessProbe:
            tcpSocket:
              port: http
            initialDelaySeconds: 20
            periodSeconds: 20
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              memory: 768Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: tmp
              mountPath: /tmp      # code runner's temp dirs
      volumes:
        - name: tmp
          emptyDir:
            sizeLimit: 128Mi
```

The important parts:

| Part | Why |
|---|---|
| `strategy.maxUnavailable: 0, maxSurge: 1` | On deploy, Kubernetes starts the new pod first and only removes the old one once the new one is Ready, so there's no downtime |
| `envFrom` | Every key in the ConfigMap and Secret becomes an environment variable, which `settings.py` already reads |
| `readinessProbe` with `Host` + `X-Forwarded-Proto` headers | The kubelet probes the pod by IP. Without a valid `Host`, Django returns 400 (`DisallowedHost`). Without `X-Forwarded-Proto: https`, `SECURE_SSL_REDIRECT` returns a 301 and the probe never exercises a real page |
| `livenessProbe: tcpSocket` | Restart the container only if gunicorn stops listening. It deliberately doesn't depend on the DB, so a Postgres blip doesn't cause restart loops |
| `automountServiceAccountToken: false` | Learner code runs in this pod (`learn/code_runner.py`), and it must not find a Kubernetes API token lying around |
| `runAsNonRoot`, `drop: ALL`, `allowPrivilegeEscalation: false`, `seccompProfile` | Standard hardening: no root, no Linux capabilities, restricted syscalls |
| `readOnlyRootFilesystem` + `/tmp` emptyDir | Nothing can modify the app's code at runtime. The code runner's temp files go to a small scratch volume that's wiped when the pod goes away |
| `limits.memory: 768Mi` | 2 gunicorn workers + code runs (each capped at 256 MB by `code_runner.py`) fit. If the pod is OOMKilled, raise this |

- [ ] File created

---

## Step 10.2 — Create the migrate Job template

**Where:** 🪟 Windows → **`k8s/templates/migrate-job.yaml`**

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: migrate
  namespace: sysdesign
spec:
  backoffLimit: 1
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: migrate
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
      containers:
        - name: migrate
          image: IMAGE_PLACEHOLDER
          command: ["python", "manage.py", "migrate", "--noinput"]
          envFrom:
            - configMapRef:
                name: sysdesign-config
            - secretRef:
                name: sysdesign-secrets
```

- A **Job** runs until it succeeds once. Migrations run **once per deploy, before** new pods start. They don't run inside every web pod, so replicas never race each other.
- `IMAGE_PLACEHOLDER` is replaced with the exact image being deployed (by `sed`, now and later in Jenkins).
- It's in `templates/` so that `kubectl apply -f k8s/` never applies it by accident. `apply -f <dir>` doesn't recurse into subfolders.
- `ttlSecondsAfterFinished: 3600` cleans the finished Job up after an hour.

- [ ] File created

---

## Step 10.3 — Create the Ingress

**Where:** 🪟 Windows → **`k8s/40-ingress.yaml`**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web
  namespace: sysdesign
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-staging
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - sysdesignquest.duckdns.org
      secretName: web-tls
  rules:
    - host: sysdesignquest.duckdns.org
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web
                port:
                  name: http
```

- `rules`: requests for this hostname go to Service `web` (port `http`).
- `tls.secretName: web-tls`: Traefik serves the certificate stored in this Secret.
- The **annotation** tells cert-manager to create that certificate using the **staging** issuer for now.

- [ ] File created

---

## Step 10.4 — Create the network policies

**Where:** 🪟 Windows → **`k8s/50-network-policies.yaml`**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: web
  namespace: sysdesign
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes: ["Ingress", "Egress"]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system   # Traefik
      ports:
        - port: 8000
          protocol: TCP
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - port: 53
          protocol: UDP
        - port: 53
          protocol: TCP
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - port: 5432
          protocol: TCP
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8        # VCN, pods, services
              - 172.16.0.0/12
              - 192.168.0.0/16
              - 100.64.0.0/10
              - 169.254.0.0/16    # OCI instance metadata
      ports:
        - port: 443
          protocol: TCP
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: postgres
  namespace: sysdesign
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - podSelector: {}                      # any pod in sysdesign (web, migrate, one-off clients)
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: airflow   # Airflow itself + backup/seed task pods
      ports:
        - port: 5432
          protocol: TCP
```

What the `web` policy means in plain words:
- **In:** only from `kube-system` (where Traefik runs), only on port 8000.
- **Out:** DNS lookups, Postgres, and HTTPS to **public** internet addresses (for the Gemini API). Nothing else.
- So if learner code tries to reach Jenkins, Airflow, the Kubernetes API, the VM itself or Oracle's metadata service (`169.254.169.254`, which can hand out cloud credentials), it's blocked.

The `postgres` policy lets only the `sysdesign` and `airflow` namespaces talk to the database.

- [ ] File created

---

## Step 10.5 — Commit, push and pull

**Where:** 🪟 Windows
```powershell
git add k8s/30-web.yaml k8s/40-ingress.yaml k8s/50-network-policies.yaml k8s/templates/migrate-job.yaml
git commit -m "Add web deployment, ingress, network policies and migrate job"
git push
```

**Where:** 🐧 VM
```bash
cd ~/sysdesign && git pull
```

- [ ] Pulled

---

## Step 10.6 — Load data: choose **A** or **B**

### Option A — Fresh database

**Where:** 🐧 VM

Run the migrations with the migrate Job:
```bash
sed "s|IMAGE_PLACEHOLDER|ghcr.io/chrisjos007/sysdesign-quest:latest|" k8s/templates/migrate-job.yaml | kubectl apply -f -
kubectl -n sysdesign wait --for=condition=complete job/migrate --timeout=300s
kubectl -n sysdesign logs job/migrate
```

**Expected:** `job.batch/migrate condition met`, and the logs list `Applying learn.0001_initial… OK` and the rest.

**If `wait` times out:** `kubectl -n sysdesign logs job/migrate` shows the error. Usually it's a wrong `DATABASE_URL`: compare it with the check in Step 9.9.

You'll seed the content in Step 10.8, once the web pod is running.

### Option B — Copy your Render/Neon data

1. 🌐 In the Neon dashboard → SQL editor → run `SELECT version();` and note the major version (e.g. 17).
2. The Postgres client image below must be the **same or a newer** major version than Neon. Use `postgres:17` for Neon 17, or `postgres:18` if Neon is on 18.
3. 🐧 VM (variables loaded, see Step 9.5):
   ```bash
   kubectl -n sysdesign run pgimport --rm -it --restart=Never --image=postgres:17 \
     --env="TARGET=postgresql://sysdesign:${APP_DB_PASS}@postgres:5432/sysdesign" -- bash
   ```
4. Inside the pod's shell:
   ```bash
   read -rsp 'Neon URL: ' NEON; echo
   pg_dump --no-owner --no-acl "$NEON" | psql -q "$TARGET"
   psql "$TARGET" -c 'SELECT count(*) FROM auth_user;'
   exit
   ```
   Paste the Neon connection string from the Neon dashboard at the prompt. The count should match your Render user count.
5. Then run the migrate Job from Option A anyway, as a consistency check. Its log should say **`No migrations to apply.`**

- [ ] Data loaded (A or B), migrate Job succeeded

---

## Step 10.7 — Start the web app

**Where:** 🐧 VM

```bash
kubectl apply -f k8s/30-web.yaml
kubectl -n sysdesign rollout status deploy/web --timeout=5m
kubectl -n sysdesign get pods -l app=web
```

**Expected:** `deployment "web" successfully rolled out` and one pod `1/1 Running`.

**Test it from inside the cluster, before exposing it:**
```bash
kubectl -n sysdesign run curltest --rm -i --restart=Never --image=curlimages/curl -- \
  curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: sysdesignquest.duckdns.org' -H 'X-Forwarded-Proto: https' http://web/accounts/login/
```

**Expected:** `200`.

**If it isn't Ready:**
- `kubectl -n sysdesign describe pod -l app=web`: check the Events (probe failures, image pull).
- `kubectl -n sysdesign logs deploy/web`: Django errors.
- A **400** from the probe means the `Host` header in `30-web.yaml` doesn't match `ALLOWED_HOSTS` in `10-config.yaml`.

- [ ] Web pod Ready; in-cluster curl returns 200

---

## Step 10.8 — Seed content (Option A only) and create your admin user

**Where:** 🐧 VM

```bash
# Option A only:
kubectl -n sysdesign exec deploy/web -- python manage.py seed_content
kubectl -n sysdesign exec deploy/web -- python manage.py seed_games

# Both options (skip if your Neon data already has a superuser you know):
kubectl -n sysdesign exec -it deploy/web -- python manage.py createsuperuser
```

`kubectl exec deploy/web` runs a command inside the running web pod, with all its environment variables and DB access.

- [ ] Content present, superuser created

---

## Step 10.9 — Expose it and get a **staging** certificate

**Where:** 🐧 VM

```bash
kubectl apply -f k8s/40-ingress.yaml
kubectl -n sysdesign get certificate -w
```

**Expected:** within 1–2 minutes, `web-tls` goes to `READY True`. Press **Ctrl+C** to stop watching.

While you wait, you can watch the HTTP-01 challenge happen:
```bash
kubectl -n sysdesign get challenges,orders
```

**If it stays `False` for more than 5 minutes:**
```bash
kubectl -n sysdesign describe certificate web-tls
kubectl -n sysdesign describe challenges
```

The last Events explain it:
- `connection refused` / timeout → port 80 is blocked (Phase 3).
- `NXDOMAIN` → the DuckDNS IP is wrong.

**Where:** 🪟 Windows
```powershell
curl.exe -k -s -o NUL -w "%{http_code}`n" https://sysdesignquest.duckdns.org/accounts/login/
```

**Expected:** `200`. The `-k` flag is needed because the staging certificate isn't trusted, which is expected. In a browser you'd see a certificate warning at this point.

- [ ] Staging certificate `READY True`; HTTPS returns 200 with `-k`

---

## Step 10.10 — Switch to the **production** certificate

**Where:** 🪟 Windows → in `k8s/40-ingress.yaml`, change

```yaml
    cert-manager.io/cluster-issuer: letsencrypt-staging
```
to
```yaml
    cert-manager.io/cluster-issuer: letsencrypt-prod
```

```powershell
git commit -am "Use production Let's Encrypt issuer"
git push
```

**Where:** 🐧 VM
```bash
cd ~/sysdesign && git pull
kubectl apply -f k8s/40-ingress.yaml
kubectl -n sysdesign delete secret web-tls     # forces a fresh certificate from prod
kubectl -n sysdesign get certificate -w
```

**Expected:** `READY True` again within a minute or two.

**Where:** 🌐 Browser → `https://sysdesignquest.duckdns.org`

**Expected:** a padlock with no warning. Click the padlock → certificate → issued by **Let's Encrypt** (an `R1x`/`E…` intermediate).

- [ ] Trusted certificate in the browser

---

## Step 10.11 — Functional checks (before network policies)

**Where:** 🌐 Browser

- [ ] `http://sysdesignquest.duckdns.org` **redirects** to `https://…`
- [ ] You can **log in**. This proves the proxy/CSRF settings from Phase 7.
- [ ] `/admin/` works with your superuser
- [ ] A **coding challenge runs and gets graded**. This proves the code runner works on a read-only filesystem with `/tmp` as scratch space.
- [ ] A **Gemini-backed feature** works (outbound HTTPS)

If any fail, fix them now. The next step adds restrictions, and you want to know that everything worked *before* them.

---

## Step 10.12 — Apply the network policies

**Where:** 🐧 VM

```bash
kubectl apply -f k8s/50-network-policies.yaml
kubectl -n sysdesign rollout restart deploy/web
kubectl -n sysdesign rollout status deploy/web --timeout=5m
kubectl -n sysdesign get pods -l app=web
```

**Expected:** the new pod becomes `1/1 Ready`.

**If the pod never becomes Ready after this, but did before:** the policy is blocking the kubelet's probe. Add this extra item under `ingress:` in the `web` policy (10.42.0.1 is the node's address on the pod network), then re-apply:
```yaml
    - from:
        - ipBlock:
            cidr: 10.42.0.1/32
      ports:
        - port: 8000
          protocol: TCP
```

- [ ] Web pod Ready with policies applied

---

## Step 10.13 — Prove the lockdown works

**Where:** 🐧 VM

**Blocked:** the web pod can't reach cluster internals or Oracle's metadata service:
```bash
kubectl -n sysdesign exec deploy/web -- python -c "import urllib.request as u; u.urlopen('http://169.254.169.254/opc/v2/instance/', timeout=3)"
kubectl -n sysdesign exec deploy/web -- python -c "import urllib.request as u; u.urlopen('https://kubernetes.default.svc', timeout=3)"
```

**Expected:** both end in a **timeout** error (`URLError … timed out`).

**Allowed:** public HTTPS works:
```bash
kubectl -n sysdesign exec deploy/web -- python -c "import urllib.request as u; print(u.urlopen('https://generativelanguage.googleapis.com', timeout=5).status)"
```

**Expected:** a status code or an HTTP error such as 404. Any HTTP response means the connection itself succeeded, which is what matters.

**Where:** 🌐 Browser → re-run the checks from Step 10.11. All still pass.

- [ ] Metadata and API are blocked; the internet and all app features still work

---

## ✅ Checkpoint — the app is live 🎉

- [ ] `https://sysdesignquest.duckdns.org` has a trusted certificate; http redirects to https
- [ ] Login, admin, code runner and Gemini all work
- [ ] Network policies applied and verified
- [ ] All manifests committed

Useful now:
```bash
kubectl -n sysdesign logs deploy/web -f       # live request log (Ctrl+C to stop)
kubectl top pods -n sysdesign
```
