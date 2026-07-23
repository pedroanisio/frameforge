---
name: typeface-and-colour
description: >-
  Apply the classical craft of the page — typography, colour, and arrangement —
  when designing or reviewing any visual document: decks, posters, books,
  letters, diagrams, brand palettes, or a FrameForge SDK client. Use when
  choosing or pairing typefaces, building a colour palette, setting body text
  (measure, leading, scale), laying out or balancing a page/spread, or judging a
  design for legibility, hierarchy, and repose. Also use to critique an existing
  design against measurable gates (WCAG tone contrast, 45–75ch measure,
  one-step hierarchy, the grey test, palette closure, steelyard balance).
  Distilled from the in-repo book "The Letter & the Hue" (Johnston 1906,
  Chevreul 1839, Batchelder/Ross 1904); the rendered artifact lives at
  out/typeface-and-colour/.
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (1M context) via Claude Code"
  date: "2026-07-02"
---

# Typeface & Colour — the craft of the page

A working grammar for designing and auditing visual documents. It is the
operational distillation of the book **_The Letter & the Hue_** (this repo,
`out/typeface-and-colour/` — 93 pages, 55 drawn plates, composed with the
FrameForge SDK), which itself reduces three primary sources to a short table of
laws:

| Craft | Source | Governs |
|---|---|---|
| **The letter** | Edward Johnston, _Writing & Illuminating, & Lettering_ (1906) | typeface choice, weight, scale, spacing, measure, margins |
| **The hue** | M. E. Chevreul, _De la loi du contraste simultané des couleurs_ (1839) | palette, contrast, harmony, legibility on grounds |
| **The arrangement** | E. A. Batchelder, _The Principles of Design_ (1904), after Denman W. Ross | balance, rhythm, harmony, the grid |

Full sourced catalogue with primary quotes and the plate index is in
[`canon.md`](canon.md). This file is the procedure and the audit.

---

## The one rule that orders every decision

> **Structure in tone before hue; readableness before style.**

Chevreul's division of labour — *hue for character, tone for structure* — and
Johnston's ranked table — *readableness first, character last* — are the same
rule stated from two crafts. Everything below is dosage.

Two consequences you will use constantly:

- **The grey test.** Drain a design of all hue. If its hierarchy still reads in
  greyscale, it was built in tone and will survive dim light, distance, poor
  print, projection, and the ~1 in 12 men whose red and green are neighbours.
  If it dissolves into one mass, it trusted hue alone — a defect, not a taste.
- **No element is seen alone.** Every colour is tinted by its neighbour toward
  the neighbour's complement; every letter is a figure that obeys the law of its
  ground. Design the *neighbourhood*, never the swatch in isolation.

---

## The four moves

Run these in order. Later moves assume the earlier ones are fixed.

### 1 · Structure the field in tone

Everything on a page pulls at the eye: **darker, larger, more eccentric = a
harder pull** (Batchelder). A composition is *balanced* when every pull is
answered, *unbalanced* when one goes unanswered.

- Assign a **tone hierarchy first**: what is display/heaviest, what is text,
  what is margin/rest. A page's blacks are its display sizes and bolds; its
  greys are the text; its whites are the margins.
- **Mass tones; do not scatter them.** The same quantity of black reads as one
  quiet statement when massed and as noise when scattered. If you bold
  everything, you have told the reader nothing about where to begin.
- Balance by the **steelyard**, not by centring. Unequal spots balance like a
  man and a boy on a see-saw: attraction × distance must agree, so the large
  element sits *near* the axis and the small one *far* from it. Centring is only
  the special case where the two arms are equal. Asymmetry and symmetry are two
  solutions of one equation — weighed vs. mirrored — not rival styles.

### 2 · Close the palette

Do not "pick colours." Build a **closed palette with assigned duties** — a type
family for colour, whose value is not the beauty of its members but the
impossibility of strangers.

| Role | Rule | Rough area |
|---|---|---|
| **Ground** | one paper, warm **or** cool — never two | ~62 % |
| **Ink** | one near-black; pure `#000000` is harsher than any real ink | (part of 30 %) |
| **Quiet steps** | greys drawn from the ink's own scale, for the second rank | (part of 30 %) |
| **Accent** | one hue with one duty (e.g. structure & emphasis) | ~8 % |

