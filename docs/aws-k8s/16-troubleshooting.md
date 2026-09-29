# Phase 16 — Troubleshooting

[← Phase 15](15-operations.md) · [Guide home](../../AWS_K8S_DEPLOYMENT.md)

---

## First, the universal debugging loop

When anything in Kubernetes isn't working, go through these in order. Most problems reveal themselves by step 3.

```bash
kubectl get pods -n <ns>                                   # 1. what state is it in?
kubectl describe pod -n <ns> <pod>                         # 2. read the Events at the bottom
kubectl logs -n <ns> <pod> [-c <container>] [--previous]   # 3. what did the program say?
kubectl get events -n <ns> --sort-by=.lastTimestamp        # 4. what else happened around it?
```

What pod states mean:

| State | Meaning | Look at |
|---|---|---|
| `Pending` | Not scheduled yet | `describe` → Events: `Insufficient cpu/memory`, unbound PVC |
| `ContainerCreating` (for a long time) | Image pull or volume mount in progress / stuck | `describe` → Events |
| `ImagePullBackOff` / `ErrImagePull` | Can't fetch the image | Image name, tag, visibility, architecture |
| `CrashLoopBackOff` | Starts, then exits, repeatedly | `logs --previous` |
| `Running` but `0/1 Ready` | The readiness probe is failing | `describe` → probe failure messages |
| `OOMKilled` (in `describe`, "Last State") | Exceeded its memory limit | Raise `limits.memory` or reduce the workload |
| `Completed` | A Job or one-off pod finished successfully | Normal |

---

## AWS / instance

| Symptom | Likely cause | Fix |
|---|---|---|
| `InsufficientInstanceCapacity` at launch | No `t4g.large` capacity in that AZ right now | Pick a subnet in another AZ ([Phase 2.6](02-aws-ec2.md)) |
| `vCPU limit` error at launch | New-account quota | ☁️ Service Quotas → request 8 vCPUs for On-Demand Standard instances |
| `ssh quest-vm` times out | Your home IP changed ("My IP" rule), or DNS still points at the old IP | ☁️ Security group → edit the SSH rule → **My IP**; `Resolve-DnsName sysdesignquest.duckdns.org` vs the console's public IP |
| DNS doesn't follow a new IP after start | DuckDNS updater failed | `ssh -i $HOME\.ssh\quest_vm ubuntu@<new IP>`, then `journalctl -u duckdns.service` ([Phase 3.3](03-network-and-dns.md)) |
| `Permission denied (publickey)` | Wrong key or user | `IdentityFile` in `~/.ssh/config`; user must be `ubuntu` |
| Instance stopped without you doing anything | The nightly-stop cron (Phase 15), or it hit a problem | ☁️ Instance → **Monitor and troubleshoot** → **Get system log** |
| Everything is slow; `kubectl top node` CPU ~100% | CPU credits exhausted (Standard mode throttles) | Wait (credits refill when idle), pause Airflow, or change to a larger type |
| Budget alert email | Something is running longer, or something new was created | ☁️ Cost Explorer grouped by *Service* and *Region*; stop or delete it |

## Network / firewall

| Symptom | Likely cause | Fix |
|---|---|---|
| `curl http://<host>` **times out** | Security group missing the rule, or DNS points at an old IP | [Phase 2.5](02-aws-ec2.md) / [Phase 3](03-network-and-dns.md). A timeout means a firewall dropped it; "refused" means nothing is listening |
| Works by IP, not by name | DNS | `Resolve-DnsName <host>`; update the DuckDNS IP |
| CoreDNS `CrashLoopBackOff`; pods get `no route to host` / can't resolve | A host firewall (ufw) was enabled | `sudo ufw disable`, then `sudo systemctl restart k3s` ([Phase 3.1](03-network-and-dns.md)) |
| Pods stuck `ContainerCreating` right after a start | Normal for 1–3 minutes while k3s restarts everything | Wait; if still stuck after 5 minutes, `kubectl describe pod` → Events |

## Images

