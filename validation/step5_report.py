"""
שלב 5 — דוח HTML.

מייצר דוח שנפתח בדפדפן, עם עברית תקינה ועם התמונות עצמן:
לכל שאילתה — מה פוספס (סימנת, המערכת לא מצאה) ומה נתפס בטעות
(המערכת מצאה, לא סימנת), עם התגיות של כל תמונה.

זה הכלי לאבחון: אם התמונות שפוספסו באמת מתאימות לשאילתה — הבעיה בזיהוי.
אם הן לא מתאימות — הבעיה בסימון או בהגדרת השאילתה.

שימוש:
    python step5_report.py
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from sift_common import die, load_json
from step4_score import PRECISION_TARGET, RECALL_TARGET, run_query, score

MAX_THUMBS = 40  # per bucket, to keep the page manageable


def pct(value):
    return "—" if value is None else f"{value * 100:.0f}%"


def thumb_grid(ids, catalog, manifest_by_id) -> str:
    if not ids:
        return '<p class="empty">אין תמונות בקטגוריה הזו.</p>'
    cells = []
    for photo_id in ids[:MAX_THUMBS]:
        entry = catalog.get(photo_id, {})
        item = manifest_by_id.get(photo_id, {})
        tags = ", ".join(entry.get("objects", [])[:10])
        caption = entry.get("caption", "")
        cells.append(
            f'<figure class="cell">'
            f'<img src="{html.escape(item.get("thumb", ""))}" loading="lazy" alt="">'
            f'<figcaption><b>{html.escape(photo_id)}</b>'
            f'<span class="cap">{html.escape(caption)}</span>'
            f'<span class="tags">{html.escape(tags)}</span>'
            f"</figcaption></figure>"
        )
    extra = ""
    if len(ids) > MAX_THUMBS:
        extra = f'<p class="empty">מוצגות {MAX_THUMBS} מתוך {len(ids)}.</p>'
    return f'<div class="grid">{"".join(cells)}</div>{extra}'


CSS = """
:root{--bg:#faf9f7;--panel:#fff;--ink:#1f1e1c;--muted:#6b6862;--line:#e3e0da;
--ok:#2f6f4f;--bad:#a8432f;--okbg:#e8f2ec;--badbg:#f7e9e5;}
@media (prefers-color-scheme:dark){:root{--bg:#1a1917;--panel:#232220;--ink:#f0eee9;
--muted:#a3a099;--line:#35332f;--ok:#6fbf95;--bad:#e08a72;--okbg:#24352c;--badbg:#3a2723;}}
*{box-sizing:border-box}
body{margin:0;padding:0 0 60px;background:var(--bg);color:var(--ink);
font:15px/1.6 -apple-system,"Segoe UI",system-ui,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:28px 20px}
h1{font-size:22px;margin:0 0 4px}
h2{font-size:18px;margin:34px 0 6px}
h3{font-size:14px;margin:20px 0 8px;color:var(--muted);font-weight:600}
.sub{color:var(--muted);margin:0 0 22px;font-size:14px}
table{border-collapse:collapse;width:100%;background:var(--panel);
border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:10px 12px;text-align:right;border-bottom:1px solid var(--line)}
th{background:var(--bg);font-size:13px;color:var(--muted);font-weight:600}
tr:last-child td{border-bottom:0}
td.num{font-variant-numeric:tabular-nums}
.pass{color:var(--ok);font-weight:600}
.fail{color:var(--bad);font-weight:600}
.verdict{padding:12px 16px;border-radius:10px;margin:10px 0 0;font-weight:600}
.verdict.ok{background:var(--okbg);color:var(--ok)}
.verdict.no{background:var(--badbg);color:var(--bad)}
.note{color:var(--muted);font-size:14px;margin:6px 0 0}
.grid{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.cell{margin:0;background:var(--panel);border:1px solid var(--line);
border-radius:8px;overflow:hidden}
.cell img{width:100%;aspect-ratio:1;object-fit:cover;display:block;background:var(--line)}
figcaption{padding:7px 8px;font-size:11px;line-height:1.45;color:var(--muted)}
figcaption b{display:block;color:var(--ink);font-size:12px}
.cap{display:block;margin:2px 0 4px}
.tags{display:block;font-family:ui-monospace,monospace;font-size:10px;opacity:.85}
.empty{color:var(--muted);font-size:14px;margin:8px 0}
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default="_sift_workspace")
    ap.add_argument("--queries", default="queries.json")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    catalog = load_json(workspace / "catalog.json")
    truth_all = load_json(workspace / "ground_truth.json")
    manifest = load_json(workspace / "manifest.json")
    queries = load_json(Path(args.queries).expanduser())

    if not (catalog and truth_all and manifest and queries):
        die("חסר אחד מהקבצים: catalog.json / ground_truth.json / manifest.json / queries.json")

    manifest_by_id = {item["id"]: item for item in manifest}
    universe = set(catalog.keys())

    rows, sections = [], []
    for query in queries:
        predicted = run_query(query, catalog)
        truth = set(truth_all.get(query["id"], []))
        result = score(predicted, truth, universe)
        n_pred, n_truth = len(predicted & universe), len(truth & universe)

        if n_truth == 0:
            verdict, cls = "לא נבדק", "no"
        elif (result["recall"] or 0) >= RECALL_TARGET and (
            result["precision"] or 0
        ) >= PRECISION_TARGET:
            verdict, cls = "עבר", "ok"
        else:
            verdict, cls = "נכשל", "no"

        rows.append(
            f"<tr><td>{html.escape(query['label'])}</td>"
            f"<td>{html.escape(query.get('difficulty',''))}</td>"
            f'<td class="num">{n_pred}</td><td class="num">{n_truth}</td>'
            f'<td class="num">{pct(result["recall"])}</td>'
            f'<td class="num">{pct(result["precision"])}</td>'
            f'<td class="{"pass" if cls == "ok" else "fail"}">{verdict}</td></tr>'
        )

        sections.append(
            f"<h2>{html.escape(query['label'])}</h2>"
            f'<p class="note">{html.escape(query.get("note",""))}</p>'
            f'<div class="verdict {cls}">{verdict} · כיסוי {pct(result["recall"])} · '
            f'דיוק {pct(result["precision"])}</div>'
            f"<h3>סימנת, המערכת לא מצאה — {len(result['missed'])} תמונות</h3>"
            f"{thumb_grid(result['missed'], catalog, manifest_by_id)}"
            f"<h3>המערכת מצאה, לא סימנת — {len(result['wrong'])} תמונות</h3>"
            f"{thumb_grid(result['wrong'], catalog, manifest_by_id)}"
        )

    page = f"""<!DOCTYPE html>
<html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sift — דוח שער האימות</title><style>{CSS}</style></head><body><div class="wrap">
<h1>דוח שער האימות</h1>
<p class="sub">{len(universe):,} תמונות · קריטריון מעבר: כיסוי ≥ {RECALL_TARGET:.0%} ודיוק ≥ {PRECISION_TARGET:.0%}</p>
<table><thead><tr><th>שאילתה</th><th>סוג</th><th>נמצאו</th><th>סימנת</th>
<th>כיסוי</th><th>דיוק</th><th>תוצאה</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
{"".join(sections)}
</div></body></html>"""

    out = workspace / "score_report.html"
    out.write_text(page, encoding="utf-8")
    print(f"\nהדוח נוצר: {out}")
    print("לפתיחה:  start _sift_workspace\\score_report.html")


if __name__ == "__main__":
    main()
