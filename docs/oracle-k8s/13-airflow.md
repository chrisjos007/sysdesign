# Phase 13 — Airflow for scheduled operations

[← Phase 12](12-jenkins.md) · [Guide home](../../ORACLE_K8S_DEPLOYMENT.md) · Next: [Phase 14 →](14-restore-drill.md)

**Goal:** Airflow running on the cluster with three DAGs: nightly DB backups shipped to OCI Object Storage, daily Django housekeeping, and an on-demand content reseed that Jenkins triggers automatically.
**Time:** ~90 minutes.

---

## Background: how the pieces fit

```
GitHub repo ── airflow/dags/sysdesign_dags.py
      │ git-sync sidecar pulls every 60s
      ▼
dag-processor (parses DAGs) ──► metadata DB (the "airflow" database in your Postgres)
                                        ▲
scheduler (LocalExecutor) ──────────────┘
      │ for each task: create a pod (KubernetesPodOperator)
      ▼
task pods in namespace airflow:
  pg_dump (postgres:17) ─► /backups PVC ─► upload (aws-cli) ─► OCI Object Storage
  manage.py clearsessions / seed_content / seed_games (your app image)
api-server ── UI + REST API (reached via SSH tunnel; Jenkins calls it in-cluster)
```

Why **KubernetesPodOperator**: every task runs in its own pod with exactly the image it needs (Postgres tools, AWS CLI, your app). Airflow's own image never needs your app's dependencies, and a misbehaving task can't take the scheduler down with it.

---

## Step 13.1 — Create the backup bucket

**Where:** ☁️ ☰ → **Storage** → **Buckets** → **Create Bucket** (compartment: root)

| Field | Value |
|---|---|
| Bucket Name | `sysdesign-backups` |
| Default Storage Tier | Standard |
| Encryption | Oracle-managed keys |
| Visibility | Private (the default; never make a backup bucket public) |

→ **Create**. Open the bucket and note the **Namespace** shown in its details as `<OCI_NAMESPACE>` in your values sheet. It's a short random-looking string.

> The Always Free allowance is 20 GB of Object Storage. A compressed dump of this app is a few MB.

- [ ] Bucket created; namespace noted

---

## Step 13.2 — Create S3-compatible credentials

