# SysDesign Quest

A gamified learning app for system design interview prep, built on an
original curriculum ([docs/learning](docs/learning/README.md)): 31 lessons
and 6 case studies that cite standards, papers and official documentation
rather than summarizing any textbook.

## What's inside

- 37 curriculum items -> 37 concept pages -> 191 quiz questions, plus two
  compiled reference chapters (Python internals, OS file handling). The
  lessons run in five stages, one dashboard topic each: Beginner
  (understand a request), Intermediate (scale a service), Advanced (handle
  distributed failures), Production (operate reliably) and Expert (reason
  about guarantees). Each lesson page shows its ID, study time, objectives,
  prerequisite links and sources, and has at least one game. The six case
  studies (ticket booking, payments, job scheduling, search, feature flags,
  multi-region SaaS) each have an Architecture Builder built from their
  reference architecture.
- **Quizzes have a clear ending** — each concept's quiz walks through
  every question in its bank exactly once, in shuffled order, with a
  "Question X of N" progress bar. Finish them all and you get a "Quiz
  Complete!" summary (score, % correct, XP earned) with buttons to retake
  (fresh shuffle) or head back to the concept.
- XP, levels, and daily streaks
- Chapters unlock as you level up (later chapters require a higher level)
- Spaced repetition (SM-2 algorithm): a Daily Review queue resurfaces
  concepts right before you'd forget them
- Badges for milestones (streaks, mastering a chapter/book, leveling up,
  completing reviews, and perfect runs in each mini-game)
- A progress map on the dashboard showing mastery per chapter
- **Three mini-games per concept, in addition to quizzes:**
  - **Architecture Builder** — drag components from a pool onto a canvas,
    click two placed components to wire them together, and submit a
    system design (e.g. "Build the Ticket-booking Flow"). Correct required parts
    and correct wires score points; parts that don't belong and wrong or
    missing wires cost points. A flawless design earns a bonus and the
    "Architect" badge.
  - **Matching** — drag definitions onto the terms they define (e.g.
    consistency models, retry controls). Right matches score, wrong matches
    cost you.
  - **Ordering** — drag steps into the correct sequence (e.g. two-phase
    commit, renaming a column with expand-migrate-contract).
    Steps in the right slot score, misplaced ones cost you.

All three mini-games use the same negative-scoring principle you asked
for: guessing wrong is never free, so there's a real incentive to reason
through the answer rather than spam every option. Every case study is
guaranteed an Architecture Builder challenge, whose distractors are the
wrong turns its builder brief warns about (a cache-only seat lock, a
DNS-only failover switch); lessons get Matching/Ordering games.
- **Superuser preview toggle** — a "🔒 Unlock All Content" button appears
  in the top nav for superusers only. Clicking it flips a per-superuser
  flag that bypasses all chapter level-gating, so you can browse and test
  every chapter/concept/game regardless of your actual level. Click again
  to restore normal locking.
- **Coding Challenges** — a fifth "play to learn" activity alongside quizzes and
  the three mini-games: the learner writes a Python 3 program in an in-browser
  editor (CodeMirror, syntax highlighting, no build step) that reads from
  stdin and prints to stdout, and submits it to be graded against a set of
  test cases (sample cases shown up front, the rest hidden). Same
  never-free-to-guess-wrong scoring principle as the other games: passing
  tests score XP, failing ones cost a little, and a fully-passing run earns
  the perfect bonus and the "Coder" badge. Submissions run in a
  best-effort sandboxed subprocess (timeout, memory/CPU limits, and an
  import allowlist that blocks `os`/`socket`/`subprocess`/etc.) — see the
  security note at the top of `learn/code_runner.py` before considering this
  hardened enough for a public multi-tenant deployment.
  - **Admins generate challenges from a scenario, not by hand-writing test
    cases.** From Django admin -> Coding challenges -> "✨ Generate from
    scenario", describe the exercise in plain language (which concept it's
    for, what the program should do, roughly what input/output looks like).
    Gemini (`learn/llm.py`) either returns a full challenge — title, prompt,
    starter code, difficulty, and 4+ stdin/expected-output test cases — or,
    if the scenario doesn't have enough in it to write unambiguous test
    cases, comes back with specific clarifying questions instead of
    guessing. Requires a free `GEMINI_API_KEY` (see below).
- **Spot the Flaw** — an architecture diagram with a few design mistakes
  planted in it (e.g. a notification system with one shared queue and a
  synchronous SMS call). Tap a box or arrow you think is wrong, then pick
  why: the right reason scores, a wrong reason or a tap on a healthy part
  costs points, and every flaw still hidden when you finish the review
  costs more. A clean run earns the perfect bonus and the "Flaw Finder"
  badge. Each tap is checked on the server, which keeps the run in the
  session, so the page never holds the answers and a reload can't wipe a
  penalty.
