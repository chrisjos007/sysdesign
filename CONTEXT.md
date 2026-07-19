# SysDesign Quest — Context for Continuing

Last updated: 2026-07-19, by Claude (Cowork session).
PROJECT PATH: A:\New folder (2)\sysdesign_quest

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
