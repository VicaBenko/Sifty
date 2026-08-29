"""Shared helpers for the Sift validation gate."""
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

# iCloud on Windows exposes photos as placeholders. These NTFS attributes mark a
# file whose contents are not on local disk. Reading such a file triggers a
# network hydration (slow) or fails when offline.
FILE_ATTRIBUTE_OFFLINE = 0x00001000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000

PLACEHOLDER_MASK = (
    FILE_ATTRIBUTE_OFFLINE
    | FILE_ATTRIBUTE_RECALL_ON_OPEN
    | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff"}


def is_placeholder(path: Path) -> bool:
    """True if the file looks like a cloud placeholder rather than real local data."""
    try:
        st = path.stat()
    except OSError:
        return True
    attrs = getattr(st, "st_file_attributes", 0)
    if attrs & PLACEHOLDER_MASK:
        return True
    # Fallback for non-Windows or when attributes are unavailable: a real photo is
    # never a handful of bytes.
    return st.st_size < 1024


def iter_images(root: Path):
    """Yield image files under root, skipping our own output folders."""
    skip = {"_sift_workspace", "תמונות להשמדה"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
        for name in filenames:
            if Path(name).suffix.lower() in IMAGE_SUFFIXES:
                yield Path(dirpath) / name


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    tmp.replace(path)


def register_heif() -> bool:
    """HEIC is the default iCloud format. Returns True if support is available."""
    try:
        import pillow_heif  # type: ignore

        pillow_heif.register_heif_opener()
        return True
    except ImportError:
        return False


def die(message: str) -> None:
    print(f"\nשגיאה: {message}\n", file=sys.stderr)
    raise SystemExit(1)
