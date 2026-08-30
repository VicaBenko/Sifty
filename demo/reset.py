"""
Reset the demo photo set so the demo can be run again.

Throwaway demo code — see demo/DEMO-SPEC.md, Phase 2, D-11.

Restores demo/photos/ from the pristine copy in demo/photos_master/, empties
demo/quarantine/, and clears demo/operation-log.json.

Touches nothing outside demo/.

Usage:
    python demo/reset.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

DEMO_DIR = Path(__file__).parent.resolve()
PHOTOS_DIR = DEMO_DIR / "photos"
MASTER_DIR = DEMO_DIR / "photos_master"
QUARANTINE_DIR = DEMO_DIR / "quarantine"
OPERATION_LOG = DEMO_DIR / "operation-log.json"


def main() -> None:
    if not MASTER_DIR.is_dir():
        print(f"Missing pristine copy: {MASTER_DIR}")
        print("Nothing to restore from. Aborting without touching anything.")
        sys.exit(1)

    PHOTOS_DIR.mkdir(exist_ok=True)

    master_names = {p.name for p in MASTER_DIR.iterdir() if p.is_file()}
    live_names = {p.name for p in PHOTOS_DIR.iterdir() if p.is_file()}

    restored = 0
    for name in sorted(master_names - live_names):
        shutil.copy2(MASTER_DIR / name, PHOTOS_DIR / name)
        restored += 1

    removed_extras = 0
    for name in sorted(live_names - master_names):
        (PHOTOS_DIR / name).unlink()
        removed_extras += 1

    cleared = 0
    if QUARANTINE_DIR.is_dir():
        for item in sorted(QUARANTINE_DIR.iterdir()):
            if item.is_file():
                item.unlink()
                cleared += 1
            elif item.is_dir():
                shutil.rmtree(item)

    log_cleared = False
    if OPERATION_LOG.exists():
        OPERATION_LOG.unlink()
        log_cleared = True

    print(f"photos/      {len(master_names)} files "
          f"({restored} restored, {removed_extras} extras removed)")
    print(f"quarantine/  cleared ({cleared} files)")
    print(f"operation log {'cleared' if log_cleared else 'was already empty'}")
    print("Demo is ready to run again.")


if __name__ == "__main__":
    main()
