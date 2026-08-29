"""
שלב 1 — דגימת תמונות מהגלריה.

קורא בלבד. מעתיק, לעולם לא מעביר ולא מוחק.
מייצר גרסאות מוקטנות ל-384 פיקסל בתיקיית עבודה נפרדת.

שימוש:
    python step1_sample.py --source "C:\\Users\\<user>\\Pictures\\iCloud Photos\\Photos"
    python step1_sample.py --source ... --count 500 --seed 42
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageOps

from sift_common import (
    die,
    is_placeholder,
    iter_images,
    register_heif,
    save_json,
)

THUMB_MAX_EDGE = 384


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="תיקיית התמונות לסריקה")
    ap.add_argument("--workspace", default="_sift_workspace", help="תיקיית העבודה")
    ap.add_argument("--count", type=int, default=500, help="כמה תמונות לדגום")
    ap.add_argument("--seed", type=int, default=42, help="זרע אקראיות, לשחזור")
    args = ap.parse_args()

    source = Path(args.source).expanduser()
    if not source.is_dir():
        die(f"התיקייה לא נמצאה: {source}")

    workspace = Path(args.workspace).expanduser().resolve()
    thumbs_dir = workspace / "thumbs"
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    heif_ok = register_heif()

    print(f"סורק את {source} ...")
    all_images = list(iter_images(source))
    if not all_images:
        die("לא נמצאו קבצי תמונה בתיקייה.")
    print(f"נמצאו {len(all_images):,} קבצי תמונה.")

    # Placeholder check before sampling, so the sample is drawn from files that
    # actually exist locally.
    local, placeholders = [], []
    for path in all_images:
        (placeholders if is_placeholder(path) else local).append(path)

    if placeholders:
        pct = 100 * len(placeholders) / len(all_images)
        print(
            f"\nשים לב: {len(placeholders):,} קבצים ({pct:.0f}%) אינם מורדים למחשב.\n"
            f'  ב-File Explorer: בחר הכל בתיקייה → קליק ימני → "Always keep on this device",\n'
            "  המתן לסיום ההורדה, והרץ שוב.\n"
        )
    if not local:
        die("אף קובץ לא זמין מקומית. יש להוריד את התמונות לפני הדגימה.")

    if not heif_ok:
        heic = sum(1 for p in local if p.suffix.lower() in {".heic", ".heif"})
        if heic:
            print(
                f"אזהרה: {heic:,} קבצי HEIC ואין תמיכה מותקנת.\n"
                "  התקן:  pip install pillow-heif\n"
            )

    rng = random.Random(args.seed)
    sample = rng.sample(local, min(args.count, len(local)))
    print(f"נדגמו {len(sample):,} תמונות. מייצר גרסאות מוקטנות ...")

    manifest, failed = [], []
    for index, src in enumerate(sample):
        thumb_name = f"{index:04d}.jpg"
        try:
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im)
                im = im.convert("RGB")
                im.thumbnail((THUMB_MAX_EDGE, THUMB_MAX_EDGE), Image.LANCZOS)
                im.save(thumbs_dir / thumb_name, "JPEG", quality=82)
        except Exception as exc:  # noqa: BLE001 - report and continue
            failed.append({"source": str(src), "error": str(exc)})
            continue

        manifest.append(
            {
                "id": thumb_name[:-4],
                "thumb": f"thumbs/{thumb_name}",
                "source": str(src),
                "filename": src.name,
            }
        )
        if (index + 1) % 50 == 0:
            print(f"  {index + 1}/{len(sample)}")

    save_json(workspace / "manifest.json", manifest)
    if failed:
        save_json(workspace / "sample_errors.json", failed)

    print(f"\nהושלם. {len(manifest):,} תמונות מוכנות ב-{thumbs_dir}")
    if failed:
        print(f"{len(failed)} קבצים נכשלו — ראה sample_errors.json")
    print("\nהשלב הבא:  python step2_tag.py")


if __name__ == "__main__":
    main()