- **Traffic Day** — run a URL shortener through one simulated day of
  traffic (an evening peak and a viral link at 19:00) and change its design
  at any time: app servers, a cache, read replicas, and 301 vs 302
  redirects. The score starts at 1,000 and loses 50 for every 10 minutes
  over the SLO, 1 for every dollar spent, and 250 if 301s break click
  analytics. The page animates the day, and the server replays the design
  the learner ran at each tick through the same load model
  (`learn/traffic.py`, with a JavaScript twin in
  `learn/static/learn/traffic_model.js`) to file the score. It pays 1 XP
  per 10 points, plus the perfect bonus and the "On Call" badge for a clean
  day.
- **Quorum Casino** — three replicas hold the key x across three tables
  with different N, W and R settings. The learner steps through writes,
  crashes, partitions and anti-entropy syncs, and before each read bets
  how likely it is to return the last successful write. Bets use a log
  scoring rule: 50% always scores 0, a sure bet that comes good scores +39,
  and one that doesn't scores −226. The server plays the script
  (`learn/quorum.py`) and draws which replicas each read asks, keeping the
  run in the session, so the page never holds a read's odds and a reload
  can't redraw one. The score is paid as XP, and a run with every bet
  within 10 points of the exact chance adds the perfect bonus and the
  "Card Counter" badge.
- **Ring Balancer** — 2,000 cache keys sit on a consistent-hash ring. The
  learner adds virtual nodes until the load evens out (+100 per balanced
  ring, −1 per 5 ring positions for routing-table memory, −20 for locking
  in an unbalanced ring), predicts how many keys move when a server crashes,
  on the ring and then under hash(key) % N (+50 / −25), and gives a
  double-capacity server its share by weighting virtual nodes. The hash lives
  only in `learn/ring.py`: the page gets every key and virtual-node position
  as data, redraws the ring as the slider moves, and the server recounts
  owners to score each lock-in. It pays 1 XP per 2 points, plus the perfect
  bonus and the "Ring Master" badge for a clean run.
- **Notes, redesigned** — each concept page shows a short one-line teaser
  plus a "📖 View Notes" button; notes are hidden until you click it (no
  wall of text up front). Once open, notes are structured as headed
  sections taken from the lesson (Intuition, How it works, Worked example,
  Trade-offs and failure modes, Practice), with the practice task's answer
  guidance behind an expandable "🔍 Click to know more" deep-dive so you
  try it first. The lesson's sources are listed beside the notes. A "🧠 Study mode" toggle turns the same sections into a
  one-card-at-a-time flashcard walkthrough (heading + body, Back/Next,
  progress bar) and a "🔊 Read aloud" button reads the notes via the
  browser's speech synthesis.

## Running it locally

Requires Python 3.10+.

```bash
cd sysdesign_quest
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_content   # loads the curriculum lessons + quiz questions
python manage.py seed_games     # loads the architecture/matching/ordering/spot-the-flaw/traffic-day/quorum-casino/ring-balancer games
python manage.py createsuperuser   # optional, for /admin access

python manage.py runserver
```

To use the admin's "Generate from scenario" button for Coding Challenges, add
a free Gemini API key to `.env`:

```
GEMINI_API_KEY=your-key-here   # https://aistudio.google.com/apikey
```

(everything else works without it — the app just won't be able to generate
new coding challenges until it's set).

Then open http://127.0.0.1:8000/ and sign up for an account (or log in
with the superuser you created).

## Adding more content

### The curriculum

The system design content is the curriculum in
[docs/learning](docs/learning/README.md). `learn/curriculum.py` reads its
Markdown, `catalogue.json` and `sources.json` when you seed, and turns each
lesson and case study into one chapter and concept (see
[the integration guide](docs/learning/dashboard-integration.md) for the
mapping). Stages unlock at levels 1, 2, 4, 6 and 8; case studies at 5, 7
and 9.

- To change a lesson's notes, objectives or sources, edit its Markdown or
  the catalogue and re-seed. Keep the section headings the loader expects
  (it raises if one is missing).
- Quiz questions are authored by hand in `learn/curriculum_questions.py`,
  keyed by lesson ID, because the catalogue's checks are short-answer.
  Re-seeding updates a bank in place, keyed by prompt text, so learners'
  attempts survive unless the prompt itself changes.
- sd-01 (**DNS, TCP, and TLS: follow a request**) keeps its hand-adapted
  notes, questions and interactive request walkthrough in
  `learn/curriculum.py`.
- sd-02 (**HTTP and API design: define the contract**) adds an interactive
  contract lab at `/concept/http-api-design/`: repeat GET/PUT/DELETE/POST,
  compare keyed retries, observe asynchronous export states and lost status
  responses, and resolve ETag conflicts between two editors. These unscored
  browser simulations sit alongside the existing notes and five-question quiz.
  Their model checks run with `node --test learn/js_tests/http_contract_model.test.js`.
