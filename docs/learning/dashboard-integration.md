# Dashboard integration guide

This package is the website's system design content. The Markdown, catalogue and source registry stay the source of truth; the app reads them at seed time.

Implementation status: all 31 lessons and 6 case studies are in the app, and they
replaced the retired earlier chapters. `learn/curriculum.py` reads this
package and returns one chapter and concept per item; `python manage.py seed_content`
writes them and removes content that is no longer defined, and
`python manage.py seed_curriculum` adds or updates them without removing anything.
What the app takes from each item:

- **Notes.** A lesson's Intuition, How it works, Worked example, Trade-offs and
  Practice sections become notes sections, with the answer guidance as a
  "Click to know more" deep dive. A case study's sections become notes the same
  way; the reference architecture is listed from the catalogue graph, and the
  rubric table becomes plain lines. Links keep their text; the lesson lists its
  sources separately.
- **Metadata.** ID, level, stage, study time, objectives, prerequisites and sources go
  into `Concept.curriculum` and appear on the lesson page.
- **Questions.** The short-answer checks are rewritten by hand as MCQ and
  multi-select questions with plausible wrong answers, five or six per item, in
  `learn/curriculum_questions.py`. sd-01 keeps its hand-adapted notes, six
  questions and request walkthrough in `learn/curriculum.py`.
- **Games.** Each case study's reference graph is an Architecture Builder in
  `seed_games.py`, with the builder brief's wrong turns as its distractors.
  Every lesson has at least one matching, ordering or other game.
- **Interactive walkthroughs.** sd-01 compares connection setup costs. sd-02
  explores method semantics and retries, asynchronous acceptance versus
  completion, and conditional edits with ETag/If-Match. sd-03 explores queue
  growth and drain time, steady-state Little’s Law, and nearest-rank latency
  percentiles. sd-04 lets learners schedule two balance increments and compare
  lost updates, a shared lock, separate server locks, and atomic increments.
  sd-05 compares sequential, tenant-index, and composite-index access paths,
  estimated versus actual row counts with loops, and N+1 versus joined or
  batched owner fetching. Its row counts are a teaching model, not a database
  benchmark or planner prediction.
  sd-06 connects active-user assumptions to average and peak reads, payload
  bandwidth, raw event retention, and conditional server counts with one failed
  server. It leaves sizing unknown until a sample throughput is selected and
  distinguishes workload assumptions, invariants, and measured objectives.
  All six are unscored browser exercises; they do not send
  actual API requests or award mastery.
  Existing quiz attempts continue to drive XP and review scheduling.

The app does not store curriculum-wide completion records or enforce knowledge
prerequisites; stages unlock by XP level instead.

## Content contract

Load [catalogue.json](catalogue.json) and resolve its document paths relative to `docs/learning/`. Load [sources.json](sources.json) separately and join on source ID. [catalogue.schema.json](catalogue.schema.json) describes field types and required structure; referential integrity and prerequisite cycles require an additional data check.

| Field | Meaning |
|---|---|
| `id` | Stable content identity: sd-01 through sd-31, cs-01 through cs-06 |
| `slug`, `title`, `summary` | Human-facing navigation and preview text |
| `type` | lesson or case_study |
| `stage`, `stage_order` | Five-stage educational progression |
| `order` | Default display sequence; cases can be attempted earlier when prerequisites are met |
| `estimated_minutes` | Suggested reading and practice time, not measured completion data |
| `path` | Relative Markdown body path |
| `prerequisite_ids` | Required knowledge edges inside this package |
| `tags`, `objectives` | Filtering and explicit learning outcomes |
| `source_ids` | References into the source registry |
| `level` | Beginner, intermediate or advanced; required on every item and stage ([content standards](CONTENT_STANDARDS.md)) |
| `assessment` | Short-answer prompts, explanatory answers, and case rubrics |
| `architecture` | Case reference components, labelled logical edges, and builder brief |
| `activities` | Content activities described here; not proof of implemented website features |
| `content_status` | documented; no assertion of import, publication, or learner completion |

