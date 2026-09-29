# Phase 12 — Jenkins CI/CD

[← Phase 11](11-remote-access.md) · [Guide home](../../AWS_K8S_DEPLOYMENT.md) · Next: [Phase 13 →](13-airflow.md)

**Goal:** every push to `master` is tested, built into an arm64 image, pushed to GHCR, migrated and rolled out automatically, with no manual steps.
**Time:** ~90 minutes.

---

## Background: how a build runs

```
Jenkins controller (always running, jenkins-0)
   │ every 5 min: "new commits on master?"  ── yes ──►
   ▼
Kubernetes plugin creates a build pod in namespace jenkins:
   ┌─────────────────────────────────────────────────────────┐
   │ jnlp      – agent; checks out the repo into a shared dir │
   │ python    – runs tests                                   │
   │ buildkit  – builds + pushes the image                    │
   │ kubectl   – runs migrate Job, updates the Deployment     │
   └─────────────────────────────────────────────────────────┘
   (identity: ServiceAccount jenkins-deployer → may only touch web + migrate in sysdesign)
   Pod is deleted when the build finishes.
```

---

## Step 12.1 — Jenkins Helm values

**Where:** 🪟 Windows → **`jenkins/values.yaml`**

```yaml
controller:
  serviceType: ClusterIP
  javaOpts: "-Xms512m -Xmx1g"
  resources:
    requests:
      cpu: 250m
      memory: 1Gi
    limits:
      memory: 2Gi
agent:
  # The default JNLP container asks for 512m CPU, which is a quarter of the node.
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 512Mi
persistence:
  size: 8Gi
```

- `serviceType: ClusterIP`: Jenkins is reachable only inside the cluster (and through your tunnel).
- `javaOpts -Xmx1g` with a `2Gi` limit: the JVM heap stays well inside the container limit, leaving room for non-heap memory.
- `agent.resources`: the chart's default for the agent container would eat a quarter of your 2 CPUs on every build.
- `persistence.size: 8Gi`: Jenkins home (jobs, build history, plugins) on a PVC.

- [ ] File created

---

## Step 12.2 — RBAC for build pods