- **Expansion rule** — need a second accent? Take the first accent's
  complement, *subdued* (never at equal strength/area — complementaries at full
  power and equal area vibrate), or a distant tone of the ink. A colour from
  outside the set must *mean* something, exactly as an italic does.
- Pick the harmony deliberately (see the harmony table below). Analogy soothes
  and risks sleep; contrast wakes and risks noise. Every workable palette is a
  treaty between the two.
- **Neutrals do specific work:** white lends a colour depth (darkens it by
  contrast), black lends brilliance but eats deep tones, grey flatters
  everything and competes with nothing — which is why proofing rooms are grey.

### 3 · Set the type

Read a typeface by its **tool**: stress (axis) and serif first tell you its
class, era, and most of its manners (see the class table below). Then:

- **Choose on x-height, not point size.** Point size measures the body, not the
  letters; x-height is what the eye reads as "big." Two faces at the same
  nominal size can differ wildly on the page.
- **Size from a modular scale.** Pick a base (~11.5) and a ratio; every size is
  a power of the ratio. `1.2` quiet/bookish · `1.25` assertive · `1.333`
  editorial · `1.5` poster. Scale is uniformity applied to size.
- **Move hierarchy one step at a time.** Regular against semibold reads as
  structure; regular against black reads as noise. **Never synthesise** — a
  slanted roman is not an italic, a smeared regular is not a bold; the eye
  convicts both.
- **Set the measure to 45–75 characters per line.** Measure and leading are one
  system: widen the line and you *must* open the leading; a wide page wants
  columns or larger type — never merely longer lines.
- **Space for even colour.** Capitals want air (track them); small letters want
  none; the word-space is a letter too. Test by squinting: the text block should
  read as one even grey — dark knots are crowding, white rivers are excess.
- **Margins: the opening (spread), not the page, is the unit.** Classical canon
  — inner 1½ + 1½, top 2, outer 3, foot 4: foot widest (readers hold the foot),
  gutter halves, top tightens (the geometric centre appears to sag). A screen's
  safe-areas rediscover the same clauses.

### 4 · Let colour meet the letter — then verify

Where type sits on colour, the two crafts shake hands: **legibility is tone
contrast between figure and ground.** Hue contrast alone adds vibration but *no*
legibility (red on green can vibrate at 1.4:1 and be unreadable).

- Choose text and ground as **tones first** — dark-on-light or light-on-dark,
  well separated in the scale — and only then admit hue.
- **Accent is information.** Reserve one hue for structure (headings, initials,
  emphasis) and use it sparingly enough that every appearance carries meaning —
  the manuscript rubricator's whole theory of accent colour.
- **Never encode rank by hue alone.** Hue has no natural order and not every eye
  receives it. Carry rank on tone + position + label; let hue sing *over* a
  structure that already stands without it.

---

## The audit — measurable gates

