# SysDesign Quest on your PC — k3d + Cloudflare Tunnel

Run the same stack as the [AWS guide](AWS_K8S_DEPLOYMENT.md) (Kubernetes, Postgres, Jenkins CI/CD and Airflow operations) **on your own Windows PC, for free**, and share the app publicly through a **Cloudflare Tunnel**.

| | This guide (local) | [AWS guide](AWS_K8S_DEPLOYMENT.md) |
|---|---|---|
| Cost | **$0** | ~$10/month at ~4 h/day |
| Accounts needed | GitHub (GHCR) only | AWS, DuckDNS, GitHub |
| Online when | Your PC is on and Docker Desktop is running | The instance is running |
| Public URL | Random `https://….trycloudflare.com`, new on each tunnel restart (or your own domain, see L10) | Fixed `https://sysdesignquest.duckdns.org` |
| HTTPS certificate | Handled by Cloudflare | cert-manager + Let's Encrypt |
| Backups | On a volume in the cluster (+ copy to your PC) | Same, plus S3 |
| CPU architecture | amd64 (your Ryzen 5 4600H) | arm64 (Graviton) |

**What you learn is the same:** k3d runs **k3s**, the identical Kubernetes distribution used on AWS, just inside Docker containers instead of a VM. Most AWS-guide phases apply unchanged. This guide covers the local-specific parts in full and tells you exactly which AWS-guide steps to follow (and what to change) for the rest.

**Time:** 4–7 hours across a few sessions.

---

## How to use this guide

**Where to run each step:**

| Label | Meaning |
|---|---|
| 🪟 **PowerShell** | Windows PowerShell, in the repo folder `A:\New folder (2)\sysdesign_quest` |
| 🐚 **Git Bash** | The Git Bash terminal (installed with Git for Windows), in the same repo folder. Use it for every command that the AWS guide marks 🐧 **VM** |
| 🌐 **Browser** | GitHub, the app, Jenkins, Airflow |

**Reading AWS-guide steps from here:**
- 🐧 **VM** → run in 🐚 **Git Bash** on your PC. There is no VM, and kubectl talks to the local cluster.
- Skip anything with `sudo`, `ssh`, `tmux`, `apt` or `systemctl`. Those are VM chores.
- `sysdesignquest.duckdns.org` → your tunnel URL's hostname, or `localhost` for local tests. Each step below says which.

**Your PC (checked):** Ryzen 5 4600H (6 cores / 12 threads), **15.4 GB RAM**, Docker Desktop on WSL2. Disk: **C: has only ~13 GB free**, **A: has ~92 GB free**. Step L1.1 moves Docker's data to A:.

---

## Architecture

```
┌──────────────────────── Your PC (Windows) ────────────────────────┐
│ Docker Desktop (WSL2, data on A:)                                 │
│ ┌─────────────── k3d cluster "sysdesign" (k3s in Docker) ───────┐ │
│ │  kube-system   Traefik (ingress) · CoreDNS · metrics-server   │ │
│ │  tunnel        cloudflared ── outbound only ──────────────────┼─┼──► Cloudflare edge ◄── https://….trycloudflare.com ◄── Internet
│ │  sysdesign     web (Django + gunicorn) ──► postgres (PVC)     │ │
│ │  jenkins       controller + short-lived build pods            │ │
│ │  airflow       scheduler · api-server · dag-processor · …     │ │
│ └───────────────────────────────────────────────────────────────┘ │
│   127.0.0.1:6550 → Kubernetes API   127.0.0.1:8088 → Traefik       │
└───────────────────────────────────────────────────────────────────┘
```

**Why a tunnel:** `cloudflared` makes an *outbound* connection to Cloudflare, and visitors reach your app through it. No router port-forwarding, no public IP, no firewall changes, and Cloudflare provides HTTPS.

---

## Phase L1 — Prepare Docker Desktop · ~20 min

### Step L1.1 — Move Docker's data off C:

**Why:** images for Jenkins, Airflow, Postgres and your app, plus build caches, need ~10–15 GB. C: only has ~13 GB free.