**Where:** ☁️ Top-right **profile icon** → **My profile** (or **User settings**) → **Customer secret keys** (under *Resources*/*Tokens and keys*) → **Generate secret key**

1. Name: `airflow-backups`.
2. **Copy the Secret key immediately.** It's shown only once. Save it to your password manager.
3. Close the dialog. The new key's **Access key** is in the list; copy it too.

- [ ] Access key + secret key saved

---

## Step 13.3 — Auto-delete old backups (retention)

**Where:** ☁️ Bucket `sysdesign-backups` → **Lifecycle Policy Rules** → **Create Rule**

| Field | Value |
|---|---|
| Name | `expire-after-30-days` |
| Target | Objects |
| Lifecycle Action | Delete |
| Number of days | 30 |
| State | Enabled |

→ **Create**.

**If it errors with a permissions message:** Object Storage needs permission to delete on your behalf. ☰ → **Identity & Security** → **Policies** → (root compartment) → **Create Policy**, name `objectstorage-lifecycle`, **Show manual editor**, statement:
```
Allow service objectstorage-<REGION> to manage object-family in tenancy
```
(e.g. `objectstorage-ap-mumbai-1`). Create it, then retry the rule.

- [ ] Lifecycle rule enabled

---

## Step 13.4 — Put the storage credentials in the cluster

**Where:** 🐧 VM

```bash
read -rp  'OCI namespace: ' OCI_NS
read -rp  'OCI region (e.g. ap-mumbai-1): ' OCI_REGION
read -rp  'Access key: ' OCI_AK
read -rsp 'Secret key: ' OCI_SK; echo
kubectl -n airflow create secret generic oci-s3 \
  --from-literal=AWS_ACCESS_KEY_ID="$OCI_AK" \
  --from-literal=AWS_SECRET_ACCESS_KEY="$OCI_SK" \
  --from-literal=AWS_DEFAULT_REGION="$OCI_REGION" \
  --from-literal=AWS_ENDPOINT_URL="https://${OCI_NS}.compat.objectstorage.${OCI_REGION}.oraclecloud.com" \
  --from-literal=AWS_REQUEST_CHECKSUM_CALCULATION=when_required \
  --from-literal=AWS_RESPONSE_CHECKSUM_VALIDATION=when_required
unset OCI_AK OCI_SK
```

- The variable names are the AWS CLI's standard ones. The AWS CLI talks to OCI through its S3-compatible endpoint (`AWS_ENDPOINT_URL`).
- The two `CHECKSUM` settings turn off newer AWS-CLI integrity headers that S3-compatible services such as OCI can reject.

**Check** the endpoint looks right (it's not secret):
```bash
kubectl -n airflow get secret oci-s3 -o jsonpath='{.data.AWS_ENDPOINT_URL}' | base64 -d; echo
```

**Expected:** `https://<namespace>.compat.objectstorage.<region>.oraclecloud.com`

**Quick connectivity test** from a throwaway pod:
```bash
kubectl -n airflow run s3test --rm -i --restart=Never --image=amazon/aws-cli:latest \
  --overrides='{"spec":{"containers":[{"name":"s3test","image":"amazon/aws-cli:latest","command":["bash","-c","aws configure set default.s3.addressing_style path && aws s3 ls s3://sysdesign-backups/ && echo S3-OK"],"envFrom":[{"secretRef":{"name":"oci-s3"}}]}]}}'
```

**Expected:** `S3-OK`. The bucket is empty, so nothing is listed above it.

**If you get `SignatureDoesNotMatch` / `InvalidAccessKeyId`:** re-create the secret carefully (`kubectl -n airflow delete secret oci-s3`, then repeat). A mistyped region or namespace in the endpoint is the most common cause.

- [ ] `S3-OK`

---

## Step 13.5 — Create the Airflow files

### `k8s/70-airflow-storage.yaml`

**Where:** 🪟 Windows

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: sysdesign-backups
  namespace: airflow
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 5Gi
```

A local staging area for dumps. The backup task writes here, and the upload task reads from here. Both run on the same node, so a ReadWriteOnce volume works. It keeps 7 days of local copies; Object Storage keeps 30.

### `airflow/values.yaml`

```yaml
# LocalExecutor: tasks run from the scheduler, so there's no Redis or Celery workers.
# Each task in our DAGs is itself a pod (KubernetesPodOperator), so the
# scheduler only orchestrates.
executor: LocalExecutor

# Use the cluster's own Postgres (Phase 9) instead of the chart's bundled one.
postgresql:
  enabled: false
redis:
  enabled: false
pgbouncer:
  enabled: false
statsd:
  enabled: false

# One secret holds all four keys; the chart reads the key names
# connection / fernet-key / api-secret-key / jwt-secret from it.
data:
  metadataSecretName: airflow-keys
fernetKeySecretName: airflow-keys
apiSecretKeySecretName: airflow-keys
jwtSecretName: airflow-keys

config:
  api:
    workers: 1          # default 4; each worker costs a few hundred MB

dags:
  gitSync:
    enabled: true
    repo: https://github.com/chrisjos007/sysdesign.git
    branch: master
    ref: master
    subPath: airflow/dags
    period: 60s

# With LocalExecutor the scheduler also runs the tasks, so the chart gives it
# a task-log volume sized for Celery workers (100Gi by default). Shrink it.
workers:
  celery:
    persistence:
      size: 5Gi

scheduler:
  resources:
    requests: {cpu: 200m, memory: 768Mi}
    limits: {memory: 1536Mi}
apiServer:
  resources:
    requests: {cpu: 100m, memory: 512Mi}
    limits: {memory: 1Gi}
dagProcessor:
  resources:
    requests: {cpu: 100m, memory: 384Mi}
    limits: {memory: 768Mi}
triggerer:
  resources:
    requests: {cpu: 100m, memory: 256Mi}
    limits: {memory: 512Mi}
```

| Setting | Why |
|---|---|
| `executor: LocalExecutor` | The chart default (Celery) adds Redis and worker pods, and there isn't room for them |
| `postgresql.enabled: false` + `data.metadataSecretName` | Use your Postgres (the `airflow` database) instead of a second, Bitnami-based one |
| `…SecretName: airflow-keys` | Stable keys from a secret. Without them the chart generates random ones, and those can change on upgrade, logging everyone out or making stored secrets unreadable |
| `config.api.workers: 1` | The API server's default of 4 processes costs >1 GB |
| `dags.gitSync` | DAGs come straight from `airflow/dags/` in your repo. Push a DAG change, and it's live within a minute |
| `workers.celery.persistence.size` | The scheduler's log volume, which would otherwise request 100 Gi |

### `airflow/dags/sysdesign_dags.py`

```python
"""Operational DAGs for SysDesign Quest, running on the same k3s cluster as the app.

Every task is its own pod (KubernetesPodOperator) in the `airflow` namespace,
using either the app image or a stock tool image, so the Airflow scheduler
only orchestrates and never needs the app's dependencies installed.
"""
import pendulum
from kubernetes.client import models as k8s

from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.sdk import DAG

NAMESPACE = 'airflow'
APP_IMAGE = 'ghcr.io/chrisjos007/sysdesign-quest:latest'
START = pendulum.datetime(2026, 9, 1, tz='UTC')

APP_ENV = [
    k8s.V1EnvFromSource(config_map_ref=k8s.V1ConfigMapEnvSource(name='sysdesign-config')),
    k8s.V1EnvFromSource(secret_ref=k8s.V1SecretEnvSource(name='sysdesign-secrets')),
]
OCI_S3_ENV = [k8s.V1EnvFromSource(secret_ref=k8s.V1SecretEnvSource(name='oci-s3'))]

BACKUPS_VOLUME = k8s.V1Volume(
    name='backups',
    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(claim_name='sysdesign-backups'),
)
BACKUPS_MOUNT = k8s.V1VolumeMount(name='backups', mount_path='/backups')


def pod_task(task_id, image, cmds, arguments, env_from, **kwargs):
    return KubernetesPodOperator(
        task_id=task_id,
        name=task_id.replace('_', '-'),
        namespace=NAMESPACE,
        image=image,
        cmds=cmds,
        arguments=arguments,
        env_from=env_from,
        get_logs=True,
        on_finish_action='delete_pod',
        container_resources=k8s.V1ResourceRequirements(
            requests={'cpu': '50m', 'memory': '128Mi'},
            limits={'memory': '512Mi'},
        ),
        **kwargs,
    )


def manage_py(task_id, *args):
    return pod_task(
        task_id, APP_IMAGE, ['python', 'manage.py'], list(args), APP_ENV,
        image_pull_policy='Always',
    )


default_args = {'retries': 2, 'retry_delay': pendulum.duration(minutes=5)}

with DAG(
    dag_id='sysdesign_db_backup',
    description='Nightly pg_dump of the app database, shipped to OCI Object Storage',
    schedule='0 2 * * *',
    start_date=START,
    catchup=False,
    is_paused_upon_creation=False,
    default_args=default_args,
    tags=['sysdesign', 'ops'],
):
    dump = pod_task(
        'pg_dump',
        'postgres:17',
        ['bash', '-c'],
        [
            'set -euo pipefail; '
            'f=/backups/sysdesign-$(date -u +%Y%m%dT%H%M%SZ).sql.gz; '
            'pg_dump --no-owner --no-acl "$DATABASE_URL" | gzip > "$f"; '
            'find /backups -name "*.sql.gz" -mtime +7 -delete; '
            'ls -lh /backups'
        ],
        APP_ENV,
        volumes=[BACKUPS_VOLUME],
        volume_mounts=[BACKUPS_MOUNT],
    )
    upload = pod_task(
        'upload_to_object_storage',
        'amazon/aws-cli:latest',
        ['bash', '-c'],
        [
            'set -euo pipefail; '
            'aws configure set default.s3.addressing_style path; '
            'aws s3 sync /backups s3://sysdesign-backups/postgres/ --exclude "*" --include "*.sql.gz"'
        ],
        OCI_S3_ENV,
        volumes=[BACKUPS_VOLUME],
        volume_mounts=[BACKUPS_MOUNT],
    )
    dump >> upload

with DAG(
    dag_id='sysdesign_maintenance',
    description='Daily Django housekeeping',
    schedule='0 3 * * *',
    start_date=START,
    catchup=False,
    is_paused_upon_creation=False,
    default_args=default_args,
    tags=['sysdesign', 'ops'],
):
    manage_py('clearsessions', 'clearsessions')

with DAG(
    dag_id='sysdesign_reseed_content',
    description='Re-run the idempotent seed commands; triggered by Jenkins or by hand',
    schedule=None,
    start_date=START,
    catchup=False,
    is_paused_upon_creation=False,
    tags=['sysdesign', 'content'],
):
    manage_py('seed_content', 'seed_content') >> manage_py('seed_games', 'seed_games')
```

Walkthrough:
- **`pod_task`**: one helper so every task gets the same namespace, log streaming (`get_logs`), cleanup (`delete_pod`) and small resource requests.
- **`manage_py`**: runs a Django management command in your app image, with the same ConfigMap and Secret as the web pod. `image_pull_policy='Always'` makes sure `:latest` is really the latest build.
- **Backup DAG** (02:00 UTC): `pg_dump` → gzip → `/backups`, prune local copies older than 7 days, then `aws s3 sync` uploads any dump that isn't in the bucket yet. `>>` means "upload runs after dump succeeds".
- **Why `$(date …)` rather than Airflow's `{{ ds }}`:** manually triggered runs in Airflow 3 have no logical date, so `{{ ds }}` isn't available for them.
- **`is_paused_upon_creation=False`**: new DAGs are active immediately instead of waiting for you to unpause them.
- **`catchup=False`**: don't back-fill runs for every day since `START`.
- **`retries: 2`**: a transient failure (e.g. an image pull hiccup) retries 5 minutes later before counting as failed.

- [ ] Three files created

---

## Step 13.6 — Commit, push, apply storage, install Airflow

**Where:** 🪟 Windows
```powershell
git add k8s/70-airflow-storage.yaml airflow/values.yaml airflow/dags/sysdesign_dags.py
git commit -m "Add Airflow values, backup storage and operational DAGs"
git push
```

**Where:** 🐧 VM (in `tmux`; variables loaded per Phase 9, Step 9.5)
```bash
cd ~/sysdesign && git pull
kubectl apply -f k8s/70-airflow-storage.yaml

kubectl -n airflow create secret generic airflow-keys \
  --from-literal=connection="postgresql://airflow:${AIRFLOW_DB_PASS}@postgres.sysdesign.svc.cluster.local:5432/airflow" \
  --from-literal=fernet-key="$AIRFLOW_FERNET_KEY" \
  --from-literal=api-secret-key="$AIRFLOW_API_SECRET" \
  --from-literal=jwt-secret="$AIRFLOW_JWT_SECRET"

helm repo add apache-airflow https://airflow.apache.org
helm repo update
helm search repo apache-airflow/airflow
```

`helm search` shows the chart version and Airflow version, e.g. `1.22.0  3.2.2`. Note them in your values sheet.

Install. The admin password goes in with `--set`, so it's never in the committed values file:
```bash
helm upgrade --install airflow apache-airflow/airflow -n airflow \
  -f airflow/values.yaml \
  --set createUserJob.defaultUser.password="$AIRFLOW_ADMIN_PASS" \
  --timeout 15m
```

The first install pulls about 1 GB of images and runs the database migrations, so allow 5–10 minutes. In a second window you can watch:
```bash
kubectl -n airflow get pods -w
```

**Expected** once it settles (names and container counts vary slightly by chart version):
```
airflow-api-server-…                  1/1   Running
airflow-dag-processor-…               2/2   Running     (+ git-sync sidecar)
airflow-scheduler-0                   2/2   Running
airflow-triggerer-0                   2/2   Running
airflow-run-airflow-migrations-…      0/1   Completed
airflow-create-user-…                 0/1   Completed
```

**If pods crash-loop with database errors:** `kubectl -n airflow logs <pod> --all-containers | tail -30`. Check the `airflow-keys` connection string (Step 9.9 shows how to test DB credentials from a pod), and that the `postgres` NetworkPolicy allows the `airflow` namespace.

- [ ] All Airflow pods Running or Completed

---

## Step 13.7 — Log in to the UI

**Where:** 🪟 Windows. Open the tunnel and leave it running:
```powershell
ssh -L 8081:127.0.0.1:8081 oci kubectl -n airflow port-forward svc/airflow-api-server 8081:8080
```

**Where:** 🌐 Browser → http://localhost:8081 → user **`admin`**, password = `AIRFLOW_ADMIN_PASS` from `~/.sysdesign-secrets`.

- [ ] Logged in

---

## Step 13.8 — Check the DAGs arrived

**Where:** 🌐 Airflow → **Dags** in the left navigation

**Expected** within about 2 minutes: `sysdesign_db_backup`, `sysdesign_maintenance` and `sysdesign_reseed_content`, all **active** (not paused), with no red import-error banner.

**If they don't appear:**
```bash
kubectl -n airflow logs deploy/airflow-dag-processor -c git-sync --tail=20     # did git-sync pull the repo?
kubectl -n airflow logs deploy/airflow-dag-processor --all-containers --tail=50 | grep -i error
```

An **import error** banner in the UI shows the Python traceback. The most common cause is a typo in the DAG file.

- [ ] Three DAGs visible and active

---

## Step 13.9 — Run a backup by hand

**Where:** 🌐 Airflow → `sysdesign_db_backup` → **Trigger** (▶) → confirm

**Where:** 🐧 VM. Watch the task pods come and go:
```bash
kubectl -n airflow get pods -w
```

**Expected:** a `pg-dump-…` pod runs and completes, then an `upload-to-object-storage-…` pod does the same.

**Where:** 🌐 Airflow → the run → click each task → **Logs**. `pg_dump`'s log ends with an `ls -lh` listing that includes a `sysdesign-…Z.sql.gz` file. The upload log shows `upload: /backups/… to s3://sysdesign-backups/postgres/…`.

**Where:** ☁️ Bucket `sysdesign-backups` → **Objects** → folder `postgres/` → your dump is there.

- [ ] Both tasks green; the dump is visible in Object Storage

---

## Step 13.10 — Run the reseed and maintenance DAGs by hand

**Where:** 🌐 Airflow → `sysdesign_reseed_content` → **Trigger**. Then `sysdesign_maintenance` → **Trigger**.

**Expected:** all tasks green. The `seed_content` / `seed_games` logs show the same output as when you ran them in Phase 10.

- [ ] Both DAGs succeed

---

## Step 13.11 — Create an API user for Jenkins

**Where:** 🐧 VM

Generate a password, keep it with the other secrets, and create the user with Airflow's CLI:
```bash
echo "AIRFLOW_JENKINS_PASS=$(openssl rand -hex 16)" >> ~/.sysdesign-secrets
set -a; source ~/.sysdesign-secrets; set +a

kubectl -n airflow exec deploy/airflow-api-server -- airflow users create \
  --role User --username jenkins \
  --firstname Jenkins --lastname CI --email jenkins@example.invalid \
  --password "$AIRFLOW_JENKINS_PASS"
```

**Expected:** `User "jenkins" created with role "User"`.

- **Role `User`** can trigger DAG runs but can't change configuration or other users (least privilege again).
- Update the copy of the secrets file in your password manager with the new line.

**Test the exact API calls Jenkins will make**, from inside the `jenkins` namespace:
```bash
kubectl -n jenkins run afapi --rm -i --restart=Never --image=alpine/k8s:1.36.4 \
  --env="AF_PASS=$AIRFLOW_JENKINS_PASS" -- sh -c '
    AF=http://airflow-api-server.airflow.svc.cluster.local:8080
    TOKEN=$(jq -n --arg p "$AF_PASS" "{username: \"jenkins\", password: \$p}" \
      | curl -sf -X POST "$AF/auth/token" -H "Content-Type: application/json" -d @- | jq -r .access_token)
    echo "token length: ${#TOKEN}"
    curl -sf "$AF/api/v2/dags/sysdesign_reseed_content" -H "Authorization: Bearer $TOKEN" | jq .dag_id'
```

**Expected:** `token length:` followed by a few hundred, then `"sysdesign_reseed_content"`.

**If it fails with 401/404:** open http://localhost:8081/docs (the live API docs for your exact Airflow version) and compare the `/auth/token` and `/api/v2/dags/...` endpoints with the ones used here and in the Jenkinsfile.

- [ ] `jenkins` user created; the API test prints the DAG id

---

## Step 13.12 — Give Jenkins the Airflow credential

**Where:** 🌐 Jenkins (tunnel from Phase 11) → **Manage Jenkins** → **Credentials** → **System** → **Global credentials** → **+ Add Credentials**

| Field | Value |
|---|---|
| Kind | Username with password |
| Username | `jenkins` |
| Password | `AIRFLOW_JENKINS_PASS` |
| ID | **`airflow-api`** |

→ **Create**.

- [ ] Credential `airflow-api` exists

---

## Step 13.13 — End-to-end: Jenkins hands off to Airflow

**Where:** 🪟 Windows. Make a harmless change to a seed file, e.g. add a comment line at the top of `learn/management/commands/seed_content.py`:
```python
# Content is re-applied by the Airflow DAG sysdesign_reseed_content after deploys.
```
```powershell
git commit -am "Document reseed hand-off"
git push
```

**Expected:**
1. 🌐 Jenkins: within ~5 minutes a build runs **all five stages**, including **Reseed content (Airflow)**.
2. 🌐 Airflow: a new `sysdesign_reseed_content` run appears (triggered via the REST API) and goes green.

- [ ] The Jenkins → Airflow hand-off works

---

## ✅ Checkpoint

- [ ] Airflow running inside the resource budget (`kubectl top pods -n airflow`)
- [ ] Three DAGs active; backup lands in Object Storage; 30-day lifecycle rule set
- [ ] `jenkins` Airflow user plus the `airflow-api` Jenkins credential
- [ ] Seed-file change → Jenkins deploy → Airflow reseed, fully automatic
- [ ] `~/.sysdesign-secrets` backup in your password manager is up to date
