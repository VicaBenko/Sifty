# Spec 01 — Source & Indexing Engine

> ספק 1 — מנוע מקור ואינדוקס. מכסה FR-A1–A10 ו-FR-B1–B6.

**Status:** ready to plan. This is the foundation; build it first.
**Binding authority:** this file. Derived from `docs/06-prd.md` sections A and B.
**Also read before planning:** `specs/00-global-constraints.md`,
`docs/02-decision-memo-001-architecture.md`.

---

## Purpose

Turn a folder of photos into a queryable local catalog. Each photo is visited
once, converted into a structured object list plus a caption, and stored. No
searching happens here — that is spec 02.

## In scope

Source folder configuration and validation, file discovery, cloud-placeholder
detection, 384px derivative generation, tagging through a swappable provider,
incremental and resumable indexing, and the local catalog schema.

## Out of scope

Query parsing and matching (spec 02). Any UI (spec 03). Quarantine or deletion
(spec 04). Cost metering and spend cap (spec 05) — this engine must expose the
per-photo cost data those requirements consume, but must not implement the cap.

---

## Requirements

### A · Source and indexing

| # | Requirement |
|---|---|
| FR-A1 | The user configures the gallery folder path. The system validates that the path exists and is readable. |
| FR-A2 | The system recognises image files with extensions `jpg, jpeg, png, heic, heif, webp, tif, tiff`. |
| FR-A3 | The system detects files that are not downloaded locally (cloud placeholders), reports how many there are, and instructs the user to download them before indexing. |
| FR-A4 | For every photo a 384px downscaled derivative is created in a separate working directory. **The source file is never opened for writing at any stage.** |
| FR-A5 | Indexing is incremental. A photo already in the catalog is not tagged again. Identity is path + modification time + size. |
| FR-A6 | Indexing runs automatically in the background when new photos appear in the gallery. |
| FR-A7 | Indexing can be stopped and resumed. Interruption must not corrupt the catalog, and a partial catalog must remain queryable. |
| FR-A8 | Indexing progress is visible: how many of how many, and estimated time remaining. |
| FR-A9 | A tagging failure on a single photo is logged and does not stop the rest. It is retried on the next run. |
| FR-A10 | The system detects the **source type** — a synced folder (iCloud, Google Drive and similar) versus a plain local folder — and stores it with the source settings. |

### B · Catalog

| # | Requirement |
|---|---|
| FR-B1 | For each photo the catalog stores: id, source path, modification time, size, object list, caption, setting, screenshot flag, tagging-model identity, and a timestamp. |
| FR-B2 | The catalog is stored locally only. It is never uploaded. |
| FR-B3 | A normalised object table that supports exact set intersection. |
| FR-B4 | A full-text index over the caption and the setting. |
| FR-B5 | The catalog survives a restart. A corrupt catalog is detected and the system offers a rebuild. |
| FR-B6 | A photo deleted from the gallery is removed from the catalog on the next scan. |

### Non-functional requirements that apply here

NFR-3 (engine runs and is testable headless) · NFR-5 (only 384px derivatives
leave the machine) · NFR-7 (one codebase, three OSes) · NFR-8 (no inconsistent
state after an external failure) · NFR-9 (uniform path and filename encoding).

---

## Acceptance criteria

| # | Criterion |
|---|---|
| AC-1 | A full index of ~2,550 photos completes without crashing, and can be stopped mid-run and resumed with no loss. |
| AC-7 | Losing the network mid-index does not corrupt the catalog; the next run continues from where it stopped. |
| S1-1 | An automated test proves no code path opens a file inside the source folder for writing. |
| S1-2 | The screenshot flag is covered by tests. Its reliability was fixed during calibration but never measured under clean conditions — see PRD section 9. |
| S1-3 | The engine runs end to end from a command line with no UI present. |

---

## Notes for the implementer

`validation/` contains a five-step measurement harness that demonstrates the
tagging prompt and the catalog shape end to end. **Read it to learn the prompt
and the data shape. Do not use it as the product's base** — it was written to
measure, not to survive.

Measured on 500 real photos: ~$0.001 per photo, median 7 objects per photo
including small ones, zero pipeline errors across 500/500.
