# Phase 2 — AWS account & EC2 instance

[← Phase 1](01-accounts-and-local-prep.md) · [Guide home](../../AWS_K8S_DEPLOYMENT.md) · Next: [Phase 3 →](03-network-and-dns.md)

**Goal:** a secured AWS account with a spending alarm, and a running Ubuntu ARM instance you can SSH into.
**Time:** ~45 minutes.

> The AWS console changes its layout from time to time. The search bar at the top of the console finds any service by name, e.g. "EC2", "IAM", "Budgets".

---

## Step 2.1 — Sign in and pick a region

**Where:** ☁️ console.aws.amazon.com → sign in

1. **Region** (top-right, next to your account name): choose one near you and your users, e.g. **Asia Pacific (Mumbai) `ap-south-1`**, which is also among the cheapest for `t4g`. Everything in this guide lives in this one region; resources in other regions are invisible from here.
2. Note the region **code** (e.g. `ap-south-1`) as `<REGION>` in your values sheet.
3. Top-right account menu → note the 12-digit **Account ID** as `<ACCOUNT_ID>`.

- [ ] Region chosen; region code and account ID noted

---

## Step 2.2 — Secure the account

**Why:** the account is linked to your card. A leaked root password without MFA is how people end up with crypto-mining bills.

### 2.2a — MFA on the root user
**Where:** ☁️ **IAM** → the dashboard's security recommendations → **Add MFA** for root user (or account menu → **Security credentials** → **Assign MFA device**)

