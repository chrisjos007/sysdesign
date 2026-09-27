# Phase 6 — cert-manager & TLS issuers

[← Phase 5](05-k3s.md) · [Guide home](../../ORACLE_K8S_DEPLOYMENT.md) · Next: [Phase 7 →](07-containerize-app.md)

**Goal:** cert-manager installed, plus two "issuers" that know how to get free certificates from Let's Encrypt.
**Time:** ~15 minutes.

---

## Background: how the certificate will be issued (Phase 10)

1. You create an Ingress for `sysdesignquest.duckdns.org` with the annotation `cert-manager.io/cluster-issuer: …`.
2. cert-manager sees it and asks Let's Encrypt for a certificate.
3. Let's Encrypt replies: "prove you control this domain by serving token X at `http://sysdesignquest.duckdns.org/.well-known/acme-challenge/…`". This is the **HTTP-01 challenge**, and it's why port 80 must be open.
4. cert-manager starts a tiny solver pod plus a temporary Ingress that serves the token through Traefik.
5. Let's Encrypt fetches the token, is satisfied, and issues the certificate.
6. cert-manager stores it in a Secret (`web-tls`) and Traefik uses it. cert-manager renews it about 30 days before its 90-day expiry.

**Staging vs production:** Let's Encrypt production has strict rate limits (e.g. 5 duplicate certificates per week). Staging has generous limits but issues untrusted "fake" certificates. Get everything working against **staging** first, then switch.

---

## Step 6.1 — Install cert-manager with Helm

**Where:** 🐧 VM (inside `tmux` is a good habit)

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set crds.enabled=true
```

- `helm upgrade --install` installs the first time and upgrades later. The same command works both ways.
- `crds.enabled=true` also installs cert-manager's CRDs (`Certificate`, `ClusterIssuer`, …).

Wait for it:
```bash
kubectl -n cert-manager rollout status deploy/cert-manager
kubectl -n cert-manager rollout status deploy/cert-manager-webhook
kubectl -n cert-manager get pods
```

**Expected:** three pods (`cert-manager`, `cert-manager-cainjector`, `cert-manager-webhook`), all `1/1 Running`.

- [ ] cert-manager pods Running

---

## Step 6.2 — Create the issuers file

**Where:** 🪟 Windows (VS Code): create **`k8s/05-cluster-issuers.yaml`**

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-staging-account
    solvers:
      - http01:
          ingress:
            ingressClassName: traefik
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-prod-account
    solvers:
      - http01:
          ingress:
            ingressClassName: traefik
```

Field by field:
- `ClusterIssuer`: usable from any namespace. A plain `Issuer` works in one namespace only.
- `server`: the Let's Encrypt API endpoint (staging vs prod).
- `privateKeySecretRef`: where cert-manager stores the ACME account key it creates for you.
- `solvers.http01.ingress.ingressClassName: traefik`: serve challenge tokens through Traefik.
- There's no `email:` field. It's optional, and leaving it out keeps your address out of a public repo.

- [ ] File created

---

## Step 6.3 — Commit, push, pull, apply

**Where:** 🪟 Windows
```powershell
git add k8s/05-cluster-issuers.yaml
git commit -m "Add Let's Encrypt cluster issuers"
git push
```

**Where:** 🐧 VM
```bash
cd ~/sysdesign && git pull
kubectl apply -f k8s/05-cluster-issuers.yaml
```

**Expected:**
```
clusterissuer.cert-manager.io/letsencrypt-staging created
clusterissuer.cert-manager.io/letsencrypt-prod created
```

**If it fails with `no matches for kind "ClusterIssuer"`:** the CRDs aren't installed. Re-run Step 6.1 and make sure `--set crds.enabled=true` is included.

- [ ] Applied

---

## Step 6.4 — Verify the issuers registered with Let's Encrypt

**Where:** 🐧 VM

```bash
kubectl get clusterissuer
```

**Expected:**
```
NAME                  READY   AGE
letsencrypt-prod      True    30s
letsencrypt-staging   True    30s
```

**If `READY` is `False`:** `kubectl describe clusterissuer letsencrypt-staging` and read the **Status/Events**. It's usually an outbound network problem from the VM.

- [ ] Both `READY True`

---

## ✅ Checkpoint

- [ ] cert-manager running (3 pods)
- [ ] `letsencrypt-staging` and `letsencrypt-prod` both `READY True`
- [ ] `k8s/05-cluster-issuers.yaml` committed
