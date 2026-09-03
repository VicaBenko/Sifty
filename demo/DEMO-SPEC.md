# Demo Specification

> **Interactive Demo Application.** Shows, on real photos and multimodal zero-shot vectors,
> that the core idea works. The full production architecture follows `specs/`
> and `docs/14-clip-search-engine-upgrade.md`.

**Audience:** Technical & Professional. Shows the pipeline workflow surviving
contact with real image data — combining client-side Transformers.js CLIP embeddings
with high-certainty query predicate matching.

---

## The demo moment

Someone types an English description into a box, presses Run, and sees the
matching photos — each showing **why** it matched and **how confident** the
system is.

That is the whole demo. Nothing is deleted, copied, or written anywhere
outside `demo/`.

---

## The photo set

`demo/photos/` — 128 public images from the COCO 2017 dataset (see
`demo/photos/SOURCE.txt`). Everyday multi-object scenes: people, animals,
food, furniture, tableware, vehicles.

**Public images are used deliberately.** No private photos appear in the demo.

---

## Step 0 — build the catalog (run once, before writing any demo code)

Do not write a new tagging pipeline. Use the harness that already passed the
validation gate:

```
python validation/step1_sample.py --source demo/photos --workspace demo/_ws --count 128
python validation/step2_tag.py --workspace demo/_ws
```

Requires `ANTHROPIC_API_KEY` in the environment. Cost is roughly $0.13 for 128
photos; it takes a few minutes. `step2_tag.py` is resumable — a interruption
loses nothing.

This produces:

- `demo/_ws/catalog.json` — dict keyed by 4-digit photo id. Each entry:
  `objects` (list of strings), `caption`, `setting`, `is_screenshot`, `_tokens`.
- `demo/_ws/manifest.json` — list of `{id, thumb, source, filename}`. `thumb`
  is relative to `demo/_ws/`.
- `demo/_ws/thumbs/` — 384px JPEGs.

Verify the catalog has 128 entries before continuing.

---

## Build this

One Python file plus one HTML page, served by a local HTTP server. Standard
library only, plus the `anthropic` package already in
`validation/requirements.txt`. No framework, no build step.

### 1. Query → predicates

Input is free English text. Decompose it into predicates — objects that must
ALL be present — and expand each with synonyms.

One Anthropic API call per query does the extraction. Show the predicates in
the UI before results, and let them be edited.
`validation/queries.json` shows the synonym-group shape; reuse it.

If the call fails, fall back to splitting on commas and "and" and matching the
words literally. The demo must never hard-fail on a query.

### 2. Predicates → matches

A photo matches when EVERY predicate is satisfied by at least one of:

- an entry in its `objects` list — channel `objects`
- a word in its `caption` or `setting` — channel `caption`

Exact set intersection. Not similarity, no score threshold.

Record per matched photo which predicate was satisfied through which channel.
That record is the match reason, and it is the point of the demo.

### 3. Confidence

- **certain** — every predicate satisfied through the `objects` channel
- **borderline** — at least one predicate satisfied only through `caption`

No verification API pass in the demo. Label the two states honestly in the UI.

### 4. The page

Follow `docs/09-ux-decisions.md` where it is cheap:

- Single page: query box on top, results grid below.
- Header row above the grid with the live total: `"9 matches · 7 certain"`.
- Editable predicate chips between the query box and the grid, with an
  explicit **Run** button. Editing a chip never auto-runs.
- Every thumbnail carries an always-visible caption strip naming the matched
  objects and their channel: `cup (objects), table (caption)`.
- A clearly visible badge separating certain from borderline.
- Interface in Hebrew, per the UX decisions. Query stays English.

Out of scope: selection checkboxes, quarantine, deletion, indexing UI,
settings, side panel, infinite scroll.

### 5. Serving

`python demo/serve.py` starts a server bound to **127.0.0.1 only**, prints the
URL, serves the page and the thumbnails. Never bind 0.0.0.0 — this rule holds
even in throwaway code.

---

## Acceptance

| # | Criterion |
|---|---|
| D-1 | `python demo/serve.py` starts, prints a localhost URL, page loads. |
| D-2 | `a dog` returns 11 photos: 10 real dogs showing `dog (objects)`, plus a hot-dog-food photo correctly downgraded to `dog (caption)` / borderline — not falsely claimed as an exact object match. |
| D-3 | `a cup on a table` returns 6 photos whose reason names both predicates and their channels. |
| D-4 | A query with no matches shows a readable empty state, not a stack trace. |
| D-5 | Removing a predicate chip and pressing Run widens the result set. |
| D-6 | The server refuses connections from any address but localhost. |
| D-7 | Nothing in `demo/` writes to, moves, or deletes anything outside `demo/`. |

---

## Demo queries — measured against the real catalog

The catalog is built: 128 photos, 518 distinct objects, median 9 objects per
photo. These counts were measured against the actual tags, not estimated.

