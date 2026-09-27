# SysDesign Quest on Oracle Cloud + Kubernetes

A hands-on, step-by-step guide to running SysDesign Quest on an **Oracle Cloud Always Free** ARM VM, with:
- **Kubernetes (k3s)** running everything,
- **Jenkins** for CI/CD: test → build → push → migrate → deploy on every commit,
- **Airflow** for scheduled operations: nightly backups, housekeeping and content reseeds.

The existing Render + Neon deployment ([DEPLOYMENT.md](DEPLOYMENT.md)) is unaffected and keeps running. This is a separate, second environment that you build yourself to learn the stack.

**Checked against (Sep 2026):** k3s `v1.36.4+k3s1` (stable channel) · Airflow Helm chart `1.22.0` (Airflow `3.2.2`) · Jenkins Helm chart `5.9.x` (Jenkins `2.568.x`) · cert-manager (current `jetstack` chart) · Oracle Always Free A1 limit of **2 OCPU / 12 GB** (halved in June 2026). If versions have moved on, the steps should still apply. Where a setting name has changed, the chart's own `values.yaml` has the final say.

---

## How to use this guide

1. **Work through the phases in order.** Each phase is its own file (linked below) and builds on the one before it.
2. **Each step tells you where to run it:**

   | Label | Meaning |
   |---|---|
   | 🪟 **Windows** | PowerShell on your PC, in the repo folder `A:\New folder (2)\sysdesign_quest` unless stated otherwise |
   | 🐧 **VM** | A shell on the Oracle VM (you get there with `ssh oci` after Phase 2) |
   | ☁️ **OCI Console** | The Oracle Cloud web console at cloud.oracle.com |
   | 🌐 **Browser** | Any other web UI: GitHub, DuckDNS, Jenkins, Airflow, the app |

3. **Every phase ends with a ✅ Checkpoint.** Don't start the next phase until every checkpoint item passes. Most problems are much easier to fix in the phase where they happen.
4. **Tick the boxes** (`- [ ]` → `- [x]`) as you go if you're reading this in VS Code or on GitHub.
5. **"Expected" output is illustrative.** Names, ages and IDs will differ. Look for the parts that matter, such as `Ready`, `Running`, `True` or `200`.
6. **When something fails:** read the step's *If it fails* note, then [Troubleshooting](docs/oracle-k8s/16-troubleshooting.md). Undo steps are given wherever an action is hard to reverse.

### Placeholders

Replace these wherever they appear:

| Placeholder | What it is | Where you get it |
|---|---|---|
| `<PUBLIC_IP>` | The VM's public IPv4 address | Phase 2 |
| `<REGION>` | Your OCI region identifier, e.g. `ap-mumbai-1` | Phase 2 |
| `<OCI_NAMESPACE>` | Your Object Storage namespace | Phase 13 |

`chrisjos007` (your GitHub user), `sysdesign` (your repo) and `sysdesignquest.duckdns.org` (your app hostname) are already filled in.

### Your values sheet

Keep this filled in somewhere private, e.g. a note in your password manager. **Put only non-secret values here.** Passwords live in the password manager itself.

```
PUBLIC_IP       =
APP_HOST        = sysdesignquest.duckdns.org
OCI REGION      =
OCI NAMESPACE   =
VM NAME         = sysdesign-k3s
```

---

## Phases

| # | Phase | Time | You'll learn |
|---|---|---|---|
| 0 | [Concepts primer](docs/oracle-k8s/00-concepts.md) | 20 min | The Kubernetes, Helm, Jenkins and Airflow vocabulary used everywhere else |
| 1 | [Accounts & local prep](docs/oracle-k8s/01-accounts-and-local-prep.md) | 30 min | GHCR tokens, DuckDNS, SSH keys |
| 2 | [Oracle account & VM](docs/oracle-k8s/02-oracle-vm.md) | 45 min+ | OCI tenancy, budgets, VCNs, A1 shapes |
| 3 | [Firewalls](docs/oracle-k8s/03-firewalls.md) | 20 min | Cloud vs host firewalls, why pods need FORWARD |
| 4 | [VM baseline](docs/oracle-k8s/04-vm-baseline.md) | 15 min | Patching, tmux, working on a remote server |
| 5 | [Install k3s](docs/oracle-k8s/05-k3s.md) | 20 min | What a Kubernetes distribution installs, kubeconfig, Helm |
| 6 | [cert-manager & TLS issuers](docs/oracle-k8s/06-cert-manager.md) | 15 min | ACME / Let's Encrypt, CRDs, controllers |
| 7 | [Containerize the app](docs/oracle-k8s/07-containerize-app.md) | 45 min | Dockerfiles, reverse-proxy settings in Django |
| 8 | [First image push](docs/oracle-k8s/08-first-image.md) | 20 min | Registries, multi-architecture images |
| 9 | [Secrets & Postgres](docs/oracle-k8s/09-secrets-and-postgres.md) | 40 min | Namespaces, ConfigMaps, Secrets, StatefulSets, PVCs |
| 10 | [App, ingress & HTTPS](docs/oracle-k8s/10-app-ingress-tls.md) | 60 min | Deployments, Services, Ingress, Jobs, NetworkPolicies |
| 11 | [Remote access](docs/oracle-k8s/11-remote-access.md) | 10 min | SSH tunnels + `port-forward` |
| 12 | [Jenkins CI/CD](docs/oracle-k8s/12-jenkins.md) | 90 min | Kubernetes build agents, BuildKit, RBAC, pipelines as code |
| 13 | [Airflow operations](docs/oracle-k8s/13-airflow.md) | 90 min | DAGs, KubernetesPodOperator, git-sync, Object Storage |
| 14 | [Restore drill](docs/oracle-k8s/14-restore-drill.md) | 20 min | Proving your backups work |
| 15 | [Operating it](docs/oracle-k8s/15-operations.md) | reference | Day-2 runbook: rollbacks, rotations, upgrades |
| 16 | [Troubleshooting](docs/oracle-k8s/16-troubleshooting.md) | reference | Symptom → cause → fix |

