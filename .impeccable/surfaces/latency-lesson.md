# Latency lesson

Mode: Read, with interactive exercises. Route: `/concept/latency-throughput/`.

## Direction contract

THESIS: Let the learner vary rates and account for waiting work before using the equations. Extend the existing lesson layout.

OWN-WORLD: Preserve the current quest.css ruled white card stock, Archivo typography, cobalt controls, ink text, spacing tokens, and sidebar activities. DESIGN.md's older violet console palette is pre-existing drift; current CSS and the sd-02 lesson are visual authority.

STORY: Predict a five-minute backlog, change arrivals to clear it, distinguish steady-state concurrency from queue growth, then inspect the slow tail. Finish in the existing quiz.

FIRST VIEWPORT: Existing lesson title and objectives lead into the queue exercise. Labelled native sliders and explicit time-advance buttons sit above plain-language results. Mobile uses a single column.

FORM: Ordinary extension of the existing lesson page; no replacement visual world. No animation is needed to convey a manual time step. All examples retain useful text without JavaScript.

FINISH: Verify desktop and mobile rendering, browser interactions, model arithmetic and Django integration; independent finish review and documentation comparison preserve the incumbent system files.

## Verification

2026-09-28: 83 Django tests and 16 JavaScript model tests passed after collecting static assets. Browser checks covered queue growth/drain, reset, Little’s Law, percentile selection, keyboard input, reload, no-JavaScript fallback, and overflow at 1440px and 390px. Screenshots: `.impeccable/review/sd03-desktop.png` and `sd03-mobile.png`.

Independent finish review: **ship**, with no material findings in the inspected code and screenshots. Automated design detection could not run because its engine was unavailable; vexp verification could not connect to a project daemon. Browser preview used existing lesson data without writing to the application database.
