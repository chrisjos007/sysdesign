# Phase 0 — Concepts primer

[← Guide home](../../ORACLE_K8S_DEPLOYMENT.md) · Next: [Phase 1 →](01-accounts-and-local-prep.md)

You don't need to memorize this. Read it once, then come back when a later step uses a term you don't recognize. Each entry says **where it shows up in this project**.

---

## Oracle Cloud (OCI)

| Term | Meaning | In this project |
|---|---|---|
| **Tenancy** | Your Oracle Cloud account | Created at signup |
| **Home region** | The data-center region your account is tied to. Always Free compute only runs here, and you can't change it later | Picked at signup |
| **Compartment** | A folder for cloud resources, used for permissions and billing | Everything goes in the root compartment |
| **Availability Domain (AD)** | A separate data center within a region. Some regions have 1, some have 3 | If one AD is out of ARM capacity, try another |
| **Shape** | A VM size and type. `VM.Standard.A1.Flex` is the ARM (Ampere) shape where you choose the OCPUs and memory | 2 OCPU / 12 GB |
| **OCPU** | Oracle's CPU unit. On A1, 1 OCPU = 1 physical ARM core | Kubernetes sees 2 CPUs |
| **VCN** | Virtual Cloud Network, your private network in OCI | Created with the VM |
| **Security List** | A firewall attached to a subnet, applied **outside** the VM | Opens 22, 80, 443 |
| **Object Storage** | S3-like file storage (buckets). It has an S3-compatible API | Nightly DB backups |
| **Customer Secret Key** | An access key + secret pair for the S3-compatible API | Used by the backup upload task |

## Linux / networking

| Term | Meaning | In this project |
|---|---|---|
| **iptables** | The Linux kernel firewall. The **INPUT** chain covers traffic *to* the VM; the **FORWARD** chain covers traffic the VM *routes*, which includes all pod traffic | Oracle's image blocks FORWARD, so you unblock it |
| **SSH tunnel** (`ssh -L`) | Forwards a port on your PC through the SSH connection to a port on the server | How you reach the Jenkins/Airflow UIs |
| **DNS A record** | Maps a hostname to an IPv4 address | DuckDNS maps your hostname → VM IP |
| **TLS termination** | The point where HTTPS is decrypted. Behind it, traffic is plain HTTP | Traefik terminates TLS; Django sees HTTP |
| **tmux** | Keeps terminal sessions alive if your SSH connection drops | Used for long installs |

## Containers

| Term | Meaning | In this project |
|---|---|---|
| **Image** | A packaged filesystem + start command, built from a `Dockerfile` | `ghcr.io/chrisjos007/sysdesign-quest` |
| **Tag** | A label on an image version, e.g. `:latest` or `:a1b2c3d4` | Jenkins pushes the commit SHA **and** `latest` |
| **Registry** | Where images are stored | GitHub Container Registry (GHCR) |
| **Architecture** | The CPU type an image is built for: `amd64` (Intel/AMD) or `arm64` | The VM is arm64, and your PC is amd64 |
| **containerd** | The container runtime k3s uses. There's no Docker on the VM | — |
| **BuildKit** | The image builder behind `docker build`. It can run on its own | Builds images inside Jenkins pods |

## Kubernetes objects

