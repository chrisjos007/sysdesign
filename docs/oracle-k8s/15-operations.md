# Phase 15 — Operating it (runbook)

[← Phase 14](14-restore-drill.md) · [Guide home](../../ORACLE_K8S_DEPLOYMENT.md) · Next: [Phase 16 →](16-troubleshooting.md)

A reference for day-to-day care. All commands run on 🐧 **VM** unless marked otherwise.

---

## Routine

### Weekly (5 minutes)

- [ ] **Anything unhealthy?**
  ```bash
  kubectl get pods -A | grep -v -E 'Running|Completed'
  ```
  Only the header line should print.
- [ ] **Resource pressure:**
  ```bash
  kubectl top node
  kubectl top pods -A --sort-by=memory | head -15
  ```
  Memory above ~85% of the node means something needs a smaller limit, or should be turned off.
- [ ] **Backups ran:** 🌐 Airflow → `sysdesign_db_backup` → the last 7 runs are green.
- [ ] **Disk:**
  ```bash
  df -h /
  ```
  Above ~80%? Prune unused images: `sudo k3s crictl rmi --prune`.

### Monthly (30 minutes)

- [ ] ☁️ **Billing** → Cost Analysis shows **0.00**.
- [ ] **OS patches + reboot:**
  ```bash
  sudo apt update && sudo apt full-upgrade -y && sudo reboot
  ```
  Then, after reconnecting, check everything came back with `kubectl get pods -A`. k3s is a systemd service and restarts all workloads automatically.
- [ ] **Restore drill** ([Phase 14](14-restore-drill.md)).
- [ ] **Certificates:** `kubectl get certificate -A` shows every certificate `READY True`. cert-manager renews ~30 days before expiry.
- [ ] **CPU requests vs capacity:**
  ```bash
  kubectl describe node | grep -A8 'Allocated resources'
  ```
  Keep CPU requests below ~90%, or builds and task pods won't fit.

---

## Common tasks

### See what the app is doing
```bash
kubectl -n sysdesign logs deploy/web -f                  # live request + error log
kubectl -n sysdesign logs deploy/web --previous          # logs from before the last crash
kubectl -n sysdesign get events --sort-by=.lastTimestamp | tail
```

### Run a Django management command
```bash
kubectl -n sysdesign exec -it deploy/web -- python manage.py <command>
```
Or use a Django shell: `kubectl -n sysdesign exec -it deploy/web -- python manage.py shell`.

### Open a SQL prompt
```bash
kubectl -n sysdesign exec -it postgres-0 -- psql -U sysdesign -d sysdesign
```

### Roll back a bad deploy
```bash
kubectl -n sysdesign rollout history deployment/web
kubectl -n sysdesign rollout undo deployment/web                  # previous version
kubectl -n sysdesign rollout undo deployment/web --to-revision=N  # a specific one
```
⚠️ This rolls back code only. Migrations aren't reversed. Next, fix forward: revert the commit in git and push, so Jenkins deploys a good version and git matches reality.

### Change a setting (ConfigMap)
1. 🪟 Edit `k8s/10-config.yaml`, then commit and push.
2. 🐧 `git pull && kubectl apply -f k8s/10-config.yaml`
3. 🐧 `kubectl -n sysdesign rollout restart deploy/web`. Pods only read environment variables at start.

### Rotate a secret
1. `nano ~/.sysdesign-secrets`: change the value, **and update your password manager**.
2. `set -a; source ~/.sysdesign-secrets; set +a`
3. Re-run that secret's `create secret … --dry-run=client -o yaml | kubectl apply -f -` command (Phase 9, Step 9.7 / Phase 13).
4. If it's a **DB password**, also change it in Postgres:
   ```bash
   kubectl -n sysdesign exec -i postgres-0 -- psql -U postgres -c "ALTER ROLE sysdesign PASSWORD '${APP_DB_PASS}';"
   ```
