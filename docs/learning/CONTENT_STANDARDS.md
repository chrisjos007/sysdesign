# Content standards

These rules apply to everything a learner reads or answers in SysDesign Quest: lessons, case studies, notes and deep dives, glossary entries, quiz questions and explanations, game text (matching pairs, ordering steps, Spot the Flaw reasons, Traffic Day, Ring Balancer and Bit Budget copy), interactive lesson copy, and marketing text about the content. They also bind every agent that writes content, including the content-scout agent.

`learn/test_content_standards.py` enforces the rules marked **(tested)**. The rest are review rules: check them before merging.

## 1. Every piece of content has a level

Content is organized into exactly three levels: **Beginner**, **Intermediate** and **Advanced**. Nothing is added without one.

| Level | Written for | After it, a learner can |
|---|---|---|
| Beginner | Someone who can build a small web app but hasn't designed a service. No prerequisites beyond general programming. | Trace one request end to end, do back-of-napkin arithmetic with units, and name the first resource that runs out. |
| Intermediate | Someone who knows the Beginner material. | Scale one service: cache, pool, queue, partition and paginate it, and explain what each choice costs. |
| Advanced | Someone who knows the Intermediate material. | Reason about failures across services, operate a system in production, and state guarantees precisely enough to find a counterexample. |

How the curriculum maps onto levels:

| Stage (learning path) | Level |
|---|---|
| 1. Understand a request | Beginner |
| 2. Scale a service | Intermediate |
| 3. Handle distributed failures | Advanced |
| 4. Operate reliably | Advanced |
| 5. Reason about guarantees | Advanced |
| Case studies | Advanced (they combine several lessons) |
| Reference chapters (Python, OS) | Set per chapter; both are Intermediate today |

Rules:

- Each catalogue item and stage carries `level`: `beginner`, `intermediate` or `advanced`. An item's level is its stage's level. **(tested)**
- The document's header line states it: `ID: sd-NN | Level: Beginner | Stage 1: Understand a request | Suggested study: NN minutes`. **(tested)**
- Along the learning path the level never goes down: no Beginner lesson after an Intermediate one. **(tested)**
- A dashboard topic for a stage is titled with its level, as in "Advanced: Operate Reliably". **(tested)**
- A reference chapter sets `difficulty` to 1, 2 or 3 (Beginner, Intermediate, Advanced). **(tested)**
- Choose the level by what the reader must already know, not by how long the item is. If an item needs an Advanced prerequisite, it is Advanced.
- Quiz questions and games inherit the level of the item they belong to. Don't put an Advanced question in a Beginner bank.

## 2. Write it in your own words

Sources are for checking facts. The words, examples and structure must be ours.

- **Never copy wording** from a book, course, blog, video, documentation page or standard into learner content. That includes close paraphrase: keeping a source's sentence and swapping a few words is still copying. Technical terms, protocol and API names, and standard keywords (such as `If-Match` or `no-store`) are fine.
- **Work from notes, not from the open page.** Read the sources, close them, write from your own notes, then compare side by side. Rewrite any run of five or more words that matches a source, unless it is a term or name.
- **Invent your own examples and numbers.** Don't reuse a source's worked example, scenario, sample data, figure, diagram layout, exercise or quiz, even with the numbers changed. If a well-known example is the obvious one to use (a classic interview scenario, a textbook's signature illustration), pick a different domain.
- **Don't mirror a source's structure.** Don't follow a book's chapter order, its list of "design X" problems, or its sequence of headings.
- **Don't name study books or courses** as sources, further reading or inspiration, anywhere in the product or the repository. **(tested: seeded text and repository text are checked against fingerprints of the names the earliest content used)**
- **Cite primary sources**: standards (RFCs), official documentation, peer-reviewed papers and first-party engineering write-ups. A citation records where a fact was checked; it is not permission to copy.
- **Check the licence before relying on a source.** Link to, don't adapt, text under a non-commercial or no-derivatives licence. Some well-known engineering books are free to read online under such a licence.
- **No quotations in learner content.** If a quotation is genuinely needed, keep it under 15 words, attribute it and link it.
- **Use generic names for third-party products in scenarios** ("email provider", "payment provider") unless the lesson is about that product. When a product must be named, name it plainly, without logos, and don't imply endorsement.
- **Label illustrative numbers** as hypothetical. Real figures (a product limit, a protocol constant) carry their source.

## 3. Make it accurate

- Check every factual claim against a primary source and record the source in `sources.json` with the date you checked it.
- State version-dependent facts with their version: "the default since Python 3.14", "removed in Linux 5.15". Recheck them when you touch the lesson.
- Work every calculation twice, keep units visible, and make the quiz answer match the lesson's arithmetic exactly.
- Keep the lesson, its catalogue checks, its quiz bank and its games consistent. If one changes, update the others.
- Prefer precise, bounded claims ("can", "typically", "under this configuration") over universal ones, unless the source guarantees the universal.
- If a fact can't be verified, leave it out.

## 4. Quiz and game choices

A learner should have to know the answer, not spot it.

- **Keep choices about the same length.** The longest choice may be at most 1.5 times the shortest; choices within 15 characters of each other always pass. Aim for about 1.25. **(tested)**
- **Don't make the right answer habitually the longest.** Across all single-answer questions, the right answer may be the single longest choice in at most 40% of them. **(tested)**
- **Balance yes/no answers.** If the right answer starts with "Yes" or "No", at least one wrong answer starts the same way, with a wrong reason. **(tested)**
- **Match form and tone.** Same grammatical shape, similar specificity, similar hedging. Don't give only the right answer a qualifier ("usually", "under this contract") or only the wrong answers absolutes ("always", "never").
- **Write plausible wrong answers** from real misconceptions, never jokes or obviously absurd options.
- **One defensible answer.** A wrong answer must be wrong, not merely less complete. Check that no distractor is true in a common reading.
- **Put detail in the explanation**, not in the right choice. The explanation says why the answer is right and, where useful, why a tempting wrong answer is wrong.
- **No "all of the above" or "none of the above".**
- **Multi-select statements** follow the same length and tone rules, true and false alike.
- **Games follow the same rules**: Spot the Flaw reasons, Ring Balancer options and Bit Budget clock answers are balanced too. **(tested)**
- **Keep prompts stable.** `seed_content` updates questions in place keyed by prompt, so changing a prompt deletes the old question and learners' attempts on it. Change the choices and explanation freely; change a prompt only when the question itself must change.

## 5. Checklist before merging content

1. The item has a level, and the header, catalogue and topic agree.
2. Every fact is checked against a dated primary source in `sources.json`.
3. Wording, examples, numbers and structure are original; no five-word run matches a source.
4. No study book or course is named anywhere.
5. Calculations are worked twice and match across lesson, checks, quiz and games.
6. Quiz and game choices are balanced in length, tone and polarity.
7. `python manage.py test learn` passes.