**Where:** Docker Desktop → ⚙️ **Settings** → **Resources** → **Advanced** → **Disk image location** → **Browse** → create and choose `A:\DockerDesktop` → **Apply & restart**.

Moving existing data can take several minutes. Wait until Docker Desktop shows *Engine running* again.

- [ ] Disk image location is `A:\DockerDesktop`

### Step L1.2 — Give WSL2 enough memory

**Why:** by default WSL2 (where Docker runs) gets half your RAM, about 7.7 GB. The full stack needs ~7 GB plus Docker's own overhead.

**Where:** 🪟 PowerShell

```powershell
@"
[wsl2]
memory=10GB
processors=6
swap=4GB
"@ | Set-Content -Path $env:USERPROFILE\.wslconfig -Encoding ascii
wsl --shutdown
```

Then start Docker Desktop again (it stopped with `wsl --shutdown`).

- `memory=10GB` leaves ~5 GB for Windows, your browser and VS Code. If Windows gets sluggish while everything runs, lower it to 9 GB and pause Airflow when you're not using it (L9).
- `processors=6` gives Docker half your threads.

**Check** (once Docker Desktop is running):
```powershell
docker info --format "{{.NCPU}} CPUs, {{.MemTotal}} bytes"
```
**Expected:** `6 CPUs` and roughly `10.4e9` bytes.

- [ ] Docker sees 6 CPUs and ~10 GB

### Step L1.3 — Make sure Docker Desktop's own Kubernetes is off

**Where:** Docker Desktop → ⚙️ **Settings** → **Kubernetes** → **Enable Kubernetes** unticked.

Two clusters on one machine would compete for memory and confuse `kubectl`.

- [ ] Docker Desktop Kubernetes disabled

---

## Phase L2 — Tools · ~15 min

### Step L2.1 — Install k3d, Helm and a current kubectl

**Where:** 🪟 PowerShell

```powershell
winget install k3d.k3d
winget install Helm.Helm
winget upgrade Kubernetes.kubectl
```

Close and reopen PowerShell so the new tools are on `PATH`, then check:
```powershell
k3d version
helm version
kubectl version --client
```

**Expected:** k3d `v5.9.x`, Helm `v3.x`/`v4.x`, kubectl `v1.35+`. Your old kubectl 1.34 is too far behind the cluster's 1.36.

- [ ] All three print versions

### Step L2.2 — Prepare Git Bash for kubectl

**Where:** 🐚 Git Bash

```bash
cat >> ~/.bashrc <<'EOF'
# Stop Git Bash rewriting Linux paths like /bin/cat into C:/Program Files/Git/...
export MSYS_NO_PATHCONV=1
alias k=kubectl
EOF
source ~/.bashrc
kubectl version --client
openssl version
```

**Why `MSYS_NO_PATHCONV=1`:** without it, Git Bash "helpfully" converts arguments that look like Unix paths, so `kubectl exec … -- /bin/cat /run/secrets/…` breaks mysteriously.

**About `-it` commands:** if an interactive command (`kubectl exec -it …`, `kubectl run … -it`) hangs or says *Unable to use a TTY*, prefix it with `winpty`, e.g. `winpty kubectl exec -it …`.

- [ ] kubectl and openssl both work in Git Bash

---

## Phase L3 — Create the cluster · ~15 min

### Step L3.1 — Create it

**Where:** 🪟 PowerShell

```powershell
k3d cluster create sysdesign `
  --image rancher/k3s:v1.36.4-k3s1 `
  --servers 1 --agents 0 `
  --api-port 127.0.0.1:6550 `
  --port "127.0.0.1:8088:80@loadbalancer" `
  --wait
```

| Flag | Meaning |
|---|---|
| `--image rancher/k3s:v1.36.4-k3s1` | The same k3s version as the AWS guide |
| `--servers 1 --agents 0` | One node, like the AWS setup |
| `--api-port 127.0.0.1:6550` | The Kubernetes API listens **only on your PC**, not your Wi-Fi network (the default is all interfaces) |
| `--port "127.0.0.1:8088:80@loadbalancer"` | `http://localhost:8088` on your PC reaches Traefik inside the cluster, for local testing. Also bound to localhost only |
| `--wait` | Return once the cluster is ready |

