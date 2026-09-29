# SysDesign Quest on AWS + Kubernetes

A hands-on, step-by-step guide to running SysDesign Quest on a single **AWS EC2** instance, with:
- **Kubernetes (k3s)** running everything,
- **Jenkins** for CI/CD: test → build → push → migrate → deploy on every commit,
- **Airflow** for scheduled operations: nightly backups to S3, housekeeping and content reseeds.

The existing Render + Neon deployment ([DEPLOYMENT.md](DEPLOYMENT.md)) is unaffected and keeps running. This is a separate, second environment that you build yourself to learn the stack.

> **Want it completely free?** The same stack runs on your own PC: [LOCAL_K3D_DEPLOYMENT.md](LOCAL_K3D_DEPLOYMENT.md) (k3d + Cloudflare Tunnel).

**Checked against (Sep 2026):** k3s `v1.36.4+k3s1` (stable channel) · Airflow Helm chart `1.22.0` (Airflow `3.2.2`) · Jenkins Helm chart `5.9.x` (Jenkins `2.568.x`) · cert-manager (current `jetstack` chart). If versions have moved on, the steps should still apply. Where a setting name has changed, the chart's own `values.yaml` has the final say.

---

## 💰 What this costs

**This is not free.** Your AWS free trial has ended, and even an active one wouldn't cover an instance big enough for Kubernetes + Jenkins + Airflow. You pay per second while the instance is **running**. Stop it when you're not using it and the compute charge stops.

Approximate on-demand prices (Sep 2026); **check the EC2 console for your region's exact numbers**:

| Item | Mumbai (`ap-south-1`) | N. Virginia (`us-east-1`) | Charged when |
|---|---|---|---|
| EC2 `t4g.large` (2 vCPU, 8 GB, ARM) | ~$0.045/hr | ~$0.067/hr | Running |
| Public IPv4 address | $0.005/hr | $0.005/hr | Running (auto-assigned IP) |
| EBS gp3 disk, 40 GB | ~$3.5/month | ~$3.2/month | Always, even stopped |
| S3 backups (a few MB) | cents | cents | Always |
| Data transfer out | first 100 GB/month free | same | — |

| Usage pattern | Mumbai, approx. per month |
|---|---|
| **Running ~4 hours a day** (stop it after each session) | **~$10** |
| Running 24/7 | ~$40 |

The guide sets a **budget alert** (Phase 2) so you're emailed before costs surprise you, and a **start/stop routine** (Phase 15) so stopping the instance is a one-liner.

