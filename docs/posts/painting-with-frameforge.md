---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-07-04"
title: "Painting with FrameForge"
subtitle: "178 trials to a vector reconstruction"
---

# Painting with FrameForge

*A reading of `frameforge-reconstruction-evolution-4k60.mp4` — sixty seconds,
178 frames, one picture assembled from nothing but primitives.*

The video does not show a drawing. It shows a **method**. A single raster
screenshot — 714×456 pixels of FrameForge primitives — is rebuilt, from
scratch, into pure vector geometry: rectangles, polygons, paths, filled
regions, layers. No pixels are pasted. Every mark in the final frame is a
FrameForge object that a validator can inspect and a renderer can re-emit at
any resolution. What you are watching is the same thing a painter does when
they block in a canvas before they render it: commit the structure first,
earn the detail last.

Two numbers frame the whole run. Frame 1 carries **39 elements**. Frame 178
carries **2,965**. Between them sit 176 trials — most of them wrong, most of
them thrown away — and the interesting part is not the count but the *order*
in which the picture earned its detail.

## The pacing is the argument

The clip is 60.0 seconds at 3840×2160, 60 fps — a hard 3,600 frames, verified
by `ffprobe` in the run report. But the 178 source frames are **not** given
equal time. The early ones are held for half a second each; the late ones flick
by in an eighth of that. Stitched into eight encoding segments, the on-screen
durations fall away steadily — **19.6s, 12.0s, 8.9s, 6.6s, 4.4s, 3.6s, 3.7s,
1.9s**.

That decay is deliberate, and it is the point. The foundation is slow because
the foundation is where the decisions live. The polish is fast because by then
the decisions are made and only the surface is moving. A timelapse that gave
every frame equal weight would lie about where the work actually is.

## Act I — Foundation (frames 1–13)

The opening is almost embarrassingly coarse. Big flat regions, snapped to a
grid, a handful of layers. By the first milestone — **frame 13** — the whole
image is down to **8 elements**. Fewer than it started with.

This is not regression. It is the underpainting. The reconstruction pipeline
begins by asking *what are the large, closed, stable regions in this picture?*
— the same question `detect_regions` answers in the FrameForge MCP workspace —
and quantizes the reference into a small number of filled blocks (the `c24`,
`c28`, `c48` suffixes in the frame names are colour-cluster counts). You cannot
render a face before you have found the head. Frame 13 is the head.

## Act II — Composition (frames 14–25)

Then detail arrives all at once. Between the layered foundation and the second
milestone — **frame 25** — the element count jumps from 8 to **1,171**. The
frame names read like a colourist's notebook: `r2c1`, `r4c3c075`,
`r2c5b050` — regions and crops, each dialled to a specific opacity, layered and
recombined. `v007-best`, `v017` — candidates picked and promoted.

This is the compose stage: arranging the blocked-in regions into a real
composition, cropping what matters, tuning transparency so overlapping fills
read correctly. It is fast in the video (it happens inside the first, longest
segment) but it is the most consequential act. Everything after it is
refinement of a structure that is now essentially fixed.

## Act III — Reconstruction (frames 26–115)

The long middle is patient, incremental version-bumping: `v14`, `v18`, `v21`
… into the sixties. Detail climbs without drama — frame 50 sits at **1,906**
elements, frame 90 at **1,983**. Paths get added at the bottom-left, opacity
sweeps run from 0.25 to 1.00, outline primitives come and go. Nothing here is a
breakthrough. This is the grind where a reconstruction is actually built:
one region, one path, one corrected colour at a time.

## Act IV — The restart at v90 (frames 116 onward)

The frame names carry a seam. Everything up to here is tagged `pre90`; then, at
milestone **frame 116**, the run switches to `post90` and the version counter
resets to a clean `v90` baseline. **115 of the 178 frames are `pre90`** — the
learning — and only **63 are `post90`** — the redo that used it.

This is the most honest moment in the whole sequence. The first eighty-odd
trials were not the answer; they were how the answer became knowable. Frame 116
re-approaches the picture with everything the earlier grind taught — filled
region primitives, the right cluster counts, the right layer order — and starts
again from a stronger footing. Real craft throws the first canvas away.

## Act V — Refinement, and the plateau (frames 116–178)

From v90 to the end the element count keeps climbing — frame 146 at **2,856**,
frame 172 at **2,965** — and then it stops climbing. Frame 178 also holds
**2,965**. The last stretch of the video adds almost no new geometry.

So what is still changing? The *quality* of the marks. Milestone **frame 172**
is `v146`, and back in the source trials that version is where **smooth paths**
land — jagged region boundaries resolved into clean curves. The final act is
not more detail; it is the same detail, drawn better. The count plateaus while
the fidelity is still rising. That gap — between "everything is present" and
"everything is right" — is exactly the gap that separates a finished picture
from a complete one.

The clip closes by holding the final frame for about half a second, and stops.

## The verification underneath

One thing the video cannot show you, but which is the reason any of it is
trustworthy: every one of those 2,965 vectors is checkable against the pixels
it claims to reproduce. FrameForge's reconstruction loop is not "trace it and
hope." It measures. `score_reconstruction` reports, as a number, how far the
drawn geometry sits from the reference's real edges; `compare_images` returns
NCC and RMSE against the source. The version bumps in the frame names are not
vanity — they are the audit trail of a metric being driven down.

This matters because the picture was assembled by a model, and **models always
produce some form of error** — omissions, a region misread, a colour off by a
cluster. Under this project's operating law, the absence of a verification
layer would be an architectural defect, not a cosmetic one. The reconstruction
survives that law precisely because the loop treats its own output as untrusted
and scores it against the pixels before promoting the next version. The
timelapse is the *visible* half of the process. The measurement is the half
that makes the visible half honest.

## What the sixty seconds actually teach

Painting with FrameForge is not drawing. It is a sequence of commitments,
ordered from most structural to most cosmetic:

1. **Find the regions** before you draw anything (frames 1–13).
2. **Compose and layer** them into a real arrangement (14–25).
3. **Grind the detail** in, version by version (26–115).
4. **Restart** from what the grind taught (116).
5. **Refine to fidelity** after the geometry is complete (117–178).
6. **Verify against the pixels** the entire way down.

The video slows where the decisions are and races where they are not, which is
the truest thing it says: the work of a reconstruction is nearly all in the
first act, and the beauty is nearly all in the last.

---

*Source: `frameforge-reconstruction-evolution-4k60.mp4` and its run report,
built by `tooling/create_reconstruction_evolution_video.py` from 178 trial
SVGs in `static/trials/`. Element counts and milestones cited above are read
directly from those frames. This is a descriptive reading of one reconstruction
run, not a general benchmark claim.*