k3d also writes the connection details into `~\.kube\config` and switches kubectl to them.

**Expected:** the output ends with `Cluster 'sysdesign' created successfully!` and a hint to use `kubectl cluster-info`.

- [ ] Cluster created

### Step L3.2 — Check it

**Where:** 🪟 PowerShell

```powershell
kubectl config current-context
kubectl get nodes -o wide
kubectl get pods -A
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

**Expected:**
- Context: `k3d-sysdesign`.
- One node `k3d-sysdesign-server-0`, `Ready`, `v1.36.4+k3s1`.
- System pods `Running`/`Completed`, exactly as in [AWS Phase 5.4](docs/aws-k8s/05-k3s.md).
- Docker shows two containers: `k3d-sysdesign-server-0` (the "node") and `k3d-sysdesign-serverlb` (with `127.0.0.1:6550` and `127.0.0.1:8088` mapped).

```powershell
curl.exe -i http://localhost:8088
```
**Expected:** `404 page not found` from Traefik. The path PC → k3d load balancer → Traefik works.

- [ ] Node Ready; Traefik answers 404 on localhost:8088

### Step L3.3 — Where your data lives

PVCs (Postgres data, Jenkins home, backups) are stored **inside the `k3d-sysdesign-server-0` container**. They survive:
- ✅ `k3d cluster stop` / `start`, Docker Desktop restarts, Windows reboots
- ❌ `k3d cluster delete sysdesign`, which removes all data. Take a backup first (L8)

- [ ] Understood

---

## Phase L4 — Let Traefik trust the tunnel's headers · ~10 min

**Why:** Cloudflare terminates HTTPS and passes `X-Forwarded-Proto: https` down the tunnel. By default Traefik doesn't trust forwarded headers from other pods and **overwrites** that header with `http`. Django would then think every request is plain HTTP, and logins would fail with CSRF errors. The fix: tell Traefik to trust headers coming from the pod network, where `cloudflared` runs.

(On AWS this doesn't come up, because Traefik itself terminates HTTPS there.)

### Step L4.1 — Create the Traefik config

**Where:** 🪟 VS Code → create **`k8s/local/traefik-config.yaml`**

```yaml
# k3s installs Traefik from a bundled Helm chart; a HelmChartConfig
# overrides that chart's values without replacing it.
apiVersion: helm.cattle.io/v1
kind: HelmChartConfig
metadata:
  name: traefik
  namespace: kube-system
spec:
  valuesContent: |-
    ports:
      web:
        forwardedHeaders:
          trustedIPs:
            - 10.42.0.0/16   # the k3s pod network, where cloudflared runs
