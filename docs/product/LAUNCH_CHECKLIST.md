# Launch Checklist

Everything SysDesign Quest needs to be production-ready and marketable, in order. Requirement IDs (→ SEC-2) point into the [product specification](PRODUCT_SPEC.md).

**How to use it**

- **P0** gates the closed beta: nothing here can wait once a stranger has an account.
- **P1** gates the public launch: it makes the product safe at scale and worth marketing.
- **P2** comes after launch.
- Each item says **why** it's here (with the evidence) and **when it's done**. Tick an item only when its "Done when" is true.
- Items marked *(if Coding launches)* or *(if paid)* depend on a decision. Skip them if the decision goes the other way.

Baseline on 2026-09-27: 79 Python tests pass (run with `DATABASE_URL=sqlite:///db.sqlite3`), 9 JS tests pass, and `manage.py check --deploy` reports 4 warnings.

---

## Decisions to make first

The options are in [spec §12](PRODUCT_SPEC.md#12-open-decisions). These shape several items below.

- [ ] **D-2** Production hosting at launch. *Needed before beta.*
- [ ] **D-3** Coding at launch: hide it, build an isolated runner, or run code in the browser. *Needed before beta.*
- [ ] **D-1** Business model: free, freemium, one-time or subscription. *Needed before launch.*
- [ ] **D-4** Domain name and trademark check. *Needed before launch.*
- [ ] **D-5** XP policy for replays and wrong quiz answers. *Needed before launch.*
- [ ] **D-6** Accessibility standard (WCAG 2.2 AA proposed). *Needed before launch.*
- [ ] **D-7** What's public without an account. *Needed before launch.*
- [ ] **D-8** Email provider · **D-9** Analytics tool · **D-10** Ring Balancer's lesson · **D-11** Voice and emoji · **D-12** Content licence · **D-13** Bit Budget's lesson

---

## P0: before the first outside user (closed-beta gate)

### Security

- [ ] **P0-01 · Close the code-runner escape, or keep Coding off** (→ GAME-6, SEC-3)
  - **Why:** `static_check` (`learn/code_runner.py:68`) only looks at import statements and call names. `sys` is on the allowlist (line 47), and `import sys; sys.modules['os']` passes the check (verified). That hands a submission the whole `os` module: files, processes, and on Linux the web server's environment (`DATABASE_URL`, `SECRET_KEY`) through `/proc`. There are no coding challenges today, so the runner can't be reached yet. The first challenge you generate opens it.
  - **Done when:** either Coding is hidden from non-staff users behind a flag, or submissions run in an isolated runner (no network, none of the app's files or environment, CPU, memory and process limits) and a test shows a `sys.modules['os']` payload can't read anything outside its sandbox. Removing `sys` from the allowlist is a stopgap only: filtering Python by its syntax tree isn't a security boundary.

- [ ] **P0-02 · Fail fast on unsafe production settings** (→ SEC-1)
  - **Why:** `config/settings.py:30` falls back to the development `SECRET_KEY` in the repo, and line 36 defaults `DEBUG` to `True`. A missing environment variable on a new host runs silently insecure.
  - **Done when:** `DEBUG` defaults to `False` (local development opts in through `.env`), and with `DEBUG` off a missing `SECRET_KEY` or empty `ALLOWED_HOSTS` stops startup with a clear error.

- [ ] **P0-03 · HTTPS and cookie hardening** (→ SEC-2)
  - **Why:** `manage.py check --deploy` warns about HSTS (W004), SSL redirect (W008), the session cookie (W012) and the CSRF cookie (W016).
  - **Done when:** `check --deploy` prints no warnings with production environment variables, `SECURE_PROXY_SSL_HEADER` matches the host's proxy, and `CSRF_TRUSTED_ORIGINS` lists the real domain. Start HSTS with a short `max-age` and raise it after a week without problems.

- [ ] **P0-04 · Rate-limit sign-in and write endpoints** (→ SEC-4, ACC-8)
  - **Why:** nothing is throttled. Passwords can be guessed without limit, signup has no bot protection, and code submissions can keep web workers busy.
  - **Done when:** repeated failed logins lock out or back off, signup and password reset are limited per IP, code submission and the `*/move/` endpoints are limited per user, and tests cover each limit.

- [ ] **P0-05 · Sanitize Markdown in coding prompts** (→ SEC-6)
  - **Why:** `learn/templates/learn/coding_challenge.html:131` puts `marked.parse(...)` straight into `innerHTML`. Prompts come from an LLM. An admin reviews them, but a scenario with injected instructions could slip HTML through.
  - **Done when:** the rendered HTML passes through DOMPurify (or is rendered and sanitized on the server), and a test shows a `<script>` or `onerror=` payload is stripped.

- [ ] **P0-06 · Keep tests off remote databases** (→ SEC-8)
  - **Why:** `.env` holds the Neon URL, and a test run once created `test_neondb` on Neon ([CONTEXT.md](../../CONTEXT.md)). Today you have to remember `DATABASE_URL=sqlite:///db.sqlite3`.
  - **Done when:** `manage.py test` uses SQLite whatever `.env` says, or refuses to run against a non-local host. Also drop the leftover `test_neondb` database from Neon.

### Data integrity

- [ ] **P0-07 · Make progress updates atomic** (→ PRG-6)
  - **Why:** `UserProfile.add_xp` (`learn/models.py:183`) reads XP, adds in Python and saves. The `record_*` functions in `learn/services.py` write the attempt, XP, streak, mastery and review card without a transaction. Two tabs or a double submit can lose XP, and an error part-way leaves progress half-written.
  - **Done when:** XP and streak updates use `F()` expressions or `select_for_update`, every `record_*` function runs inside `transaction.atomic()`, and a test with two concurrent awards keeps both.

- [ ] **P0-08 · Bring production content up to date, safely** (→ ADM-1, ADM-3)
  - **Why:** Neon hasn't been reseeded since the curriculum replaced the earlier content, so production still serves chapters summarized from third-party study books ([IP audit](IP_AUDIT.md) IP-02). `seed_content` deletes every concept that's no longer defined, along with learners' attempts on it, and `seed_games` now also removes the retired Spot the Flaw and Traffic Day scenarios.
  - **Done when:** a backup is taken, then `migrate`, `seed_content` and `seed_games` run against production. Every concept page and game loads, and the counts match the repo: 39 concepts, 225 questions, 6 Builder, 28 Matching and 14 Ordering challenges, and one each of the five other games. Better still, add a `--dry-run` to the seed commands first (P1-22).

- [ ] **P0-09 · Automated backups with a tested restore** (→ OPS-3)
  - **Why:** DEPLOYMENT.md notes Neon's free tier has no long-term backup guarantee. Beta users' progress is real data from day one.
  - **Done when:** daily backups run without you, you've restored one into a scratch database and run the app against it, and the steps are written down.

### Accounts

- [ ] **P0-10 · Email at signup and a working password reset** (→ ACC-2, ACC-4, NTF-1)
  - **Why:** signup (`learn/views.py:30`) collects only a username, so a beta user who forgets their password is locked out for good. The reset URLs exist, but there's no email backend, no templates and no link.
  - **Done when:** signup takes a unique email, a transactional email provider sends mail from your domain with SPF and DKIM set up, the login page has a "Forgot password?" link that sends a working reset, and new accounts get a verification email. django-allauth covers verification, reset, login throttling (P0-04) and social login (P2) in one package.

- [ ] **P0-11 · Account deletion and data export** (→ ACC-6, ACC-7, PRV-2)
  - **Why:** privacy laws give users both rights, and beta users will ask.
  - **Done when:** a learner can download their data as JSON and delete their account from a settings page. Deletion removes the profile, attempts, review cards, badges, code submissions and sessions.

### Legal

- [ ] **P0-12 · Privacy policy and terms** (→ PRV-1, PUB-4)
  - **Why:** both are needed the moment strangers create accounts.
  - **Done when:** both pages are live and linked from the footer and the signup form. The privacy policy lists the data and third parties in [spec §8.2](PRODUCT_SPEC.md#82-privacy-prv). The terms cover acceptable use (including code submissions), who owns the content (D-12), and say the product doesn't guarantee interview results.

- [ ] **P0-16 · Clear the P0 items in the IP audit**
  - **Why:** the [IP and marketability audit](IP_AUDIT.md) lists what could stop the product being sold or shown: third-party study material still in production and in git history, superseded prototypes that keep book-derived scenarios, and licence and attribution gaps.
  - **Done when:** every IP-audit item marked P0 is ticked, and new content follows [CONTENT_STANDARDS.md](../learning/CONTENT_STANDARDS.md).

### Visibility

- [ ] **P0-13 · Error tracking and logs** (→ OPS-5)
  - **Why:** there's no `LOGGING` configuration and no error reporting. With `DEBUG=False`, beta users' 500 errors vanish.
  - **Done when:** unhandled exceptions reach an error tracker that emails you, app logs go to stdout at INFO, and events are scrubbed of passwords and code submissions.

- [ ] **P0-14 · Health check and uptime alert** (→ OPS-4)
  - **Done when:** `/healthz` returns 200 after a database query, and an external monitor checks it every few minutes and alerts you when it fails.

- [ ] **P0-15 · CI on every push** (→ OPS-6)
  - **Why:** the repo has no CI configuration, so the tests only run when someone remembers to run them.
  - **Done when:** a pipeline runs `manage.py test` on SQLite, `node --test learn/js_tests/*.test.js` (Node 24 won't take the directory itself), `makemigrations --check --dry-run`, `check --deploy` with production-like variables, and `pip-audit`. A red build blocks merging.

---

## P1: before public launch

### Public site and marketing

- [ ] **P1-01 · Landing page** (→ PUB-1)
  - **Why:** every page requires a login today, so a visitor from a link or search sees only a login form.
  - **Done when:** anonymous visitors to `/` see what the product is, how the loop works, the curriculum, a live game preview and a sign-up button, and signed-in users still land on the dashboard. It must work at 360 px wide.

- [ ] **P1-02 · Try without an account** (→ PUB-2)
  - **Why:** portfolio viewers won't sign up, and learners want to try first.
  - **Done when:** one lesson's notes, its quiz and one game work without an account, and signing up keeps that progress.

- [ ] **P1-03 · Public catalogue and search basics** (→ PUB-3, PUB-5, D-7)
  - **Done when:** every lesson and case study has a public page with its objectives and sources, each page has its own title, description, canonical URL and Open Graph/Twitter card, `sitemap.xml` and `robots.txt` are served, and Google Search Console shows the pages indexed.

- [ ] **P1-04 · Brand assets** (→ PUB-5, D-4)
  - **Done when:** there's a logo, favicon, app icons, a share image, screenshots of each game, and a 60–90 second clip of two or three games for launch posts.

- [ ] **P1-05 · Domain and email** (→ D-4)
  - **Done when:** the app runs on your own domain with HTTPS, and a contact address plus the transactional sending domain have SPF, DKIM and DMARC.

- [ ] **P1-06 · About, FAQ, contact and a feedback channel** (→ PUB-4, LRN-9)
  - **Done when:** the pages are linked from the footer, and each concept and question has a "Report a problem" link that lands in admin.

- [ ] **P1-07 · Branded 404 and 500 pages** (→ PUB-6)
  - **Done when:** both use the site's layout with a way back to the dashboard, and the 500 page loads no database data.

### Learner experience

- [ ] **P1-08 · First-run onboarding** (→ NAV-4)
  - **Done when:** a new account sees the loop explained in a few steps, gets a suggested starting point, and the empty dashboard has one obvious next action.

- [ ] **P1-09 · Real-device phone pass** (→ GAME-4, A11Y-2)
  - **Why:** PRODUCT.md makes "every activity works on a phone" a confirmed requirement. The tap fallbacks exist, but no one has tested them on a real phone.
  - **Done when:** every activity, including the code editor, has been played to the end on iOS Safari and Android Chrome at 360 px, and the defects found are fixed. CodeMirror 5 is weak on touch; consider CodeMirror 6.

- [ ] **P1-10 · Accessibility audit** (→ A11Y-1 to A11Y-4, D-6)
  - **Done when:** every game can be finished by keyboard alone, screen readers announce game state changes, contrast passes, no meaning rests on colour alone, and motion respects `prefers-reduced-motion`.

- [ ] **P1-11 · Streaks in the learner's time zone** (→ REV-4)
  - **Why:** `TIME_ZONE = 'UTC'` and `touch_streak` uses the server's date, so a learner in India (UTC+5:30) who studies at 05:00 one day and 23:00 the next loses their streak: those are two UTC days apart.
  - **Done when:** each profile stores a time zone (detected in the browser and editable), and streaks and "due today" use it.

- [ ] **P1-12 · Review reminder emails** (→ REV-5, NTF-2)
  - **Why:** the product runs on coming back daily, and nothing reminds learners to.
  - **Done when:** learners can opt in to an email when reviews are due, sends are capped (say one a day), and every email has a one-click unsubscribe.

- [ ] **P1-13 · Apply the XP policy** (→ GAME-5, QZ-4, D-5)
  - **Why:** every replay pays full XP and a wrong quiz answer pays 2 XP, so grinding one easy game unlocks every level-gated chapter.
  - **Done when:** the chosen policy is implemented and tested, and the badges page or the game's end screen explains it.

- [ ] **P1-14 · Settings page** (→ ACC-5)
  - **Done when:** learners can change their password, email, time zone and reminder preferences, and reach export and delete (P0-11) from it.

- [ ] **P1-15 · Coding content, or Coding hidden** (→ GAME-7, ADM-4, D-3) *(if Coding launches)*
  - **Why:** there are no coding challenges, and the Gemini generator has never run with a real key. Until one exists, nobody can earn the Coder or Game Master badges. If Coding stays hidden, drop the perfect-coding condition from Game Master (`learn/services.py:646`).
  - **Done when:** there's at least one reviewed challenge per stage, each generated through the admin flow (the generator's first real run) and solved by you against its hidden tests.

- [ ] **P1-16 · Copy and docs consistency** (→ D-11)
  - **Why:** the docs have drifted from the code. PRODUCT.md and README.md say styling is Tailwind from a CDN (it's `quest.css` now), README says drag and drop is desktop-only (Builder and Matching have tap fallbacks), and the counts differ between documents.
  - **Done when:** the voice is decided, UI labels follow it, and README, PRODUCT.md and CONTEXT.md match the code.

### Infrastructure

- [ ] **P1-17 · Always-on production hosting and staging** (→ OPS-1, OPS-2, OPS-7, D-2)
  - **Why:** the free tiers sleep, so the first visitor after an idle spell waits 30–60 seconds. That's a launch-day first impression. It's worth doing before the beta too, so cold starts don't skew its numbers.
  - **Done when:** production is on an always-on instance with managed Postgres and point-in-time restore, and a staging environment gets every migration and reseed first.

- [ ] **P1-18 · Self-host fonts and scripts, and add a CSP** (→ SEC-5, PRV-1)
  - **Why:** Google Fonts and cdnjs receive every visitor's IP address, and none of the 5 cdnjs assets has an `integrity` hash.
  - **Done when:** Archivo, SortableJS, CodeMirror and marked are served from `static/`, and a Content Security Policy header allows only your own origin for scripts. Check it with the browser console clean on every page.

- [ ] **P1-19 · Measure and fix performance** (→ PERF-1, PERF-2, PERF-3, PERF-5)
  - **Why:** `_tiers_for_chapters` (`learn/views.py:42`) runs two count queries per chapter, the dashboard counts eight challenge types one by one (`learn/views.py:157`), and the Procfile uses Gunicorn's default of one worker.
  - **Done when:** those pages use a fixed number of queries, the Gunicorn worker count is set for the instance, a load test with 50 concurrent learners meets PERF-1, and Lighthouse on the landing page and dashboard meets PERF-2.

- [ ] **P1-20 · Take code execution off the request path** (→ PERF-4) *(if Coding launches)*
  - **Done when:** submissions go to a queue or a remote runner, and the page polls for the result.

- [ ] **P1-21 · Harden admin** (→ ADM-5)
  - **Done when:** admin lives somewhere other than `/admin/`, staff accounts need two-factor sign-in, and only the owner has staff access.

- [ ] **P1-22 · Runbook and a reseed dry run** (→ OPS-8, ADM-3)
  - **Done when:** one document covers deploying, rolling back, restoring, reseeding and rotating secrets for the chosen host, and each seed command has a `--dry-run` that lists what it would create, update and delete (including learner attempts).

- [ ] **P1-23 · Dependency hygiene** (→ SEC-7)
  - **Why:** `psycopg` is pinned to a range, nothing flags vulnerable packages, and CodeMirror 5 and marked 4.3 are several major versions behind.
  - **Done when:** every dependency is pinned exactly, Dependabot (or similar) opens update PRs, and the front-end libraries are current.

- [ ] **P1-24 · Analytics and an owner dashboard** (→ ANL-1, ANL-2, ADM-6, D-9)
  - **Done when:** cookieless page analytics run, and you can see signups, activation, D1/D7 retention and the most-missed questions without writing SQL.

### Legal and business

- [ ] **P1-25 · Cookie check** (→ PRV-3)
  - **Done when:** the site still sets only strictly necessary cookies, or a consent banner gates the rest.

- [ ] **P1-26 · Name and trademark check** (→ D-4)
  - **Done when:** a trademark search in your main markets finds no conflict with "SysDesign Quest", and the domain and social handles are registered.

- [ ] **P1-27 · Payments** (→ BIZ-1 to BIZ-3, PUB-7, D-1) *(if paid)*
  - **Done when:** entitlements gate paid content, checkout, receipts, cancellation and refunds work end to end in the provider's test mode, sales tax is handled, and the pricing page and refund policy are live.

- [ ] **P1-28 · State the content licence** (→ D-12)
  - **Done when:** the footer and the terms say how the curriculum text may be reused.

### Beta

- [ ] **P1-29 · Run the closed beta**
  - **Done when:** 20–50 invited learners have used the app for at least 2 weeks with a feedback form in the app, their blocking feedback is fixed, and the activation and D7 baselines are recorded in [spec §5](PRODUCT_SPEC.md#5-success-metrics) with launch targets set.

---

## P2: after launch

- [ ] **P2-01** Sign in with Google and GitHub (→ ACC-9)
- [ ] **P2-02** Search across lessons, case studies and the glossary (→ NAV-5)
- [ ] **P2-03** Shareable badge and progress cards, and an optional leaderboard (→ PRG-7, after D-5)
- [ ] **P2-04** Installable app (PWA) with offline notes and push reminders
- [ ] **P2-05** Port the remaining game prototypes in `docs/games/prototypes`: ~~Bit Budget~~ (ported 2026-09-29, reworked under IP-18), Estimathon, Pattern Deck
- [ ] **P2-06** Work through the content ideas queue in [content-ledger.md](../learning/content-ledger.md): rate limiting, replication lag, real-time delivery and more
- [ ] **P2-07** A scheduled check of every source link against `sources.json`
- [ ] **P2-08** Mock interview mode: a timed case study, self-scored against its rubric
- [ ] **P2-09** Housekeeping: delete the untracked clutter in the repo root (`file.doc`, `file.docx`, `file.html`, `table.csv`, `try.py`, `testfile.tmp`, `db.sqlite3-journal-*.bak`)

---

## Go/no-go gates

**Closed beta:** go when

- [ ] every P0 item is ticked
- [ ] D-2 and D-3 are decided
- [ ] *(recommended)* P1-17 is done, so cold starts don't skew the beta's numbers

**Public launch:** go when

- [ ] every P1 item that applies is ticked
- [ ] D-1, D-4, D-5, D-6 and D-7 are decided
- [ ] the beta ran for at least 2 weeks with no open P0-severity bug

Then we plan the go-to-market together: positioning, channels, launch assets and timing.
