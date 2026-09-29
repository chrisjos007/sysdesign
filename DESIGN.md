---
name: SysDesign Quest
description: Gamified system design study app. Dark console surfaces with electric violet and cyan signals.
colors:
  ink: "#0f0f1a"
  panel: "#1a1a2e"
  signal-violet: "#8b5cf6"
  signal-cyan: "#06b6d4"
  text-primary: "#f1f5f9"
  text-strong: "#ffffff"
  text-body: "#cbd5e1"
  text-muted: "#94a3b8"
  text-faint: "#64748b"
  border: "#334155"
  hairline: "#1e293b"
  success: "#34d399"
  danger: "#f87171"
  reward: "#fcd34d"
typography:
  headline:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: "2rem"
  title:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: "1.75rem"
  body:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.625
  body-small:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: "1.25rem"
  label:
    fontFamily: "ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: "1rem"
    letterSpacing: "0.025em"
rounded:
  sm: "0.25rem"
  md: "0.5rem"
  lg: "0.75rem"
  full: "9999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "24px"
  section: "40px"
components:
  button-primary:
    backgroundColor: "{colors.signal-violet}"
    textColor: "{colors.text-strong}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  button-review:
    backgroundColor: "{colors.signal-cyan}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  button-pill-outline:
    textColor: "{colors.signal-violet}"
    rounded: "{rounded.full}"
    padding: "8px 16px"
  button-pill-outline-hover:
    backgroundColor: "{colors.signal-violet}"
    textColor: "{colors.text-strong}"
  card:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.lg}"
    padding: "20px"
  tile-link:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.lg}"
    padding: "16px"
  input:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
  badge-chip:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.full}"
    padding: "4px 12px"
  nav:
    backgroundColor: "{colors.panel}"
    padding: "12px 24px"
---

# Design System: SysDesign Quest

## Overview

**Creative North Star: "The Night Shift Console"**

SysDesign Quest looks like a console for studying late at night. Near-black ink surfaces keep the room dark, so the screen doesn't glare during long sessions. Against that darkness, two electric signals (violet and cyan) light up only where something is happening: progress being made, an action to take, a review waiting. The interface stays quiet and the signals carry the energy.

The layout is dense and practical. Content runs the full width of the viewport inside generous side gutters. Panels are flat, slightly lifted slabs separated by hairline borders rather than shadows. Hierarchy comes from weight and value more than size: bold white headings, slate body copy, and small uppercase labels that name each section.

The owner has rejected three parts of the incumbent look. Future work should replace them, not extend them: emoji used as icons, the violet-to-cyan gradient on progress bars, and the lack of a chosen typeface (everything currently falls back to the system sans stack).

**Key Characteristics:**
- Near-black, slightly blue-violet ink canvas with one lighter panel tone for cards and navigation.
- Two signal colors with fixed jobs: violet means act and progress, cyan means review and look deeper.
- Flat surfaces; depth comes from tone and 1px borders, never drop shadows.
- Small uppercase labels title sections instead of large headings.
- Semantic feedback (green correct, red wrong, amber reward) shown as tinted, translucent slabs.

## Colors

The palette is a dark, cool neutral base with two saturated signals, plus a small semantic set for feedback.

