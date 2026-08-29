# Global Constraints — Sift

These constraints apply to EVERY spec, plan, task and code review in this
project. Violating any of them is a blocking review failure, regardless of
what a plan or task description says.

- Target platforms: Windows, macOS, Linux from one codebase. No OS-specific
  logic outside the filesystem layer.
- The engine runs locally. The UI is served by a local HTTP server that
  listens on localhost ONLY. Never bind 0.0.0.0 or any external interface.
- Access to the local server is gated by a token generated at startup.
- Only two operations are permitted against the user's source folder:
  read, and delete-in-place after explicit user approval in that same session.
  NEVER move files out of the source folder. NEVER write into it.
- Quarantine is populated by COPY. Originals stay in place until approval.
- The quarantine folder must be OUTSIDE the source folder; refuse otherwise.
- Only 384px downscaled derivatives are sent to the external tagging provider.
  Original files never leave the machine.
- Catalog, operation log and API key are stored locally only.
- The tagging provider sits behind a swappable interface.
- Query language is English. No Hebrew query parsing in scope.
- Query response under 1s on a 50k-photo catalog, excluding verification.
- Engine, query engine and UI are separable; the engine must run and be
  testable headless.
- External failures (network, provider, disk) must never leave the catalog or
  the quarantine folder in an inconsistent state.
- Path, permission and filename-encoding handling is uniform across operating
  systems. Hebrew and emoji filenames must work on all three.

## The three blocking requirements

| Requirement | Why it blocks | Verified by |
|---|---|---|
| FR-H2 — localhost only | An exposed server opens the entire gallery to anyone on the network | AC-9 |
| FR-E10 — never move files | A violation deletes the user's photos without approval | AC-3, AC-4 |
| FR-F4 — monthly spend cap | Indexing is automatic; without a cap it spends money unasked | AC-6 |

## Why "copy, never move"

The gallery folder may be a sync provider's folder. Deleting a file from it
propagates to every device (documented by Apple). Move behaviour is NOT
documented at all, and there is evidence that moving to another drive is
interpreted as a delete. See docs/02-decision-memo-001-architecture.md,
decision 1.

Anyone who replaces the copy with a move "because it is more efficient" will
delete the user's photos from their phone before the user approved anything.
