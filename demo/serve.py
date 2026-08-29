"""
Demo server — Phase 1 only. See demo/DEMO-SPEC.md.

Throwaway demo code. Serves the query -> predicates -> matches flow over the
128-photo catalog built by Step 0 (validation/step1_sample.py + step2_tag.py).

Usage:
    python demo/serve.py [--port 8000]

Binds to 127.0.0.1 only. Never 0.0.0.0.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DEMO_DIR = Path(__file__).parent.resolve()
WORKSPACE = DEMO_DIR / "_ws"
THUMBS_DIR = WORKSPACE / "thumbs"
INDEX_HTML = DEMO_DIR / "index.html"
CACHE_PATH = DEMO_DIR / "predicates-cache.json"

MODEL = os.environ.get("SIFT_MODEL", "claude-haiku-4-5")

PREDICATE_PROMPT = """Decompose this photo-search query into predicates: objects
that must ALL be present in a matching photo.

Query: "{query}"

For each predicate, give a short canonical label (lowercase singular noun) and
a list of synonym terms — including the label itself — that might appear as an
object tag, in a caption, or in a scene description for that object. Keep
synonym lists short (2-5 terms) and concrete; don't include the query's other
predicates as synonyms of each other.

Respond with ONLY a JSON array, no other text:
[{{"label": "dog", "terms": ["dog", "puppy", "canine"]}},
 {{"label": "table", "terms": ["table", "desk", "dining table"]}}]"""


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


CATALOG: dict = load_json(WORKSPACE / "catalog.json", default={})
_manifest = load_json(WORKSPACE / "manifest.json", default=[])
THUMB_BY_ID = {item["id"]: item["thumb"] for item in _manifest}
PREDICATE_CACHE: dict = load_json(CACHE_PATH, default={})

if not CATALOG:
    print("demo/_ws/catalog.json is missing or empty. Run Step 0 first (see DEMO-SPEC.md).")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Query -> predicates
# ---------------------------------------------------------------------------

def parse_predicates_response(text: str) -> list[dict]:
    """Models sometimes wrap JSON in prose or code fences. Be forgiving."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    else:
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end > start:
            text = text[start : end + 1]

    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("predicate response was not a JSON array")

    predicates = []
    for item in data:
        label = str(item.get("label", "")).strip().lower()
        terms = [str(t).strip().lower() for t in item.get("terms", []) if str(t).strip()]
        if not label:
            continue
        if label not in terms:
            terms.insert(0, label)
        predicates.append({"label": label, "terms": terms})
    if not predicates:
        raise ValueError("predicate response had no usable predicates")
    return predicates


def call_anthropic_for_predicates(query: str) -> list[dict]:
    import anthropic  # type: ignore — only imported when actually needed

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    headers = {}
    workspace_id = os.environ.get("SIFT_WORKSPACE_ID", "").strip()
    if workspace_id:
        headers["anthropic-workspace-id"] = workspace_id

    client = anthropic.Anthropic(default_headers=headers or None)
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": PREDICATE_PROMPT.format(query=query)}],
    )
    return parse_predicates_response(response.content[0].text)


def fallback_predicates(query: str) -> list[dict]:
    """Never hard-fail: split on commas/"and" and match the words literally."""
    segments = re.split(r",| and ", query, flags=re.IGNORECASE)
    predicates = []
    for segment in segments:
        phrase = segment.strip().lower()
        phrase = re.sub(r"^(a|an|the)\s+", "", phrase)
        if phrase:
            predicates.append({"label": phrase, "terms": [phrase]})
    if not predicates:
        predicates = [{"label": query.strip().lower(), "terms": [query.strip().lower()]}]
    return predicates


def extract_predicates(query: str) -> tuple[list[dict], str]:
    """Returns (predicates, source) where source is cache/api/fallback."""
    if query in PREDICATE_CACHE:
        return PREDICATE_CACHE[query], "cache"

    try:
        predicates = call_anthropic_for_predicates(query)
        PREDICATE_CACHE[query] = predicates
        save_json(CACHE_PATH, PREDICATE_CACHE)
        return predicates, "api"
    except Exception as exc:  # noqa: BLE001 — the demo must never hard-fail on a query
        print(f"[predicates] API extraction failed ({exc}); using literal fallback.")
        return fallback_predicates(query), "fallback"