### Primary
- **Signal Violet** (#8b5cf6): the action and progress color. Used for the primary submit buttons (quiz, retake), outline pill buttons (View Notes, Study mode), the brand wordmark, hover borders on tiles, chapter mastery bars, the quiz progress bar, and XP totals. When something moves the learner forward, it's violet.

### Secondary
- **Signal Cyan** (#06b6d4): the review and exploration color. Used for Daily Review buttons (with ink text, not white), "Select all that apply" hints, "Click to know more" deep-dive toggles and their left rule, Study mode card headings, inline code, Markdown links, and hover borders on the Matching and Ordering tiles.

### Neutral
- **Ink** (#0f0f1a): the page canvas, and the recessed fill for inputs and code blocks. Also the text color on cyan buttons.
- **Panel** (#1a1a2e): cards, the nav bar, the tile grid and badge chips. The one lifted surface tone.
- **Text Primary** (#f1f5f9): default body text on ink.
- **Text Strong** (#ffffff): headings inside notes and Markdown, strong emphasis, and text on violet buttons.
- **Text Body** (#cbd5e1): long-form notes copy, summaries and secondary buttons.
- **Text Muted** (#94a3b8): metadata lines, back links, tile descriptions, explanations.
- **Text Faint** (#64748b): uppercase section labels, "unlocks at" hints, counters. At about 3.9:1 on ink it fails AA for small text; see Do's and Don'ts.
- **Border** (#334155): default 1px borders on tiles, answer rows, inputs and code blocks.
- **Hairline** (#1e293b): the quieter border on panels and the nav, and the empty track of progress bars.

### Tertiary (semantic feedback)
- **Success Green** (#34d399): correct-answer text and "done" states. Its slab is emerald-950 at 40% with an emerald-700 border.
- **Danger Red** (#f87171): wrong answers, logout hover, the remove-component ×. Its slab is red-950 at 40% with a red-700 border.
- **Reward Amber** (#fcd34d): badges earned, flash messages. Its slab is amber-900/950 at 30–40% with an amber-700 border.

### Named Rules
**The Two Signals Rule.** Violet means *act or progress*; cyan means *review or look deeper*. Never swap them. Never add a third brand hue: semantic green, red and amber are for feedback only and never decorate.

**The Dark Room Rule.** Surfaces stay in the ink-to-panel range. Nothing lighter than Panel is ever used as a surface fill. Light comes only from text and signals.

## Typography

**Body Font:** system sans stack (ui-sans-serif, system-ui, sans-serif). No typeface is loaded.

**Character:** neutral and native, with hierarchy made from weight (700 bold / 600 semibold / 400) and value (white → slate-300 → slate-400 → slate-500) rather than a wide size range. The owner has named the missing typeface as a gap: a deliberate face (or pairing) should replace the system fallback in future work.

### Hierarchy
- **Headline** (700, 1.5rem / 2rem): page titles (concept name, dashboard level). The biggest type in the app apart from the one-off 🏁 completion moment.
- **Title** (700, 1.125rem / 1.75rem): topic headings on the dashboard, quiz result headlines.
- **Body** (400, 1rem, relaxed 1.625): notes sections and question prompts. Notes run the full width of the panel today, with no measure cap.
- **Body Small** (400, 0.875rem): nav links, summaries, explanations, tile titles in metadata rows.
- **Label** (600, 0.75rem, 0.025em tracking, UPPERCASE): section labels ("PLAY TO LEARN", tier names, "NOTES · source"). Also used unbolded for counts and hints.

### Named Rules
**The Weight-Not-Size Rule.** Hierarchy steps through weight and text value before size. New screens stay within the five roles above. No display sizes are added unless a deliberate typographic redesign introduces them.

## Layout

The page is full-width, not centered in a container. `main` has 24px side gutters on phones, 40px from 640px and 64px from 1024px, with 32px vertical padding. The nav is a single row: wordmark on the left, links and user controls on the right. It doesn't collapse on small screens today.

Content stacks vertically in panels. Tile collections (chapter grids, Play to learn) use a one-column grid that becomes two columns at 640px, with 12px gaps. Spacing works on a 4px base, mostly 12px gaps, 16–24px panel padding and 40px between dashboard topic groups. Density is comfortable-to-dense, suited to scanning progress.

The Architecture Builder uses an absolutely positioned canvas with an SVG wire layer. The games currently rely on HTML5 drag-and-drop and mouse clicks. PRODUCT.md requires every activity to work on phones, so touch interactions are an open layout debt.

## Elevation & Depth

The system is flat. Depth comes from tone (ink canvas → panel slab) and 1px borders (hairline for resting panels, border-slate-700 for interactive tiles). There are no ambient drop shadows. The only ring is a 2px violet halo at 33% alpha on a selected Architecture Builder component. Disabled or locked items are recessed by fading them to 60% opacity on a slate-900/50 fill, rather than by being shaded.

### Named Rules
**The No-Shadow Rule.** Separate surfaces with tone and borders, never drop shadows. Selection and focus appear as a violet border or ring, not as elevation.

## Shapes

Corners are soft but not bubbly:
- 0.75rem (rounded-xl) on panels and tiles
- 0.5rem (rounded-lg) on buttons, answer rows, inputs and code blocks
- 0.25rem on inline code
- fully rounded pills for badge chips, secondary action buttons (View Notes, Study mode, Read aloud, the Unlock toggle) and progress bar tracks

Borders are always 1px solid, except the dashed 2px drop slots in the Matching game and the 2px cyan left rule on deep dives.

## Components

### Buttons
Buttons read as confident but compact: solid for the one main action, pill outlines for secondary tools.
- **Shape:** gently rounded (0.5rem) for solid buttons, fully rounded pills for outline buttons.
- **Primary:** solid Signal Violet with white semibold text, 10px × 20px padding. Used for Submit Answer and Retake Quiz.
- **Review:** solid Signal Cyan with ink text, the same geometry. Used for review-queue actions and the dashboard's "N reviews due".
- **Hover:** solid buttons drop to 90% opacity. Outline pills fill with their signal color and turn their text white.
- **Pill Outline:** 1px Signal Violet border and violet text, 8px × 16px padding, semibold. The neutral variant uses a slate-700 border and slate-300 text, turning cyan on hover.
- **Text Buttons:** Back/Next in Study mode are plain text links (slate-400 → violet, or violet at 80% on hover).

### Chips
- **Badge chip:** panel fill, 1px slate-700 border, fully rounded, 4px × 12px, small text with the badge icon and name.
- **Builder component chip:** ink fill, 1px slate-600 border, 0.5rem corners, no-wrap label. When selected it gets a violet border and a violet halo.

### Cards / Containers
- **Corner Style:** 0.75rem.
- **Background:** Panel (#1a1a2e) on Ink.
- **Shadow Strategy:** none; see Elevation & Depth.
- **Border:** 1px hairline (#1e293b) on static panels, 1px slate-700 on clickable tiles.
- **Internal Padding:** 16px on tiles, 20px on content panels, 24px on the dashboard hero.
- **Tile hover:** the border becomes violet (or cyan for Matching and Ordering tiles). Locked tiles are faded and marked with a lock.

### Inputs / Fields
- **Style:** ink fill, 1px slate-700 border, 0.5rem corners, 8px × 12px padding, slate-100 text, full width.
- **Focus:** the browser outline is removed and the border becomes Signal Violet. There is no ring, so this focus signal is weak.
- **Answer rows (quiz):** a label row with a 1px slate-700 border, 0.5rem corners and 12px padding, holding the native radio or checkbox tinted violet. The border turns violet on hover.

### Navigation
The nav is a panel-colored bar with a hairline bottom border and 12px × 24px padding. The wordmark is bold xl violet. Links are small text that turns violet on hover, with no active-page state. The username is muted, and Logout turns red on hover. The superuser Unlock toggle is a small pill: slate at rest, emerald when active.

### Progress Bar (signature)
The recurring "quest" meter: a fully rounded slate-800 track with a fill. The fill is solid violet for chapter mastery and quiz progress, and currently a violet→cyan gradient for XP and Study mode (a rejected pattern). Heights are 8–12px on the dashboard and 6px on quizzes.

### Feedback Slab
After an answer, a tinted, translucent panel appears: an emerald or red slab at 40% with a matching 700 border, 0.75rem corners and 20px padding. It carries a bold headline with the XP delta, the correct answer, the explanation, and any level-up (violet) or badge (amber) lines.

## Do's and Don'ts

### Do:
- **Do** keep every surface in the Ink (#0f0f1a) → Panel (#1a1a2e) range and separate layers with 1px borders (#1e293b resting, #334155 interactive).
- **Do** use Signal Violet (#8b5cf6) for acting and progressing, and Signal Cyan (#06b6d4) for review, deep dives and code (the Two Signals Rule).
- **Do** give cyan buttons ink text (#0f0f1a) and violet buttons white text.
- **Do** title sections with the uppercase 0.75rem / 600 / 0.025em label rather than a larger heading.
- **Do** show state with border color (violet hover or selection, emerald/red feedback), not with shadows.
- **Do** raise small metadata text above Text Faint (#64748b) when it carries information a learner needs. At 0.75rem it fails WCAG AA on ink.
- **Do** make white text on violet buttons at least 18.66px bold (≈4.1:1 contrast), or darken the fill, when the label must meet AA at small sizes.

### Don't:
- **Don't** use emoji as icons for buttons, tiles or section labels (📖, 🧠, 🏗️, 🧩). The owner has rejected this; use a consistent icon set or plain labels.
- **Don't** fill progress bars with a violet→cyan gradient. Use a single solid signal color per meter.
- **Don't** ship new screens that rely on the default system font as a design choice. The missing typeface is a known gap to fill deliberately.
- **Don't** add drop shadows or glows to create depth (the No-Shadow Rule).
- **Don't** introduce a third brand hue or use green, red or amber decoratively. They are reserved for correct, wrong and reward feedback.
- **Don't** use any surface fill lighter than Panel (the Dark Room Rule).
