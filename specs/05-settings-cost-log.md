# Spec 05 — Settings, Cost Control & Log

> ספק 5 — הגדרות, עלות ויומן. מכסה FR-F1–F5 ו-FR-G1–G3.

**Status:** cross-cutting. Build last, but do not skip — FR-F4 is a blocking
requirement and FR-G2 is the product's built-in accuracy measure.
**Binding authority:** this file. Derived from `docs/06-prd.md` sections F and G.
**Also read before planning:** `specs/00-global-constraints.md`,
`docs/05-validation-gate-result.md`.

---

## Purpose

Two things that cross every other subsystem: keeping the automatic indexing
from spending money unasked, and recording what the product actually did.

## In scope

Provider and model configuration, API key storage, the cost meter, the monthly
spend cap, pause/resume, the operation log, and the release-rate metric.

## Out of scope

Tagging itself (spec 01 — this spec configures the provider interface spec 01
calls). The copy and delete operations (spec 04 — this spec records them).

---

## Requirements

### F · Settings and cost control

| # | Requirement |
|---|---|
| FR-F1 | The tagging provider sits behind a swappable interface. The provider and the model are configurable. |
| FR-F2 | The API key is stored locally and protected. It is never written to the catalog, the log, or any shareable file. |
| FR-F3 | A running cost meter: how many photos were tagged, how many tokens, and estimated cost — since installation and since the start of the month. |
| FR-F4 | **A monthly spend cap.** On reaching it, automatic indexing stops and the user is notified. Blocking requirement. |
| FR-F5 | Automatic indexing can be paused and resumed at any moment. |

### G · Log and metrics

| # | Requirement |
|---|---|
| FR-G1 | An operation log for every deletion: id, source path, signature, date, and the query that led to it. |
| FR-G2 | **Release-rate metric:** for each round, record how many items were released from the quarantine folder versus how many were deleted. This is the product's built-in accuracy measure. |
| FR-G3 | The log is human-readable and exportable. |

### Non-functional requirements that apply here

NFR-6 (catalog, log and key stored locally only).

---

## Acceptance criteria

| # | Criterion |
|---|---|
| AC-6 | On reaching the spend cap, indexing stops and a notification is shown. |
| S5-1 | A test asserts the API key does not appear in the catalog, the log, or any exported file. |
| S5-2 | The release-rate metric is written for a complete round and is readable afterwards. |
| S5-3 | Pausing and resuming automatic indexing takes effect immediately and does not corrupt an in-flight index. |

---

## Why FR-G2 matters more than it looks

The validation gate measured the pipeline successfully but **could not measure
accuracy on multi-object queries** — the manual ground truth was unreliable.
That risk was consciously carried into the PRD rather than re-tested.

FR-G2 is the answer to it. The release rate is an accuracy measurement that
collects itself from ordinary use: every item the user pulls out of quarantine
is a false positive, recorded automatically. Implement it properly and the open
risk closes on its own over a few rounds.

An implementation that logs deletions but skips the release count leaves the
project's one open risk permanently unmeasured.
