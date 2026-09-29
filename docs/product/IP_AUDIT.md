# IP and marketability audit

Everything found on 2026-09-29 that could stop SysDesign Quest being sold, shown to buyers or investors, or marketed publicly because of third-party material, licences or ownership. Work through it one item at a time and tick an item only when its **Done when** is true. The [launch checklist](LAUNCH_CHECKLIST.md) tracks this audit as P0-16; related checklist items are cross-referenced (→ P1-26).

**Priority:** **P0** before any outside user, buyer or public repository · **P1** before public launch or marketing · **P2** after launch.

---

## Fixed in the 2026-09-29 pass

- [x] **IP-01 · Named study books and chapter citations removed.** Titles, authors and chapter references were removed from the product, the docs, the tests, the agent instructions and the game prototypes. `learn/test_content_standards.py` now fails if seeded or repository text names any of them. It stores only hashed fingerprints, so the check itself names nothing.
- [x] **Book-derived scenarios in live content replaced.** Spot the Flaw's notification-system diagram became an original event-delivery service (customer webhooks and emailed receipts). Traffic Day's URL-shortener day, with its 301-versus-302 analytics trade-off, became a flash sale on a shop's product pages with a browser-caching trade-off. sd-25's write-skew practice now uses a workspace that must keep one owner instead of the familiar on-call example. Estimathon's copied worked examples were replaced with original numbers.
- [x] **Quiz answers no longer give themselves away.** Before this pass, the right answer was the longest choice in 167 of 200 single-answer questions. Every question was rebalanced, and tests now enforce the length, tone and yes/no rules.
- [x] **Content standards written.** [CONTENT_STANDARDS.md](../learning/CONTENT_STANDARDS.md) sets out the rules for originality, accuracy, quiz design and the three levels, and it binds the content-scout agent.
- [x] **Outdated facts corrected.** Python 3.14's default start method, the free-threaded build's status, string-hash randomization and iteration order, the `umask` arithmetic, ext4 inode allocation and Linux's removal of mandatory locking.

---

## P0: before any outside user, buyer or public repository

- [ ] **IP-02 · Production still serves the retired book-summary content** (→ P0-08)
  - **Why:** Neon hasn't been reseeded since the curriculum replaced the chapters that summarized third-party study books. Anyone who signs in today sees them.
  - **Done when:** after a backup, `migrate`, `seed_content` and `seed_games` have run against production, and a search of every concept, question and game in production finds none of the retired content. The local `db.sqlite3` needs the same reseed.

- [ ] **IP-03 · Git history and other branches still contain the retired content**
  - **Why:** the commits before 2026-09-27 hold the book-derived chapters, and the book titles and authors appear in `origin/main`, `origin/master`, `content-scout` and `claude/dazzling-robinson-f8f6d4`. Cleaning the working tree doesn't clean history. Anyone with access to `github.com/chrisjos007/sysdesign` can read it. (This pass couldn't check whether that repository is public, because the `gh` CLI isn't installed.)
  - **Done when:** the repository is private, or published history no longer contains the material. Rewrite it with `git filter-repo`, or start a fresh repository from a squashed commit of the cleaned tree. Delete or merge the stale branches, and remove the `.claude/worktrees/dazzling-robinson-f8f6d4` worktree. Do the same before sharing the code with a buyer, contractor or investor.

- [ ] **IP-04 · Superseded game prototypes keep book-derived scenarios**
  - **Why:** the citations are gone, but `docs/games/prototypes/spot-the-flaw.html` still draws the notification-system design, and `traffic-day.html` still runs the URL shortener with its 301-versus-302 analytics trade-off. The matching tabs in `game-lab.html` do the same. The live games replaced both.
  - **Done when:** the superseded prototypes and their `game-lab.html` tabs are deleted (recommended, since the live games are the source of truth), or re-themed to match the live games.

- [ ] **IP-05 · Someone else's coding-assessment files in the project folder** (→ P2-09)
  - **Why:** `file.doc`, `file.docx`, `file.html`, `table.csv` and `try.py` in the repository root are a downloaded third-party coding-assessment puzzle. Git ignores them, but they travel with any copy of the folder.
  - **Done when:** they are deleted from the project folder.

- [ ] **IP-06 · Local copies of the retired content**
  - **Why:** these hold the old chapters or old game text outside git: `.claude/worktrees/dazzling-robinson-f8f6d4`, `db.sqlite3` until it is reseeded, `learn/**/__pycache__`, `staticfiles/`, the `.impeccable/review/*.png` screenshots, and the local code indexes (`.vexp/`, codebase-memory). They leak through a zipped folder, a shared drive or a laptop handover.
  - **Done when:** each is deleted or regenerated from the cleaned tree.

## P1: before public launch or marketing

- [ ] **IP-07 · Decide on the one citation by the author of a retired book**
  - **Why:** sd-28, cs-03 and cs-06 cite a standalone blog post on distributed locking and fencing tokens by the author of one of the retired books. It is a legitimate, freely available primary source, not the book, so this pass kept it. The content standards allow it.
  - **Done when:** you keep it, or replace it with the original papers: the Chubby lock-service paper (Burrows, OSDI 2006), whose "sequencers" are fencing tokens, and Gray and Cheriton's leases paper (SOSP 1989). If you replace it, update `sources.json` and the three documents.

- [ ] **IP-08 · Sources under non-commercial or no-derivatives licences**
  - **Why:** several lessons cite the Google SRE books on sre.google, licensed CC BY-NC-ND 4.0: sd-03, sd-06, sd-18, sd-19, sd-22, cs-03, cs-05 and the capacity lesson's interactive page. sd-03 also cites MIT OpenCourseWare notes, licensed CC BY-NC-SA. Linking and stating facts in our own words is fine in a commercial product. Quoting, adapting figures or closely paraphrasing is not.
  - **Done when:** a side-by-side check of those lessons against their sources finds no adapted sentences, tables or figures, and `sources.json` records each source's licence (IP-09).

