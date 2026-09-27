# Phase 11 — Remote access to admin UIs

[← Phase 10](10-app-ingress-tls.md) · [Guide home](../../ORACLE_K8S_DEPLOYMENT.md) · Next: [Phase 12 →](12-jenkins.md)

**Goal:** understand how you'll reach Jenkins, Airflow and (optionally) the Kubernetes API **without exposing them to the internet**.
**Time:** ~10 minutes. You'll actually use these tunnels in Phases 12 and 13.

---

## Background: two hops

```
Your browser ──► localhost:8080 on your PC
                   │  (ssh -L: encrypted SSH tunnel)
                   ▼
                 127.0.0.1:8080 on the VM
                   │  (kubectl port-forward)
                   ▼
                 svc/jenkins:8080 inside the cluster
```

Nothing new is opened in the Security List or iptables. Only someone who can SSH into the VM can reach these UIs.

---

## Step 11.1 — The tunnel commands

Each is **one** command, run in its own 🪟 Windows PowerShell window. It stays running while you use the UI; close the window, or press **Ctrl+C**, to disconnect.

**Jenkins** (available after Phase 12.4) → http://localhost:8080
```powershell
ssh -L 8080:127.0.0.1:8080 oci kubectl -n jenkins port-forward svc/jenkins 8080:8080
```

**Airflow** (available after Phase 13.6) → http://localhost:8081
```powershell
ssh -L 8081:127.0.0.1:8081 oci kubectl -n airflow port-forward svc/airflow-api-server 8081:8080
```

How to read the Jenkins one:
- `ssh -L 8080:127.0.0.1:8080 oci`: "forward my PC's port 8080 to port 8080 on the VM's loopback address".
- `kubectl -n jenkins port-forward svc/jenkins 8080:8080`: the command SSH runs on the VM. It forwards the VM's `127.0.0.1:8080` into the Jenkins Service.

**Expected output** while connected:
```
Forwarding from 127.0.0.1:8080 -> 8080
Handling connection for 8080
```

**If you get `bind: Address already in use`:** something on your PC already uses that port. Change the **first** number, e.g. `-L 9090:127.0.0.1:8080`, and browse to http://localhost:9090.

- [ ] You know which command opens which UI

---

## Step 11.2 — (Optional) Run kubectl from Windows

Handy if you prefer your local terminal and editor.

1. 🪟 Upgrade your local kubectl. You have v1.34, and the cluster is v1.36; kubectl supports ±1 minor version.
   ```powershell
   winget upgrade Kubernetes.kubectl
   kubectl version --client
   ```
2. 🪟 Copy the kubeconfig from the VM:
   ```powershell
   scp oci:.kube/config $HOME\.kube\config-oci
   ```
   Leave `server: https://127.0.0.1:6443` in it unchanged. The tunnel makes that address work.
3. 🪟 Open the API tunnel in its own window (`-N` means "no remote command, tunnel only"):
   ```powershell
   ssh -N -L 6443:127.0.0.1:6443 oci
   ```
4. 🪟 In another window:
   ```powershell
   $env:KUBECONFIG = "$HOME\.kube\config-oci"
   kubectl get nodes
   ```

**Expected:** your node, `Ready`.

> `config-oci` is a full-admin credential for your cluster. Keep it out of the repo and out of cloud-synced folders.

- [ ] (Optional) Local kubectl works through the tunnel

---

## ✅ Checkpoint

- [ ] You understand the two-hop tunnel and have the two commands handy
- [ ] Port 6443 and the UIs remain closed to the internet
