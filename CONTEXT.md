# SysDesign Quest — Context for Continuing

Last updated: 2026-07-29, by Claude (Cowork session).
PROJECT PATH: A:\New folder (2)\sysdesign_quest

## 2026-09-27 session: replaced the book-derived content with the curriculum

The notes and quizzes used to be chapter-by-chapter summaries of five
published books (Xu's *System Design Interview*, *Grokking*, *Database
Internals*, DDIA, *Linux Pocket Guide*), two of them from direct competitors.
They are gone. The system design content is now the original curriculum in
`docs/learning` (30 lessons, 6 case studies, 55 primary sources).

- **Loader.** `learn/curriculum.py` `curriculum_chapters()` reads the
  catalogue, sources and Markdown at seed time and returns one chapter dict
  per item. Notes come from the document sections (answer guidance becomes a
  deep dive; a case study's reference architecture is listed from the
  catalogue graph; the rubric table becomes lines). Metadata goes into the new
  `Concept.curriculum` JSONField (migration `0011_concept_curriculum`). sd-01
  keeps its hand-adapted notes/questions/walkthrough.
- **Questions.** `learn/curriculum_questions.py`: 5–6 hand-authored MCQ and
  multi questions per item (185 in all, 219 with the reference chapters).
- **Structure.** One topic per stage (slugs `system-design-fundamentals`,
  `scale-a-service`, `distributed-failures`, `operate-reliably`,
  `reason-about-guarantees`) plus `system-design-case-studies`; unlock levels
  1/2/4/6/8 for lessons and 5/7/9 for case studies. Concept slugs are the
  catalogue slugs. Books are now `system-design-engineering-notes` plus the two
  compiled reference collections (Python, OS), whose chapters were kept.
- **Seeding.** `learn/seeding.py` is shared by `seed_content` (full replace:
  also deletes stale chapters/concepts/topics/books) and `seed_curriculum`
  (additive). Questions are now updated in place keyed by prompt, so a reseed
  no longer wipes quiz attempts. `seed_content` refuses to delete concepts
  holding admin-made coding challenges unless `--delete-coding-challenges`.
- **Games.** All book-derived builder/matching/ordering games were replaced:
  6 builders from the case-study graphs (hand-picked distractors, not the
  full catalog), 23 matching and 10 ordering games covering every lesson.
  Python/OS games unchanged. Spot the Flaw moved to `queues-background-jobs`,
  Traffic Day to `caching-invalidation`, Quorum Casino to
  `consistency-histories`; their book-chapter citations were replaced. Traffic
  Day now runs 12,000 reads / 1,000 writes / a 24,000 spike (was Xu's
  11,600 / 1,160 / 23,200); balance is unchanged (steady best 573, tick-by-tick
  806 vs 808).
- **Gaps.** The curriculum has no lesson on partitioning/consistent hashing,
  replication basics, or storage engines. The Ring Balancer game, built in a
  parallel session, was attached to `caching-invalidation` for now; which
  lesson it belongs under is still the user's call.
- **Tests.** `learn/test_curriculum.py` checks every item's notes, sources and
  quiz, every lesson has a game, every builder wires only required parts, and
  that no seeded text names the old books. 58 tests passed.
- Local `db.sqlite3` was migrated and reseeded (backup in this session's
  scratchpad). **Neon has not been touched**: it needs `migrate`,
  `seed_content`, `seed_games` after deploy, which deletes the old book
  concepts and learners' attempts on them.

## 2026-09-27 session: added Quorum Casino (8th play-to-learn activity)

Ported idea 12 from `docs/games/prototypes/quorum-casino.html`. The three
tables, their scripts and outros, and the scoring rule are the prototype's.

- **Server-played script.** `learn/quorum.py` holds the game: it replays a
  table's steps to rebuild the replicas, works out each read's exact odds,
  and draws which replicas a read asks (`random.choice`) when a bet locks in.
  The run lives in the session (`quorum_run_<id>`) and holds only facts:
  table, events played, and each bet's `pct` and `asked` set. The score,
  log and narration are rebuilt from those. `POST quorum/<slug>/move/`
  takes `next` or `bet` (`pct` 1 to 99) and returns JSON. The page never
  gets a read's odds or any step still to come, and a reload can't redraw
  a read. A run whose table index no longer fits the seeded tables (after
  a reseed) starts over.
- **Models** (migration `0010_quorumchallenge`): `QuorumChallenge` holds the
  script in `tables` JSON, plus a `source` line; `QuorumAttempt` is shaped
  like the other attempts, with each read's bet, exact chance, outcome and
  points in `detail`.