**Where:** 🪟 Windows → **`k8s/60-jenkins-rbac.yaml`**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins-deployer
  namespace: jenkins
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployer
  namespace: sysdesign
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "patch"]
  - apiGroups: ["apps"]
    resources: ["replicasets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["batch"]
    resources: ["jobs"]
    verbs: ["get", "list", "watch", "create", "patch", "delete"]
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: jenkins-deployer
  namespace: sysdesign
subjects:
  - kind: ServiceAccount
    name: jenkins-deployer
    namespace: jenkins
roleRef:
  kind: Role
  name: deployer
  apiGroup: rbac.authorization.k8s.io
```

How the three objects relate:
- **ServiceAccount** `jenkins-deployer` (in `jenkins`) is the identity build pods run as.
- **Role** `deployer` (in `sysdesign`) is a list of allowed actions. It's scoped to the `sysdesign` namespace only.
- **RoleBinding** grants that Role to that ServiceAccount.

What it deliberately **can't** do: read Secrets, create Deployments or Services, touch any other namespace, or change RBAC. Jenkins can only roll out new images and run the migrate Job. **You** apply everything else from git.

- [ ] File created

---

## Step 12.3 — The Jenkinsfile

**Where:** 🪟 Windows → **`Jenkinsfile`** at the repo root

```groovy
pipeline {
  agent {
    kubernetes {
      defaultContainer 'python'
      yaml '''
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: jenkins-deployer
  containers:
    - name: python
      image: python:3.13-slim
      command: ["sleep"]
      args: ["infinity"]
      resources:
        requests: {cpu: 100m, memory: 256Mi}
        limits: {memory: 1Gi}
    - name: buildkit
      image: moby/buildkit:v0.33.0
      command: ["sleep"]
      args: ["infinity"]
      securityContext:
        privileged: true   # BuildKit needs it to create build sandboxes; see notes
      resources:
        requests: {cpu: 250m, memory: 512Mi}
        limits: {memory: 2Gi}
    - name: kubectl
      image: alpine/k8s:1.36.4
      command: ["sleep"]
      args: ["infinity"]
      resources:
        requests: {cpu: 50m, memory: 64Mi}
        limits: {memory: 256Mi}
'''
    }
  }

  options {
    timeout(time: 30, unit: 'MINUTES')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  triggers {
    pollSCM('H/5 * * * *')
  }

  environment {
    IMAGE  = 'ghcr.io/chrisjos007/sysdesign-quest'
    APP_NS = 'sysdesign'
    AIRFLOW_URL = 'http://airflow-api-server.airflow.svc.cluster.local:8080'
  }

  stages {
    stage('Test') {
      steps {
        sh '''
          pip install -r requirements.txt
          python manage.py check
          python manage.py makemigrations --check --dry-run
          python manage.py test
        '''
      }
    }

    stage('Build & push image') {
      steps {
        script { env.TAG = env.GIT_COMMIT.substring(0, 8) }
        container('buildkit') {
          withCredentials([usernamePassword(credentialsId: 'ghcr',
                            usernameVariable: 'GHCR_USER', passwordVariable: 'GHCR_TOKEN')]) {
            sh '''
              export DOCKER_CONFIG="$(mktemp -d)"
              trap 'rm -rf "$DOCKER_CONFIG"' EXIT
              AUTH=$(printf '%s:%s' "$GHCR_USER" "$GHCR_TOKEN" | base64 | tr -d '\\n')
              printf '{"auths":{"ghcr.io":{"auth":"%s"}}}' "$AUTH" > "$DOCKER_CONFIG/config.json"

              buildctl-daemonless.sh build \
                --frontend dockerfile.v0 \
                --local context=. \
                --local dockerfile=. \
                --import-cache "type=registry,ref=${IMAGE}:buildcache" \
                --export-cache "type=registry,ref=${IMAGE}:buildcache,mode=max" \
                --output "type=image,\\"name=${IMAGE}:${TAG},${IMAGE}:latest\\",push=true"
            '''
          }
        }
      }
    }

    stage('Migrate') {
      steps {
        container('kubectl') {
          sh '''
            sed "s|IMAGE_PLACEHOLDER|${IMAGE}:${TAG}|" k8s/templates/migrate-job.yaml > migrate-job.yaml
            kubectl -n "$APP_NS" delete job migrate --ignore-not-found --wait=true
            kubectl apply -f migrate-job.yaml
            if ! kubectl -n "$APP_NS" wait --for=condition=complete job/migrate --timeout=300s; then
              kubectl -n "$APP_NS" logs job/migrate || true
              exit 1
            fi
            kubectl -n "$APP_NS" logs job/migrate
          '''
        }
      }
    }

    stage('Deploy') {
      steps {
        container('kubectl') {
          sh '''
            kubectl -n "$APP_NS" set image deployment/web web="${IMAGE}:${TAG}"
            kubectl -n "$APP_NS" rollout status deployment/web --timeout=300s
          '''
        }
      }
    }

    stage('Reseed content (Airflow)') {
      when { changeset 'learn/management/commands/seed_*.py' }
      steps {
        container('kubectl') {
          withCredentials([usernamePassword(credentialsId: 'airflow-api',
                            usernameVariable: 'AF_USER', passwordVariable: 'AF_PASS')]) {
            sh '''
              TOKEN=$(jq -n --arg u "$AF_USER" --arg p "$AF_PASS" '{username: $u, password: $p}' \
                | curl -sf -X POST "$AIRFLOW_URL/auth/token" -H 'Content-Type: application/json' -d @- \
                | jq -r .access_token)
              curl -sf -X POST "$AIRFLOW_URL/api/v2/dags/sysdesign_reseed_content/dagRuns" \
                -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
                -d '{"logical_date": null}'
            '''
          }
        }
      }
    }
  }
}
```

Stage by stage:

| Stage | Container | What happens | Fails the build when… |
|---|---|---|---|
| **Test** | python | Installs deps; `check` validates settings and models; `makemigrations --check` fails if you changed a model but forgot to commit its migration; `test` runs `learn/tests.py` | Any check or test fails |
| **Build & push** | buildkit | Writes a temporary registry login, builds the Dockerfile natively on arm64, pushes `:<sha>` + `:latest`, and reuses a registry-stored build cache (`:buildcache`) so unchanged layers aren't rebuilt | Build error, or GHCR refuses the push |
| **Migrate** | kubectl | Replaces the old migrate Job with one using the **new** image and waits for it | Migration error (log printed) or >5 min |
| **Deploy** | kubectl | Points the Deployment at `:<sha>` and waits for the rolling update | The new pod never becomes Ready (the old pod keeps serving) |
| **Reseed** | kubectl | Only if this build's commits changed a `seed_*.py`: logs in to Airflow's API and triggers the reseed DAG | Airflow unreachable or auth fails |

Details worth knowing:
- **Two tags:** the commit SHA tag is immutable, so the Deployment always points at an exact build and `kubectl rollout undo` means something. `latest` is for Airflow's task pods.
- **The quoting** in the `--output` line: the Groovy `'''` string turns `\\"` into `\"`, which the shell turns into a literal `"`. BuildKit needs those quotes because the value contains a comma.
- **Privileged BuildKit** is acceptable on a single-user learning cluster. The rootless variant (`moby/buildkit:*-rootless`) needs extra seccomp/AppArmor settings; try it as a stretch goal.
- **`alpine/k8s:1.36.4`** matches the cluster version. When you upgrade k3s, bump this tag to match.
- **Build #1 skips Reseed**, because a first build has no "changes since last build".

- [ ] File created

---

## Step 12.4 — Commit, push, apply RBAC, install Jenkins

**Where:** 🪟 Windows
```powershell
git add jenkins/values.yaml k8s/60-jenkins-rbac.yaml Jenkinsfile
git commit -m "Add Jenkins values, deployer RBAC and pipeline"
git push
```

**Where:** 🐧 VM (in `tmux`, since the first start takes a few minutes)
```bash
cd ~/sysdesign && git pull
kubectl apply -f k8s/60-jenkins-rbac.yaml

helm repo add jenkins https://charts.jenkins.io
helm repo update
helm upgrade --install jenkins jenkins/jenkins -n jenkins -f jenkins/values.yaml
kubectl -n jenkins rollout status statefulset/jenkins --timeout=15m
```

**Expected:** the rollout eventually reports success. The first start downloads plugins, which takes 3–8 minutes.
```bash
kubectl -n jenkins get pods,pvc
```
This shows `jenkins-0` at `2/2 Running` (Jenkins + a config-reload sidecar) and PVC `jenkins` as `Bound`.

**Check the RBAC works as intended:**
```bash
SA=system:serviceaccount:jenkins:jenkins-deployer
kubectl auth can-i patch deployments -n sysdesign --as=$SA   # yes
kubectl auth can-i create jobs -n sysdesign --as=$SA          # yes
kubectl auth can-i get secrets -n sysdesign --as=$SA          # no
kubectl auth can-i patch deployments -n airflow --as=$SA      # no
```

- [ ] `jenkins-0` Running; RBAC answers yes, yes, no, no

---

## Step 12.5 — First login

**Where:** 🐧 VM. Get the generated admin password:
```bash
kubectl exec -n jenkins -it svc/jenkins -c jenkins -- /bin/cat /run/secrets/additional/chart-admin-password && echo
```

**Where:** 🪟 Windows. Open the tunnel (Phase 11) and leave the window open:
```powershell
ssh -L 8080:127.0.0.1:8080 quest-vm kubectl -n jenkins port-forward svc/jenkins 8080:8080
```

**Where:** 🌐 Browser → http://localhost:8080 → user **`admin`**, and the password from above.

**Change the admin password now:** top-right user menu (**admin**) → **Security** (or **Configure**) → **Password** → set a strong one → **Save**. Store it in your password manager.

> The chart configures Jenkins through "configuration as code", so there's no setup wizard. If a banner mentions an ignored `admin` password from the chart, that's expected after you change it in the UI.

- [ ] Logged in; admin password changed and saved

---

## Step 12.6 — Add the GHCR credential

**Where:** 🌐 Jenkins → **Manage Jenkins** → **Credentials** → under *Stores scoped to Jenkins*, click **System** → **Global credentials (unrestricted)** → **+ Add Credentials**

| Field | Value |
|---|---|
| Kind | Username with password |
| Scope | Global |
| Username | `chrisjos007` |
| Password | the classic PAT from Phase 1 |
| ID | **`ghcr`** (must match the Jenkinsfile exactly) |
| Description | GHCR push token |

→ **Create**.

(The `airflow-api` credential is added in Phase 13, once the Airflow user exists.)

- [ ] Credential `ghcr` exists

---

## Step 12.7 — Create the pipeline job

**Where:** 🌐 Jenkins → **+ New Item**

1. Name: `sysdesign-quest` → select **Pipeline** → **OK**.
2. **General**: tick **Do not allow concurrent builds** (optional; the Jenkinsfile enforces it anyway).
3. Scroll to **Pipeline**:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: `https://github.com/chrisjos007/sysdesign.git`
   - Credentials: *- none -* (the repo is public)
   - Branch Specifier: `*/master`
   - Script Path: `Jenkinsfile`
   - Leave **Lightweight checkout** ticked
4. **Save**.

- [ ] Job created

---

## Step 12.8 — First build

**Where:** 🌐 Jenkins → `sysdesign-quest` → **Build Now**

**Where:** 🐧 VM. Watch the build pod appear:
```bash
kubectl -n jenkins get pods -w
```

**Expected:** a pod like `sysdesign-quest-1-xxxxx` goes `Pending` → `ContainerCreating` → `4/4 Running`, then disappears when the build ends. Press **Ctrl+C** to stop watching.

**Where:** 🌐 Jenkins → build **#1** → **Console Output**. Watch the stages go by. The first build takes longest, about 5–10 minutes, because images and build caches start cold.

**Expected** near the end:
```
deployment "web" successfully rolled out
...
Finished: SUCCESS
```

**Check the deployed image:**

**Where:** 🐧 VM
```bash
kubectl -n sysdesign get deploy web -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
```

**Expected:** `ghcr.io/chrisjos007/sysdesign-quest:` followed by 8 hex characters, matching the latest commit (`git log -1 --format=%h` on Windows shows the first 7).

**If the build fails:**

| Where it failed | Look at |
|---|---|
| Pod stuck `Pending` | `kubectl -n jenkins describe pod <build-pod>` → usually `Insufficient cpu` (check requests) |
| Test | The console output shows the failing test or check |
| Build & push: `denied` | The `ghcr` credential: PAT type or scope |
| Build & push: `operation not permitted` | BuildKit `privileged: true` missing |
| Migrate / Deploy: `forbidden` | RBAC (Step 12.4 checks) |
| Migrate timeout | The printed migrate logs; DB credentials |

- [ ] Build #1 `SUCCESS`; web runs the `:<sha>` image

---

## Step 12.9 — Prove push-to-deploy works

**Where:** 🪟 Windows. Make a small visible change, e.g. a word in a template heading under `learn/templates/`, then:
```powershell
git commit -am "Test automatic deploy"
git push
```

**Where:** 🌐 Jenkins. Within ~5 minutes build **#2** starts on its own (**Changes** shows your commit).

**Where:** 🌐 App. Once it's done, refresh: your change is live.

> **Why build #1 had to run manually:** Jenkins only learns about `triggers { pollSCM }` from the Jenkinsfile after running it once.

- [ ] Automatic build triggered and deployed

---

## Step 12.10 — Practice a rollback

**Where:** 🐧 VM

```bash
kubectl -n sysdesign rollout history deployment/web
kubectl -n sysdesign rollout undo deployment/web
kubectl -n sysdesign rollout status deployment/web
```

**Expected:** the site shows the previous version (your test change is gone).

Roll forward again: 🌐 Jenkins → **Build Now** (or push a new commit).

> A rollback swaps the **code** only. Database migrations are not reversed. If a bad release included a migration, you'd restore from backup (Phase 14) or write a reverse migration.

- [ ] Rolled back and forward

---

## ✅ Checkpoint

- [ ] Jenkins running, admin password changed, reachable only through the tunnel
- [ ] `ghcr` credential and `sysdesign-quest` job exist
- [ ] Push → test → build → migrate → deploy works hands-free
- [ ] Rollback practiced
