# SysDesign Quest: Product Specification

| | |
|---|---|
| Status | Draft 1, pre-launch |
| Owner | Christo Joseph |
| Last updated | 2026-09-27 |
| Related | [PRODUCT.md](../../PRODUCT.md) (positioning, audience, voice) · [DESIGN.md](../../DESIGN.md) (visual system) · [docs/learning](../learning/README.md) (curriculum) · [DEPLOYMENT.md](../../DEPLOYMENT.md) · [Launch checklist](LAUNCH_CHECKLIST.md) |

This document describes what SysDesign Quest does today and what it must do before a public launch. Each requirement has an ID and a status so the [launch checklist](LAUNCH_CHECKLIST.md) can point at it:

- **Built**: in the code on `master` and covered by tests or a documented check.
- **Partial**: exists but falls short of the requirement. The note says how.
- **Planned**: not built.

Business calls (pricing, hosting, what's public) are listed under [Open decisions](#12-open-decisions) rather than decided here.

---

## 1. Summary

SysDesign Quest is a web app for people preparing for system design and backend interviews. It turns an original curriculum (31 lessons, 6 case studies, 62 cited primary sources) into a daily learning loop: read structured notes, answer a quiz, play games that make you build and reason about systems, and come back for spaced-repetition reviews. XP, levels, streaks and badges sit on top.

It runs on Render's free tier with a Neon Postgres database and hasn't been opened to the public. [PRODUCT.md](../../PRODUCT.md) records one confirmed launch condition: the app isn't opened to the public until code submissions run in a truly isolated environment.

## 2. Problem

Candidates usually prepare for system design interviews by reading and watching. That builds recognition: a design looks familiar when you see it again. The interview tests recall and reasoning instead. You have to produce a design from a blank page, defend its trade-offs, and adjust when the interviewer changes a constraint. Passive study gives little practice at that, and nothing brings a topic back before it fades.

SysDesign Quest answers with three mechanisms:

- **Retention.** Short daily reps (Daily Review, quizzes, streaks), scheduled by SM-2, bring concepts back just before they would be forgotten.
- **Comprehension.** Longer sessions (notes, deep dives, architecture building, simulations, coding) make the learner produce and reason rather than recognize.
- **Guessing costs.** Every game uses negative scoring, so spamming options loses points.

## 3. Goals and non-goals

### Goals for public launch (v1.0)

1. A stranger can understand the product, try it without an account, and sign up in one visit.
2. A signed-up learner can work through the whole curriculum on desktop or phone, and the app brings them back when reviews are due.
3. The service is safe to open: untrusted code is isolated, accounts can be recovered, personal data can be exported and deleted, and the owner sees errors before users report them.
4. It behaves like a finished product: no cold starts, no dead ends, consistent copy.

### Non-goals for v1.0

- Native iOS or Android apps. The web app must work on phones instead.
- Video lessons or live mock interviews with people.
- Coding in languages other than Python 3.
- AI grading of free-form designs.
- Team, classroom or enterprise accounts.
- Languages other than English.

## 4. Users

| Persona | Who | What they need | Priority |
|---|---|---|---|
| Public learner | Software engineers preparing for system design or backend interviews | A path from beginner to expert, practice that forces recall, a reason to return daily, short sessions that work on a phone | Primary launch audience |
| Owner-learner | The builder, studying daily | The same, plus admin tools and the unlock-all preview | Current user |
| Portfolio viewer | Recruiters and peers judging the builder's work | To see the product working within two minutes, without signing up | Secondary. They don't return |
| Content admin | The owner, maintaining content | To seed and update content safely, generate coding challenges, and see what learners get wrong | Internal |

## 5. Success metrics

The definitions belong to the spec. Set the targets from the closed-beta baseline, and don't publish any number before it's measured (PRODUCT.md: no fabricated user counts or outcomes).

| Metric | Definition |
|---|---|
| **North star: weekly retained learners** | Accounts with learning activity (a quiz answer, game attempt or review) on 3 or more distinct days in a calendar week |
| Activation | Share of new signups who finish a full quiz run or a game within 24 hours of signing up |
| D1 / D7 / D30 retention | Share of a signup cohort with any learning activity on day 1, 7 and 30 |
| Review completion | Share of due review cards answered within 24 hours of falling due |
| Landing conversion | Anonymous landing-page visitors who sign up |
| Mastery progress | Median concepts mastered per active learner after 30 days |

## 6. Content model and curriculum

```
Book (source collection)
 └─ Topic (a dashboard section; one per curriculum stage)
     └─ Chapter (unlock level, difficulty)
         └─ Concept
             ├─ Notes: teaser, headed sections, deep dives, objectives, prerequisites, sources
             ├─ Question bank (single-answer and multi-select)
             └─ "Play to learn" challenges: any of the 9 game types in §7.7
```

**Curriculum stages** (source: [docs/learning](../learning/README.md), loaded by `learn/curriculum.py`):

| Stage | Content level | Theme | Unlocks at XP level |
|---|---|---|---|
| 1 | Beginner | Understand a request | 1 |
| 2 | Intermediate | Scale a service | 2 |
| 3 | Advanced | Handle distributed failures | 4 |
| 4 | Advanced | Operate reliably | 6 |
| 5 | Advanced | Reason about guarantees | 8 |
| Case studies (6) | Advanced | Ticket booking, payments, job scheduling, search, feature flags, multi-region SaaS | 5, 7, 9 |
| Reference chapters (2) | Intermediate | Python internals, OS file handling | 1 |

Every piece of content has exactly one of three levels: Beginner, Intermediate or Advanced. New content must declare its level ([content standards](../learning/CONTENT_STANDARDS.md), section 1).

**Content in the repo seed, as of 2026-09-27:** 39 concepts, 225 quiz questions, 6 Architecture Builder, 28 Matching and 14 Ordering challenges, one each of Spot the Flaw, Traffic Day, Quorum Casino, Ring Balancer and Bit Budget, 19 badges, and **0 coding challenges** (those are generated in admin, and none has been made yet).

**Databases lag the repo.** The local `db.sqlite3` has 38 concepts, 219 questions and 27 Matching challenges (sd-31 isn't seeded). Production on Neon hasn't been reseeded since the curriculum replaced the retired earlier content ([CONTEXT.md](../../CONTEXT.md)), so it still serves that content until it is.

**Content rules** ([docs/learning/CONTENT_STANDARDS.md](../learning/CONTENT_STANDARDS.md) is the full version; tests in `learn/test_content_standards.py`, `learn/test_curriculum.py` and `learn/tests.py` enforce the checkable parts):

1. Original writing grounded in primary sources. Wording, examples, numbers and structure are our own, never copied or closely paraphrased from a book, course, blog or documentation page, and no study book or course is named anywhere. The tests check seeded and repository text against fingerprints of the names the earliest content used.
2. Every lesson has at least one game. Every case study has an Architecture Builder built from its reference architecture, and builders wire only required parts.
3. Every lesson lists its sources. `sources.json` records a review date for each.
4. Examples, capacity numbers and latencies are hypothetical unless a source says otherwise, and every fact is checked against a dated primary source.
5. Every item is Beginner, Intermediate or Advanced.
6. Quiz and game choices are similar in length, tone and yes/no polarity, so the right answer can't be spotted by its shape.

## 7. Functional requirements

### 7.1 Accounts (ACC)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| ACC-1 | Sign up with a username and a password that passes Django's four password validators | Built | `learn/views.py` `signup`, `UserCreationForm` |
| ACC-2 | Sign up with an email address that is unique per account and verified by link | Planned | There's no email field, so nothing in this spec that needs email works yet |
| ACC-3 | Log in, and log out with a POST | Built | |
| ACC-4 | Reset a forgotten password by email | Partial | Django's reset URLs are mounted under `/accounts/`, but there's no email backend, no styled templates and no link on the login page |
| ACC-5 | Settings page: change password, email, time zone and reminder preferences | Planned | |
| ACC-6 | Delete my account and all my data, self-service, after confirming | Planned | |
| ACC-7 | Download my data (profile, attempts, badges, code submissions) as JSON | Planned | |
| ACC-8 | Throttle repeated logins, signups and reset requests per IP and per account | Planned | |
| ACC-9 | Sign in with Google or GitHub | Planned, post-launch | |

### 7.2 Public site (PUB)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| PUB-1 | Anonymous visitors to `/` get a landing page: what it is, how the loop works, the curriculum, a live game preview, and a sign-up call to action. Signed-in users still get the dashboard | Planned | Every page except login and signup is `login_required` today, so `/` redirects to the login form |
| PUB-2 | Try it without an account: at least one lesson's notes, quiz and game, with progress carried into the account on signup | Planned | Also serves portfolio viewers |
| PUB-3 | Public curriculum catalogue listing each lesson and case study's title, stage, objectives and sources, indexable by search engines | Planned | How much of the notes is public is D-7 |
| PUB-4 | About, FAQ, contact, privacy policy and terms pages, linked from a footer on every page | Planned | `base.html` has no footer |
| PUB-5 | Search and sharing metadata: a title and description per page, Open Graph and Twitter cards, canonical URLs, `sitemap.xml`, `robots.txt`, favicon and app icons | Planned | `base.html` sets only charset, viewport and title |
| PUB-6 | Branded 404 and 500 pages | Planned | Django's plain defaults show when `DEBUG=False` |
| PUB-7 | Pricing page and checkout | Planned if paid | Depends on D-1 |

### 7.3 Dashboard and navigation (NAV)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| NAV-1 | Dashboard shows level and XP progress, streak, due reviews, "continue where you left off", and a progress map with mastery per chapter | Built | |
| NAV-2 | Topic, chapter and concept pages with breadcrumbs and the file-drawer navigation | Built | |
| NAV-3 | A locked chapter shows the level it needs. Opening one redirects with a message | Built | |
| NAV-4 | First-run onboarding: explain the loop (notes, quiz, games, review), suggest a starting stage, and give the empty dashboard a clear first step | Planned | |
| NAV-5 | Search across lessons, case studies and glossary terms | Planned, post-launch | |

### 7.4 Lessons and case studies (LRN)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| LRN-1 | A concept page shows a one-line teaser. "View Notes" opens headed sections (Intuition, How it works, Worked example, Trade-offs and failure modes, Practice) | Built | |
| LRN-2 | Practice answers and dense sub-topics sit behind "Click to know more" deep dives | Built | |
| LRN-3 | Lesson metadata: ID, stage, study time, objectives, linked prerequisites and sources | Built | |
| LRN-4 | Study mode shows the notes one card at a time with Back, Next and progress | Built | |
| LRN-5 | Read aloud through the browser's speech synthesis | Built | |
| LRN-6 | Unscored interactive walkthroughs where a lesson benefits from one | Built for 4 lessons | sd-01 request walkthrough, sd-02 HTTP contract lab, sd-03 latency and queueing lab, sd-04 shared-state concurrency lab |
| LRN-7 | Case study pages show requirements, estimates, the reference architecture and the rubric | Built | |
| LRN-8 | The "Play to learn" grid lists every activity attached to the concept | Built | |
| LRN-9 | "Report a problem" on each concept and question, landing in an admin queue | Planned | |

### 7.5 Quiz (QZ)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| QZ-1 | A run asks every question in the concept's bank once, shuffled, showing "Question X of N". The end screen shows the score, % correct and XP. Retake reshuffles | Built | |
| QZ-2 | Single-answer and multi-select questions. A multi-select answer is correct only if it's exactly the right set | Built | |
| QZ-3 | Each answer shows the question's explanation | Built | |
| QZ-4 | A correct answer pays 10 × difficulty XP. A wrong answer pays 2 XP | Built | Paying for wrong answers conflicts with the "Earn the answer" principle (D-5) |
| QZ-5 | A run survives a page reload | Built | Kept in the session, so it's lost if the session expires |
| QZ-6 | Every answer updates the concept's mastery and review schedule | Built | |

### 7.6 Daily Review and streaks (REV)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| REV-1 | One SM-2 card per learner and concept. A correct answer counts as quality 5 and a wrong one as quality 1. Intervals run 1 day, 6 days, then the previous interval × the ease factor (floor 1.3). A wrong answer resets to 1 day | Built | `ReviewCard.schedule` |
| REV-2 | The review page serves due cards and shows how many remain and each card's Leitner box | Built | |
| REV-3 | Streaks count consecutive days with activity. The longest streak is kept | Built | Days are UTC days (see REV-4) |
| REV-4 | Day boundaries for streaks and "due today" follow the learner's time zone | Planned | `TIME_ZONE = 'UTC'`, so for a learner in India the day rolls over at 05:30 |
| REV-5 | Opt-in email reminder when reviews are due, with one-click unsubscribe | Planned | Needs ACC-2 |

### 7.7 Games (GAME)

| Activity | The learner… | Scoring | Perfect-run badge | Seeded |
|---|---|---|---|---|
| Architecture Builder | places components for a case study and wires them together | +15 per required part, −10 per distractor, −5 per missing part; +10 per correct wire, −8 per wrong wire, −4 per missing wire | Architect | 6 |
| Matching | drags or taps definitions onto terms | +10 per right match, −5 per wrong one | Matchmaker | 28 |
| Ordering | puts steps in sequence | +8 per step in the right slot, −4 per misplaced step | Sequencer | 14 |
| Coding | writes a Python 3 stdin/stdout program, graded against sample and hidden tests | +12 per passing test, −3 per failing test | Coder | 0 |
| Spot the Flaw | taps planted design flaws and picks the reason | +25 per flaw with the right reason, −10 per wrong reason, −10 per healthy part tapped, −15 per flaw missed | Flaw Finder | 1 |
| Traffic Day | runs a shop's product pages through a flash-sale day, changing the design as it goes | Starts at 1,000: −50 per 10 minutes over the SLO, −1 per dollar spent, −250 if browser caching shows stale prices. XP is the score ÷ 10 | On Call | 1 |
| Quorum Casino | bets on the chance that each quorum read returns the last write | 40 × (1 + log₂ p) per bet. A perfect run has every bet within 10 points of the exact chance | Card Counter | 1 |
| Ring Balancer | balances a consistent-hash ring and predicts how many keys move | +100 per balanced ring minus positions ÷ 5, −20 per unbalanced lock-in, +50 or −25 per prediction. XP is the score ÷ 2 | Ring Master | 1 |
| Bit Budget | splits a time-ordered ID's bits between its fields, spots the spec that can't be met, and answers clock questions | +100 per spec met or impossibility spotted, −25 per failed check or wrong call, +50 or −25 per clock question. XP is the score ÷ 4 | Bit Packer | 1 |

A perfect run in any game also pays a 25 XP bonus. Game Master needs perfect runs in Builder, Matching, Ordering and Coding.

| ID | Requirement | Status | Notes |
|---|---|---|---|
| GAME-1 | Every scored game costs points for wrong moves | Built | The quiz is the exception (QZ-4) |
| GAME-2 | The server computes every score. Games with per-move feedback (Spot the Flaw, Quorum Casino, Ring Balancer, Bit Budget) keep the run in the session and never send answers to the page. Traffic Day replays the submitted plan on the server | Built | |
| GAME-3 | Each attempt stores the score, XP, a perfect flag and per-item detail | Built | |
| GAME-4 | Every game is playable by touch alone and by keyboard alone | Partial | Builder and Matching have tap-to-place and Ordering uses SortableJS, but no real-device or keyboard-only pass has been recorded |
| GAME-5 | Replays follow a stated XP policy | Partial | Every replay pays full XP today (D-5) |
| GAME-6 | Code submissions run in an isolated environment with no network, no access to the app's files, processes or secrets, CPU, memory and process limits, and off the web request path | Partial | A best-effort subprocess only, and its import allowlist can be bypassed (checklist P0-01). PRODUCT.md makes this a public-launch condition |
| GAME-7 | Coding has enough content to be worth showing: at least one challenge per stage before it's advertised | Planned | 0 challenges exist. The Coding card only appears on a concept that has one, so no page is broken, but nobody can earn the Coder or Game Master badges |

### 7.8 Progression (PRG)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| PRG-1 | Level L starts at 25 × L × (L − 1) total XP: level 2 at 50, 3 at 150, 5 at 500, 9 at 1,800 | Built | `learn/models.py` `xp_for_level` |
| PRG-2 | Chapters unlock by level (see §6) | Built | |
| PRG-3 | Superusers can toggle "Unlock All Content" to bypass level gating | Built | |
| PRG-4 | 18 badges for streaks, mastery, levels, reviews and perfect runs, with a badges page | Built | |
| PRG-5 | A concept counts as mastered after 3 or more correct answers at 70% or better accuracy | Built | |
| PRG-6 | XP, streak and mastery updates are atomic, so two tabs or a double submit can't lose an update | Planned | `UserProfile.add_xp` reads, adds and saves in Python, and the `record_*` functions don't use transactions |
| PRG-7 | Shareable badge and progress cards, and an optional leaderboard | Planned, post-launch | Only meaningful once D-5 is settled |

### 7.9 Admin and content operations (ADM)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| ADM-1 | `seed_content` (full replace), `seed_curriculum` (additive) and `seed_games` load content idempotently from `docs/learning` and the Python seed data | Built | |
| ADM-2 | `seed_content` refuses to delete concepts that hold admin-made coding challenges | Built | It does delete learners' attempts on any other removed concept |
| ADM-3 | A dry run of each seed command lists what it would create, update and delete, including learner attempts, before it touches production | Planned | |
| ADM-4 | Generate a coding challenge from a plain-language scenario with Gemini, which asks clarifying questions when the scenario is too vague. The admin previews and saves | Partial | Never run with a real API key; the admin flow was tested with the call mocked |
| ADM-5 | Django admin covers all content, lives somewhere other than `/admin/`, and requires two-factor sign-in | Partial | Default `/admin/`, password only |
| ADM-6 | An owner view of product health: signups, active learners, activation, retention and the most-missed questions | Planned | The attempt tables already hold most of this |

### 7.10 Notifications (NTF)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| NTF-1 | Transactional email for verification, password reset and account-deletion confirmation | Planned | |
| NTF-2 | Review reminders (REV-5) and an optional weekly progress email, each with unsubscribe | Planned | |

### 7.11 Monetization (BIZ)

Undecided (D-1). If the product is paid:

| ID | Requirement | Status | Notes |
|---|---|---|---|
| BIZ-1 | Entitlements decide which stages, case studies and games are free and which are paid | Planned | `chapter_is_unlocked` already gates access and is the natural place to enforce it |
| BIZ-2 | Checkout, receipts, cancellation and refunds through a payment provider, with sales tax handled | Planned | A merchant-of-record provider collects and files VAT and GST for you |
| BIZ-3 | Pricing page (PUB-7) | Planned | |

## 8. Non-functional requirements

### 8.1 Security (SEC)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| SEC-1 | Production refuses to start without `SECRET_KEY` and `ALLOWED_HOSTS`, and `DEBUG` defaults to off | Partial | `config/settings.py` falls back to the development key committed in the repo and defaults `DEBUG` to `True` |
| SEC-2 | HTTPS only: SSL redirect, HSTS, secure session and CSRF cookies, `CSRF_TRUSTED_ORIGINS`. `manage.py check --deploy` passes with no warnings | Partial | 4 warnings today: W004, W008, W012, W016 |
| SEC-3 | Untrusted code is isolated | Partial | Same as GAME-6 |
| SEC-4 | Rate limits on login, signup, password reset, code submission and game move endpoints | Planned | |
| SEC-5 | A Content Security Policy, with third-party scripts self-hosted or pinned with Subresource Integrity | Planned | 5 cdnjs assets and Google Fonts load with no `integrity` attributes |
| SEC-6 | HTML rendered from Markdown is sanitized | Planned | Coding prompts go through `marked.parse` straight into `innerHTML` |
| SEC-7 | Dependencies pinned and scanned. Secrets never committed | Partial | `.env` has never been committed (checked). No scanning, and `psycopg` is a version range |
| SEC-8 | Tests can never run against a remote database | Planned | `.env` points at Neon, and a test run once created `test_neondb` there |

### 8.2 Privacy (PRV)

**Data the app holds**

| Data | Where | Why |
|---|---|---|
| Username and password hash (email planned) | `auth_user` | The account |
| Learning activity: answers, attempts, scores, review schedule, mastery, badges | `learn_*` tables | The product |
| Code submissions | `CodingAttempt.code` | Grading history |
| Session data, including in-progress game runs | `django_session` | Resuming runs |
| IP addresses and user agents | The host's request logs | Operations |

**Third parties that receive data**

| Party | What it receives | Note |
|---|---|---|
| Render (host) | Every request | Processor |
| Neon (database) | All stored data | Processor |
| Google Fonts | Every visitor's IP address on each page load | Removed by self-hosting the font |
| cdnjs (Cloudflare) | Visitors' IP addresses on pages that load SortableJS, CodeMirror or marked | Removed by self-hosting the scripts |
| Google Gemini | Admin-written scenarios only, no learner data | Admin only |

| ID | Requirement | Status | Notes |
|---|---|---|---|
| PRV-1 | A privacy policy covering the data above, its purposes, retention and processors | Planned | |
| PRV-2 | Export and delete (ACC-6, ACC-7) | Planned | |
| PRV-3 | Only strictly necessary cookies unless the visitor consents | Built | Only the session and CSRF cookies today. Pick cookieless analytics to keep it that way without a consent banner |
| PRV-4 | Retention: request logs kept 30 days or less. Inactive accounts get a warning and are deleted after a period to be decided | Planned | |

Which laws apply depends on where the owner and learners live: for example GDPR (EU and UK), India's DPDP Act 2023 and CCPA (California). An interview-prep product will draw learners from all of them.

### 8.3 Reliability and operations (OPS)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| OPS-1 | Always-on hosting, with no cold start on the first request | Planned | Render's free tier sleeps after 15 idle minutes (30–60 s cold start), and Neon's free compute scales to zero after 5 |
| OPS-2 | 99.5% monthly availability for the public app, about 3.6 hours of downtime a month | Planned | |
| OPS-3 | Automated daily backups, with a restore tested at least quarterly. RPO 24 hours or less, RTO 4 hours or less | Planned | |
| OPS-4 | A `/healthz` endpoint that checks the database, watched by an external uptime monitor that alerts the owner | Planned | |
| OPS-5 | Error tracking with alerts, and structured logs to stdout | Planned | No `LOGGING` configuration exists |
| OPS-6 | CI on every push: Python tests, JS tests, `makemigrations --check`, `check --deploy` and a dependency audit | Planned | The repo has no CI configuration |
| OPS-7 | A staging environment that mirrors production for migrations and reseeds | Planned | |
| OPS-8 | A runbook for deploying, rolling back, restoring, reseeding and rotating secrets | Partial | DEPLOYMENT.md and docs/aws-k8s cover parts of this for their environments |

### 8.4 Performance (PERF)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| PERF-1 | Server p95 under 500 ms for page views and under 300 ms for game move endpoints, with 50 concurrent learners on the production instance | Planned | Never measured |
| PERF-2 | Core Web Vitals in the "good" range on the landing page and dashboard on a mid-range phone: LCP 2.5 s or less, INP 200 ms or less, CLS 0.1 or less | Planned | |
| PERF-3 | List pages don't run a query per row | Partial | `_tiers_for_chapters` runs two count queries per chapter, and the dashboard counts eight challenge types one query at a time |
| PERF-4 | Code runs don't tie up a web worker | Planned | Runs happen synchronously inside the request, up to 5 s per test case |
| PERF-5 | Gunicorn worker and thread counts are set for the instance size | Planned | The Procfile uses Gunicorn's defaults (1 sync worker unless `WEB_CONCURRENCY` is set) |

### 8.5 Accessibility (A11Y)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| A11Y-1 | Meet WCAG 2.2 AA | Planned | The proposed standard (D-6). PRODUCT.md sets none yet |
| A11Y-2 | Every game playable by keyboard alone and by touch alone. Dragging is never the only way | Partial | See GAME-4 |
| A11Y-3 | Meaning never rests on colour alone | Partial | Done for Ring Balancer, Traffic Day and Bit Budget. The other games need an audit |
| A11Y-4 | Animation respects `prefers-reduced-motion` | Partial | Handled in `quest.css` and the simulation games. Audit the rest |

### 8.6 Compatibility

- **Browsers:** the current and previous major versions of Chrome, Edge, Firefox and Safari on desktop, Safari on iOS, and Chrome on Android.
- **Widths:** 360 px and up. Every activity works at phone width (confirmed in PRODUCT.md), including the code editor.

### 8.7 Analytics (ANL)

| ID | Requirement | Status | Notes |
|---|---|---|---|
| ANL-1 | Privacy-friendly, cookieless page analytics | Planned | |
| ANL-2 | Product events: signup, activation, quiz completed, game completed (type, score, perfect), review answered, level up, badge earned | Planned | Most can be derived from the existing attempt tables for ADM-6 |

## 9. Architecture

**Stack**

- Django 5.2 (Python 3.13 locally) with server-rendered templates in one app, `learn`.
- Front end: hand-written CSS (`learn/static/learn/quest.css`, tokens in [DESIGN.md](../../DESIGN.md)) and vanilla JavaScript per page. CodeMirror 5, marked 4 and SortableJS load from cdnjs and the Archivo font from Google Fonts. There's no build step.
- Game logic runs on the server: `learn/services.py`, `learn/traffic.py` (mirrored in `learn/static/learn/traffic_model.js`), `learn/quorum.py`, `learn/ring.py` and `learn/bitbudget.py`.
- Gunicorn, with WhiteNoise serving compressed, hashed static files.
- Postgres (Neon) in production through `DATABASE_URL`, SQLite locally.
- The Gemini REST API for admin challenge generation (`learn/llm.py`).
- Code execution in a subprocess (`learn/code_runner.py`).

**Environments**

| Environment | Hosting | Purpose | State |
|---|---|---|---|
| Local | `runserver` and SQLite | Development | Working |
| Production | Render free tier and Neon free tier | Private deployment | Running. Content lags the repo |
| AWS | k3s, Jenkins and Airflow on one EC2 instance ([AWS_K8S_DEPLOYMENT.md](../../AWS_K8S_DEPLOYMENT.md)) | The owner's Kubernetes learning environment | Guide only, not a launch target |
| Local Kubernetes | k3d and a Cloudflare Tunnel ([LOCAL_K3D_DEPLOYMENT.md](../../LOCAL_K3D_DEPLOYMENT.md)) | Free learning environment | Guide only |

Where production runs at launch is D-2.

## 10. Release plan

| Phase | Audience | Entry gate | Exit criteria |
|---|---|---|---|
| 0. Private (now) | The owner and portfolio viewers | | Every P0 item in the checklist done |
| 1. Closed beta | 20–50 invited learners | All P0 items done. D-2 and D-3 decided | At least 2 weeks with no P0-severity incident, activation and D7 baselines measured, and blocking feedback fixed |
| 2. Public launch | Anyone | All P1 items done. D-1, D-4, D-5, D-6 and D-7 decided | |
| 3. Growth | | | Works through the P2 backlog, guided by beta and launch data |

## 11. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| A code submission escapes the sandbox | The database and secrets are exposed | GAME-6 before any public coding, or hide Coding (D-3) |
| Reseeding production deletes attempts on removed concepts | Learners lose progress | ADM-3 dry run, a backup before every reseed, and frozen concept slugs after launch |
| Free-tier cold starts | Visitors bounce on the first page, and beta metrics are skewed | OPS-1 |
| A single maintainer | Slow incident response and stale content | Alerts (OPS-4, OPS-5), a runbook (OPS-8), and the content-scout agent for curriculum upkeep |
| XP farming through replays | Level gating and any leaderboard stop meaning anything | D-5 |
| Source links rot | "Cite the source" quietly breaks | A scheduled link check against the review dates in `sources.json` |

## 12. Open decisions

| ID | Decision | Options | Blocks |
|---|---|---|---|
| D-1 | Business model | Free (portfolio and community); freemium (early stages free, later stages and case studies paid); a one-time purchase; a subscription | BIZ, PUB-7, terms |
| D-2 | Production hosting at launch | **Recommended:** an always-on managed platform with managed Postgres and point-in-time restore, keeping the k3s setups for learning and staging. One EC2 instance running k3s, Jenkins and Airflow is a single point of failure you'd operate alone | OPS-1, OPS-2, OPS-3 |
| D-3 | Coding at launch | (a) Hide Coding from learners until isolation is done and challenges exist; it's the only activity with no content yet. (b) An isolated server-side runner: a hosted judge, or a separate sandbox host using gVisor or Firecracker. (c) Run code in the browser with Pyodide for instant feedback, and grade hidden tests on an isolated runner | The public-launch condition in PRODUCT.md |
| D-4 | Domain and brand assets | Check "SysDesign Quest" for trademarks and domain availability; commission or make a logo, favicon and share image | PUB-5, the email sending domain |
| D-5 | XP policy | Full XP on every replay (today); XP only for beating your best score; diminishing XP per replay. Also whether a wrong quiz answer keeps paying 2 XP | GAME-5, QZ-4, PRG-7 |
| D-6 | Accessibility standard | WCAG 2.2 AA proposed | A11Y |
| D-7 | What's public without an account | The catalogue only; the catalogue plus the Beginner stage's notes; all notes readable, with games needing an account | PUB-2, PUB-3, search visibility |
| D-8 | Email provider and reminder cadence | | ACC-2, NTF |
| D-9 | Analytics tool | Plausible, self-hosted Umami, or PostHog in cookieless mode | ANL |
| D-10 | Where Ring Balancer lives: sd-08 or sd-31 | Recorded under "Needs your decision" in [content-ledger.md](../learning/content-ledger.md) | |
| D-13 | Where Bit Budget lives: sd-28, or a new unique-ID lesson (ideas queue item 4) | Recorded under "Needs your decision" in [content-ledger.md](../learning/content-ledger.md) | |
| D-11 | Voice: keep the emoji-labelled actions? | PRODUCT.md says the current voice isn't binding | Marketing copy |
| D-12 | Content licence | All rights reserved, or a Creative Commons licence for the curriculum text | Terms, the public catalogue |

## Appendix A: Data model

| Group | Models |
|---|---|
| Content | `Book`, `Topic`, `Chapter`, `Concept`, `Question`, `Choice` |
| Games | `ComponentType`, `DesignChallenge` (with components and connections), `MatchingChallenge` (pairs), `OrderingChallenge` (steps), `CodingChallenge` (test cases), `FlawChallenge` (parts and reasons), `TrafficChallenge`, `QuorumChallenge`, `RingChallenge`, `BitBudgetChallenge` |
| Learner state | `UserProfile` (XP, streaks, unlock-all flag), `Attempt` (quiz answers), `ReviewCard`, `ConceptMastery`, `Badge`, `UserBadge`, and one attempt model per game type |

Migrations run from `0001` to `0012` (`learn/migrations`).
