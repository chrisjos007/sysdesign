---
version: 1
slug: "learn-templates-learn-dashboard-html"
primary_target: "learn/templates/learn/dashboard.html"
related_targets: ["learn/templates/learn/base.html"]
---

## Scope

The dashboard (`learn/templates/learn/dashboard.html`) is the first surface of a whole-site redesign. It sets the world that every other template inherits: base shell, topic, chapter, concept, quiz, review, badges, the four games and auth. Visitor mode: **Operate** (notes pages lean Read).

## Audience and job

- **Learners:** logged-in interview preppers (the owner, public learners). They need to see what is due, where they are, and what to do next.
- **Recruiters:** they skim once.
- **Pain the owner named:** "all pages are very difficult to navigate".
- **What would feel wrong:** childish or cartoony, hard-to-read long notes, a generic "AI SaaS" look (dark + neon, gradients, glass).

## Direction contract

THESIS: The dashboard is a Leitner file drawer pulled open. Every concept is a ruled index card, filed in compartment 1–5 by its real SM-2 repetition count, and wrong answers send it back to 1. Topic tab dividers are the navigation. It refuses the category's dark XP dashboard with its course grid and neon meters.

OWN-WORLD:
- **Palette:** pale enamelled-steel ground; white ruled card stock with a red head rule and faint blue ruling; ink type; cobalt for actions and the current selection; index red only for "due"; six muted office card-stock colours, one per topic tab.
- **Type:** one family, Archivo. Condensed caps for tabs and labels, normal width for reading, tabular figures throughout.
- **Surfaces:** flat, with 1px edges, near-square card corners and angled tab tops.

STORY: The learner sees what's due and where they left off. They trust the filing system and act: they clear compartment 1, or they reopen their current card.

FIRST VIEWPORT:
- **Header:** a drawer-front header with a label-holder wordmark on the left and level, a ruled XP meter and the streak on the right.
- **Tab row:** 6 numbered topic tabs plus Review (red count) and Badges.
- **Main area:** a Continue card at index-card proportion (title about 1.75rem, primary cobalt "Open notes", secondary "Quiz") beside the Leitner box. The box has five numbered, patterned compartments with counts, and compartment 1 carries the red due count and the Review action.
- **Below:** the drawer contents, with topic rows of chapter cards stamped with their compartment.
- **Signature interaction:** clicking a compartment pulls its cards (filters the drawer in place).

FORM: The Leitner File (index-card cabinet + Leitner box), candidate 7 of 7 on the ordered list. Seed key c6e254fd. Raises:
- index-card 5:3 module grid, orthogonal builder wires (Man-Machine)
- numbered, patterned compartments (Cyclorama)
- numbered margin column for sequences (Origami)
- red = due only, tabular figures (Exposure Record)

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved

- **Dark theme:** it is out of scope for the first build.
- **Badge icons:** they are emoji stored in the DB. They render as typed monogram stamps instead, and the data is unchanged.