Keep IDs stable when editing titles or moving files. Change the path and content version as needed. Prerequisites reference IDs, so routing changes do not break the knowledge graph. Keep learner progress in separate user records keyed to content ID and a relevant content version.

## Suggested dashboard views

- **Continue learning:** last opened or incomplete content, with its objectives and study estimate.
- **Learn next:** earliest incomplete item whose prerequisites have been demonstrated.
- **Explore:** filter by stage, topic, tag, or concept versus case study.
- **Practice:** show questions before revealing the explanatory answer.
- **Design lab:** offer the case prompt first, then reference architecture and rubric.
- **Review:** schedule selected concepts from learner evidence; viewing a document alone need not mean mastery.

These are implementation suggestions. Prerequisites express knowledge dependencies, not a mandate to block browsing. A learner may already understand a prerequisite through existing content or experience.

## Mapping to the Django website

| Catalogue | App |
|---|---|
| Collection | One Book row, “System Design Engineering Notes” (`ENGINEERING_NOTES`) |
| Stage | One Topic per stage, plus a Case Studies topic (`curriculum.TOPICS`) |
| Item | One Chapter holding one Concept; both use the catalogue `slug` |
| `stage` | Chapter unlock level: lessons 1, 2, 4, 6, 8 by stage; case studies 5, 7, 9 |
| `level` | Chapter difficulty: beginner 1, intermediate 2, advanced 3 (stages 3 to 5 are all advanced) |
| `id`, `objectives`, `prerequisite_ids`, `source_ids` | `Concept.curriculum` |

Educational prerequisites are distinct from the XP unlock level: the lesson page links them but does not block on them. Keep the per-lesson links to standards, papers and official documentation. Never name a study book or course as a source. `learn/test_content_standards.py` fails if seeded or repository text names one of the study books the earliest content drew on, if quiz choices are unbalanced, or if an item has no level; see [CONTENT_STANDARDS.md](CONTENT_STANDARDS.md).

## Assessment and architecture conversion

The catalogue's checks are short-answer questions with explanatory reference answers, which the Question model does not support. `learn/curriculum_questions.py` holds deliberately authored MCQ and multi-select versions with plausible wrong answers, plus questions on each worked example and practice task. When a lesson changes, update its bank there; the seed keeps a question's identity (and learners' attempts) while its prompt text stays the same.

Each case's reference graph is an Architecture Builder challenge in `seed_games.py`. Its components are case-specific ComponentTypes, its connections are the graph's edges as undirected pairs, and its distractors are the wrong turns the builder brief names, such as a cache-only seat lock or a DNS-only failover switch. The builder scores parts and wires; the 20-point rubric stays in the notes for self-assessment of the reasoning.

## Maintenance

1. Edit the Markdown, catalogue or source registry; keep IDs stable.
2. Update the matching question bank and any game that quotes the changed text.
3. When adding browser assets, run `python manage.py collectstatic --noinput` first so the test environment's static-file manifest includes them. Run `python manage.py test learn`, which checks every item has notes, sources and a valid quiz, and every lesson a game. For interactive lesson models, also run `node --test learn/js_tests/*.test.js`.
4. Re-run `seed_content` and `seed_games`. Try them on a copy of the database first: `seed_content` removes chapters and concepts that are no longer defined, with their learners' attempts, and refuses to remove admin-made coding challenges unless given `--delete-coding-challenges`.

For Markdown rendering, keep code, tables, and Mermaid support consistent with the future renderer. Treat source content as untrusted input and apply the application's normal HTML sanitization policy. If a renderer does not support Mermaid, the catalogue's component/connection arrays preserve the same architecture information.

Review product-specific source links when their provider contract changes. Update the review date only after a substantive review. Preserve the distinction between a source-supported mechanism and an original example or design choice.
