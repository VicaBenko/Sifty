"""
שלב 3 — תיוג ידני ליצירת "אמת".

מייצר דף HTML מקומי. לכל שאילתה סורקים את רשת התמונות ולוחצים על אלה
שבאמת מתאימות. בסוף לוחצים על כפתור השמירה, והקובץ ground_truth.json
נשמר בתיקיית ההורדות — יש להעביר אותו לתיקיית העבודה.

חשוב: לא להסתכל על תוצאות המודל לפני שמסיימים. זו הנקודה של המבחן.

שימוש:
    python step3_label.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sift_common import die, load_json

TEMPLATE = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sift — תיוג ידני</title>
<style>
  :root {
    --bg: #faf9f7; --panel: #fff; --ink: #1f1e1c; --muted: #6b6862;
    --line: #e3e0da; --accent: #2f6f4f; --accent-soft: #e8f2ec;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #1a1917; --panel: #232220; --ink: #f0eee9; --muted: #a3a099;
      --line: #35332f; --accent: #6fbf95; --accent-soft: #24352c;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font: 15px/1.5 -apple-system, "Segoe UI", system-ui, sans-serif;
  }
  header {
    position: sticky; top: 0; z-index: 10; background: var(--panel);
    border-bottom: 1px solid var(--line); padding: 14px 20px;
  }
  h1 { margin: 0 0 10px; font-size: 17px; font-weight: 600; }
  .tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
  .tab {
    padding: 7px 14px; border: 1px solid var(--line); border-radius: 999px;
    background: transparent; color: var(--ink); cursor: pointer; font: inherit;
    font-size: 14px;
  }
  .tab[aria-selected="true"] {
    background: var(--accent); border-color: var(--accent); color: #fff;
  }
  .bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
  .note { color: var(--muted); font-size: 13px; margin: 0; flex: 1 1 320px; }
  .count { font-variant-numeric: tabular-nums; font-weight: 600; }
  button.save {
    padding: 8px 16px; border: 0; border-radius: 8px; background: var(--accent);
    color: #fff; font: inherit; font-weight: 600; cursor: pointer;
  }
  .grid {
    display: grid; gap: 8px; padding: 16px 20px 80px;
    grid-template-columns: repeat(auto-fill, minmax(128px, 1fr));
  }
  .cell {
    position: relative; aspect-ratio: 1; border-radius: 8px; overflow: hidden;
    border: 3px solid transparent; cursor: pointer; background: var(--line);
  }
  .cell img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .cell.on { border-color: var(--accent); }
  .cell.on::after {
    content: "\\2713"; position: absolute; top: 4px; inset-inline-end: 4px;
    width: 22px; height: 22px; border-radius: 50%; background: var(--accent);
    color: #fff; font-size: 14px; line-height: 22px; text-align: center;
  }
  .saved { background: var(--accent-soft); padding: 10px 20px; font-size: 14px; }
</style>
</head>
<body>
<header>
  <h1>תיוג ידני — סמן את התמונות שבאמת מתאימות</h1>
  <div class="tabs" id="tabs"></div>
  <div class="bar">
    <p class="note" id="note"></p>
    <span class="count"><span id="count">0</span> מסומנות</span>
    <button class="save" id="save">שמור ground_truth.json</button>
  </div>
</header>
<div class="saved" id="status" hidden></div>
<div class="grid" id="grid"></div>
<script>
const MANIFEST = __MANIFEST__;
const QUERIES = __QUERIES__;
const STORE_KEY = "sift-ground-truth-v1";

let current = QUERIES[0].id;
let marks = {};
QUERIES.forEach(q => marks[q.id] = new Set());

try {
  const saved = JSON.parse(localStorage.getItem(STORE_KEY) || "{}");
  Object.keys(saved).forEach(k => { if (marks[k]) marks[k] = new Set(saved[k]); });
} catch (e) { /* storage unavailable - start clean */ }

function persist() {
  try {
    const plain = {};
    Object.keys(marks).forEach(k => plain[k] = [...marks[k]]);
    localStorage.setItem(STORE_KEY, JSON.stringify(plain));
  } catch (e) { /* ignore */ }
}

const tabsEl = document.getElementById("tabs");
const gridEl = document.getElementById("grid");
const noteEl = document.getElementById("note");
const countEl = document.getElementById("count");

function renderTabs() {
  tabsEl.innerHTML = "";
  QUERIES.forEach(q => {
    const b = document.createElement("button");
    b.className = "tab";
    b.textContent = q.label + " (" + marks[q.id].size + ")";
    b.setAttribute("aria-selected", q.id === current);
    b.onclick = () => { current = q.id; render(); };
    tabsEl.appendChild(b);
  });
}

function render() {
  const q = QUERIES.find(x => x.id === current);
  noteEl.textContent = q.note;
  countEl.textContent = marks[current].size;
  renderTabs();
  gridEl.innerHTML = "";
  MANIFEST.forEach(item => {
    const cell = document.createElement("div");
    cell.className = "cell" + (marks[current].has(item.id) ? " on" : "");
    cell.title = item.filename;
    const img = document.createElement("img");
    img.src = item.thumb;
    img.loading = "lazy";
    img.alt = "";
    cell.appendChild(img);
    cell.onclick = () => {
      const set = marks[current];
      set.has(item.id) ? set.delete(item.id) : set.add(item.id);
      cell.classList.toggle("on");
      countEl.textContent = set.size;
      renderTabs();
      persist();
    };
    gridEl.appendChild(cell);
  });
}

document.getElementById("save").onclick = () => {
  const out = {};
  QUERIES.forEach(q => out[q.id] = [...marks[q.id]].sort());
  const blob = new Blob([JSON.stringify(out, null, 2)], {type: "application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "ground_truth.json";
  a.click();
  const status = document.getElementById("status");
  status.hidden = false;
  status.textContent = "נשמר. העבר את ground_truth.json מתיקיית ההורדות לתיקיית העבודה, והרץ step4_score.py";
};

render();
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default="_sift_workspace")
    ap.add_argument("--queries", default="queries.json")
    args = ap.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    manifest = load_json(workspace / "manifest.json")
    if not manifest:
        die("לא נמצא manifest.json. הרץ קודם את step1_sample.py")

    queries = load_json(Path(args.queries).expanduser())
    if not queries:
        die("לא נמצא queries.json")

    slim = [
        {"id": i["id"], "thumb": i["thumb"], "filename": i["filename"]} for i in manifest
    ]
    html = TEMPLATE.replace("__MANIFEST__", json.dumps(slim, ensure_ascii=False))
    html = html.replace(
        "__QUERIES__",
        json.dumps(
            [
                {"id": q["id"], "label": q["label"], "note": q.get("note", "")}
                for q in queries
            ],
            ensure_ascii=False,
        ),
    )

    out = workspace / "label.html"
    out.write_text(html, encoding="utf-8")

    print(f"נוצר: {out}")
    print(f"\nפתח את הקובץ בדפדפן, סמן לכל שאילתה את התמונות המתאימות,")
    print("ולחץ על כפתור השמירה. אז העבר את ground_truth.json לתיקיית העבודה.")
    print(f"\n{len(slim):,} תמונות · {len(queries)} שאילתות")


if __name__ == "__main__":
    main()
