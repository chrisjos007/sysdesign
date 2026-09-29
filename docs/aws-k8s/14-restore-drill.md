# Phase 14 — Restore drill

[← Phase 13](13-airflow.md) · [Guide home](../../AWS_K8S_DEPLOYMENT.md) · Next: [Phase 15 →](15-operations.md)

**Goal:** prove a backup can actually be restored, into a scratch database so production isn't touched.
**Time:** ~20 minutes. Repeat monthly.

> A backup you haven't restored isn't a backup yet. Dumps can be empty, truncated, or made by the wrong user, and you want to find that out now rather than during an outage.

---

## Step 14.1 — Start a toolbox pod with the backups mounted

**Where:** 🐧 VM

```bash
kubectl -n airflow apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: restore-toolbox
spec:
  restartPolicy: Never
  containers:
    - name: pg
      image: postgres:17
      command: ["sleep", "3600"]
      volumeMounts:
        - name: backups
          mountPath: /backups
  volumes:
    - name: backups
      persistentVolumeClaim:
        claimName: sysdesign-backups
EOF
kubectl -n airflow wait --for=condition=Ready pod/restore-toolbox --timeout=2m
```

This pod runs `sleep` for an hour, so you can `exec` into it. It lives in `airflow` because that's where the backups volume is, and the `postgres` NetworkPolicy lets that namespace reach the database.

**Expected:** `pod/restore-toolbox condition met`.

- [ ] Toolbox Ready

---

## Step 14.2 — Restore the newest dump into a scratch database

**Where:** 🐧 VM

```bash
grep PG_SUPER_PASS ~/.sysdesign-secrets        # copy the value
kubectl -n airflow exec -it restore-toolbox -- bash
```

**Inside the pod:**
```bash
export PGHOST=postgres.sysdesign.svc.cluster.local PGUSER=postgres
read -rsp 'Postgres superuser password: ' PGPASSWORD; export PGPASSWORD; echo

ls -lh /backups
latest=$(ls -t /backups/*.sql.gz | head -1); echo "Restoring $latest"

createdb restore_test
gunzip -c "$latest" | psql -q -v ON_ERROR_STOP=1 -d restore_test
```

**Expected:** no errors. With `ON_ERROR_STOP=1`, psql stops at the first problem instead of scrolling past it.

- [ ] Restore completed without errors

---

## Step 14.3 — Compare against production

**Still inside the pod:**
```bash
for db in restore_test sysdesign; do
  echo "== $db"
  psql -d "$db" -Atc "SELECT 'users', count(*) FROM auth_user
                      UNION ALL SELECT 'migrations', count(*) FROM django_migrations
                      UNION ALL SELECT 'tables', count(*) FROM information_schema.tables WHERE table_schema='public';"
done
```

**Expected:** the numbers match. Users may differ slightly if people signed up after the dump was taken.

- [ ] Counts match

---

## Step 14.4 — Clean up

**Inside the pod:**
```bash
dropdb restore_test
exit
```

**Where:** 🐧 VM
```bash
kubectl -n airflow delete pod restore-toolbox
```

- [ ] Scratch DB dropped, toolbox deleted

---

## Step 14.5 — (Know how) Restore from S3

If the instance or its disk were lost, the local `/backups` volume goes with it, and you'd restore from the bucket:

1. ☁️ **S3** → your bucket → `postgres/` → tick the newest object → **Download**. Or, on a rebuilt instance with the IAM role attached, from any pod with the AWS CLI: `aws s3 cp s3://<BACKUP_BUCKET>/postgres/<file> .`
2. Rebuild the cluster through Phase 9, stopping after Step 9.9 (empty databases).
3. Stream the file into the `sysdesign` database **as the `sysdesign` role**. Copy the dump to the VM with `scp` first, then:
   ```bash
   gunzip -c sysdesign-….sql.gz | kubectl -n sysdesign exec -i postgres-0 -- psql -U sysdesign -d sysdesign -v ON_ERROR_STOP=1
   ```
   The dump was made with `--no-owner`, so every table ends up owned by whoever runs the restore. Restoring as `sysdesign` (not `postgres`) means the app owns its tables, just as before. Inside the container, local connections don't need a password.
4. Continue from Phase 10, Step 10.7. The migrate Job should report *No migrations to apply*.

- [ ] Read and understood

---

## ✅ Checkpoint

- [ ] Latest backup restored into a scratch DB; counts matched production
- [ ] Scratch DB and toolbox removed
- [ ] Calendar reminder set to repeat this monthly
