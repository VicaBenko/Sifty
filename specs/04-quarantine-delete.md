# Spec 04 — Quarantine & Deletion

> ספק 4 — הסגר ומחיקה. מכסה FR-E1–E13. **הרכיב הרגיש. לבדוק בכבדות.**

**Status:** plan only after spec 03 is working and results have been seen to be
correct with real eyes.
**Binding authority:** this file. Derived from `docs/06-prd.md` section E.
**Read in full before planning:** `specs/00-global-constraints.md` and
`docs/02-decision-memo-001-architecture.md` decision 1.

---

## This is the component where a bug destroys the user's photos

Every other subsystem, when it fails, wastes time. This one, when it fails,
removes photographs from every device the user owns, permanently after 30 days,
without them having approved it.

Test it heavily. Treat every review finding here as blocking. When a
simplification and a safety property conflict, the safety property wins.

## Purpose

Copy the selected photos into a quarantine folder, let the user review that
folder outside the application, and then delete from the gallery only what
survived that review.

## In scope

Quarantine path validation, copying, the manifest, the approval gate,
delete-in-place, the release record, and the source-type warning.

## Out of scope

Selecting the photos (spec 03). Querying (spec 02). The operation log and the
release-rate metric (spec 05) — this subsystem emits the events, spec 05
records them.

---

## Requirements

| # | Requirement |
|---|---|
| FR-E1 | The selected photos are **copied** into the quarantine folder. The originals stay where they are. |
| FR-E2 | The quarantine path is configurable. The system verifies it is **outside** the gallery folder and refuses otherwise. |
| FR-E3 | Free disk space is checked before copying. If there is not enough, the operation stops with a clear message. |
| FR-E4 | Copying is resumable after interruption and reports individual failures. |
| FR-E5 | A manifest is written mapping each copy to its source path and file signature. |
| FR-E6 | The user reviews the quarantine folder outside the application and removes from it everything that should **not** be deleted. |
| FR-E7 | On approval, the system deletes from the gallery only those sources whose copy still exists in the quarantine folder, according to the manifest. |
| FR-E8 | A final count is shown before deletion and explicit approval is required. |
| FR-E9 | Deletion happens in place, inside the gallery folder, so that iCloud routes it to "Recently Deleted". |
| FR-E10 | **The system never moves files out of the gallery folder.** Copy, and delete-in-place, are the only permitted operations against it. |
| FR-E11 | A photo the user removed from the quarantine folder is recorded as "released" for that query and is never offered again for it. |
| FR-E12 | The release list is visible to the user and can be reset, wholly or per item. |
| FR-E13 | **Before final approval the meaning of the deletion is shown, per source type.** Synced folder — the photos will disappear from every device, and for iCloud will remain 30 days in "Recently Deleted". Local folder — the deletion is local only. |

### Non-functional requirements that apply here

NFR-1 (nothing is deleted or modified without explicit approval in that same
round) · NFR-2 (two operations only against the gallery: read, and
delete-in-place after approval) · NFR-8 (an external failure never leaves the
catalog or the quarantine folder inconsistent).

---

## Acceptance criteria

| # | Criterion |
|---|---|
| AC-3 | After a full round, every photo the user removed from the quarantine folder still exists in the gallery. |
| AC-4 | Code inspection **and** an automated test prove there is no move call, and no delete call that is not conditional on approval. |
| AC-5 | Re-running an identical query does not show photos released in the previous round. |
| AC-10 | Before final approval the user is shown the correct meaning of deletion for the configured source type. |
| S4-1 | A quarantine path inside the gallery folder is refused, tested. |
| S4-2 | A source whose copy was removed from quarantine is not deleted, tested against the manifest. |
| S4-3 | Interrupting the copy midway and resuming produces a consistent manifest. |

---

## The manifest is the safety mechanism

Deletion is never driven by the selection the user made on screen. It is driven
by what is still present in the quarantine folder at approval time, matched
through the manifest. The user's review of that folder is the last word.

A plan that deletes based on the in-app selection has broken the product's
central promise, even if every test passes.