**Why not EKS (AWS's managed Kubernetes)?** The EKS control plane alone costs $0.10/hr (~$73/month) before any worker nodes. k3s on one EC2 instance teaches the same Kubernetes for a fraction of that.

---

## How to use this guide

1. **Work through the phases in order.** Each phase is its own file (linked below) and builds on the one before it.
2. **Each step tells you where to run it:**

   | Label | Meaning |
   |---|---|
   | 🪟 **Windows** | PowerShell on your PC, in the repo folder `A:\New folder (2)\sysdesign_quest` unless stated otherwise |
   | 🐧 **VM** | A shell on the EC2 instance (you get there with `ssh quest-vm` after Phase 2) |
   | ☁️ **AWS Console** | The AWS web console at console.aws.amazon.com |
   | 🌐 **Browser** | Any other web UI: GitHub, DuckDNS, Jenkins, Airflow, the app |

3. **Every phase ends with a ✅ Checkpoint.** Don't start the next phase until every checkpoint item passes. Most problems are much easier to fix in the phase where they happen.
4. **Tick the boxes** (`- [ ]` → `- [x]`) as you go if you're reading this in VS Code or on GitHub.
5. **"Expected" output is illustrative.** Names, ages and IDs will differ. Look for the parts that matter, such as `Ready`, `Running`, `True` or `200`.
6. **When something fails:** read the step's *If it fails* note, then [Troubleshooting](docs/aws-k8s/16-troubleshooting.md).

### Placeholders

Replace these wherever they appear:

| Placeholder | What it is | Where you get it |
|---|---|---|
| `<PUBLIC_IP>` | The instance's current public IPv4 address | Phase 2 (changes on every stop/start; Phase 3 keeps DNS in sync automatically) |
| `<REGION>` | Your AWS region code, e.g. `ap-south-1` | Phase 2 |
| `<BACKUP_BUCKET>` | Your S3 bucket name (globally unique), e.g. `sysdesignquest-backups-7f3k` | Phase 13 |
| `<ACCOUNT_ID>` | Your 12-digit AWS account ID | Phase 13 |

`chrisjos007` (your GitHub user), `sysdesign` (your repo) and `sysdesignquest.duckdns.org` (your app hostname) are already filled in.

### Your values sheet

Keep this filled in somewhere private, e.g. a note in your password manager. **Put only non-secret values here.** Passwords live in the password manager itself.

```
APP_HOST        = sysdesignquest.duckdns.org
AWS REGION      =
AWS ACCOUNT ID  =
INSTANCE ID     =             (i-0…)
BACKUP BUCKET   =
```

---

## Phases

| # | Phase | Time | You'll learn |
|---|---|---|---|
| 0 | [Concepts primer](docs/aws-k8s/00-concepts.md) | 20 min | The AWS, Kubernetes, Helm, Jenkins and Airflow vocabulary used everywhere else |
| 1 | [Accounts & local prep](docs/aws-k8s/01-accounts-and-local-prep.md) | 30 min | GHCR tokens, DuckDNS, SSH keys |
| 2 | [AWS account & EC2 instance](docs/aws-k8s/02-aws-ec2.md) | 45 min | Account safety (MFA, IAM, budgets), key pairs, security groups, Graviton instances |
| 3 | [Network & DNS](docs/aws-k8s/03-network-and-dns.md) | 20 min | Security groups in practice, keeping DNS in sync with a changing IP |
| 4 | [VM baseline](docs/aws-k8s/04-vm-baseline.md) | 15 min | Patching, tmux, working on a remote server |
| 5 | [Install k3s](docs/aws-k8s/05-k3s.md) | 20 min | What a Kubernetes distribution installs, kubeconfig, Helm |
| 6 | [cert-manager & TLS issuers](docs/aws-k8s/06-cert-manager.md) | 15 min | ACME / Let's Encrypt, CRDs, controllers |
| 7 | [Containerize the app](docs/aws-k8s/07-containerize-app.md) | 45 min | Dockerfiles, reverse-proxy settings in Django |
| 8 | [First image push](docs/aws-k8s/08-first-image.md) | 20 min | Registries, multi-architecture images |
| 9 | [Secrets & Postgres](docs/aws-k8s/09-secrets-and-postgres.md) | 40 min | Namespaces, ConfigMaps, Secrets, StatefulSets, PVCs |
| 10 | [App, ingress & HTTPS](docs/aws-k8s/10-app-ingress-tls.md) | 60 min | Deployments, Services, Ingress, Jobs, NetworkPolicies |
| 11 | [Remote access](docs/aws-k8s/11-remote-access.md) | 10 min | SSH tunnels + `port-forward` |
| 12 | [Jenkins CI/CD](docs/aws-k8s/12-jenkins.md) | 90 min | Kubernetes build agents, BuildKit, RBAC, pipelines as code |
| 13 | [Airflow operations](docs/aws-k8s/13-airflow.md) | 90 min | DAGs, KubernetesPodOperator, git-sync, S3, IAM roles |
| 14 | [Restore drill](docs/aws-k8s/14-restore-drill.md) | 20 min | Proving your backups work |
| 15 | [Operating it](docs/aws-k8s/15-operations.md) | reference | Start/stop routine, costs, rollbacks, rotations, upgrades |
| 16 | [Troubleshooting](docs/aws-k8s/16-troubleshooting.md) | reference | Symptom → cause → fix |

**Total:** 6–10 hours across a few sessions. Phases 1–10 get the app live. Phases 11–14 add the automation.

**Good stopping points:** the end of any phase. **Stop the instance between sessions** (Phase 15 shows how). Everything comes back when you start it again.

---

## What you're building

```
                          Internet
                             │ :80 / :443
┌────────────────────────────▼──────────────────────────────────────┐
│ AWS default VPC — Security group allows 22 (you), 80, 443 only    │
│ ┌───────────────────────────────────────────────────────────────┐ │
│ │ EC2 t4g.large · 2 vCPU · 8 GB · Ubuntu 24.04 (arm64/Graviton) │ │
│ │ k3s single-node cluster                                       │ │
│ │                                                               │ │
│ │  kube-system   Traefik (ingress) · CoreDNS · metrics-server   │ │
│ │  cert-manager  Let's Encrypt TLS certificates                 │ │
│ │  sysdesign     web (Django + gunicorn) ──► postgres (EBS)     │ │
│ │  jenkins       controller + short-lived build pods            │ │
│ │  airflow       scheduler · api-server · dag-processor ·       │ │
│ │                triggerer + short-lived task pods              │ │
│ └───────────────────────────────────────────────────────────────┘ │
│   IAM role on the instance → may write backups to one S3 bucket   │
└───────────────────────────────────────────────────────────────────┘
 You ──SSH tunnel──► Jenkins UI / Airflow UI   (never exposed publicly)
 Jenkins ──► ghcr.io (container images)      Airflow ──► S3 (backups)
 Instance boots ──► updates DuckDNS with its new public IP
```

**Pipeline flow**

```
git push ─► Jenkins polls (5 min) ─► test ─► build arm64 image ─► push ghcr.io
        ─► run migrate Job ─► rolling update of web ─► [seed files changed?] ─► trigger Airflow reseed DAG

Airflow schedules:  02:00 UTC  pg_dump → backups volume → S3
                    03:00 UTC  manage.py clearsessions
                    on demand  seed_content + seed_games
```
(Scheduled runs only happen while the instance is running. If it was stopped at 02:00, that night's backup is skipped.)

**Who does what**
- **Kubernetes** runs and restarts everything, handles networking and TLS, and isolates the workloads from each other.
- **Jenkins** is event-driven CI/CD. Each commit is tested, built into an image and rolled out.
- **Airflow** runs scheduled, retryable operations work and keeps a run history. Jenkins hands off to it when content changes.

### Key decisions (and why)

| Decision | Why |
|---|---|
| **k3s on one EC2 instance**, not EKS | EKS's control plane alone costs ~$73/month. k3s is certified Kubernetes with Traefik, local storage and a NetworkPolicy controller built in. |
| **`t4g.large` (Graviton ARM)** | 8 GB is the minimum that fits the app + Jenkins + Airflow. Graviton is ~20% cheaper than the equivalent Intel `t3.large`. |
| **Burstable credits set to "Standard"** | T-family instances in "Unlimited" mode bill extra when CPU stays high. "Standard" throttles instead of charging. |
| **Postgres inside the cluster** (StatefulSet on EBS) | RDS would cost more than the instance. Airflow's metadata DB shares the same server. |
| **Backups to S3 via an IAM role** | No access keys to create, store or rotate. The role may only write to one bucket prefix and can't delete. |
| **DuckDNS updated on boot** | The auto-assigned public IP changes on each stop/start. A tiny boot service updates DNS, which is cheaper than an Elastic IP (charged even while the instance is stopped). |
| **Images on GHCR, public package** | Your GitHub repo is already public, so a public image leaks nothing new and needs no pull secret. Secrets are **never** baked into the image. |
| **BuildKit inside Jenkins build pods** | k3s uses containerd, not Docker. BuildKit builds natively on arm64 with no Docker daemon. |
| **Jenkins/Airflow UIs only reachable over SSH tunnels** | Admin UIs on the public internet are an avoidable risk. Only the app gets a public hostname. |

### Resource budget (must fit 2 vCPU / 8 GB)

Kubernetes places pods using their **requests**, not what they actually use. The sum of CPU requests must stay under **2000m** (2 vCPUs), or new pods sit in `Pending`. All manifests in this guide are sized to fit.

| Workload | CPU request | Memory request / limit |
|---|---|---|
| k3s system (Traefik, CoreDNS, metrics-server) | ~200m | ~600 MB (actual) |
| cert-manager | — | ~150 MB (actual) |
| postgres | 100m | 256 Mi / 1 Gi |
| web | 100m | 256 Mi / 768 Mi |
| Jenkins controller | 250m | 1 Gi / 2 Gi |
| Jenkins build pod (only during builds) | 450m | ~1 Gi / 3.5 Gi |
| Airflow (4 components) | 500m | ~2 Gi / 4 Gi |
| **Total** | **~1600m** | **~5.5 GB steady, ~6.5–7 GB during builds** |

8 GB is **tight** with everything running. If builds get slow or pods are OOMKilled, pause Airflow during a Jenkins session (Phase 15 shows the one-liner), or use `t4g.xlarge` (16 GB, roughly double the price).

### Files you'll add to the repo

| File | Created in | Purpose |
|---|---|---|
| `config/settings.py` (edit) | Phase 7 | Trust the TLS proxy; secure cookies |
| `Dockerfile`, `.dockerignore` | Phase 7 | Container image |
| `k8s/05-cluster-issuers.yaml` | Phase 6 | Let's Encrypt staging + prod issuers |
| `k8s/00-namespaces.yaml`, `k8s/10-config.yaml`, `k8s/20-postgres.yaml` | Phase 9 | Namespaces, settings, database |
| `k8s/30-web.yaml`, `k8s/40-ingress.yaml`, `k8s/50-network-policies.yaml`, `k8s/templates/migrate-job.yaml` | Phase 10 | The app itself |
| `jenkins/values.yaml`, `k8s/60-jenkins-rbac.yaml`, `Jenkinsfile` | Phase 12 | CI/CD |
| `k8s/70-airflow-storage.yaml`, `airflow/values.yaml`, `airflow/dags/sysdesign_dags.py` | Phase 13 | Scheduled operations |

> ⚠️ **The repo is public.** No password, key, token or connection string goes into any of these files. Secrets are created directly in the cluster with `kubectl create secret` (Phase 9) and kept in your password manager.
