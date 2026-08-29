# UX Decisions — Results Screen

**Date:** 29.08.2026 · **Status:** Decided in brainstorming session, unblocks `specs/03-server-ui.md`
**Scope:** The results/review screen (FR-D1–D6) and the app shell it sits in
(FR-H1–H8). Produced to close the open questions listed at the bottom of
`specs/03-server-ui.md`.
**Binding authority:** This file plus `specs/03-server-ui.md`. Read both
before planning that spec.

---

## 1. Navigation structure

Single-page, query-centric app. One main screen: search bar on top, results
grid below. Indexing status, settings (synonym dictionary, cost meter,
verification N, source/quarantine folder pickers), the operation log, and the
release list live in a side panel — never a separate screen you navigate away
to. The user is never taken off the query/results view to reach them.

## 2. Interface language

The query input field is always English-only, regardless of UI language —
this is fixed by the PRD and not negotiable in this doc.

The surrounding interface (labels, buttons, match reasons, settings copy) is
**user-selectable** between Hebrew and English, toggled from settings.
**Default on first launch: Hebrew.**

## 3. Indexing visibility

A persistent, thin status strip appears near the search bar whenever
background indexing is active — e.g. "1,840 / 2,550 indexed, ~4 min left" —
so the user always knows results may be drawn from a partial catalog. It
collapses away when indexing is idle or complete. Full detail (errors,
pause/resume per FR-F5) lives in the side panel.

## 4. Query → predicates → run

1. User types an English query.
2. The system extracts predicates and shows them as **editable chips**
   (remove an object, add a synonym) — this is always an explicit step,
   never skipped, even when results already exist from a previous run.
3. Adding a synonym on this screen **saves to the global dictionary**
   (FR-C3) — it isn't a this-run-only edit. The dictionary is also directly
   editable from settings, independent of running a query.