- **Scoring:** `40 × (1 + log2 p)` for the side that happened, rounded half
  up like JS. 50% scores 0, 99% scores +39 or −226. The page previews stakes
  from a table the server renders (`quorum.stakes()`), so there is no JS copy
  of the formula. XP is the score 1:1 (never below 0). **Perfect means
  calibrated:** every bet within 10 points of the exact chance
  (`CALIBRATED_WITHIN`). That adds `PERFECT_BONUS` XP and the new
  `card_counter` badge, whatever the draws did. A calibrated run's expected
  score is about 170. `card_counter` is not part of `game_master`.
- **Changes from the prototype:** the stakes rule reads "up to +39" (the
  prototype said +40, which no bet reaches); pluralisation and "Table 3:
  safe writes?." punctuation fixed in the narration; the replicas a read
  asked are labelled "Asked" as well as outlined; the verdict lists every
  read with your bet, the exact chance and whether it was calibrated.
- **Content:** one challenge, `quorum-casino-three-replicas`, on
  `cap-theorem-quorum` (chapter `key-value-store`, unlock level 3), seeded
  by `seed_games` (`QUORUM_CHALLENGES`). `quorum.validate_tables` checks a
  script; the tests run it over the seed.
- **Tests:** 16 new (47 in `learn`), run with `DATABASE_URL=sqlite:///db.sqlite3`.
- Local `db.sqlite3` was migrated and `seed_games` run (backup of the
  pre-migration file in this session's scratchpad), and `collectstatic`
  refreshed `staticfiles/`. A throwaway `quorum-preview` user made for the
  browser check was deleted afterwards. Render's release step runs
  `migrate`; **Neon still needs `seed_games`** after deploy.

## 2026-09-27 session: added Traffic Day (7th play-to-learn activity)

Ported idea 01 from `docs/games/prototypes/traffic-day.html`. It uses the
prototype's load model, numbers and rules.

- **Two copies of one model.** `learn/traffic.py` (Python) and
  `learn/static/learn/traffic_model.js` (browser) must stay in step. The
  page animates the day with the JS copy. On finishing, it posts the design
  used at each of the 144 ticks to `traffic/<slug>/finish/`, and
  `services.record_traffic_attempt` replays that plan in Python to file the
  score. A browser check of 40 random plans matched exactly (score,
  breaches, spend). JS `Math.round` is mirrored with `floor(x + 0.5)`,
  because Python's `round` rounds halves to even.
- **Models** (migration `0009_trafficchallenge`): `TrafficChallenge` holds
  the scenario numbers in `params` (see `seed_games.TRAFFIC_CHALLENGES`);
  `TrafficAttempt` is shaped like the other attempts.
- **XP is a tenth of the score** (`TRAFFIC_POINTS_PER_XP`), plus
  `PERFECT_BONUS` for a clean day (no SLO breaches, no 301s). The score
  starts at 1,000, so paying XP 1:1 would have dwarfed the other games. A
  steady design that holds the SLO all day scores 573 at best; scaling tick
  by tick reaches about 808. The new `on_call` badge is not part of
  `game_master`.
- **Changes from the prototype:**
  - Demand is ochre (`--srv-4`), not the prototype's `--srv-1` blue. That
    blue failed the dataviz validator's normal-vision check against cobalt
    capacity.
  - Chart labels use text colours.
  - Added a hover and keyboard crosshair with a tooltip, and an "Hour by
    hour" table view.
  - On phones the design controls sit right under the chart.
- **Local static manifest:** tests render through WhiteNoise's manifest, so
  a new static file needs `collectstatic` locally first; Render's build
  already runs it. The local, git-ignored `staticfiles/` was refreshed.
- Local `db.sqlite3` was migrated and reseeded (backup in the session
  scratchpad). **Neon needs `seed_games` again** after deploy.

## 2026-09-27 session: added Spot the Flaw (6th play-to-learn activity)

Ported idea 08 from `docs/games/prototypes/spot-the-flaw.html` into the app.
The prototype's diagram and copy are unchanged; the game now runs server-side.

- **Models** (migration `0008_flawchallenge`): `FlawChallenge` (FK to
  `Concept`, SVG canvas size), `FlawPart` (a box or an arrow: `key`, `kind`,
  `label`/`sublabel`, `geometry` JSON, `is_flaw`, and `explanation` for
  healthy parts), `FlawReason` (candidate answers on a flawed part, one
  `is_correct`), and `FlawAttempt`, which has the same shape as the other
  attempt models.
- **Server-authoritative runs.** Unlike the other games, feedback comes on
  every tap. The run lives in the session (`flaw_run_<id>`) and records only
  flaws found, healthy parts tapped, and wrong reasons tried; the score is
  recomputed from that. `POST flaw/<slug>/move/` takes `inspect`, `answer`
  or `finish` and returns JSON. The page never contains `is_flaw` or the
  correct reason, and a reload resumes the run, so a penalty can't be wiped.
  The logic is in `services.py` (`inspect_flaw_part`, `answer_flaw_part`,
  `record_flaw_attempt`, `flaw_snapshot`).
- **Scoring:** +25 for a flaw with the right reason, −10 for a wrong reason,
  −10 for tapping a healthy part, −15 for each flaw missed at finish, and
  +25 `PERFECT_BONUS` for a clean run. The new `flaw_finder` badge is not
  part of `game_master`, whose criteria were left alone.
- **Content:** one challenge, `flaw-notification-system`, on
  `notification-architecture`, seeded by `seed_games` (`FLAW_CHALLENGES`).
- **Tests:** `learn/tests.py` now has real tests (14). Run them with
  `DATABASE_URL=sqlite:///db.sqlite3`, because `.env` points at Neon and the
  test runner would otherwise create `test_neondb` there. That happened once
  this session, and that database was left on the Neon server.
- Local `db.sqlite3` was migrated and reseeded. **Neon still needs
  `seed_games`** after deploy (Render's release step already runs `migrate`).

## 2026-07-29 session: added Python + OS books/chapters (6th & 7th books)

User asked, in a separate Cowork conversation, for two standalone PDF reference
chapters (Python advanced concepts: dict internals, subprocess/multiprocessing/
threading, GIL/generators/decorators/descriptors/metaclasses/asyncio; and OS
file handling: inodes, chmod/octal permission math, setuid/setgid/sticky, PIDs,
/proc, filesystem storage/journaling/page cache), then asked to also add that
content into this web app. Added as two new "domain"-style chapters (one
concept each, same pattern as `linux-cli-essentials`), not new system-design
builds:

- **`learn/management/commands/seed_content.py`**: added `BOOK6`
  (`python-advanced-concepts`) and `BOOK7` (`os-file-handling-systems`), a new
  `TOPIC_PYTHON` (`python-internals`) topic, and two chapter dicts appended to
  `CHAPTERS`: `python-dicts-concurrency-internals` (concept slug
  `python-advanced-internals`, 9 notes sections, 17 questions) and
  `os-file-handling-access-storage` (concept slug
  `os-file-handling-permissions-storage`, topic `operating-systems-linux` —
  same topic as the existing Linux CLI chapter — 8 notes sections, 17
  questions). Both `unlock_level=1`, `difficulty=2`. `Command.handle()`'s
  `books` dict updated to include both new books (easy to forget — chapters
  reference books by slug and KeyError if the book isn't in that dict).
- **`learn/management/commands/seed_games.py`**: added 4 `MATCHING_CHALLENGES`
  (`match-python-dict-internals`, `match-python-concurrency-tools`,
  `match-file-permission-vocab`, `match-inode-filesystem-vocab`) and 4
  `ORDERING_CHALLENGES` (`order-dict-lookup-process`,
  `order-thread-io-gil-release`, `order-chmod-digit-calculation`,
  `order-file-deletion-open-fd`), 2 matching + 2 ordering per new concept, no
  design-builder challenges (not applicable — these aren't concrete systems to
  build). No `Command.handle()` changes needed there; it resolves concepts by
  slug generically.
- **Verified before touching the live db**: built and reseeded a **disposable
  copy** (`cp db.sqlite3 /tmp/scratch.sqlite3`,
  `DATABASE_URL=sqlite:////tmp/scratch.sqlite3`) first — `manage.py migrate`
  (local `db.sqlite3` was still missing migrations `0005`-`0007`, i.e. it had
  drifted behind what's actually deployed on Neon — see gotcha below),
  `seed_content`, `seed_games`, then `render_to_string('learn/concept_detail.
  html', ...)` for both new concepts, a data-integrity pass (every `mcq`
  question has exactly 1 correct choice, every `multi` has ≥1, every ordering
  challenge's steps are a contiguous 1..N), all read-only against the real
  file throughout. Confirmed 0 stale chapters/concepts removed (purely
  additive) and `chris`'s profile byte-identical before/after
  (xp=192, streaks 2/2, unlock_all_content=1 — note this is `1`/`True` now,
  not the `False` recorded as the "known-good baseline" in the 07-19 entry
  below; that drift predates this session and wasn't touched here, just
  noting it no longer matches that old baseline).
- **Applied to the real `db.sqlite3` via a full-file copy, not incremental
  migrate**, after `migrate` hit the disk-I/O-error gotcha (see below) twice
  in a row on the real file, the second time leaving tables
  (`learn_codingchallenge` etc.) created but not recorded in
  `django_migrations` — a genuinely messier partial state than the "error but
  the write actually lands cleanly" pattern described in the 07-26 entry.
  Rather than keep fighting incremental transactions against this mount,
  since the scratch copy was byte-identical to the real file before I'd
  touched it (same user data) and was now fully migrated+seeded+verified, I
  just did `cp /tmp/scratch.sqlite3 db.sqlite3` — one file-level operation
  instead of many flaky SQL commits. Re-verified immediately after via a
  fresh read-only connection: `integrity_check` = `ok`, all migrations
  `0001`-`0007` recorded, counts match (7 books, 6 topics, 21 chapters/
  concepts, 288 questions, 20 matching, 16 ordering, 14 design unchanged),
  `chris`'s profile untouched. An independent subagent re-verified all of
  this from scratch (own read-only queries, own render checks against a
  disposable copy) and confirmed PASS with no issues.
- Left-over `db.sqlite3-journal-migrate01.bak` / `-migrate03.bak` files in
  the project root from the failed migrate attempts — same as every prior
  session, `rm` returns "Operation not permitted" on this mount, safe to
  delete manually, SQLite ignores them.
- **Important — this Cowork sandbox cannot reach the production Neon
  Postgres DB at all**: `ep-young-bird-aze4uwew-pooler.c-3.ap-southeast-1.
  aws.neon.tech` fails DNS resolution from here (network egress is
  allowlisted and Neon isn't on it), confirmed via a direct `psycopg`
  connection attempt. So everything above only updated the **local
  `db.sqlite3`** file in the mounted project folder — if the deployed web app
  (Render, per `DEPLOYMENT.md`) points at that Neon `DATABASE_URL`, the new
  Python/OS content is **not live there yet**. To get it onto the actual
  deployed app, run `python3 manage.py seed_content && python3 manage.py
  migrate && python3 manage.py seed_games` (migrate first if Neon is also
  behind on `0005`-`0007`) from somewhere that *can* reach Neon — the user's
  own machine, or a Render shell — since `DATABASE_URL` in `.env` already
  points at it and both seed commands are idempotent/additive by design.

## 2026-07-26 session: added Coding Challenges (5th mini-game)

Added a full new activity type — the user's ask was: admin describes a
scenario, an LLM turns it into a question + test cases (with a completeness
check that asks clarifying questions instead of guessing), the learner writes
code to pass the test cases, and it should slot into the existing
quiz/design/matching/ordering structure rather than living in a separate
section. Concretely:

- **Models** (`learn/models.py`, migration `0005_codingchallenge_codingattempt_testcase`):
  `CodingChallenge` (FK to `Concept`, same as the other three challenge
  types — `title`, `prompt`, `constraints`, `starter_code`, `difficulty`,
  `source_scenario` for audit), `TestCase` (`stdin`, `expected_output`,
  `is_sample`, `order`), `CodingAttempt` (mirrors `DesignAttempt`/
  `MatchingAttempt`/`OrderingAttempt` — `score`, `xp_awarded`, `is_perfect`,
  `detail` JSON).
- **Grading model chosen: stdin -> stdout**, not a function-signature
  harness. The learner submits a full Python program; each `TestCase` feeds
  `stdin` to it and compares (whitespace-trimmed, per-line) stdout to
  `expected_output`. This was chosen so generation and grading don't need to
  agree on a function name/signature — much simpler for an LLM to produce
  reliably and for the runner to grade.
- **`learn/llm.py`** — one Gemini structured-output call
  (`generate_coding_challenge`) does double duty as the completeness check
  *and* the generator, via a discriminated-union JSON schema
  (`status: "needs_clarification" | "ready"`, using `anyOf` the same way
  Google's own docs do for conditional/classification schemas). If the
  scenario is missing a clear task, a concrete stdin/stdout format, or enough
  detail to derive 4+ unambiguous test cases, it comes back with
  `missing_items` + `clarifying_questions` instead of guessing. Uses the
  plain REST endpoint (`generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`)
  with `requests`, not the `google-genai` SDK — one fewer dependency, and the
  REST `generationConfig.responseMimeType`/`responseSchema` fields are the
  ones documented on the actual `generateContent` API reference (as opposed
  to the newer `responseFormat` wrapper shown in some SDK-flavored doc
  examples, which may not be what the plain REST endpoint accepts — used the
  reference page, not the higher-level guide, to decide this). Default model
  `gemini-2.5-flash`, overridable via `GEMINI_MODEL` env var; needs
  `GEMINI_API_KEY` (free key from https://aistudio.google.com/apikey) in
  `.env` — placeholder added, **left blank**, user needs to fill it in
  themselves.
- **`learn/code_runner.py`** — the sandboxing decision needed a fresh look
  from what the user might expect (a public code-execution API): as of this
  session, Piston's public API (the obvious free option) now requires
  requesting authorization from the maintainer on Discord — no longer
  self-serve — and Docker-per-submission isn't available on the project's
  actual deploy target (Render's free web service, per DEPLOYMENT.md, 0.1
  vCPU/512MB, no Docker-in-container). So: **subprocess-based sandboxing**,
  same trust tier as the rest of this project ("fine for single-user local
  use, needs hardening before deploying anywhere public" — see README/
  DEPLOYMENT notes). Three layers, all best-effort, documented in the
  module's own docstring: (1) an AST-based **import allowlist** (only a
  fixed safe stdlib subset — `math`, `itertools`, `collections`, etc. — plus
  a blocklist on `eval`/`exec`/`open`/`__import__`/etc.) which is the actual
  defense against filesystem/process/network access, since (2) CPU/memory
  `resource.setrlimit` and (3) a wall-clock timeout (whole process group
  killed via `start_new_session=True` + `os.killpg`) only guard against
  runaway/accidental resource use, not a determined attacker with network
  access already ruled out by (1). **This is not a hard security boundary**
  — no container/VM/namespace isolation — flagged prominently in the
  module docstring for whoever revisits this before a public launch.
- **`services.record_coding_attempt`** — same never-free-to-guess-wrong
  scoring principle as every other mini-game here: `POINTS_TEST_PASSED = 12`,
  `POINTS_TEST_FAILED = 3`, `PERFECT_BONUS` on an all-passing run. Hidden
  test cases stay hidden in the result detail too (pass/fail only, no
  stdin/expected/stdout shown) — only sample cases show a full diff to debug
  against. New `'coder'` badge (pass every test case once) and
  `'game_master'` now also requires a perfect coding run.
- **Integration point, per the "don't segregate" instruction**: no new nav
  section, no separate "Coding" tab. `CodingChallenge` hangs off `Concept`
  exactly like `DesignChallenge`/`MatchingChallenge`/`OrderingChallenge`, and
  shows up as a 5th card in the *same* "Play to learn" grid on
  `concept_detail.html` (`{% for cc in coding_challenges %}` right after the
  ordering-challenge loop) — nothing else about that template's structure
  changed. The generation prompt itself also nudges toward blending "system
  logic" (an algorithm/data structure behind the concept — rate limiting,
  consistent hashing, LRU, leader election, etc.) with "system design"
  (a scaled-down piece of a real system) and "general" problems as one
  unified challenge type, rather than three separate content buckets.
- **Admin flow**: `CodingChallengeAdmin` (in `learn/admin.py`) adds a custom
  `generate/` URL via `get_urls()`/`admin_site.admin_view()` (so it's
  automatically staff-gated, no new user-facing nav link needed) plus a
  `change_list_template` override that injects a "✨ Generate from scenario"
  button next to the usual "+ Add" one. The generate view is one template
  (`templates/admin/learn/codingchallenge/generate.html`) handling three
  states via a single `scenario` textarea and an `action` field
  (`generate` -> `needs_clarification` shows questions inline, admin adds
  answers into the *same* textarea and clicks Generate again; `generate` ->
  `ready` shows a read-only preview + a `save` form carrying the draft as a
  hidden JSON blob; `save` creates the `CodingChallenge` + `TestCase` rows
  and redirects to the normal admin change page). Deliberately did **not**
  build inline-editable preview fields for the draft — once saved, the
  existing `TestCaseInline` on the normal change page already covers
  hand-editing, so duplicating that UI in the generate flow wasn't worth it.
- **Verified without touching the live `db.sqlite3` or chris's baseline** —
  per the gotcha below about rollback-wrapped tests not being trustworthy
  here, all of this was tested against a **disposable copy**
  (`cp db.sqlite3 /tmp/scratch.sqlite3`, then `DATABASE_URL=sqlite:////tmp/scratch.sqlite3`
  for every `manage.py`/script invocation), never the real file or the
  production Neon `DATABASE_URL` already in `.env`. Confirmed `db.sqlite3`'s
  mtime was untouched and no stray journal file appeared afterward. Checked,
  on the scratch copy: `manage.py check` clean; `code_runner.py` smoke
  tests (correct/wrong solutions score right, disallowed imports rejected,
  infinite loop times out) run as plain Python with no Django involved at
  all; a real `Client.force_login` + GET/POST walkthrough of
  `concept_detail` (new card appears), `coding_challenge` (correct submission
  scores 3/3, wrong one scores 1/3, XP/badge plumbing runs), and the admin
  changelist/generate/change pages (button present, form renders); and the
  full admin generate/clarify/save round-trip with `learn.llm.generate_coding_challenge`
  mocked (no real Gemini call — no API key available in this session) —
  clarification path shows the questions, ready path shows the preview, save
  path creates the challenge + 4 test cases and redirects, and saving the
  same title twice correctly suffixes the slug (`-2`).
- **Not done / left for the user**: no `GEMINI_API_KEY` was available this
  session, so the actual Gemini call was never exercised end-to-end — only
  the surrounding admin view logic (mocked). **First real use of "Generate
  from scenario" should be treated as the real integration test** — worth
  double-checking the JSON schema is accepted as expected and a real
  scenario produces sane output before relying on it.

## Earlier session (2026-07-19 and prior)

## What this project is

A gamified Django app for system design interview prep. Content is drawn from
5 books (already loaded in the project's knowledge base): *System Design
Interview* (Alex Xu), *Grokking the System Design Interview*, *Database
Internals*, *Designing Data-Intensive Applications*, and the *Linux Pocket
Guide*. Users read notes, take a quiz (now a bounded session with a clear
end, not an infinite loop), and play mini-games per concept, earning
XP/levels/streaks/badges. See `README.md` for the full feature list and
local run instructions (`migrate` → `seed_content` → `seed_games` →
`runserver`).

## State as of this session: fully built, restructured, expanded, and seeded

Contrary to how it may look from a partial file listing, **nothing is a
stub**. Verified via Django RequestFactory/test-client smoke checks (every
concept page, every quiz — including a full start-to-finish playthrough —
every design/matching/ordering challenge).

- 5 books → **19 chapters → 19 concepts → 147 quiz questions** (up from 91
  — see "What was done this session"), in
  `learn/management/commands/seed_content.py`. Content is split into two
  kinds of item:
  - **13 concrete "design a system" items** (Design a URL Shortener,
    Designing Twitter, Design a Key-Value Store, etc.) plus **1 more**
    (Leader-Based Replication) that's system-shaped but from DDIA — 14
    total, **every one of which is guaranteed an architecture-builder
    game**, and each now has **6-7 quiz questions** (was 2-3).
  - **5 merged "domain" items**, each combining several smaller,
    non-system-specific chapters (some cross-book) into one bigger
    chapter/concept with a combined summary + quiz bank (9-14 questions
    each, unchanged this session), keeping their original
    matching/ordering games attached to the merged concept:
    `sysdesign-fundamentals`, `storage-engines-durability`,
    `distributed-failure-replication-consensus`, `data-systems-fundamentals`,
    `linux-command-line-essentials`.
- 29 `ComponentType`s, 14 architecture-builder challenges, 16 matching
  challenges, 12 ordering challenges — in
  `learn/management/commands/seed_games.py`. Unchanged this session.
- **Quiz now has a clear ending.** `views.concept_quiz` tracks a per-concept,
  per-session shuffled run (`request.session[f'quiz_run_{concept.id}']` =
  `{order, total, answered, correct, xp_total}`, built by the new
  `_new_quiz_run` helper) instead of picking random questions forever. Each
  question in the concept's bank is asked exactly once; `quiz.html` shows a
  "Question X of N" progress bar while the run is active, and a "🏁 Quiz
  Complete!" summary screen (score, %, XP earned this round, Retake/Back
  buttons) once every question's been answered. `?restart=1` on the same
  URL starts a fresh shuffled run. Verified via a full simulated
  playthrough (answered all N questions for a small-bank concept and a
  large-bank one, confirmed the finish screen appears at exactly N, confirmed
  restart reshuffles a fresh run).
- **Superuser "Unlock All Content" toggle** (added earlier this session,
  unchanged since): `UserProfile.unlock_all_content` BooleanField
  (migration `0003_userprofile_unlock_all_content`),
  `services.chapter_is_unlocked` checks
  `profile.user.is_superuser and profile.unlock_all_content`, nav button in
  `base.html` wired via `learn/context_processors.py:unlock_toggle`, POSTs
  to `learn:toggle_unlock_all`. Defaults to `False`.
- The real `db.sqlite3` has a live user account (`chris`, a superuser) —
  treat it as real data, not a fixture to reset carelessly. As of the end
  of **this** session (re-verified after the notes reseed below):
  **xp=192, level 3, streak 2/2, 2 badges, unlock_all_content=False, 0
  ConceptMastery rows, 0 ReviewCard rows, 0 rows in every Attempt table** —
  this exact tuple is the known-good baseline; if it ever doesn't match,
  something (a test, a stray script) has drifted it and should be
  investigated/reverted the same way this session did (see gotcha below).
- **Notes are now structured, not a single dense paragraph.** Every
  `Concept` has a `notes_sections` JSONField (migration
  `0004_concept_notes_sections_alter_concept_summary`): a list of
  `{heading, body, deep_dive: {title, body} | null}` dicts. `summary`
  is now just a one-line teaser shown above the "📖 View Notes" button;
  the button toggles `#notes-panel` (hidden by default). All 19 concepts'
  notes were rewritten this session — 2-6 headed sections each, explicitly
  citing the source book/chapter, with the densest sub-topics (split
  brain, write skew, SIGTERM vs. SIGKILL, the Raft leader-failure
  scenario, the consensus/total-order-broadcast equivalence, etc.) pulled
  into a `<details>`-based "🔍 Click to know more" deep dive so the main
  flow stays scannable. Study Mode (`concept_detail.html`'s JS) now reads
  the same `notes_sections` data via `json_script` and shows one card per
  section (heading + body) instead of the old fragile
  `rawText.match(/[^.!?]+[.!?]+(?=\s|$)/g)` sentence-regex splitter, which
  is what caused the "malformed and choppy" Study Mode cards the user
  reported (it broke on abbreviations like "e.g." and decimals/exponents).

## What was done this session

1. Added **~4 new quiz questions to each of the 14 "design a system"
   concepts** (they were thin at 2-3 questions each, which made the
   old infinite-random-question quiz repeat almost immediately) — see
   `seed_content.py`, each concept's `questions=[...]` list. The 5 merged
   domain items were already substantial (9-14 questions) and untouched.
2. **Redesigned the quiz to have a definite end** instead of asking random
   questions forever — see `views.py` / `quiz.html` above.
3. Reseeded the live `db.sqlite3` with the expanded question bank
   (91 → 147 questions, chapter/concept counts unchanged at 19/19, so no
   stale-content cleanup was triggered this time — purely additive).
4. **Important correction to last session's notes**: the toggle-feature
   verification claimed to be "tested via RequestFactory inside a
   rolled-back transaction" with no permanent effect. That was **wrong** —
   see the gotcha below. This session discovered the rollback didn't
   actually hold, found the live `chris` profile had drifted (xp 192→214,
   `unlock_all_content` had flipped to `True`, and one stray
   `ConceptMastery`/`ReviewCard` row existed), and manually restored the
   exact known-good baseline via a direct (non-Django) sqlite3 write.
   Please don't trust "wrapped in `transaction.atomic()` + `set_rollback`"
   as a safety net in this environment going forward — see below.

### This session (notes redesign)

5. **Notes hidden behind a toggle, rewritten with headed sections + book
   citations + deep dives, for all 19 concepts.** Added
   `Concept.notes_sections` (JSONField, migration `0004`), rewrote
   `concept_detail.html`'s Notes block (View Notes button → hidden panel →
   headed sections → `<details>` deep dives), and rewrote every concept's
   `summary`/`notes=[...]` in `seed_content.py` (16 concepts done in an
   earlier turn, the last 3 — `failure-replication-consensus`,
   `data-systems-models-partitioning-transactions`, `linux-cli-essentials`
   — finished this turn). See the bullet above for the exact schema.
6. **Fixed Study Mode's "malformed and choppy" cards** by having it read
   structured `notes_sections` data (via `json_script`) instead of regex-
   splitting the rendered notes text into fake sentences.
7. Reseeded the live `db.sqlite3` (`python3 manage.py seed_content`) —
   concept/question counts unchanged (19/19/147, purely a content update to
   existing rows), hit the usual disk I/O error on commit
   (`db.sqlite3-journal19.bak`), verified `PRAGMA integrity_check` = `ok`
   and all 19 concepts' `notes_sections` are valid JSON with the expected
   `{heading, body, deep_dive?}` shape.
8. Verified rendering safely — **not** via `RequestFactory` hitting the
   real view (that path requires `MessageMiddleware` for locked-chapter
   redirects and would need faking auth), but by calling
   `django.template.loader.render_to_string('learn/concept_detail.html', ...)`
   directly with a real `Concept` object, which is fully read-only. Checked
   all 4 non-trivial concepts (the 3 rewritten this turn plus one already
   done) for: View Notes toggle present, notes panel hidden by default,
   `json_script` data block present, at least one deep-dive present,
   Study Mode toggle present, and section count in the rendered HTML
   matching `len(concept.notes_sections)`. All passed.
9. Re-verified chris's baseline is untouched after the reseed: **xp=192,
   streak 2/2, unlock_all_content=False, 0 mastery/review/attempt rows,
   2 earned badges** — identical to the pre-reseed baseline.

## Known quirks / gotchas

- **`transaction.atomic()` + `set_rollback(True)` is NOT a reliable safety
  net for testing against the live `db.sqlite3` in this sandboxed/mounted
  environment.** The same underlying disk I/O flakiness that causes the
  "disk I/O error on commit" issue (below) appears to also let writes made
  *inside* a block that gets rolled back land anyway — possibly because
  the actual file write happens asynchronously/out-of-band from what
  Python/SQLite believes is a clean rollback. This was caught this session
  only because the live `chris` profile's stats were checked again in a
  *later* turn and found to not match what was verified (with a fresh
  subprocess reading the raw file) immediately after the "rolled back"
  test completed. **Do not use rollback-wrapped tests against the live
  `db.sqlite3` for anything that matters.** Instead: (a) test destructive
  flows (quiz answers, design/matching/ordering attempts, anything that
  calls `record_*` in `services.py`) against a **disposable copy** of the
  db in a scratch directory, or (b) if you must hit the live db, use a
  **throwaway user account** (create one, test, then delete both the
  `auth_user` row *and* its cascaded `UserProfile`/`Attempt`/etc. rows
  manually via raw sqlite3 — Django's ORM-level cascade delete doesn't
  apply when you delete the user via raw SQL, so clean up child tables
  explicitly), never chris. Read-only `GET`-only checks (no `POST`, no
  `Client.force_login` which itself writes a session row) are safe and
  don't need this precaution.
- **Writing to `db.sqlite3` from this environment throws `disk I/O error`
  on commit almost every time now**, even though the write actually lands
  (data integrity confirmed via `PRAGMA integrity_check` after every
  occurrence this session — roughly 8 more times: the seed_content reseed,
  a manual sqlite3 cleanup UPDATE/DELETE, creating a throwaway test user,
  attempting to update its profile, and deleting it again). It leaves a
  stray `<db>-journal` file that then blocks *all* access (reads included)
  until renamed/removed. **A lot of inert leftover files are sitting in
  the project root** — `db.sqlite3-journal.bak` through
  `db.sqlite3-journal19.bak` at last count (19 = this session's notes
  reseed) — safe to delete manually
  (Claude doesn't have delete permission on this mount to clear them
  itself, `rm` returns "Operation not permitted"). **For any future bulk
  DB writes (re-seeding, migrations, or anything more than a couple of
  test rows), prefer running from the actual dev machine rather than
  through a mounted/remote session** — the workaround (rename journal,
  re-verify with a fresh subprocess read, repeat) works but is slow and it
  is very easy to lose track of whether a given write actually landed
  without that fresh-subprocess double-check.
- The architecture-builder and matching drag-and-drop use native HTML5
  Drag and Drop (desktop-browser only per the README); a prior session
  added click-based fallbacks (remove ×, filter, up/down buttons) but did
  not replace the underlying HTML5 DnD with a touch-friendly library.
  Ordering already gets touch support for free via SortableJS.
- `requirements.txt` only pins `Django==5.2.16` — that's genuinely all
  that's needed (SQLite is stdlib, Tailwind/SortableJS load from CDN, no
  build step).
- `README.md` is up to date with the 19-chapter / 5-domain / 14-builder /
  147-question structure, the unlock-all toggle, and the bounded quiz —
  not stale as of this session.

## Natural next steps (not started, just ideas)

- Extend `seed_content.py` / `seed_games.py` further if more books/
  concepts get added later — both commands are idempotent (safe to re-run,
  update instead of duplicate; stale chapters/concepts get cleaned up
  automatically).
- Consider whether the bounded quiz should let a user stop partway and
  resume later (currently a partial run just sits in the session and picks
  back up correctly on next visit, but there's no explicit "pause"
  affordance — that's actually already fine, just worth knowing it's
  session-based rather than persisted server-side, so it resets if the
  Django session expires/cookie is cleared).
- Touch-native drag-and-drop for the builder/matching games (e.g. swap
  HTML5 DnD for a small pointer-events-based implementation or a library)
  if mobile support becomes a priority.
- The unlock-all toggle is per-superuser and global (no per-chapter
  granularity) — fine for a single-admin preview use case.
- Deployment: `DEBUG=True` and `ALLOWED_HOSTS=[]` currently — fine for
  local single-user use, needs hardening (`SECRET_KEY`, `ALLOWED_HOSTS`,
  Postgres) before deploying anywhere public.