| Query | Matches | Why it is worth showing |
|---|---|---|
| `a dog` | 11 | Baseline: 10 real dogs, certain. The 11th is a hot-dog-food photo, correctly downgraded to borderline via the caption channel instead of falsely claimed as an exact object match — a live demonstration of the confidence system catching a false friend. |
| `a clock` | 10 | **The important one.** A small, non-dominant object — precisely the case where embedding search collapses. |
| `a cat` | 4 | A second clean single-object case. |
| `a cup on a table` | 6 | Two objects bound together. The everyday case. |
| `a bowl of food on a table` | 3 | Multi-predicate, including matches satisfied through the caption channel — shows both confidence levels in one screen. |

Re-measured after fixing whole-word matching (2026-08-29): matching used to
test predicate terms via substring containment, so `a cat` picked up baseball
"catcher" photos and captions containing "location"/"scattered" — 8 matches,
only 4 real cats. Terms now match as whole words (`cat` matches `cat` and
`cats`, never `catcher`), which also dropped `a bowl of food on a table`
from 4 to 3. `a cup on a table` was unaffected.

Re-measured again after fixing head-word matching (2026-08-29): whole-word
matching still matched a term against *any* word inside a multi-word object
phrase, so `a dog` counted a hot-dog-food photo (tagged `hot dog`, `hot dog
bun`) as an exact object match. The objects channel now matches only the
full phrase or its last word (the head noun) — `cup` matches `coffee cup`,
`cat` no longer matches `cat toy` — plus a small lexical exception list for
compounds where the head noun isn't the referent (`hot dog`, `corn dog`,
etc.). `a dog` is still 11 total, but the hot-dog photo now surfaces through
the caption channel (its caption literally says "hot dogs") at borderline
confidence instead of falsely claimed as `dog (objects)`/certain — see the
reworded D-2 above. The other four queries were unaffected by this change.
See `demo/test_matching.py` for the regression tests.

Avoid in the demo: `a laptop` (1 match), `a cup and a bowl on a table` (1).
Three-predicate queries are thin at 128 photos. That is a property of the demo
set size, not of the architecture — the validation run over 500 real photos is
where multi-object behaviour was actually measured, and it is written up in
`docs/05-validation-gate-result.md`.

The talking point behind rows 2 and 4: CLIP-style embedding search drops from
99.6% to 52-72% precision on exactly these cases — small objects, and objects
that must be bound together. Sources are in
`docs/02-decision-memo-001-architecture.md`, decision 2. This architecture
exists to answer that, and the demo is the answer running.

---

# Phase 2 — closing the loop (only after Phase 1 works)

**Do not start this until every acceptance criterion above passes.** Phase 1
standing on its own is the safety net. Phase 2 is additive.

## Why

The product's promise is cleaning a gallery, and Phase 1 stops at finding
photos. The distinctive design work in this project — copy never move, the
quarantine manifest, the approval gate — lives in the half that Phase 1 does
not show. This phase makes the full user journey run.

## Why it is safe to demo deletion here

`demo/photos/` holds public COCO images, stored locally, not synced to
anything. Deleting them costs nothing and touches no personal data. Keep a
pristine copy at `demo/photos_master/` and have `demo/reset.py` restore
`demo/photos/` from it, so the demo can be run repeatedly.

This is the ONLY reason deletion is demonstrable at all. The production rules
in `specs/04-quarantine-delete.md` are unchanged and are not exercised here.

## Requirements

| # | Requirement |
|---|---|
| P2-1 | Each result carries a checkbox. Certain results are pre-selected; borderline results are not (per `docs/09-ux-decisions.md`). |
| P2-2 | An action bar shows the live selected count and total size, with a "Copy N to quarantine" button. |
| P2-3 | Copying writes to `demo/quarantine/` — **copy, never move.** Originals stay in `demo/photos/`. |
| P2-4 | A manifest at `demo/quarantine/manifest.json` maps each copy to its source path and file signature. |
| P2-5 | The quarantine path is verified to be outside the photo folder; the app refuses otherwise. |
| P2-6 | After copying, a persistent banner shows "N photos awaiting approval", surviving new queries and restarts. |
| P2-7 | Clicking the banner opens the approval screen: final count, an explicit confirm, and a plain statement of what deletion means for this source type (a local folder — deletion is local only). |
| P2-8 | On approval, delete from `demo/photos/` **only** those sources whose copy still exists in `demo/quarantine/`, per the manifest. |
| P2-9 | An operation log at `demo/operation-log.json` records every deletion: id, source path, date, and the query that led to it. |
| P2-10 | The round's release rate is recorded: how many items were pulled out of quarantine versus how many were deleted. |

## Acceptance

| # | Criterion |
|---|---|
| D-8 | A full round runs: query, select, copy, review the folder in the file explorer, approve, delete. |
| D-9 | **A photo removed from `demo/quarantine/` before approval still exists in `demo/photos/` afterwards.** This is AC-3 from the PRD, demonstrated live. |
| D-10 | No code path moves a file out of `demo/photos/`. Copy and delete-in-place only. |
| D-11 | `python demo/reset.py` restores the photo set so the demo can be run again. |

## The moment worth rehearsing

Pull two photos out of the quarantine folder in the file explorer, in front of
the audience, before approving. Then approve. Then show that those two are
still in the photo folder and the rest are gone.

That is AC-3 — the product's central safety promise — proven in ten seconds,
by hand, on screen. It is the strongest thing in the whole demo.