4. Two explicit actions run the query: **Run** (with verification) and
   **Run without verification** (FR-C8's raw-results path). Both are
   reachable from the same predicate-chip step.
5. Once results are showing, the predicate chips **remain visible and
   editable** above the grid. Editing them **never auto-reruns the query** —
   the user must click Run (or Run without verification) again explicitly.
   Re-running clears the current selection, with a warning if anything was
   selected.

## 5. Results grid

- **Layout:** infinite scroll, single ranked list — verified first, then by
  predicate count (FR-C6). No pagination.
- **Header row** above the grid (below the predicate chips) shows the live
  total, e.g. "1,240 matches · 47 certain (12/50 verified)" — visible before
  any scrolling, updating as verification progresses.
- **Match reason (FR-D2):** an always-visible caption strip on each
  thumbnail, e.g. "monitor (objects), code (caption)" — no hover or click
  needed to see why a photo matched.
- **Confidence (FR-D3):** a visual badge on the thumbnail distinguishes
  certain from borderline.

### Verification timing and selection (resolves a real conflict)

Clicking **Run** shows the full raw result set almost instantly, every photo
marked borderline. Each thumbnail's badge live-upgrades to certain as its
verification check completes — nothing is blocked waiting for verification.

This creates a hazard: if "certain" photos were simply pre-selected by
default, the selection would grow under the user's hands mid-review as
badges flip. Resolved as follows:

- **No automatic selection is ever applied based on a badge flip.** Selection
  only changes from a direct user action.
- **Individual select/deselect** always works in real time, regardless of
  verification state.
- **Bulk "select only certain"** is **disabled** while verification is in
  progress, showing a pending count (e.g. "select only certain
  (12/50 verified)"). It becomes clickable once verification finishes, and
  applies to whatever is certain at that moment.
- **"Select all" / "deselect all"** are unaffected by verification state,
  since they don't depend on confidence.
- **Open (see §9):** whether "select all" acts on the full result set or only
  the portion currently loaded by infinite scroll is unresolved.

### Enlarge / lightbox (FR-D5)

Enlarging a photo opens a lightbox: full image, match reason, confidence
badge, prev/next navigation (click or arrow keys) to step through results,
and a select/deselect control inline — no need to close and return to the
grid to act.

### Zero results / refine loop

If a query returns nothing, or the user wants to try different wording, the
predicate chips stay editable in place (§4.5) rather than sending the user
back to a blank query box.

## 6. Selection → quarantine copy

A persistent action bar shows the live counter (FR-D6: selected count + total
size) and a **"Copy N to quarantine"** button, enabled once at least one
photo is selected. Clicking it starts the copy **directly — no confirm
dialog** — because copying is non-destructive; originals are untouched
(FR-E1). The one destructive-action gate in the whole flow is the approval
step below, not this one.

## 7. Release semantics (clarifies the spec 03 / spec 04 boundary)

Deselecting a photo on the results screen — before it is ever copied to
quarantine — is a **session-only exclusion**. It leaves that photo out of
this round's copy and it **can resurface** on a future run of the same
query.

The permanent "released, never shown again for this query" record (FR-E11,
read by FR-C9) is created **only** when the user pulls a photo back out of
the quarantine folder afterward, outside the app. This screen never writes
that record — it is spec 04's mechanism, not spec 03's.

## 8. Return-and-approve moment

After copying to quarantine, the user leaves the app, reviews the quarantine
folder in the file explorer (FR-E6), and comes back. This step needed its
own defined place — it is a return from outside the app, not a scroll
position to relocate.

**Resolution:** the moment a batch is copied to quarantine, a **persistent
banner** appears near the top of the app — "N photos awaiting approval in
quarantine, copied [time]" — and stays visible across new queries and across
app restarts (FR-H7) until the user acts. It is also always reachable via a
**Quarantine entry in the side panel**, so it never depends on scroll
position or on the user remembering to check back.

Clicking the banner opens the approve/delete flow: final count (FR-E8), the
source-type deletion meaning (FR-E13), and an explicit confirm — this is the
flow's one true destructive-action gate.

Running a second query while a batch is still pending approval does not
block the new query; the banner persists alongside it.

---

## 9. Open, to resume

Unresolved items surfaced during this session that still need a decision
before (or during) planning `specs/03-server-ui.md`, `04-quarantine-delete.md`,
or `05-settings-cost-log.md`:

1. **"Select all" scope under infinite scroll.** Does it act on the entire
   result set, or only the portion already loaded by scrolling? Matters for
   large result sets (hundreds of matches).
2. **Multiple pending quarantine batches.** If the user runs a second query
   and copies another batch before approving the first, can two batches be
   pending at once? If so, how are they distinguished and listed in the side
   panel's Quarantine section — is approval per-batch or all-at-once?
3. **Side panel detailed layout.** Positioned as home for indexing detail,
   settings (dictionary editor, cost meter, verification N, folder pickers),
   operation log, release list, and Quarantine — but its internal structure
   (sections, ordering, drawer vs. fixed) was not designed.
4. **First-run onboarding flow.** Choosing the gallery folder and the
   quarantine folder (FR-H5, FR-A1, FR-E2) before any indexing starts —
   not walked through. Includes what invalid-path errors look like at setup
   time.
5. **Error-state visual treatment (FR-H8).** Agreed in-app, plain language,
   not a browser error page — but no concrete pattern chosen (toast, inline
   banner, modal) or how it differs for a transient error vs. one that
   blocks further action.
6. **Empty-results state.** The refine loop (§5) is decided, but the actual
   copy/visual shown when a query returns zero matches was not designed.
7. **Cost-cap-hit notification (FR-F4).** How the alert is surfaced in the
   UI when auto-indexing stops after hitting the monthly spend ceiling.
8. **Release list visibility and reset (FR-E12).** Confirmed to live
   somewhere in the side panel, but the list view itself — and the
   reset-all vs. reset-one-item interaction — was not designed.
