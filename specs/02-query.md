# Spec 02 — Query Engine

> ספק 2 — מנוע שאילתה. מכסה FR-C1–C9.

**Status:** ready to plan once spec 01 is built.
**Binding authority:** this file. Derived from `docs/06-prd.md` section C.
**Also read before planning:** `specs/00-global-constraints.md`,
`docs/02-decision-memo-001-architecture.md` decision 2.

---

## Purpose

Answer a free-text English query against the catalog built by spec 01. A query
is an exact set intersection over the object table plus full-text over caption
and setting — **not** vector similarity.

## The reason this subsystem exists

The obvious approach is CLIP/SigLIP embeddings. It does not work for this
product. Such models do not bind objects together: when a query mentions a
small or non-primary object, accuracy drops from 99.6% to 52–72%, **and it does
not improve with larger models.** The structured-tag architecture exists
specifically to route around this. Sources are in decision memo 001, decision 2.

Do not replace the matching strategy with an embedding search.

## In scope

Query input, predicate extraction, synonym expansion, matching, the verification
pass, ranking, and the released-photo exclusion.

## Out of scope

Everything about how results are displayed (spec 03). Indexing (spec 01).
Quarantine and release recording (spec 04) — this engine reads the release
record, it does not write it.

---

## Requirements

| # | Requirement |
|---|---|
| FR-C1 | A free-text input field in English. |
| FR-C2 | The system decomposes the query into predicates — objects that must all be present. |
| FR-C3 | Each predicate is expanded with synonyms from a dictionary the user can edit. |
| FR-C4 | A match occurs when every predicate is satisfied either by the object list or by the caption/setting text. |
| FR-C5 | A verification pass runs on the top N candidates — a focused yes/no check. N is configurable, default 50. |
| FR-C6 | Results are ranked: verified first, then by how many predicates were satisfied. |
| FR-C7 | **The user can see and edit the extracted predicates before the query runs** — remove an object, add a synonym. |
| FR-C8 | The verification pass can be skipped to see raw results. |
| FR-C9 | Photos previously released for the same query are not shown (see FR-E11). |

### Non-functional requirements that apply here

NFR-3 (separable from the UI, testable headless) · NFR-4 (**under 1 second on a
50,000-photo catalog, excluding verification**).

---

## Acceptance criteria

| # | Criterion |
|---|---|
| AC-2 | A query returns in under one second, and every result carries a reason and a confidence level. |
| AC-5 | Re-running an identical query does not show photos released in the previous round. |
| S2-1 | Matching is verifiably set intersection: a test asserts that a photo missing any one predicate is not returned. |
| S2-2 | The query engine is exercised end to end without a UI. |

---

## What each result must carry

The engine returns, per photo, not just a match but the material spec 03 needs
to display:

- **which** query objects were found in it
- **through which channel** — the object list, or the caption/setting text
- **a confidence level**: certain (passed verification) or borderline
  (matched without verification, or verification was inconclusive)

Store the match reasoning, not a boolean. FR-D2 and FR-D3 depend on it.
