# SysDesign Quest

A gamified learning app for system design interview prep, built on five
loaded books: *System Design Interview: An Insider's Guide* (Alex Xu),
*Grokking the System Design Interview*, *Database Internals*, *Designing
Data-Intensive Applications*, and the *Linux Pocket Guide*.

## What's inside

- 19 chapters -> 19 concept cards -> 147 quiz questions across all five
  books. Content is split into two kinds of item: concrete "design a
  system" items (Design a URL Shortener, Designing Twitter, etc. — each
  guaranteed its own architecture-builder game and a 6-7 question quiz)
  and bigger merged "domain" items that bundle several more
  general/theoretical chapters together (e.g. Storage Engines, or all six
  Linux command-line chapters) into one combined quiz (9-14 questions)
  with multiple matching/ordering mini-games attached.
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
    system design (e.g. "Design a URL Shortener"). Correct required parts
    and correct wires score points; parts that don't belong and wrong or
    missing wires cost points. A flawless design earns a bonus and the
    "Architect" badge.
  - **Matching** — drag definitions onto the terms they define (e.g. CAP
    theorem, rate-limiting algorithms). Right matches score, wrong matches
    cost you.
  - **Ordering** — drag steps into the correct sequence (e.g. the 7-step
    design framework, scaling a single server to millions of users).
    Steps in the right slot score, misplaced ones cost you.

All three mini-games use the same negative-scoring principle you asked
for: guessing wrong is never free, so there's a real incentive to reason
through the answer rather than spam every option. Every concrete
"design a system" item (URL Shortener, Twitter, Key-Value Store, etc.) is
guaranteed an Architecture Builder challenge; domain items instead get one
or more Matching/Ordering games.
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
- **Notes, redesigned** — each concept page shows a short one-line teaser
  plus a "📖 View Notes" button; notes are hidden until you click it (no
  wall of text up front). Once open, notes are structured as headed
  sections (2-6 per concept) that explicitly cite the book/chapter they're
  drawn from, each written as a few full paragraphs rather than a single
  dense block. Particularly gnarly sub-topics (split brain, write skew,
  SIGTERM vs. SIGKILL, why total order broadcast = consensus, etc.) get an
  expandable "🔍 Click to know more" deep-dive so the main flow stays
  readable. A "🧠 Study mode" toggle turns the same sections into a
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
python manage.py seed_content   # loads the book content + quiz questions
python manage.py seed_games     # loads the architecture/matching/ordering/spot-the-flaw/traffic-day games
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

- Quiz content and notes both live in `learn/management/commands/seed_content.py`
  — each concept's `notes=[...]` is a list of
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

Both are plain Python data structures — add entries and re-run the
matching `manage.py` command; both commands are idempotent, so re-running
updates existing content instead of duplicating it (re-running
`seed_content` also deletes any chapter/concept no longer listed in
`CHAPTERS`, so a merge/rename is safe to do in place).

When adding a new concrete system to design, give it its own chapter +
concept in `seed_content.py` and make sure it gets a `DesignChallenge` in
`seed_games.py` — every "design a system" item is expected to have a
builder game. For more general/theoretical content that doesn't warrant
its own item, prefer folding it into an existing (or new) merged "domain"
chapter alongside related topics, with a combined summary/quiz and however
many matching/ordering games make sense — a `Concept` can hold any number
of each.

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
`(from_slug, to_slug)` pairs.

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