| Object | Meaning | In this project |
|---|---|---|
| **Cluster / Node** | The whole Kubernetes system and the machines in it | One node: the VM |
| **Namespace** | A folder for objects. Names, permissions and policies are scoped to it | `sysdesign`, `jenkins`, `airflow`, `cert-manager`, `kube-system` |
| **Pod** | One or more containers scheduled together, sharing a network address. Pods are disposable | Every running thing |
| **Deployment** | Keeps N identical pods running and does rolling updates | `web`, Airflow's api-server |
| **StatefulSet** | Like a Deployment, but each pod gets a stable name (`postgres-0`) and its own disk | `postgres`, `jenkins`, Airflow scheduler |
| **Job** | Runs pods until they complete successfully once | `migrate` (DB migrations on each deploy) |
| **Service** | A stable DNS name and virtual IP that load-balances to pods matching a label selector | `postgres.sysdesign.svc.cluster.local`, `web` |
| **Ingress** | An HTTP routing rule: hostname/path → Service | `sysdesignquest.duckdns.org` → `web` |
| **Ingress controller** | The proxy that implements Ingress rules | Traefik (built into k3s) |
| **ConfigMap** | Non-secret key/value settings, usually injected as environment variables | `sysdesign-config` (DEBUG, ALLOWED_HOSTS…) |
| **Secret** | Like a ConfigMap, but for sensitive values. Base64-encoded, not encrypted | `sysdesign-secrets`, `postgres-superuser`… |
| **PersistentVolumeClaim (PVC)** | A request for disk space that survives pod restarts | Postgres data, Jenkins home, backups |
| **StorageClass** | How PVCs get their disks. k3s's `local-path` uses folders on the VM's disk | Default for everything |
| **Probe** | A health check. *Readiness*: send traffic now? *Liveness*: restart the container? | `web` has both |
| **Requests / limits** | Requests = reserved capacity (used for scheduling). Limits = hard caps (going over the memory limit gets the container killed, "OOMKilled") | Sized to fit 2 CPU / 12 GB |
| **NetworkPolicy** | A firewall between pods | Locks the web pod down |
| **ServiceAccount** | An identity for pods that talk to the Kubernetes API | `jenkins-deployer` |
| **Role / RoleBinding (RBAC)** | "This identity may do these verbs on these resources in this namespace" | Jenkins may only update `web` and run the migrate Job |
| **CRD** | Custom Resource Definition: new object types added by an extension | cert-manager's `Certificate`, `ClusterIssuer` |
| **Controller / operator** | A program that watches objects and makes reality match them | cert-manager, Traefik, and Kubernetes itself |

## Tools

| Tool | Meaning |
|---|---|
| **kubectl** | The Kubernetes command-line client. `kubectl get/describe/logs/apply/exec` are the ones you'll use most |
| **kubeconfig** | The file telling kubectl which cluster to talk to and with which credentials (`~/.kube/config`) |
| **Helm** | A package manager for Kubernetes. A **chart** is a package; a **release** is an installed copy; a **values file** configures it |
| **k3s** | A lightweight, certified Kubernetes distribution: a single binary including Traefik, CoreDNS, local-path storage, metrics-server and a NetworkPolicy controller |

## Jenkins

| Term | Meaning |
|---|---|
| **Controller** | The Jenkins server: UI, job configuration, scheduling |
| **Agent** | Where builds actually run. Here, a fresh pod per build, created by the Kubernetes plugin and deleted afterwards |
| **Jenkinsfile** | The pipeline definition, stored in the repo ("pipeline as code") |
| **Stage / step** | A named phase of a pipeline / one action within it |
| **Credential** | A secret stored in Jenkins, referenced by ID in the Jenkinsfile (`ghcr`, `airflow-api`) |
| **pollSCM** | Jenkins checks git every N minutes and builds if there are new commits |

## Airflow

| Term | Meaning |
|---|---|
| **DAG** | A workflow: tasks plus the order they run in, defined in Python |
| **Task / operator** | One unit of work / the template for it. **KubernetesPodOperator (KPO)** runs a task as its own pod |
| **DAG run / task instance** | One execution of a DAG / of a task within that run |
| **Scheduler** | Decides what should run and when |
| **DAG processor** | Parses DAG files |
| **API server** | Serves the web UI and REST API (Airflow 3) |
| **Triggerer** | Runs deferrable (async-waiting) tasks |
| **Executor** | How tasks get run. **LocalExecutor** runs them as processes of the scheduler, which is cheap and fine for one node |
| **git-sync** | A sidecar container that keeps pulling DAG files from a git repo |
| **Metadata DB** | Airflow's own database of runs, users and state (here, the `airflow` database in your Postgres) |