This is the verification layer (CLAUDE.md, PALS's Law): a design is not "done"
because it looks done. Run every gate; each has an objective pass condition.

| Gate | Test | Passes when |
|---|---|---|
| **Grey test** | render/convert to greyscale | hierarchy still reads; nothing dissolves into one mass |
| **Body legibility** | tone-contrast ratio, text vs. ground (WCAG 2.x relative luminance) | **≥ 4.5:1** for body text (≥ 3:1 for large/display) |
| **Hue-only rank** | is any ranking/legend carried only by colour? | no — rank also on tone, position, or label |
| **Measure** | characters per line in body copy | **45–75** |
| **Measure↔leading** | wide measure with tight leading? | no — leading opens as measure widens |
| **Hierarchy step** | adjacent type levels | separated by **one** scale/weight step, not a leap |
| **Synthesis** | any faux-italic / faux-bold / stretched face | none — real family members only |
| **Scale discipline** | every type & spacing size | traces to the modular scale / a shared module |
| **Palette closure** | count distinct hues with duties | closed set; any outsider carries meaning |
| **Complementary dose** | complementary pair at full strength + equal area? | no — one rules, the other visits (subdued or a line) |
| **Balance** | is every strong attraction answered? | yes — the field is at repose (steelyard, not luck) |
| **Rhythm** | recurrence of baselines/measures/shapes | governed change — neither monotony nor noise |

Report failures plainly with the number that failed (e.g. "caption/ground is
3.1:1 — below the 4.5:1 body floor"). Fix the defect; do not attribute it.

---

## Enacting it in FrameForge

This repo renders with the FrameForge SDK/MCP; the book itself is a worked
example — read `out/typeface-and-colour/` (PDF + per-page SVG/PNG) as the
reference build, and see
[`frameforge-mcp-docker`](https://github.com/pedroanisio/frameforge/blob/main/skills/frameforge-mcp-docker/SKILL.md)
for the runtime. (Absolute, not `../`: this file is mirrored verbatim into
`plugin/skills/`, where that sibling does not exist — a sparse plugin install
fetches only `plugin/`.)

| Move | SDK enactment |
|---|---|
| Closed palette | define ground/ink/accent/greys **once** as named constants; reuse them — never inline ad-hoc hex |
| Tone structure | set weight/size/grey by role from the scale; keep pure `#000` out of body ink |
| Modular scale | compute sizes as `base * ratio ** step`; drive all headings/body/caption from it |
| Grid & balance | place the heavy element near the column axis, small labels far out; margins as the frame |
| Verify | render to PNG (not YAML) and check the pixels — `compare_images` for tone contrast, the grey test by eye on the raster; fonts resolve only in the font-rich runtime |

**Font reality:** display type may collapse to one generic sans in a fontless
raster path — draw hero lettering as vectors, or render in the font-rich
frameforge image. Verify against the rendered pixels, never the YAML alone.

---

## Quick reference

### The six harmonies (Chevreul)

| # | Harmony | Recipe | Fails as | Reach for it when |
|---|---|---|---|---|
| 1 | Analogy · of scale | tones of one scale, in order (monochrome) | sleep | safest option; engravings, washes, dark-mode UI |
| 2 | Analogy · of hues | like tones of neighbouring scales | dullness | calm, natural palettes (foliage) |
| 3 | Analogy · of a dominant light | many colours under one tint | muddiness | the tinted overlay, sepia archive, brand wash |
| 4 | Contrast · of scale | two distant tones of one scale | — (robust) | the safe strong statement; greys/prints/every eye |
| 5 | Contrast · of hues | neighbouring scales, unequal in depth | clash | subtle energy — subordinate one, don't balance |
| 6 | Contrast · of colours | complementaries (opposites) | noise | the loudest chord — one as field, one as event |

### Type classes (read the tool)

| Class | Stress / contrast / serif | Character · use |
|---|---|---|
| Garalde (old-style) | oblique stress, moderate contrast, bracketed serifs | the book face; 500 years of text service |
| Didone (modern) | vertical stress, extreme contrast, flat serifs | display brilliance; dissolves at small sizes |
| Grotesque / neo-grotesque | serif removed, near-flat contrast, closed apertures | neutral interface default; says little by design |
| Humanist sans | the pen's skeleton without serifs, open apertures | humane, readable sans |
| Geometric sans | compass & rule; circle O, single-storey forms | constructed, cool |
| Monospace | one advance width for every glyph | data, code, tables, figures — not prose |

### Numbers to remember

- Body measure **45–75 ch**; hierarchy moves **one step**.
- Scale ratios: **1.2 / 1.25 / 1.333 / 1.5**.
- Margin canon (opening): **inner 1½+1½ · top 2 · outer 3 · foot 4**.
- Body tone contrast **≥ 4.5:1**; large text **≥ 3:1**.
- Palette proportion ~ **ground 62 % · text&structure 30 % · accent 8 %**.
- Red–green colour-vision deficiency ≈ **8 % of men** — never rank by hue alone.

---

## The whole book in four lines

> A letter is a skeleton given voice by a tool.
> A colour is a note played by its neighbours.
> An arrangement is a truce among attractions.
> Everything else in design is dosage.

When in doubt, drop back to move 1: fix the structure in tone, and let the hue
follow — for no letter stands on nothing.
