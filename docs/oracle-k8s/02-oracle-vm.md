# Phase 2 — Oracle account & VM

[← Phase 1](01-accounts-and-local-prep.md) · [Guide home](../../ORACLE_K8S_DEPLOYMENT.md) · Next: [Phase 3 →](03-firewalls.md)

**Goal:** an Oracle account with a spending alarm, and a running Ubuntu ARM VM you can SSH into.
**Time:** ~45 minutes. Longer if ARM capacity is scarce in your region.

> Oracle redesigns its console from time to time, so menu labels may differ slightly from the ones below. The ☰ menu's search box (top left) finds any page by name, e.g. "Instances", "Budgets", "Buckets".

---

## Step 2.1 — Sign up

**Where:** 🌐 Browser (cloud.oracle.com → Sign up)

1. Fill in your details. **A credit or debit card is required for identity verification.** You won't be charged for Always Free resources. Some prepaid and virtual cards are rejected; if yours is, try a regular card.
2. **Home region:** choose carefully. It **cannot be changed**, and Always Free compute only runs there.
   - Pick one geographically near you and your users.
   - Big regions (e.g. Ashburn, Frankfurt) often run out of free ARM capacity. A smaller nearby region is often easier.
3. Finish signup and wait for the "Your account is ready" email. This can take from minutes to a few hours.
4. Sign in to the console. Note the region identifier shown in the top bar's region menu (e.g. `ap-mumbai-1`) as `<REGION>` in your values sheet.

- [ ] Can sign in to the console; region noted

---

## Step 2.2 — (Recommended) Upgrade to Pay As You Go

**Where:** ☁️ OCI Console → ☰ → **Billing & Cost Management** → **Upgrade and Manage Payment**

**Why:**
- Free-only accounts get the lowest priority for ARM capacity.
- Oracle may reclaim Always Free VMs it considers idle. PAYG accounts are exempt.
- Always Free resources **stay free** on PAYG. You're billed only if you create something that isn't Always Free, which this guide never does.

1. Choose **Pay As You Go** → confirm the payment method.
2. The upgrade can take a few minutes to a day. You can continue with the next steps meanwhile.

- [ ] Upgrade requested (or consciously skipped)

---

## Step 2.3 — Set a $1 budget alert

**Where:** ☁️ ☰ → **Billing & Cost Management** → **Budgets** → **Create Budget**

**Why:** if anything ever starts costing money, you hear about it the same day.

1. Name: `free-tier-guard`.
2. Target: **Compartment** → your root compartment (the tenancy name).
3. Schedule: **Monthly**. Amount: **1** (in your billing currency).
4. **Budget alert rule:** threshold type **Actual spend**, threshold **100** %, email = your address, message "OCI is charging money — check what was created".
5. **Create**.

- [ ] Budget shows under Budgets with an alert rule

---

## Step 2.4 — Create the VM

**Where:** ☁️ ☰ → **Compute** → **Instances** → **Create instance**

Go through the form top to bottom:

1. **Name:** `sysdesign-k3s`. **Compartment:** root.
2. **Placement:** leave the default Availability Domain for now. You'll change it if capacity fails.
3. **Image and shape**:
   - **Change shape** first → **Virtual machine** → **Ampere** → tick **VM.Standard.A1.Flex**.
     - **Number of OCPUs: 2**, **Amount of memory (GB): 12**.
     - Confirm the **Always Free-eligible** label is visible → **Select shape**.
   - **Change image** → **Ubuntu** → **Canonical Ubuntu 24.04**. Pick the standard image, **not** "Minimal". The console automatically picks the **aarch64** build because you chose an ARM shape; confirm the image name contains `aarch64`. → **Select image**.
4. **Networking**:
   - **Primary network:** *Create new virtual cloud network* (name e.g. `sysdesign-vcn`).
   - **Subnet:** *Create new public subnet*.
   - **Public IPv4 address:** make sure **Automatically assign public IPv4 address** is on.