**Total:** 6–10 hours across a few sessions. Phases 1–10 get the app live. Phases 11–14 add the automation.

**Good stopping points:** the end of any phase. Everything you've built keeps running on the VM between sessions.

---

## What you're building

```
                          Internet
                             │ :80 / :443
┌────────────────────────────▼──────────────────────────────────────┐
│ OCI VCN — Security List allows 22 (you), 80, 443. Nothing else.   │
│ ┌───────────────────────────────────────────────────────────────┐ │
│ │ VM.Standard.A1.Flex · 2 OCPU · 12 GB · Ubuntu 24.04 (arm64)   │ │
│ │ k3s single-node cluster                                       │ │
│ │                                                               │ │
│ │  kube-system   Traefik (ingress) · CoreDNS · metrics-server   │ │
│ │  cert-manager  Let's Encrypt TLS certificates                 │ │
│ │  sysdesign     web (Django + gunicorn) ──► postgres (PVC)     │ │
│ │  jenkins       controller + short-lived build pods            │ │
│ │  airflow       scheduler · api-server · dag-processor ·       │ │
│ │                triggerer + short-lived task pods              │ │
│ └───────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
 You ──SSH tunnel──► Jenkins UI / Airflow UI   (never exposed publicly)
 Jenkins ──► ghcr.io (container images)      Airflow ──► OCI Object Storage (backups)
```

**Pipeline flow**

```
git push ─► Jenkins polls (5 min) ─► test ─► build arm64 image ─► push ghcr.io
        ─► run migrate Job ─► rolling update of web ─► [seed files changed?] ─► trigger Airflow reseed DAG

Airflow schedules:  02:00 UTC  pg_dump → backups volume → OCI Object Storage
                    03:00 UTC  manage.py clearsessions
                    on demand  seed_content + seed_games
```

**Who does what**
- **Kubernetes** runs and restarts everything, handles networking and TLS, and isolates the workloads from each other.
- **Jenkins** is event-driven CI/CD. Each commit is tested, built into an image and rolled out.
- **Airflow** runs scheduled, retryable operations work and keeps a run history. In the real world you wouldn't use Airflow as a CI tool. Here it does the ops/data jobs it's designed for, and Jenkins hands off to it.

### Key decisions (and why)

| Decision | Why |
|---|---|
| **k3s on one VM**, not OKE (Oracle's managed Kubernetes) | Always Free gives only 2 OCPU / 12 GB in total. One node wastes the least. k3s is certified Kubernetes with Traefik, local storage and a NetworkPolicy controller built in. |
| **Postgres inside the cluster** (StatefulSet + PVC) | No external DB dependency. Airflow's metadata DB shares the same server, so the chart's bundled Bitnami Postgres isn't needed. |
| **Images on GHCR, public package** | Your GitHub repo is already public, so a public image leaks nothing new and needs no pull secret. Secrets are **never** baked into the image. |
| **BuildKit inside Jenkins build pods** | k3s uses containerd, not Docker. BuildKit builds natively on arm64 with no Docker daemon. |
| **Jenkins/Airflow UIs only reachable over SSH tunnels** | Admin UIs on the public internet are an avoidable risk. Only the app gets a public hostname. |
| **Free hostname from DuckDNS** | Let's Encrypt needs a real DNS name. Use your own domain if you have one. |
| **Oracle account upgraded to Pay As You Go** (recommended) | Always Free resources stay free. PAYG makes ARM capacity easier to get and exempts the VM from idle reclamation. A $1 budget alert is your safety net. |

### Resource budget (must fit 2 CPU / 12 GB)

Kubernetes places pods using their **requests**, not what they actually use. The sum of CPU requests must stay under **2000m** (2 cores), or new pods sit in `Pending`. All manifests in this guide are sized to fit.

| Workload | CPU request | Memory request / limit |
|---|---|---|
| k3s system (Traefik, CoreDNS, metrics-server) | ~200m | ~600 MB (actual) |
| cert-manager | — | ~150 MB (actual) |
| postgres | 100m | 256 Mi / 1 Gi |
| web | 100m | 256 Mi / 768 Mi |
| Jenkins controller | 250m | 1 Gi / 2 Gi |
| Jenkins build pod (only during builds) | 450m | ~1 Gi / 3.5 Gi |
| Airflow (4 components) | 500m | ~2 Gi / 4 Gi |
| **Total** | **~1600m** | **~5.5 GB steady, ~7 GB during builds** |

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
