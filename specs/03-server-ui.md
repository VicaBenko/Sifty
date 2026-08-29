# Spec 03 — Local Server & User Interface

> ספק 3 — שרת מקומי וממשק. מכסה FR-H1–H8 ו-FR-D1–D6.

**Status: UNBLOCKED for planning.** The UX brainstorming session ran and
`docs/09-ux-decisions.md` now exists as co-authority alongside this file.
**Not clean, though:** section 9 of that doc, "Open, to resume," still holds
8 undecided items. In particular, **item 1 — "select all" scope under
infinite scroll — must be resolved before any task touches the bulk
selection controls (FR-D4).**
**Binding authority:** this file plus `docs/09-ux-decisions.md`.
Derived from `docs/06-prd.md` sections H and D.
**Also read before planning:** `specs/00-global-constraints.md`.

---

## Purpose

Serve the engine's output to a browser on the same machine, and let the user
review results and choose what to act on. This spec is built **before**
quarantine and deletion on purpose — so the user can see results and confirm
they are correct before any code touches their files.

## In scope

The local HTTP server, its security model, and the results and review screens.

## Out of scope

Indexing (spec 01), matching (spec 02), any file operation on the gallery or
the quarantine folder (spec 04).

---

## Requirements

### H · Deployment and serving

| # | Requirement |
|---|---|
| FR-H1 | The engine runs a local server that serves the interface. The interface opens in a browser. |
| FR-H2 | **The server listens on localhost ONLY.** No external address, no local-network exposure. Blocking requirement. |
| FR-H3 | Access to the interface is gated by a token generated at startup, so other applications on the same machine cannot reach the server. |
| FR-H4 | A single launch starts the server and opens the browser. The user never types a command. |
| FR-H5 | The source folder and the quarantine folder are chosen through a native picker or by typing a path — **not** through the browser's file picker, which cannot select a server-side path. |
| FR-H6 | Thumbnails are served by the local server only. No image is uploaded to any external server other than during the tagging step. |
| FR-H7 | Closing the browser does not stop a background index. Reopening shows the current state. |
| FR-H8 | A server error is shown inside the interface in plain language, not as a browser error page. |

### D · Results and review

| # | Requirement |
|---|---|
| FR-D1 | Results are shown as a grid of thumbnails. |
| FR-D2 | Each photo shows **why it was selected** — which query objects were found, and through which channel. |
| FR-D3 | Each photo shows a **confidence level**: certain (verified) or borderline. |
| FR-D4 | Select and deselect a single photo; select all; deselect all; select only the certain ones. |
| FR-D5 | A photo can be enlarged to full view before deciding. |
| FR-D6 | A counter shows how many are selected and their total size. |

### Non-functional requirements that apply here

NFR-3 (UI separable from the engine) · NFR-10 (works in leading modern browsers,
no extension required).

---

## Acceptance criteria

| # | Criterion |
|---|---|
| AC-9 | **A port scan from another machine on the same network does not find the server. A request from a non-localhost address is rejected.** |
| AC-2 | Every displayed result carries its reason and confidence level. |
| S3-1 | Killing the browser mid-index and reopening shows correct live state. |
| S3-2 | A server-side failure surfaces as a readable in-app message, tested. |

---

## Open UX questions to settle before planning

These are unresolved in the PRD and must be answered by the UX session:

1. **Interface language.** The query language is English. A Hebrew interface
   with an English-only search field is a friction point to design around, not
   to discover during implementation.
2. **Opening screen and navigation structure.** Undecided.
3. How the editable predicate list from FR-C7 is presented before a query runs.
4. How "borderline" is communicated so it changes user behaviour rather than
   being decoration.