- `seed_content` seeds the curriculum plus the two reference chapters and
  **removes every chapter, concept, topic and book no longer defined**,
  including learners' attempts on them. It refuses to remove a concept that
  holds an admin-made coding challenge unless you pass
  `--delete-coding-challenges`. `seed_curriculum` adds or updates the
  curriculum without removing anything.

```bash
python manage.py seed_content
python manage.py seed_games
python manage.py collectstatic --noinput
```

- The two reference chapters (Python internals, OS file handling) live in
  `learn/management/commands/seed_content.py` as `REFERENCE_CHAPTERS`. Each
  concept's `notes=[...]` is a list of
  `dict(heading=..., body=..., deep_dive=dict(title=..., body=...) | omitted)`
  dicts, rendered behind the View Notes toggle and reused as Study Mode's
  flashcards.
- Mini-game content (architecture builder pools/wiring, matching pairs,
  ordering steps, spot-the-flaw diagrams) lives in
  `learn/management/commands/seed_games.py`. A spot-the-flaw diagram is
  hand-placed boxes and SVG arrow paths in a 1000×430 viewBox; see the
  comment above `FLAW_CHALLENGES`, and run the tests, which check the
  seeded diagrams for typos. Point them at SQLite so they don't create a
  test database on whatever server `.env`'s `DATABASE_URL` names:
  `DATABASE_URL=sqlite:///db.sqlite3 python manage.py test learn`. Tests
  render pages through the static manifest, so run `collectstatic` first
  after adding a static file.
- A Traffic Day scenario is a `params` dict in `TRAFFIC_CHALLENGES` (same
  file): traffic, capacities, hourly prices, SLO, the spike, scoring,
  control limits, the starting design and ops-log lines. The load model's
  shape of the day, latency curve and cache hit rates live in
  `learn/traffic.py` and `learn/static/learn/traffic_model.js`; change both
  together.
- A Quorum Casino challenge is a list of `tables` in `QUORUM_CHALLENGES`
  (same file): each has N, W, R, an outro, and a script of `write`,
  `status`, `sync` and `read` steps. `learn/quorum.py` documents the step
  shapes, and the tests run `quorum.validate_tables` over every seeded
  script.
- A Ring Balancer challenge is a list of `stages` in `RING_CHALLENGES`
  (same file): `balance` stages (servers with a capacity `w`, a `busiest` or
  `every` rule, a tolerance, and whether weighting is offered) and `predict`
  stages (questions that crash a server on the ring or under hash % N).
  `learn/ring.py` documents the shapes; the tests run `ring.validate_stages`
  over the seed and check each ring teaches what its text says.

Both commands are idempotent, so re-running updates existing content
instead of duplicating it.

When adding a new case study, add it to the curriculum (Markdown, catalogue
entry with an `architecture` graph, and a question bank) and give it a
`DesignChallenge` in `seed_games.py`: every case study is expected to have a
builder game, and every lesson at least one other game. The tests check
both. Don't add content that summarizes a published book or names one as a
source; `learn/test_curriculum.py` checks seeded text for the titles and
authors the earlier content used.

### Adding a new coding challenge

Unlike everything else above, coding challenges aren't seeded via a
management command — they're created one at a time through Django admin
(Coding challenges -> "✨ Generate from scenario"), since each one is
generated from a free-text scenario via Gemini rather than hand-authored as a
Python data structure. After generating, the challenge (and its test cases)
are normal rows you can hand-edit from the challenge's admin change page like
any other content — the generator just gets you a well-specified starting
point instead of a blank page, and won't produce one until it's sure the
scenario has enough in it (task, exact stdin/stdout format, a worked example)
to write unambiguous test cases.

### Adding a new architecture-builder challenge

In `seed_games.py`, add a `ComponentType` for any new building block you
need, then add an entry to `DESIGN_CHALLENGES` with the concept it belongs
to, a `prompt` describing the scenario, a list of `required` component
slugs, a list of `distractors` (wrong-for-this-scenario components that
penalize the player if used), and the correct `connections` as
`(from_slug, to_slug)` pairs. The pool shown to the player is exactly the
required parts plus these distractors, and every required part must be
wired at least once (the tests check this).

## Notes

- Uses SQLite by default (`db.sqlite3`, created on first `migrate`) — fine
  for single-user local use.
- Styling is Tailwind via CDN; the ordering game also loads SortableJS
  from cdnjs for drag-to-reorder. No build step required.
- The architecture-builder and matching drag-and-drop use the native
  HTML5 Drag and Drop API, which is desktop-browser only (no touchscreen
  support).
- To deploy somewhere with a real URL (Railway, Render, Fly.io), set
  `DEBUG = False` and `ALLOWED_HOSTS` in `config/settings.py`, and swap
  SQLite for Postgres.