```

### Step L4.2 — Apply and verify

**Where:** 🪟 PowerShell
```powershell
kubectl apply -f k8s/local/traefik-config.yaml
kubectl -n kube-system rollout status deploy/traefik --timeout=3m
kubectl -n kube-system get deploy traefik -o yaml | Select-String trustedIPs
```

**Expected:** a line containing `--entryPoints.web.forwardedHeaders.trustedIPs=10.42.0.0/16`. k3s re-ran its Traefik install with your override.

- [ ] Traefik args include `trustedIPs=10.42.0.0/16`

---

## Phase L5 — Containerize the app and push an image · ~45 min

### Step L5.1 — Settings, Dockerfile, `.dockerignore`

Follow **[AWS Phase 7](docs/aws-k8s/07-containerize-app.md)** exactly: steps 7.1–7.7. Nothing changes; it all runs on Windows already.

- [ ] AWS Phase 7 checkpoint passed

### Step L5.2 — Push a multi-architecture image to GHCR

Follow **[AWS Phase 8](docs/aws-k8s/08-first-image.md)** with **one change** in Step 8.3: build for **both** architectures, so the same `latest` tag works here (amd64) and on AWS (arm64) if you ever do both:

```powershell
docker buildx build --platform linux/amd64,linux/arm64 -t ghcr.io/chrisjos007/sysdesign-quest:latest --push .
```

Everything else in Phase 8 is the same: log in, make the package public, then verify. In 8.5, `imagetools inspect` should list **both** `linux/amd64` and `linux/arm64`. Skip the last check in 8.5 (`sudo k3s ctr …` on the VM).

- [ ] Image is public on GHCR with amd64 + arm64

---

## Phase L6 — Secrets & Postgres · ~40 min

Follow **[AWS Phase 9](docs/aws-k8s/09-secrets-and-postgres.md)** with these changes:

| AWS step | Change for local |
|---|---|
| 9.1 `k8s/10-config.yaml` | Create it exactly as written (AWS uses it). **Also** create the local variant below, and apply the **local** one in 9.6 |
| 9.3 "VM: git pull" | Skip. You're already in the repo |
| 9.4–9.9 🐧 commands | Run in 🐚 **Git Bash**. `~/.sysdesign-secrets` becomes `C:\Users\<you>\.sysdesign-secrets`, private to your Windows user. `umask`/`chmod` have no effect on Windows; that's fine |
| 9.6 apply | `kubectl apply -f k8s/00-namespaces.yaml -f k8s/local/10-config.yaml` |

### The local config file

**Where:** 🪟 VS Code → create **`k8s/local/10-config.yaml`**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sysdesign-config
  namespace: sysdesign
data:
  DEBUG: "False"
  # Quick-tunnel hostnames are random subdomains of trycloudflare.com; the
  # leading dot allows any of them. localhost = health checks + local tests.
  ALLOWED_HOSTS: .trycloudflare.com,localhost
  CSRF_TRUSTED_ORIGINS: https://*.trycloudflare.com
  # Cloudflare already serves the public URL over HTTPS; keeping this off lets
  # you also test on http://localhost:8088.
  SECURE_SSL_REDIRECT: "False"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: sysdesign-config
  namespace: airflow
data:
  DEBUG: "False"
  ALLOWED_HOSTS: .trycloudflare.com,localhost
  CSRF_TRUSTED_ORIGINS: https://*.trycloudflare.com
  SECURE_SSL_REDIRECT: "False"
```

- [ ] AWS Phase 9 checkpoint passed (with the local ConfigMap applied)

---

## Phase L7 — App, ingress and the public tunnel · ~60 min

### Step L7.1 — App manifests

From **[AWS Phase 10](docs/aws-k8s/10-app-ingress-tls.md)**, create these files exactly as written: `k8s/30-web.yaml` (10.1), `k8s/templates/migrate-job.yaml` (10.2), `k8s/40-ingress.yaml` (10.3, used by AWS only) and `k8s/50-network-policies.yaml` (10.4). Then add the local ingress:

**Where:** 🪟 VS Code → create **`k8s/local/40-ingress.yaml`**

```yaml
# No host and no TLS: every request reaching Traefik goes to the app.
# Cloudflare handles HTTPS; Django's ALLOWED_HOSTS still filters hostnames.
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web
  namespace: sysdesign
spec:
  ingressClassName: traefik
  rules:
    - http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web
                port:
                  name: http
```

- [ ] Files created

### Step L7.2 — Data, web app, seed, superuser

Follow AWS Phase 10 steps **10.6, 10.7 and 10.8** in 🐚 Git Bash, with one change: in 10.7's in-cluster `curl` test, use `-H 'Host: localhost'` instead of the duckdns hostname.

- [ ] Web pod Ready; data loaded; superuser created

### Step L7.3 — Local ingress and a local test