| Symptom | Likely cause | Fix |
|---|---|---|
| `exec format error` in logs | amd64 image on the arm64 node | Build with `--platform linux/arm64`, or let Jenkins build on the node |
| `ImagePullBackOff` … `401`/`403`/`denied` | The package is private | Make it public ([Phase 8.4](08-first-image.md)) or add a pull secret |
| `ImagePullBackOff` … `not found` | Wrong name/tag | `docker buildx imagetools inspect <image>` |

## The app (Django)

| Symptom | Likely cause | Fix |
|---|---|---|
| Browser shows **400 Bad Request** | Hostname not in `ALLOWED_HOSTS` | `k8s/10-config.yaml` → apply → `rollout restart deploy/web` |
| Pod never Ready; `describe` shows the probe getting **400** | `localhost` missing from `ALLOWED_HOSTS` (the probe sends `Host: localhost`) | Add it in `k8s/10-config.yaml`, apply, restart web |
| **403 CSRF verification failed** on login/forms | Proxy not trusted / origin mismatch | [Phase 7.1](07-containerize-app.md) settings present? `CSRF_TRUSTED_ORIGINS` = `https://<host>` exactly (with `https://`, no trailing slash) |
| Infinite redirect loop | `SECURE_SSL_REDIRECT=True` without `SECURE_PROXY_SSL_HEADER` | Phase 7.1 |
| Logged out on every request | `SECRET_KEY` changed between pods, or secure cookies over plain http | Same secret for all pods; browse via https |
| Page without CSS | `collectstatic` didn't run in the image | Check the Dockerfile's `collectstatic` line; rebuild |
| 500 errors | Python exception | `kubectl -n sysdesign logs deploy/web` |
| Code runner fails with `Read-only file system` | Something writes outside `/tmp` | Make that code use `tempfile`, or mount another emptyDir |
| Gemini features fail after NetworkPolicy | Egress blocked | Egress rule for 443 to `0.0.0.0/0` (minus private ranges) present? DNS rule present? |
| Pod `OOMKilled` | 768Mi too small under load | Raise `limits.memory` in `30-web.yaml`, or reduce `--workers` |
| Migrate Job times out | DB unreachable, wrong password, or a failing migration | `kubectl -n sysdesign logs job/migrate`; test the credentials as in [Phase 9.9](09-secrets-and-postgres.md) |

## TLS / cert-manager

| Symptom | Likely cause | Fix |
|---|---|---|
| Certificate stuck `READY False` | Challenge can't complete | `kubectl -n sysdesign describe challenges` → read the last event |
| Challenge: `connection refused` / timeout | Port 80 closed | Phase 3 |
| Challenge: `NXDOMAIN` / wrong IP | DNS | DuckDNS IP |
| `too many certificates already issued` | Let's Encrypt prod rate limit | Wait (up to a week), and use **staging** while debugging |
| Browser warns "not secure" after switching to prod | The old staging cert is still in `web-tls` | `kubectl -n sysdesign delete secret web-tls` |

## Network policies

| Symptom | Likely cause | Fix |
|---|---|---|
| Web pod not Ready **only** after applying policies | The policy blocks kubelet probes | Add the `10.42.0.1/32` ingress rule ([Phase 10.12](10-app-ingress-tls.md)) |
| Site returns 504 / Bad Gateway after policies | Traefik can't reach the pod | The ingress rule must allow namespace `kube-system` on port 8000 |
| Airflow or a task can't reach Postgres | The `postgres` policy doesn't allow that namespace | Check `k8s/50-network-policies.yaml` |
| Quick test: is a policy the cause? | — | `kubectl delete -f k8s/50-network-policies.yaml`, retest, then re-apply once fixed |

## Jenkins

