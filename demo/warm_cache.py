"""
Warm the predicate cache so free-text queries work instantly and offline.

Throwaway demo code — see demo/DEMO-SPEC.md.

Runs the REAL extraction path (serve.py's extract_predicates -> one Anthropic
call per query), then measures each query against the actual catalog and
prints how many photos it returns. Results are written to demo/demo-queries.md.

Nothing is hand-written into the cache: every entry here is what the model
actually returned, through the same code the page uses.

    set ANTHROPIC_API_KEY=sk-ant-...
    python demo\\warm_cache.py

Roughly 45 short calls — a couple of cents. Already-cached queries are skipped
and cost nothing, so it is safe to re-run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import serve  # noqa: E402 — the demo server module IS the implementation

# Candidate queries, drawn from the objects that actually appear in the
# catalog (518 distinct, 128 photos). Phrasing is deliberately ordinary —
# this is what someone would type, not tuned syntax.
QUERIES = [
    # single objects
    "a dog", "a cat", "a clock", "a car", "a bottle", "a cup", "a bowl",
    "a plate", "a chair", "a lamp", "a mirror", "a bench", "a spoon",
    "a pizza", "an airplane", "a frisbee", "a flag", "a towel", "a stove",
    "a sign", "a shoe", "a plant", "a window", "a door", "a tree",
    "a building", "a skyscraper", "a fence", "a bicycle", "a boat",
    # two objects bound together — the interesting case
    "a cup on a table", "a bowl of food on a table", "a plate and a spoon",
    "a cup and a plate", "a chair and a table", "a pot and a pan",
    "a pot on a stove", "a pan on a stove", "a dog and a person",
    "a person on a bench", "a person with a frisbee", "a baseball glove",
    "a person in a baseball uniform", "a lamp and a window",
    "a car and a building", "a sign on a building", "a tree and a fence",
    "trees and grass", "a person wearing a shirt", "a street with poles",
    # three objects — thin at 128 photos, kept to show the honest limit
    "a pot, a pan and a stove", "a plate, a cup and a table",
]


def main() -> None:
    print(f"Catalog: {len(serve.CATALOG)} photos\n")
    rows, failed = [], []

    for query in QUERIES:
        predicates, source = serve.extract_predicates(query)
        if source == "fallback":
            failed.append(query)
        result = serve.search(predicates)
        rows.append((query, result["total"], result["certain"], source))
        print(f"  {result['total']:>3}  {query:<34} [{source}]")

    rows.sort(key=lambda r: -r[1])
    strong = [r for r in rows if r[1] >= 3]
    thin = [r for r in rows if r[1] < 3]

    lines = [
        "# שאילתות מדודות — מאגר ההדגמה",
        "",
        f"נמדד מול הקטלוג בפועל: {len(serve.CATALOG)} תמונות. "
        "כל הפרדיקטים במטמון, כלומר רצות מיידית וללא רשת.",
        "",
        "> נוצר על ידי `python demo/warm_cache.py`. אין כאן פרדיקט שנכתב ביד — "
        "כולם חזרו מהמודל דרך אותו מסלול שהדף משתמש בו.",
        "",
        "## בטוחות להדגמה (3 תוצאות ומעלה)",
        "",
        "| שאילתה | תוצאות | ודאיות |",
        "|---|---|---|",
    ]
    lines += [f"| `{q}` | {t} | {c} |" for q, t, c, _ in strong]
    lines += [
        "",
        "## דקות מדי במאגר הזה (פחות מ-3)",
        "",
        "רצות ועובדות, אבל מחזירות מעט מדי כדי להרשים. "
        "זו תכונה של 128 תמונות, לא של האדריכלות — "
        "המדידה על 500 תמונות אמיתיות במסמך 05.",
        "",
        "| שאילתה | תוצאות |",
        "|---|---|",
    ]
    lines += [f"| `{q}` | {t} |" for q, t, _, _ in thin]
    Path(__file__).parent.joinpath("demo-queries.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print(f"\n{len(strong)} queries return 3+ results, {len(thin)} are thin.")
    print("Written: demo/demo-queries.md")
    if failed:
        print(f"\n{len(failed)} query(ies) fell back to literal splitting "
              f"(no API key, or the call failed) and were NOT cached:")
        for q in failed:
            print(f"  - {q}")
        print("Set ANTHROPIC_API_KEY and re-run; cached queries cost nothing.")


if __name__ == "__main__":
    main()
