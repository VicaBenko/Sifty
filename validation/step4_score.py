"""
שלב 4 — ציון.

מריץ את השאילתות מול הקטלוג, משווה לתיוג הידני, ומדפיס כיסוי ודיוק
מול קריטריון המעבר של שער האימות.

שימוש:
    python step4_score.py
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from sift_common import die, load_json, save_json

# קריטריון המעבר, ממסמך החלטה 001
RECALL_TARGET = 0.80
PRECISION_TARGET = 0.80


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", text.lower())


def matches_predicate(synonyms: list[str], tags: list[str], caption: str) -> bool:
    """A predicate is satisfied if any synonym appears in the tags or the caption."""
    tag_blob = " | ".join(normalize(t) for t in tags)
    caption_blob = normalize(caption)
    for synonym in synonyms:
        pattern = r"\b" + re.escape(normalize(synonym).strip()) + r"\b"
        if re.search(pattern, tag_blob) or re.search(pattern, caption_blob):
            return True
    return False


def run_query(query: dict, catalog: dict) -> set[str]:
    """A photo matches when every predicate group is satisfied, and — when the
    query specifies it — the screenshot flag agrees."""
    wants_screenshot = query.get("is_screenshot")
    groups = query.get("all_of") or []

    hits = set()
    for photo_id, entry in catalog.items():
        if wants_screenshot is not None:
            if bool(entry.get("is_screenshot", False)) != bool(wants_screenshot):
                continue
        tags = entry.get("objects", [])
        caption = f"{entry.get('caption', '')} {entry.get('setting', '')}"
        if all(matches_predicate(group, tags, caption) for group in groups):
            hits.add(photo_id)
    return hits


def score(predicted: set[str], truth: set[str], universe: set[str]) -> dict:
    predicted &= universe
    truth &= universe
    tp = len(predicted & truth)
    fp = len(predicted - truth)
    fn = len(truth - predicted)
    recall = tp / len(truth) if truth else None
    precision = tp / len(predicted) if predicted else None
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "recall": recall,
        "precision": precision,
        "missed": sorted(truth - predicted),
        "wrong": sorted(predicted - truth),
    }


def pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.0f}%"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default="_sift_workspace")
    ap.add_argument("--queries", default="queries.json")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    catalog = load_json(workspace / "catalog.json")
    if not catalog:
        die("לא נמצא catalog.json. הרץ קודם את step2_tag.py")

    truth_all = load_json(workspace / "ground_truth.json")
    if not truth_all:
        die(
            "לא נמצא ground_truth.json בתיקיית העבודה.\n"
            "  הרץ את step3_label.py, סמן בדפדפן, ושמור את הקובץ לכאן."
        )

    queries = load_json(Path(args.queries).expanduser())
    universe = set(catalog.keys())

    print(f"\nקטלוג: {len(universe):,} תמונות מתויגות")
    print(f"קריטריון מעבר: כיסוי ≥ {RECALL_TARGET:.0%} · דיוק ≥ {PRECISION_TARGET:.0%}\n")
    print(f"{'שאילתה':<28}{'סוג':<12}{'נמצאו':>7}{'אמת':>7}{'כיסוי':>9}{'דיוק':>9}")
    print("-" * 72)

    report, verdicts = {}, {}
    for query in queries:
        predicted = run_query(query, catalog)
        truth = set(truth_all.get(query["id"], []))
        result = score(predicted, truth, universe)
        result["predicted_count"] = len(predicted & universe)
        result["truth_count"] = len(truth & universe)
        report[query["id"]] = result

        print(
            f"{query['label'][:26]:<28}{query.get('difficulty', ''):<12}"
            f"{result['predicted_count']:>7}{result['truth_count']:>7}"
            f"{pct(result['recall']):>9}{pct(result['precision']):>9}"
        )

        if result["truth_count"] == 0:
            verdicts[query["id"]] = "לא נבדק — לא סומנו תמונות בתיוג הידני"
        elif (result["recall"] or 0) >= RECALL_TARGET and (
            result["precision"] or 0
        ) >= PRECISION_TARGET:
            verdicts[query["id"]] = "עבר"
        else:
            verdicts[query["id"]] = "נכשל"

    print("\n" + "=" * 72)
    for query in queries:
        verdict = verdicts[query["id"]]
        print(f"  {query['label']}: {verdict}")

    decisive = next((q for q in queries if q.get("difficulty") == "hard"), None)
    if decisive:
        result = report[decisive["id"]]
        outcome = verdicts[decisive["id"]]
        print("\n" + "=" * 72)
        print(f"השאילתה המכריעה — {decisive['label']}: {outcome}")
        if outcome == "נכשל":
            print(
                "\nהתיוג לא עמד בקריטריון. לפני שמסיקים שהמוצר לא אפשרי, בדוק ידנית\n"
                "כמה מהתמונות שפוספסו — האם האובייקט באמת מזוהה בקושי, או שהמילה\n"
                "בתיוג שונה ממה שרשום ב-queries.json (נרדפות). ההבדל הזה מכריע."
            )
            if result["missed"][:8]:
                print(f"\nדוגמאות לתמונות שפוספסו: {', '.join(result['missed'][:8])}")
                for photo_id in result["missed"][:3]:
                    entry = catalog.get(photo_id, {})
                    print(f"  {photo_id}: {entry.get('objects', [])[:12]}")
            if result["wrong"][:8]:
                print(f"\nדוגמאות לתוצאות שגויות: {', '.join(result['wrong'][:8])}")

    save_json(
        workspace / "score_report.json",
        {"targets": {"recall": RECALL_TARGET, "precision": PRECISION_TARGET},
         "results": report, "verdicts": verdicts},
    )
    print(f"\nדוח מלא נשמר ב-{workspace / 'score_report.json'}")


if __name__ == "__main__":
    main()