5. Restart whatever uses it: `kubectl -n sysdesign rollout restart deploy/web`. For Airflow keys, restart all Airflow components:
   ```bash
   kubectl -n airflow rollout restart deployment
   kubectl -n airflow rollout restart statefulset
   ```

### Rotate the GHCR token (every 90 days)
1. 🌐 GitHub → create a new classic PAT with `write:packages` (Phase 1, Step 1.2).
2. 🌐 Jenkins → Credentials → `ghcr` → **Update** → paste the new token.
3. Trigger a build to confirm it works, then delete the old token on GitHub.

### Change the Jenkins or Airflow configuration
Edit `jenkins/values.yaml` or `airflow/values.yaml`, commit, push, pull, then re-run the same `helm upgrade --install …` command from Phase 12 or 13. For Airflow, include `--set createUserJob.defaultUser.password=…` again.

---

## Upgrades

| What | How | Notes |
|---|---|---|
| **k3s** | Re-run the Phase 5 install command | Upgrade **one minor version at a time** (1.36 → 1.37). Then bump `alpine/k8s:<version>` in the Jenkinsfile |
| **cert-manager** | `helm repo update && helm upgrade cert-manager jetstack/cert-manager -n cert-manager --set crds.enabled=true` | Read the release notes for CRD changes |
| **Jenkins** | `helm repo update && helm upgrade jenkins jenkins/jenkins -n jenkins -f jenkins/values.yaml` | Plugin updates come with chart updates |
| **Airflow** | `helm repo update && helm upgrade airflow apache-airflow/airflow -n airflow -f airflow/values.yaml --set createUserJob.defaultUser.password="$AIRFLOW_ADMIN_PASS"` | Runs DB migrations. **Take a backup first** (trigger the backup DAG) |
| **Postgres** (major, e.g. 17 → 18) | Dump → new StatefulSet → restore | Never just change the image tag. The data directory format differs between major versions |
| **Python / Django** | `requirements.txt` / `Dockerfile` → push | Jenkins tests and deploys it like any change |

Before any upgrade: **trigger a backup**, and check `helm history <release> -n <ns>`. If something goes wrong, `helm rollback <release> <revision> -n <ns>` restores the previous chart release.

---

## Oracle-specific

- **Idle reclamation:** Oracle may stop Always Free instances whose CPU, network *and* memory all stay under 20% for 7 days. This stack's memory use keeps it well above that, and PAYG accounts are exempt. If the VM is ever stopped: ☁️ Instances → **Start**. Everything comes back on its own.
- **Stay inside Always Free:** never change the shape to more than 2 OCPU / 12 GB, never add block volumes beyond the 200 GB total, and don't create load balancers. The budget alert catches mistakes.
- **Snapshots (optional):** ☁️ Boot volume → **Backups** → Create manual backup before risky changes. Always Free includes 5 volume backups.

---

## Shutting it all down (if you ever want to)

1. Take and download a final backup (Phase 14.5).
2. ☁️ Instances → `sysdesign-k3s` → **Terminate** → also delete the boot volume.
3. ☁️ Delete the bucket objects and then the bucket, the customer secret key, and the VCN.
4. 🌐 GitHub: delete the PAT (and the GHCR package, if you want).
5. 🌐 DuckDNS: remove the subdomain.

---

## Stretch goals

- [ ] **GitHub webhook → Jenkins** instead of polling. This needs Jenkins exposed through its own Ingress + TLS. Add Traefik basic-auth or an IP allow-list first.
- [ ] **Rootless BuildKit** instead of privileged.
- [ ] **Sealed Secrets** or **External Secrets** (with OCI Vault) so secrets can live in git, encrypted.
- [ ] **Argo CD** for GitOps: Jenkins commits the new image tag to git, and Argo CD applies it.
- [ ] **Monitoring:** a lightweight Prometheus/Grafana setup (e.g. VictoriaMetrics single-node + Grafana) sized to fit the remaining memory.
- [ ] **HSTS** once HTTPS is solid: `SECURE_HSTS_SECONDS` in settings.