**Where:** 🪟 PowerShell
```powershell
kubectl apply -f k8s/local/40-ingress.yaml
curl.exe -s -o NUL -w "%{http_code}`n" http://localhost:8088/accounts/login/
```

**Expected:** `200`.

🌐 Open http://localhost:8088. The app should work here too: log in, run a coding challenge.

**Skip AWS 10.9–10.10** (Let's Encrypt). Cloudflare provides HTTPS.

- [ ] App works on http://localhost:8088

### Step L7.4 — Start the Cloudflare quick tunnel

**Where:** 🪟 VS Code → create **`k8s/local/cloudflared.yaml`**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tunnel
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudflared
  namespace: tunnel
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cloudflared
  template:
    metadata:
      labels:
        app: cloudflared
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
      containers:
        - name: cloudflared
          image: cloudflare/cloudflared:2026.9.3
          # The image's entrypoint is `cloudflared --no-autoupdate`.
          # A "quick tunnel" (--url, no account) gets a random
          # https://<words>.trycloudflare.com address.
          args: ["tunnel", "--url", "http://traefik.kube-system.svc.cluster.local:80"]
          resources:
            requests:
              cpu: 10m
              memory: 32Mi
            limits:
              memory: 128Mi
```

**Where:** 🪟 PowerShell
```powershell
kubectl apply -f k8s/local/cloudflared.yaml
kubectl -n tunnel rollout status deploy/cloudflared
kubectl -n tunnel logs deploy/cloudflared | Select-String trycloudflare.com
```

**Expected:** a line like `|  https://quiet-river-sample-words.trycloudflare.com  |`. That's your public URL.

> The URL **changes whenever the cloudflared pod restarts**: cluster stop/start, PC reboot, or the pod being rescheduled. Re-run the `logs … | Select-String` command to get the current one. For a fixed URL, see L10.

- [ ] Tunnel URL obtained

### Step L7.5 — Functional checks through the tunnel

**Where:** 🌐 Browser → your `https://….trycloudflare.com` URL (also try it on your phone, on mobile data)