| Symptom | Likely cause | Fix |
|---|---|---|
| Build pod `Pending`: `Insufficient cpu` | Requests exceed 2 CPUs | `kubectl describe node` → Allocated; lower requests; make sure `agent.resources` in `jenkins/values.yaml` is applied |
| `Build & push`: `denied` / `unauthorized` | The `ghcr` credential | Classic PAT, `write:packages`, not expired; ID exactly `ghcr` |
| BuildKit: `operation not permitted` / `failed to mount` | Not privileged | `securityContext.privileged: true` on the buildkit container |
| `Migrate`/`Deploy`: `forbidden` | RBAC | `kubectl auth can-i … --as=system:serviceaccount:jenkins:jenkins-deployer` ([Phase 12.4](12-jenkins.md)) |
| No automatic builds | pollSCM not registered, or the wrong branch | Run the job once by hand; check the branch specifier `*/master` |
| `GIT_COMMIT` is null | Job isn't "Pipeline script from SCM" | Reconfigure the job ([Phase 12.7](12-jenkins.md)) |
| `Scripts not permitted to use method …` | Script security sandbox | Manage Jenkins → **In-process Script Approval** → approve, or simplify the Groovy |
| Controller `OOMKilled` | Heap + plugins exceed 2Gi | Raise `controller.resources.limits.memory`, keep `-Xmx` about half of it |

## Airflow

| Symptom | Likely cause | Fix |
|---|---|---|
| Pods crash with DB errors | `airflow-keys` connection string, or the postgres NetworkPolicy | `kubectl -n airflow logs <pod> --all-containers`; test with `psql` from a pod in `airflow` |
| `run-airflow-migrations` Job fails | Same as above | Its logs show the SQL error |
| DAGs don't appear | git-sync can't pull, or wrong `subPath` | `kubectl -n airflow logs deploy/airflow-dag-processor -c git-sync` |
| Red "import errors" banner | Python error in the DAG file | The banner shows the traceback; fix, push, and wait ~1 min |
| Task fails: `pods is forbidden` | Airflow RBAC | Keep `allowPodLaunching: true` (chart default) and tasks in namespace `airflow` |
| Task pod `ImagePullBackOff` | Image private / wrong | Same as for the app |
| Task can't find `sysdesign-config`/`sysdesign-secrets` | Not created in `airflow` | [Phase 9](09-secrets-and-postgres.md): the ConfigMap has an `airflow` copy, and the secret loop covers both namespaces |
| Backup upload `Unable to locate credentials` | Pods can't reach the metadata service | Instance metadata options: enabled, **hop limit 2**; IAM role attached ([Phase 13.4](13-airflow.md)) |
| Backup upload `AccessDenied` | Bucket name typo in the policy or `backup-config`, or wrong prefix | Compare the policy JSON, `kubectl -n airflow get configmap backup-config -o yaml`, and the bucket name |
| Upload task logs "BACKUP_BUCKET not set" | `backup-config` ConfigMap missing in `airflow` | Create it ([Phase 13.4](13-airflow.md)) |
| Jenkins Reseed stage 401 | Wrong `airflow-api` credential | Re-test with [Phase 13.11](13-airflow.md)'s API test |
| Jenkins Reseed stage 404/422 | API path/body differs in your Airflow version | Compare with http://localhost:8081/docs |
| UI login loops or everyone gets logged out after upgrade | API/JWT secrets changed | Keep `apiSecretKeySecretName` / `jwtSecretName` pointing at `airflow-keys` |

## Resetting a component (last resort)

| Component | Reset | Loses |
|---|---|---|
| Web app | `kubectl -n sysdesign delete deploy web && kubectl apply -f k8s/30-web.yaml` | Nothing (stateless) |
| Jenkins | `helm uninstall jenkins -n jenkins && kubectl -n jenkins delete pvc --all`, then Phase 12.4 onward | Jobs, build history, credentials |
| Airflow | `helm uninstall airflow -n airflow`, drop and recreate the `airflow` database (Phase 9.9), then Phase 13.6 onward | Run history, users |
| Postgres | ⚠️ `kubectl -n sysdesign delete statefulset postgres && kubectl -n sysdesign delete pvc data-postgres-0` | **All data**: restore from backup afterwards (Phase 14.5) |
| Whole cluster | `/usr/local/bin/k3s-uninstall.sh`, then Phase 5 onward | **Everything** on the cluster (the VM, firewall and secrets file remain) |
