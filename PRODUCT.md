# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Three audiences, all confirmed:

- **The owner, studying.** The builder is also a daily learner. They use it to prepare for system design and backend interviews and to work through the curriculum.
- **Public learners.** Other people preparing for system design and backend interviews, who sign up for an account and come back regularly. The app is meant to grow toward this audience.
- **Portfolio viewers.** Recruiters and peers who look at the deployed app to judge what the builder can make. They browse briefly and don't come back.

## Product Purpose

SysDesign Quest turns an original system design curriculum into a gamified learning loop. A session does two jobs equally:

- **Retention:** short daily reps (the Daily Review queue, quizzes, streaks) that bring concepts back just before they would be forgotten.
- **Comprehension:** longer study sessions (structured notes, deep dives, Study mode flashcards, architecture building, coding) for understanding the material, not just recognizing it.

Success means the learner can recall a concept under interview pressure and reason through a design out loud, and keeps coming back day after day.

## Positioning

- **Original lessons grounded in primary sources.** The system design content is an original curriculum (`docs/learning`): 31 lessons in five stages and 6 case studies, citing 62 standards, papers and official documentation pages (IETF RFCs, PostgreSQL, Kubernetes, Google SRE, Raft and others). Every lesson page lists its sources. Two compiled reference chapters cover Python internals and OS file handling. No content summarizes a published textbook.
- **Guessing wrong always costs.** Every game uses negative scoring: wrong matches, misplaced steps, extra components, wrong wires and failing tests all lose points. Spamming options doesn't pay, so learners have to reason.
- **Designs are built, not just recalled.** In the Architecture Builder the learner places components and wires them together. Coding challenges grade real stdin/stdout programs against hidden test cases.
- **Spaced repetition underneath the game layer.** SM-2 scheduling drives the Daily Review. XP, levels and badges sit on top of real retention mechanics.

## Operating Context

- **Desktop:** deeper sessions such as the drag-and-drop games (Architecture Builder, Matching, Ordering), the CodeMirror coding editor, and long-form notes.
- **Phone:** mostly quick daily reviews and quizzes, but every activity must also work fully on a phone (see Capabilities and Constraints).
- **Content hierarchy:** Book (the source collection) → Topic → Chapter → Concept. Each concept holds a notes teaser, notes sections (some with a "Click to know more" deep dive), a quiz bank, and any number of challenges in the "Play to learn" grid.
- **Two kinds of concept:**
  - Lessons (sd-01 to sd-31), one topic per stage: Beginner, Intermediate, Advanced, Production, Expert. Each shows its objectives, prerequisites and sources, and has at least one game.
  - Case studies (cs-01 to cs-06: ticket booking, payments, job scheduling, search, feature flags, multi-region SaaS). Each always has an Architecture Builder game built from its reference architecture.
- **Admin workflow:** content is seeded from `docs/learning` (read by `learn/curriculum.py`, questions in `learn/curriculum_questions.py`) and from Python data (`seed_content.py`, `seed_games.py`). Coding challenges are generated in Django admin from a plain-language scenario via Gemini, which asks clarifying questions when the scenario is too vague to write test cases.

## Capabilities and Constraints

- **Capabilities:**
  - Quizzes (mcq/multi) walk through the whole bank once in shuffled order and end with a completion summary.
  - Six challenge types: Architecture Builder, Matching, Ordering, Coding, Spot the Flaw, Traffic Day.
  - XP, levels, daily streaks and badges. Chapters unlock by level.
  - Daily Review (SM-2) and a dashboard progress map.
  - Notes support Study mode (one card at a time) and Read aloud (browser speech synthesis).
  - Superusers get an "Unlock All Content" toggle that bypasses level gating.
- **Stack:**
  - Django with server-rendered templates.
  - Tailwind from the CDN (no build step), CodeMirror, and marked.js for Markdown.
  - Hosted on Render's free web service (cold starts of 30–60 s after idle) with a Neon Postgres database (also scales to zero). SQLite locally.
- **Terminology in use:** Book, Topic, Chapter, Concept, Notes, Deep dive, Study mode, Quiz, Daily Review, Play to learn, Architecture Builder, Matching, Ordering, Coding Challenge, Spot the Flaw, Traffic Day, XP, Level, Streak, Badge.
- **Public launch requires a hardened sandbox (confirmed).** Today's coding sandbox is best-effort only (import allowlist, rlimits, timeout; no container isolation). Public launch waits until submissions run in a truly isolated environment, such as a container or a hosted runner. Until then, the app is not opened to the public.
- **Every activity works on a phone (confirmed).** That includes Architecture Builder, Matching, Ordering and the code editor. Drag-and-drop and wiring need touch-capable interactions, not desktop-only mouse behavior.
- **No book-derived content.** Notes, questions and games are original teaching material that cites primary sources. Don't add content that summarizes a published book, and don't name one as a source; the tests check seeded text for the titles and authors the earlier content used.

## Brand Commitments

- **Name:** "SysDesign Quest".
- **Voice (not binding, confirmed).** The current interface uses a playful, game-flavored voice with emoji-labelled actions ("📖 View Notes", "🧠 Study mode"). The owner has said this isn't a brand commitment, so future work may change the tone or drop the emoji. Keep the product terminology listed above.

## Evidence on Hand

- **Real content (seed data in the repo, as of 2026-09-27):**
  - 3 source collections, 8 topics, 39 chapters/concepts (37 curriculum items plus the Python and OS reference chapters)
  - 225 quiz questions
  - 6 Architecture Builder, 28 Matching and 14 Ordering challenges, plus Spot the Flaw, Traffic Day and Quorum Casino
  - Defined in `docs/learning`, `learn/curriculum_questions.py`, `learn/management/commands/seed_content.py` and `seed_games.py`.
- **Not live yet:** the local database and the production Neon database may lag behind this content until they are re-seeded.
- **Absent, must not be fabricated:** testimonials, user counts, pass-rate or outcome claims, press, logos, pricing.

## Product Principles

1. **Earn the answer.** Mechanics reward reasoning over guessing. New activities keep the negative-scoring principle.
2. **Retention and comprehension together.** Every feature should serve the quick daily rep or the deep session, and ideally link the two.
3. **Cite the source.** Content stays traceable to the standards, papers and official documentation it rests on. Nothing is presented as authoritative without a source.
4. **One learning loop, not separate sections.** New activity types join the existing Concept → "Play to learn" structure instead of getting their own silos.
5. **Should hold up for strangers.** Anything shipped should work for a new public learner and a skimming recruiter, not only for the builder.

## Accessibility & Inclusion

No formal standard has been set. Every activity must work on both desktop and phone. Quick reviews and quizzes are the most common phone use, but games and coding must work there too. Any drag or wiring interaction needs a touch-capable version, and ideally a tap-based alternative as well. Read aloud already exists as an alternative way to take in the notes.