- [ ] Page loads over **https** with a valid padlock (Cloudflare's certificate)
- [ ] You can **log in**. This proves Cloudflare → cloudflared → Traefik (trusted headers) → Django (`SECURE_PROXY_SSL_HEADER`) all agree it's HTTPS
- [ ] `/admin/` works
- [ ] A **coding challenge runs and gets graded**
- [ ] A **Gemini-backed feature** works

**If login fails with "CSRF verification failed":** the `X-Forwarded-Proto: https` header was lost. Recheck Phase L4, and make sure the Phase 7.1 settings are in the image you're running.

### Step L7.6 — Network policies

Follow AWS Phase 10 steps **10.12 and 10.13** in 🐚 Git Bash. Notes:
- 10.13's metadata test (`169.254.169.254`) should still time out. There's no cloud metadata service locally anyway, but the policy blocks the whole range.
- Re-check L7.5 afterwards. The tunnel reaches the app via Traefik in `kube-system`, which the policy allows.

- [ ] Policies applied; app still works through the tunnel

---

## Phase L8 — Jenkins, Airflow, restore drill

### Remote access (replaces AWS Phase 11)

No SSH is needed: the cluster is on your PC. Open each UI with a plain port-forward in its own PowerShell window:

```powershell
# Jenkins → http://localhost:8080
kubectl -n jenkins port-forward svc/jenkins 8080:8080
```
```powershell
# Airflow → http://localhost:8081
kubectl -n airflow port-forward svc/airflow-api-server 8081:8080
```

### Jenkins: follow [AWS Phase 12](docs/aws-k8s/12-jenkins.md)

Changes:
- 🐧 commands → 🐚 Git Bash. Skip `cd ~/sysdesign && git pull` (you're in the repo) and `tmux`.
- 12.5: skip the `ssh -L …` tunnel and use the port-forward above.
- Builds run on your PC, so BuildKit produces **amd64** images natively and pushes them as `:<sha>` and `:latest`.
- ⚠️ **Don't run this Jenkins and an AWS Jenkins at the same time.** Both push `:latest`, and each would overwrite the other's architecture. Pick one environment for CI.

- [ ] AWS Phase 12 checkpoint passed locally

### Airflow: follow [AWS Phase 13](docs/aws-k8s/13-airflow.md)

Changes:
- **Skip 13.1–13.4** (S3 bucket, IAM role, `backup-config`). There's no cloud storage locally.
- Everything from **13.5** onward is the same, including the DAG file, unchanged. Without a `backup-config` ConfigMap, the backup DAG's upload task logs *"BACKUP_BUCKET not set: keeping backups on the local volume only"* and succeeds.
- 13.9: skip the S3 console check. Instead confirm the dump in the `pg_dump` task's log listing.
- 13.11: run the commands in 🐚 Git Bash. `winpty` isn't needed (no `-t`).

- [ ] AWS Phase 13 checkpoint passed (minus S3)

### Copy backups to your PC (your off-cluster copy)

Locally, "off-site" means "off-cluster". Copy the dumps somewhere that survives `k3d cluster delete`, e.g. a folder that OneDrive or Google Drive syncs.

**Where:** 🐚 Git Bash

```bash
kubectl -n airflow apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: backup-copier
spec:
  restartPolicy: Never
  containers:
    - name: c
      image: busybox:1.37
      command: ["sleep", "600"]
      volumeMounts:
        - name: backups
          mountPath: /backups
  volumes:
    - name: backups
      persistentVolumeClaim:
        claimName: sysdesign-backups
EOF
kubectl -n airflow wait --for=condition=Ready pod/backup-copier
mkdir -p /a/k3d-backups && cd /a/k3d-backups
for f in $(kubectl -n airflow exec backup-copier -- ls /backups); do
  kubectl -n airflow cp "backup-copier:/backups/$f" "$f"
done
cd - > /dev/null
kubectl -n airflow delete pod backup-copier
ls -lh /a/k3d-backups
```
(The loop `cd`s into the target folder and copies to plain file names, because Windows `kubectl` misreads both `/a/...` and `A:\...` destinations.)

**Expected:** your `.sql.gz` dumps in `A:\k3d-backups`. Repeat weekly, or before deleting the cluster.

- [ ] Dumps copied to `A:\k3d-backups`

### Restore drill: follow [AWS Phase 14](docs/aws-k8s/14-restore-drill.md) steps 14.1–14.4

Run in 🐚 Git Bash. Use `winpty kubectl exec -it …` if the interactive shell misbehaves.

- [ ] Restore drill passed

---

## Phase L9 — Daily use

| Task | Command (🪟 PowerShell) |
|---|---|
| **Start a session** | Start Docker Desktop, then `k3d cluster start sysdesign` |
| Get today's public URL | `kubectl -n tunnel logs deploy/cloudflared \| Select-String trycloudflare.com` |
| Everything healthy? | `kubectl get pods -A \| Select-String -NotMatch 'Running\|Completed'` (only the header should print) |
| **End a session** (frees ~7 GB RAM) | `k3d cluster stop sysdesign` |
| Pause Airflow (saves ~2 GB) | `kubectl -n airflow scale deployment --all --replicas=0; kubectl -n airflow scale statefulset --all --replicas=0` |
| Resume Airflow | the same with `--replicas=1` |
| Pause Jenkins | `kubectl -n jenkins scale statefulset jenkins --replicas=0` (`=1` to resume) |
| Memory use | `kubectl top pods -A --sort-by=memory` and Docker Desktop's dashboard |
| Clean Docker leftovers | `docker system prune` (safe: doesn't touch the running cluster) |
| **Delete everything** ⚠️ | Copy backups first (L8), then `k3d cluster delete sysdesign`. Recreate from L3 |

Scheduled Airflow runs (02:00 / 03:00 UTC = 07:30 / 08:30 IST) only happen if the cluster is running then. Trigger `sysdesign_db_backup` by hand at the start of a session if you care about a fresh backup.

For rollbacks, secret rotation and Helm upgrades, [AWS Phase 15](docs/aws-k8s/15-operations.md)'s "Common tasks" and "Upgrades" sections apply as-is. Skip the start/stop, AWS-specific and OS-patching parts. To upgrade k3s locally, recreate the cluster with a newer `--image` after backing up.

---

## Phase L10 — (Optional) A fixed URL with your own domain

Quick tunnels are for testing: random URL, no uptime guarantee. For a stable address, use a **named tunnel**. It's still free, but it needs a domain whose DNS is on Cloudflare (domains cost ~$10/year; DuckDNS names can't be used).

1. 🌐 Add your domain to Cloudflare (free plan) and switch its nameservers at your registrar as instructed.
2. 🌐 Cloudflare dashboard → **Zero Trust** → **Networks** → **Tunnels** → **Create a tunnel** → **Cloudflared** → name `sysdesign` → copy the **token** from the install command it shows.
3. 🌐 In the tunnel's **Public Hostname** tab: subdomain `quest`, your domain, service type **HTTP**, URL `traefik.kube-system.svc.cluster.local:80`.
4. 🐚 Store the token in the cluster:
   ```bash
   read -rsp 'Tunnel token: ' t; echo
   kubectl -n tunnel create secret generic cloudflared-token --from-literal=token="$t"; unset t
   ```
5. 🪟 In `k8s/local/cloudflared.yaml`, replace the `args:` line with:
   ```yaml
          args: ["tunnel", "run"]
          env:
            - name: TUNNEL_TOKEN
              valueFrom:
                secretKeyRef:
                  name: cloudflared-token
                  key: token
   ```
   Then `kubectl apply -f k8s/local/cloudflared.yaml`.
6. 🪟 In `k8s/local/10-config.yaml`, set `ALLOWED_HOSTS: quest.<your-domain>,localhost` and `CSRF_TRUSTED_ORIGINS: https://quest.<your-domain>` (both namespaces), apply it, and `kubectl -n sysdesign rollout restart deploy/web`.

**Expected:** `https://quest.<your-domain>` serves the app, and the URL stays the same across restarts.

---

## Troubleshooting (local-specific)

For everything else, see [AWS Phase 16](docs/aws-k8s/16-troubleshooting.md). The Kubernetes, app, Jenkins and Airflow sections apply unchanged.

| Symptom | Likely cause | Fix |
|---|---|---|
| `k3d cluster create` fails: `port is already allocated` | Something on your PC uses 6550 or 8088 | Pick other ports in L3.1, e.g. `--api-port 127.0.0.1:6551`, `--port "127.0.0.1:8089:80@loadbalancer"` |
| `kubectl` says `connection refused` to `127.0.0.1:6550` | Cluster stopped or Docker Desktop not running | Start Docker Desktop, then `k3d cluster start sysdesign` |
| `kubectl` talks to the wrong cluster | Context switched | `kubectl config use-context k3d-sysdesign` |
| Git Bash: `kubectl exec … /bin/cat` fails with a `C:/Program Files/Git/...` path | MSYS path conversion | `export MSYS_NO_PATHCONV=1` (L2.2) |
| Git Bash: `-it` command hangs or `Unable to use a TTY` | mintty TTY | Prefix with `winpty` |
| Pods `Evicted` / `OOMKilled`; PC very slow | WSL memory limit reached | Pause Airflow or Jenkins (L9); lower other apps; adjust `.wslconfig` (L1.2) |
| Docker Desktop: "disk full" | Images + caches | `docker system prune`; check `A:` free space; make sure L1.1 moved the data |
| Tunnel URL shows **502 / Bad gateway** | Traefik or web not ready, or the tunnel's target is wrong | `kubectl -n tunnel logs deploy/cloudflared`; `curl.exe http://localhost:8088/accounts/login/` works? |
| Tunnel URL shows **400 Bad Request** | Hostname not allowed | `ALLOWED_HOSTS` must contain `.trycloudflare.com` (L6) |
| Login: **CSRF verification failed** via tunnel | `X-Forwarded-Proto` overwritten | Phase L4 trustedIPs; Phase 7.1 settings in the image |
| Old tunnel URL stopped working | cloudflared restarted → new URL | Get the current one (L9) |
| BuildKit error mentioning `overlay` / `mount` in Jenkins | Overlay-in-overlay isn't supported in this Docker setup | In the Jenkinsfile's buildkit container, add `env: [{name: BUILDKITD_FLAGS, value: "--oci-worker-snapshotter=native"}]` |
| Jenkins build is very slow | Normal for the first build; later builds use the registry cache | Check `kubectl top pods -n jenkins`; pause Airflow while building |
