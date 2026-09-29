# Phase 8 — First image push to GHCR

[← Phase 7](07-containerize-app.md) · [Guide home](../../AWS_K8S_DEPLOYMENT.md) · Next: [Phase 9 →](09-secrets-and-postgres.md)

**Goal:** an **arm64** image of the app at `ghcr.io/chrisjos007/sysdesign-quest:latest`, publicly pullable.
**Time:** ~20 minutes.

---

## Background: why a special build

Your PC is **amd64** and the VM is **arm64**. An image built normally on Windows contains amd64 binaries, and on the VM it fails with `exec format error`. Docker's **buildx** can cross-build for arm64 using emulation (QEMU, bundled with Docker Desktop). Emulation is slow, but you only do it this once. From Phase 12 onward, Jenkins builds natively on the ARM VM.

---

## Step 8.1 — Check buildx can target arm64

**Where:** 🪟 Windows

```powershell
docker buildx ls
```

**Expected:** a builder (usually `default` or `desktop-linux`) whose **PLATFORMS** column includes `linux/arm64`.

**If arm64 isn't listed:** create a dedicated builder and check again:
```powershell
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap
```
The `Platforms:` line should now include `linux/arm64`.

- [ ] `linux/arm64` available

---

## Step 8.2 — Log in to GHCR

**Where:** 🪟 Windows

```powershell
docker login ghcr.io -u chrisjos007
```

At the `Password:` prompt, paste the **classic PAT** from Phase 1. The prompt shows nothing while you type or paste; that's normal.

**Expected:** `Login Succeeded`.

**If you get `denied`:** the token is fine-grained rather than classic, is missing `write:packages`, or has expired.

- [ ] `Login Succeeded`

---

## Step 8.3 — Build for arm64 and push

**Where:** 🪟 Windows (repo root)

```powershell
docker buildx build --platform linux/arm64 -t ghcr.io/chrisjos007/sysdesign-quest:latest --push .
```

**Expected:** a slower build than Phase 7, often 3–10 minutes under emulation, ending with lines like `pushing layers … done` and `pushing manifest for ghcr.io/chrisjos007/sysdesign-quest:latest`.

- [ ] Push finished

---

## Step 8.4 — Make the package public

**Where:** 🌐 Browser → github.com/chrisjos007 → **Packages** tab → **sysdesign-quest**

1. Right sidebar → **Package settings**.
2. Scroll to **Danger Zone** → **Change visibility** → **Public** → type the package name to confirm.
3. *(Optional)* Under **Manage Actions access / Repository access**, link the package to the `sysdesign` repo so it shows on the repo page.

**Why public:** the cluster (and Airflow task pods) can pull it without a pull secret. Your source is already public, and the image contains only what `.dockerignore` lets through, which you checked in Step 7.5.

> **Prefer private?** Keep it private and create a pull secret in both the `sysdesign` and `airflow` namespaces, then add `imagePullSecrets: [{name: ghcr-pull}]` to the web Deployment, the migrate Job and the DAG's pods:
> `kubectl -n <ns> create secret docker-registry ghcr-pull --docker-server=ghcr.io --docker-username=chrisjos007 --docker-password=<PAT>`.
> Private packages count against GitHub's free storage quota.

- [ ] Package is Public

---

## Step 8.5 — Verify the image is arm64 and pullable anonymously

**Where:** 🪟 Windows

```powershell
docker logout ghcr.io
docker buildx imagetools inspect ghcr.io/chrisjos007/sysdesign-quest:latest
docker login ghcr.io -u chrisjos007
```

**Expected:** `imagetools inspect` works **while logged out** (proving the image is public) and shows `Platform: linux/arm64`. It may also list an `unknown/unknown` attestation entry, which is normal.

**Where:** 🐧 VM. Pull it with the cluster's own runtime:
```bash
sudo k3s ctr images pull ghcr.io/chrisjos007/sysdesign-quest:latest
```

**Expected:** ends with `done`, with no auth error.

- [ ] Inspect shows linux/arm64; the VM can pull it

---

## ✅ Checkpoint

- [ ] `ghcr.io/chrisjos007/sysdesign-quest:latest` exists, is public, and is arm64
- [ ] The VM pulled it successfully