1. Device name `root-phone`, type **Authenticator app**.
2. Scan the QR code with an authenticator app (Google Authenticator, Microsoft Authenticator, or your password manager's TOTP feature), enter two consecutive codes → **Add MFA**.

### 2.2b — An everyday admin user
**Where:** ☁️ **IAM** → **Users** → **Create user**

1. User name `admin`, tick **Provide user access to the AWS Management Console** → **I want to create an IAM user** → custom password → untick "must create a new password".
2. Permissions: **Attach policies directly** → tick **AdministratorAccess** → **Next** → **Create user**.
3. Copy the **console sign-in URL** shown (`https://<ACCOUNT_ID>.signin.aws.amazon.com/console`) and the password into your password manager.
4. Let IAM users see billing: account menu → **Account** → **IAM user and role access to Billing information** → **Edit** → tick **Activate IAM Access** → **Update**.
5. Sign out, sign back in with the new URL as `admin`, and add MFA for this user as well (IAM → Users → admin → **Security credentials** → **Assign MFA device**).

From now on, use the `admin` user. Keep the root login for account-level emergencies only.

- [ ] Root has MFA; `admin` user created, has MFA, and is what you're signed in as

---

## Step 2.3 — Set a budget alert

**Where:** ☁️ **Billing and Cost Management** → **Budgets** → **Create budget**

1. **Use a template (simplified)** → **Monthly cost budget**.
2. Budget name `sysdesign-monthly`, amount **15** (USD). At ~4 h/day you should land around $10; 24/7 would trip it mid-month.
3. Email recipients: your address.
4. **Create budget**.

**Expected:** the template sets up alerts when **actual** spend reaches 85% and 100%, and when **forecasted** spend reaches 100%. The first two budgets in an account are free.

- [ ] Budget `sysdesign-monthly` exists with your email

---

## Step 2.4 — Import your SSH key

**Where:** ☁️ **EC2** → left menu **Network & Security** → **Key Pairs** → **Actions** → **Import key pair**

1. Name: `quest-vm`.
2. Paste the whole line from:
   ```powershell
   Get-Content $HOME\.ssh\quest_vm.pub
   ```
3. **Import key pair**.

(Importing means AWS never sees your private key. The alternative, letting AWS generate one, works too but makes AWS the source of your private key file.)

- [ ] Key pair `quest-vm` listed

---

## Step 2.5 — Create the security group (firewall)

**Where:** ☁️ **EC2** → **Network & Security** → **Security Groups** → **Create security group**

| Field | Value |
|---|---|
| Name | `sysdesign-k3s-sg` |
| Description | SSH from me, HTTP/HTTPS from anywhere |
| VPC | the default VPC (`vpc-…` *(default)*) |

**Inbound rules** → **Add rule** three times:

| Type | Source | Description |
|---|---|---|
| SSH (22) | **My IP** | SSH from my PC |
| HTTP (80) | **Anywhere-IPv4** (`0.0.0.0/0`) | Let's Encrypt + redirect |
| HTTPS (443) | **Anywhere-IPv4** (`0.0.0.0/0`) | The app |

**Outbound rules:** leave the default (all traffic allowed).

→ **Create security group**.

> **"My IP" trade-off:** SSH is invisible to everyone else, but if your home IP changes (common with ISPs), SSH will time out until you edit this rule to "My IP" again. That's a 30-second fix in this same screen.
>
> **Never add** 6443 (Kubernetes API), 8080 or 8081 here. Those are reached through SSH only (Phase 11).

- [ ] `sysdesign-k3s-sg` created with exactly three inbound rules

---

## Step 2.6 — Launch the instance

**Where:** ☁️ **EC2** → **Instances** → **Launch instances**

Go through the form top to bottom:

1. **Name:** `sysdesign-k3s`.
2. **Application and OS Images (AMI):** **Ubuntu** → **Ubuntu Server 24.04 LTS (HVM), SSD Volume Type** → Architecture **64-bit (Arm)**.
3. **Instance type:** `t4g.large`. The panel shows the on-demand hourly price for your region, so note it.
4. **Key pair:** `quest-vm`.
5. **Network settings** → **Edit**:
   - VPC: the default VPC · Subnet: *No preference* · **Auto-assign public IP: Enable**
   - Firewall: **Select existing security group** → `sysdesign-k3s-sg`
6. **Configure storage:** **40** GiB, **gp3**.
7. **Advanced details** (expand it):

   | Setting | Value | Why |
   |---|---|---|
   | Termination protection | **Enable** | A misclick on "Terminate" can't delete your server |
   | Credit specification | **Standard** | Throttles CPU when credits run out, instead of billing extra ("Unlimited" is the default for `t4g`) |
   | Metadata accessible | Enabled | Needed for the IAM role in Phase 13 |
   | Metadata version | **V2 only (token required)** | Hardened metadata service (IMDSv2) |
   | Metadata response hop limit | **2** | Lets *pods* (one network hop further away) reach the metadata service for the S3 backup role |
   | IAM instance profile | *(leave empty)* | Added in Phase 13 |

8. **Summary** panel → **Launch instance**.

**Expected:** "Successfully initiated launch of instance (i-…)". Instances → your instance goes **Pending** → **Running**, and **Status checks** reach `3/3 checks passed` within ~2 minutes.

**If it fails:**
- `InsufficientInstanceCapacity` → edit Network settings and pick a specific subnet in another Availability Zone, then launch again.
- `You have requested more vCPU capacity than your current vCPU limit` → new accounts sometimes start with low limits. ☁️ **Service Quotas** → Amazon EC2 → *Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances* → request **8**. This is usually approved within hours.

- [ ] Instance **Running**, 3/3 checks passed

---

## Step 2.7 — Note the instance details

**Where:** ☁️ **EC2** → **Instances** → click `sysdesign-k3s`

Note into your values sheet:
- **Instance ID** (`i-0…`)
- **Public IPv4 address**, your current `<PUBLIC_IP>`. It **changes every time you stop and start** the instance. Phase 3 makes DuckDNS follow it automatically.

- [ ] Instance ID and current public IP noted

---

## Step 2.8 — Set up a short SSH alias

**Where:** 🪟 Windows

```powershell
@"

Host quest-vm
    HostName sysdesignquest.duckdns.org
    User ubuntu
    IdentityFile ~/.ssh/quest_vm
    ServerAliveInterval 30
    StrictHostKeyChecking accept-new
"@ | Add-Content -Path $HOME\.ssh\config -Encoding ascii
```

- `HostName` is your **DuckDNS name**, not the IP, so the alias keeps working after the IP changes (once Phase 3's updater runs).
- `StrictHostKeyChecking accept-new` accepts the server's identity the first time and still refuses if it ever *changes*, which is the case that matters.

Until DuckDNS points at the instance (next phase), connect by IP once:

```powershell
ssh -i $HOME\.ssh\quest_vm ubuntu@<PUBLIC_IP>
```

- [ ] `$HOME\.ssh\config` contains the `Host quest-vm` block

---

## Step 2.9 — First login

**Where:** 🪟 Windows → `ssh -i $HOME\.ssh\quest_vm ubuntu@<PUBLIC_IP>`

Answer `yes` to the host-key question the first time, and enter your key passphrase if asked.

**Expected:** a prompt like `ubuntu@ip-172-31-x-x:~$`.

```bash
uname -m
lsb_release -ds
nproc
free -h
```

**Expected:** `aarch64`, `Ubuntu 24.04.x LTS`, `2`, and about 7.6 Gi total memory.

Stay logged in for Phase 3.

**If it fails:**
- `Connection timed out` → the SSH rule's "My IP" doesn't match your current IP (Step 2.5), or the instance has no public IP (check Step 2.6's *Auto-assign public IP*).
- `Permission denied (publickey)` → wrong key, or you used a user other than `ubuntu`.

- [ ] Logged in; shows aarch64 / Ubuntu 24.04 / 2 CPUs / ~7.6 Gi

---

## ✅ Checkpoint

- [ ] Root + `admin` have MFA; you work as `admin`
- [ ] Budget alert exists
- [ ] Instance `t4g.large` Running, 40 GiB gp3, termination protection on, credits Standard, IMDSv2 with hop limit 2
- [ ] SSH by IP works