# ---------------------------------------------------------------------------
# Predicates -> matches
# ---------------------------------------------------------------------------

def word_match(term: str, text: str) -> bool:
    """Whole-word match, allowing a simple plural "s" (e.g. "cat" matches
    "cat" and "cats", but never "catcher" or "location"). Used for the
    caption channel, which is prose."""
    return re.search(r"\b" + re.escape(term) + r"s?\b", text) is not None


# Lexical exception list, NOT synonym tuning: these are fixed compounds
# where the head noun is not the referent a query means (a hot dog is
# food, not a dog) — head-word matching alone would still produce a false
# positive for them, so they are blocked outright.
OBJECT_LEXICAL_EXCEPTIONS: dict[str, set] = {
    "dog": {"hot dog", "hot dogs", "hot dog bun", "corn dog"},
}


def objects_match(term: str, entry: str) -> bool:
    """Head-word match against an object phrase: a term matches only if it
    equals the whole phrase, or equals the phrase's last word (the head
    noun) — so "cup" matches "coffee cup" and "table" matches "dining
    table", but "cat" does not match "cat toy" and "dog" does not match
    "dog house"."""
    entry_l = entry.lower().strip()
    if entry_l in OBJECT_LEXICAL_EXCEPTIONS.get(term, ()):
        return False
    if entry_l == term or entry_l == term + "s":
        return True
    head = entry_l.rsplit(" ", 1)[-1]
    return head == term or head == term + "s"


def channel_for(photo: dict, terms: list[str]) -> str | None:
    for entry in photo.get("objects", []):
        if any(objects_match(term, entry) for term in terms):
            return "objects"
    text = (photo.get("caption", "") + " " + photo.get("setting", "")).lower()
    if any(word_match(term, text) for term in terms):
        return "caption"
    return None


def search(predicates: list[dict]) -> dict:
    matches = []
    for photo_id, photo in CATALOG.items():
        reasons = []
        satisfied = True
        for pred in predicates:
            terms = pred.get("terms") or [pred.get("label", "")]
            ch = channel_for(photo, terms)
            if ch is None:
                satisfied = False
                break
            reasons.append({"label": pred.get("label", ""), "channel": ch})
        if not satisfied:
            continue
        confidence = "certain" if all(r["channel"] == "objects" for r in reasons) else "borderline"
        matches.append(
            {
                "id": photo_id,
                "thumb": THUMB_BY_ID.get(photo_id, ""),
                "reasons": reasons,
                "confidence": confidence,
            }
        )

    matches.sort(key=lambda m: (m["confidence"] != "certain", m["id"]))
    certain = sum(1 for m in matches if m["confidence"] == "certain")
    return {"matches": matches, "total": len(matches), "certain": certain}


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter default logging
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 — required method name
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._send_file(INDEX_HTML, "text/html; charset=utf-8")
            return

        if path.startswith("/_ws/thumbs/"):
            name = path[len("/_ws/thumbs/") :]
            candidate = (THUMBS_DIR / name).resolve()
            if THUMBS_DIR.resolve() not in candidate.parents or not candidate.is_file():
                self.send_error(404, "Not found")
                return
            content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
            self._send_file(candidate, content_type)
            return

        self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802 — required method name
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length else b"{}"

        try:
            body = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON body"})
            return

        try:
            if parsed.path == "/api/predicates":
                query = str(body.get("query", "")).strip()
                if not query:
                    self._send_json(400, {"error": "query is required"})
                    return
                predicates, source = extract_predicates(query)
                self._send_json(200, {"predicates": predicates, "source": source})
                return

            if parsed.path == "/api/search":
                predicates = body.get("predicates", [])
                self._send_json(200, search(predicates))
                return

            self.send_error(404, "Not found")
        except Exception as exc:  # noqa: BLE001 — never let one bad request kill the server
            self._send_json(500, {"error": str(exc)})


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Catalog: {len(CATALOG)} photos")
    print(f"Serving at {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