5. **Add SSH keys:** **Paste public keys** → paste the whole line from `Get-Content $HOME\.ssh\oci_sysdesign.pub`.
6. **Boot volume:** tick **Specify a custom boot volume size** → **100** GB. The Always Free block storage allowance is 200 GB total. Leave the performance setting at default.
7. **Create**.

**Expected:** the instance goes from **Provisioning** (orange) to **Running** (green) within 1–3 minutes.

**If it fails with "Out of capacity for shape VM.Standard.A1.Flex":**
- Go back and pick a different **Availability Domain** under Placement, if your region has more than one.
- Retry at a different time of day. Early morning in your region's time zone often works.
- Finishing the PAYG upgrade (Step 2.2) usually helps a lot.
- As a last resort, 1 OCPU / 6 GB also fits the free tier. It's enough for the app and Jenkins, but not for Airflow as well.

- [ ] Instance is **Running**

---

## Step 2.5 — Note the public IP

**Where:** ☁️ Instance details page → **Instance access** / **Primary VNIC** section

Copy the **Public IPv4 address** into your values sheet as `<PUBLIC_IP>`.

> This "ephemeral" public IP stays the same through stops, starts and reboots. It only changes if you terminate the instance. You can optionally convert it to a **reserved** public IP (Networking → IP Management) so it survives even that.

- [ ] Public IP noted

---

## Step 2.6 — Point your hostname at the VM

**Where:** 🌐 Browser (duckdns.org)

1. In the row for your subdomain, put `<PUBLIC_IP>` in **current ip** → **update ip**.
2. Wait about a minute, then check from Windows:

**Where:** 🪟 Windows
```powershell
Resolve-DnsName sysdesignquest.duckdns.org
```

**Expected:** an `A` record with your `<PUBLIC_IP>`.

- [ ] Hostname resolves to the VM IP

---

## Step 2.7 — Set up a short SSH alias

**Where:** 🪟 Windows

Put your real IP in place of `<PUBLIC_IP>`, then run:

```powershell
@"

Host oci
    HostName <PUBLIC_IP>
    User ubuntu
    IdentityFile ~/.ssh/oci_sysdesign
    ServerAliveInterval 30
"@ | Add-Content -Path $HOME\.ssh\config -Encoding ascii
```

`ServerAliveInterval` stops idle connections from being dropped.

- [ ] `$HOME\.ssh\config` contains the `Host oci` block

---

## Step 2.8 — First login

**Where:** 🪟 Windows

```powershell
ssh oci
```

1. The first time, SSH asks *"Are you sure you want to continue connecting (yes/no/[fingerprint])?"* → type `yes`. This records the server's identity, so later connections can detect impersonation.
2. Enter your key passphrase if asked.

**Expected:** a prompt like `ubuntu@sysdesign-k3s:~$`.

Run:
```bash
uname -m
lsb_release -ds
nproc
free -h
```

**Expected:** `aarch64`, `Ubuntu 24.04.x LTS`, `2`, and about 11 Gi total memory.

Type `exit` to leave.

**If it fails:**
- `Connection timed out` → the port-22 rule is missing from the Security List (Phase 3.1 shows where to find it; the default list includes it).
- `Permission denied (publickey)` → the wrong public key was pasted in Step 2.4, or the `IdentityFile` path is wrong. You can add a key to a running instance via the console's **Cloud Shell** / **Console connection**. Recreating the instance is often faster.

- [ ] `ssh oci` works and shows aarch64 / Ubuntu 24.04 / 2 CPUs / ~11 Gi

---

## ✅ Checkpoint

- [ ] Budget alert exists
- [ ] VM **Running**, 2 OCPU / 12 GB, 100 GB boot volume
- [ ] `sysdesignquest.duckdns.org` resolves to the VM
- [ ] `ssh oci` logs you in