- [ ] **IP-09 · Record a licence for every source**
  - **Why:** `sources.json` records the kind and the review date, but not the terms. Reviewers can't see which sources are link-only.
  - **Done when:** each source has a `licence` field (for example `CC-BY-4.0`, `CC-BY-NC-ND-4.0`, `IETF-Trust`, `PostgreSQL`, `all-rights-reserved`), the schema requires it, and the content standards point to it.

- [ ] **IP-10 · State who owns the content, and how AI drafting affects it** (→ D-12, P1-28)
  - **Why:** there is no `LICENSE` file and no copyright line, and much of the curriculum was drafted with AI tools. In some jurisdictions, including the US, purely machine-generated text can't be copyrighted, but human selection, arrangement and editing can. That affects what a buyer or investor can be told is exclusive.
  - **Done when:** the footer and the terms carry a copyright notice and the chosen content licence. The repository has a `LICENSE` file, or a statement that all rights are reserved. The human review and editing of each lesson is on record, for example in the content ledger or commit history.

- [ ] **IP-11 · Generated coding challenges could reproduce known problems**
  - **Why:** coding challenges are generated in admin by the Gemini API. A language model can reproduce well-known problem statements from competitive-programming sites or interview books nearly word for word.
  - **Done when:** each generated challenge is checked against the content standards before publication (own wording, own examples, no named source), the admin flow says so, and the Gemini API terms for output use and free-tier data handling have been reviewed for commercial use.

- [ ] **IP-12 · Product name and domain** (→ D-4, P1-26)
  - **Done when:** the trademark search for "SysDesign Quest" is clear in your main markets, and the domain and handles are registered.

- [ ] **IP-13 · Third-party product names in lessons**
  - **Why:** lessons name Kubernetes, PostgreSQL, PgBouncer, RabbitMQ, Apache Kafka, Debezium, Redis, Apache Cassandra, Amazon DynamoDB and S3, Stripe, Elasticsearch, Google Bigtable and CockroachDB to explain documented behavior. That is normal descriptive use, but the product should say it isn't affiliated with them. The live games now use generic names ("email provider", "PDF renderer").
  - **Done when:** the footer or the terms state that product names are trademarks of their owners and imply no affiliation or endorsement, no third-party logos appear, and new scenarios use generic names unless the lesson is about that product.

- [ ] **IP-14 · Third-party code and font notices**
  - **Why:** the app ships or loads Django (BSD-3-Clause), WhiteNoise (MIT), Gunicorn (MIT), psycopg (LGPL-3.0), Requests (Apache-2.0), dj-database-url and python-dotenv (BSD), CodeMirror 5 and marked (MIT, from cdnjs) and the Archivo font (SIL OFL 1.1). Hosting a web app isn't distribution under these licences, but a buyer's due diligence will ask for the list, and shipping a self-hosted or desktop build would trigger the notice requirements, psycopg's LGPL terms included.
  - **Done when:** a `THIRD_PARTY_NOTICES` file lists each dependency with its licence, and adding a dependency means updating it.

- [ ] **IP-15 · Fonts load from Google's servers**
  - **Why:** `base.html` loads Archivo from fonts.googleapis.com, which sends every visitor's IP address to Google. A German court (LG München I, January 2022) held this a GDPR breach without consent. The OFL allows self-hosting.
  - **Done when:** the font files are served from the app's own static files and the Google Fonts links are gone.

- [ ] **IP-16 · Keep marketing copy clear of the retired sources**
  - **Why:** positioning copy that says "based on" or "better than" a named book, course or company invites both copyright and trademark claims, and it contradicts IP-01.
  - **Done when:** the marketing site, store listings and social posts name no study book, course or author, make no claim of affiliation, and make no promise of interview results (already in spec).

## P2: after launch

- [ ] **IP-17 · Case-study topics overlap common interview reading lists**
  - **Why:** ticket booking, payment processing and search autocomplete also appear in popular interview books. Topics can't be owned, and this pass reviewed the six designs as original, but the overlap invites comparison.
  - **Done when:** each case study has had a side-by-side originality check against the best-known published treatments, and the next case studies come from outside the usual list (the ideas queue in the [content ledger](../learning/content-ledger.md)).

- [ ] **IP-18 · Rework the unported prototypes before porting them** (→ P2-05)
  - **Why:** Bit Budget, Estimathon and Pattern Deck were sketched against classic interview topics. Their citations and copied numbers are fixed, but a port must re-derive each game under the content standards: own scenario, own numbers, and a curriculum lesson it teaches.
  - **Done when:** each is ported under the standards or dropped.
  - **Progress:** Bit Budget was ported on 2026-09-29 with its own scenario (a parcel carrier's tracking IDs), its own field layouts, epochs and needs, and a second clock question, on sd-28. The prototype's 41/5/5/12 split, the common textbook layout, is gone. Estimathon and Pattern Deck remain.

- [ ] **IP-19 · Say "collection", not "book", to learners**
  - **Why:** the data model, admin and some templates call a content collection a `Book` (see `learn/templates/learn/book_detail.html`). Learner-facing text that says "book" suggests the lessons summarize books.
  - **Done when:** learner-facing pages and badge text say "collection" or name the collection. The model can keep its internal name.

- [ ] **IP-20 · Re-run the source-name and originality checks on a schedule**
  - **Done when:** CI runs `learn/test_content_standards.py` on every push (→ P0-15), and a quarterly review re-checks a sample of lessons side by side against their sources.
