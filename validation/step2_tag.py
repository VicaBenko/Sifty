"""
שלב 2 — תיוג מובנה של התמונות.

שולח כל תמונה מוקטנת למודל ראייה ומקבל רשימת אובייקטים + תיאור.
ניתן לעצירה והמשך: מה שכבר תויג לא נשלח שוב.

הגדרת מפתח:
    Windows CMD:      set ANTHROPIC_API_KEY=sk-ant-...
    PowerShell:       $env:ANTHROPIC_API_KEY="sk-ant-..."

אם מתקבלת השגיאה "anthropic-workspace-id is required", המפתח מקושר לזהות
ולא ל-workspace. יש להוסיף גם:
    PowerShell:       $env:SIFT_WORKSPACE_ID="wrkspc_..."
או לחלופין ליצור בקונסולה מפתח המשויך ל-workspace מסוים.

שימוש:
    python step2_tag.py
    python step2_tag.py --limit 50        # הרצת ניסיון קטנה קודם
    python step2_tag.py --model <model-id>
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from sift_common import die, load_json, save_json

DEFAULT_MODEL = os.environ.get("SIFT_MODEL", "claude-haiku-4-5")

PROMPT = """List the distinct physical objects visible in this image.

INCLUDE:
- Small objects, not just large or central ones. A pen, a sheet of paper, a
  charging cable, a mug, a remote — these matter as much as the furniture.
- Objects that are partially visible or in the background.

DO NOT INCLUDE:
- Body parts (hand, face, hair, finger, arm, paw, fur). List "person", "cat" etc.
  once instead.
- Materials, textures, colors, shadows, reflections.
- Room surfaces (wall, floor, ceiling) unless the surface itself is the subject.
- Vague placeholders. Never write "object", "small object on desk", "thing".
  If you cannot name it, leave it out.
- On-screen interface elements (button, icon, status bar, battery indicator,
  cursor, scroll bar). Describe screen content in the caption instead.

FORMAT:
- Lowercase English singular nouns. No duplicates — list each object type once.
- Use the MOST SPECIFIC everyday word you are confident in. Write "cat", never
  "animal". Write "sofa", never "furniture". Write "hammer", never "tool".
  Only fall back to a broad word when you genuinely cannot tell what it is.
- The one exception is brands: prefer the generic product word ("tablet" not
  "iPad", "laptop" not "MacBook"). If the brand is clearly identifiable, add it
  as one extra entry alongside the generic word.
- Do not guess objects you cannot actually see.

Also provide:
- caption: one short factual sentence describing the scene.
- setting: a few words for where this is (e.g. "office desk", "living room",
  "street", "restaurant", "car").
- is_screenshot: true ONLY if the ENTIRE image is a capture of a phone or
  computer screen. A photograph that happens to contain a TV, monitor or phone
  is NOT a screenshot — that is false.

Respond with JSON only, no other text:
{"objects": ["..."], "caption": "...", "setting": "...", "is_screenshot": true/false}"""

_print_lock = threading.Lock()


def encode_image(path: Path) -> str:
    return base64.standard_b64encode(path.read_bytes()).decode("ascii")


def parse_response(text: str) -> dict:
    """Models sometimes wrap JSON in prose or code fences. Be forgiving."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]

    data = json.loads(text)
    raw = data.get("objects") or []
    if not isinstance(raw, list):
        raw = []

    # Deduplicate while preserving order — the model sometimes repeats an object
    # once per instance ("bowl", "bowl").
    seen, objects = set(), []
    for item in raw:
        name = str(item).strip().lower()
        if name and name not in seen:
            seen.add(name)
            objects.append(name)

    return {
        "objects": objects,
        "caption": str(data.get("caption", "")).strip(),
        "setting": str(data.get("setting", "")).strip(),
        "is_screenshot": bool(data.get("is_screenshot", False)),
    }


class AnthropicTagger:
    """Tagging provider. Swap this class to move to another API or a local model."""

    name = "anthropic"

    def __init__(self, model: str):
        try:
            import anthropic  # type: ignore
        except ImportError:
            die("חסרה חבילה. הרץ:  pip install anthropic")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            die("לא הוגדר ANTHROPIC_API_KEY. ראה את ההוראות בראש הקובץ.")

        # מפתח המקושר לזהות (identity-linked) חייב לציין workspace בכל בקשה.
        # מפתח המשויך ל-workspace לא זקוק לזה, והמשתנה פשוט יישאר ריק.
        headers = {}
        workspace_id = os.environ.get("SIFT_WORKSPACE_ID", "").strip()
        if workspace_id:
            headers["anthropic-workspace-id"] = workspace_id

        self.client = anthropic.Anthropic(default_headers=headers or None)
        self.model = model

    def tag(self, thumb_path: Path) -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=600,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": encode_image(thumb_path),
                            },
                        },
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ],
        )
        result = parse_response(response.content[0].text)
        usage = getattr(response, "usage", None)
        if usage is not None:
            result["_tokens"] = {
                "in": getattr(usage, "input_tokens", 0),
                "out": getattr(usage, "output_tokens", 0),
            }
        return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default="_sift_workspace")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=0, help="תייג רק N תמונות")
    ap.add_argument("--workers", type=int, default=4, help="בקשות במקביל")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    manifest = load_json(workspace / "manifest.json")
    if not manifest:
        die("לא נמצא manifest.json. הרץ קודם את step1_sample.py")

    catalog_path = workspace / "catalog.json"
    catalog = load_json(catalog_path, default={}) or {}

    pending = [item for item in manifest if item["id"] not in catalog]
    if args.limit:
        pending = pending[: args.limit]

    if not pending:
        print(f"הכל כבר מתויג ({len(catalog):,} תמונות). ממשיך לשלב 3.")
        return

    print(f"מתייג {len(pending):,} תמונות עם {args.model} ...")
    if catalog:
        print(f"({len(catalog):,} כבר מתויגות, מדלג עליהן)")

    tagger = AnthropicTagger(args.model)
    done = 0
    failures: list[dict] = []

    def work(item: dict) -> tuple[dict, dict | None, str | None]:
        try:
            return item, tagger.tag(workspace / item["thumb"]), None
        except Exception as exc:  # noqa: BLE001 - collect and continue
            return item, None, str(exc)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(work, item) for item in pending]
        for future in as_completed(futures):
            item, tags, error = future.result()
            if error:
                failures.append({"id": item["id"], "error": error})
            else:
                catalog[item["id"]] = tags
            done += 1
            with _print_lock:
                if done % 25 == 0 or done == len(pending):
                    print(f"  {done}/{len(pending)}")
                    save_json(catalog_path, catalog)

    save_json(catalog_path, catalog)

    tokens_in = sum(t.get("_tokens", {}).get("in", 0) for t in catalog.values())
    tokens_out = sum(t.get("_tokens", {}).get("out", 0) for t in catalog.values())

    print(f"\nהושלם. {len(catalog):,} תמונות בקטלוג.")
    if tokens_in:
        print(f"טוקנים: {tokens_in:,} קלט / {tokens_out:,} פלט")
        print("העלות בפועל מופיעה בלוח הבקרה של הספק.")
    if failures:
        save_json(workspace / "tag_errors.json", failures)
        print(f"{len(failures)} כשלונות — ראה tag_errors.json. הרצה חוזרת תנסה שוב.")
    print("\nהשלב הבא:  python step3_label.py")


if __name__ == "__main__":
    main()
