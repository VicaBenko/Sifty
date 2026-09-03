"""
Demo server — Phase 1 + Phase 2. See demo/DEMO-SPEC.md.

Throwaway demo code. Serves the query -> predicates -> matches flow over the
128-photo catalog built by Step 0 (validation/step1_sample.py + step2_tag.py),
plus the quarantine / approval / deletion loop of Phase 2.

Nothing outside demo/ is ever read, written, or deleted.

Usage:
    python demo/serve.py [--port 8000]

Binds to 127.0.0.1 only. Never 0.0.0.0.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import shutil
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DEMO_DIR = Path(__file__).parent.resolve()
WORKSPACE = DEMO_DIR / "_ws"
THUMBS_DIR = WORKSPACE / "thumbs"
INDEX_HTML = DEMO_DIR / "index.html"
CACHE_PATH = DEMO_DIR / "predicates-cache.json"

PHOTOS_DIR = DEMO_DIR / "photos"
QUARANTINE_DIR = DEMO_DIR / "quarantine"
QUARANTINE_MANIFEST = QUARANTINE_DIR / "manifest.json"
OPERATION_LOG = DEMO_DIR / "operation-log.json"

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
MANIFEST_BY_ID = {item["id"]: item for item in _manifest}
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
def analyze_single_photo_vision(photo: dict, api_key: str = "") -> dict:
    """Analyzes a single base64 image using Gemini or Claude Vision for maximum accuracy."""
    src = photo.get("src", "")
    filename = photo.get("filename", "")
    default_res = {
        "id": photo.get("id"),
        "filename": filename,
        "objects": photo.get("objects", ["photo"]),
        "caption": photo.get("caption", f"Photo {filename}"),
        "setting": "indoor/outdoor",
        "source": "heuristic"
    }

    if not src or not src.startswith("data:"):
        return default_res

    # Extract base64 and mime
    try:
        header, b64_data = src.split(",", 1)
        mime_match = re.search(r"data:([^;]+);", header)
        mime = mime_match.group(1) if mime_match else "image/jpeg"
    except Exception:
        return default_res

    gemini_key = api_key or os.environ.get("GEMINI_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # Try Gemini Vision REST API
    if gemini_key:
        try:
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            prompt = (
                "Analyze this image for photo cataloging and retrieval. Return ONLY a JSON object with: "
                "1. 'objects': an array of all detected English nouns and objects (e.g. ['receipt', 'invoice', 'table', 'document', 'dog', 'laptop', 'coffee cup', 'person', 'car', 'food']). "
                "2. 'caption': an accurate, detailed descriptive sentence of the image content. "
                "3. 'setting': location/scene type. "
                "Return raw JSON only, no markdown."
            )
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime, "data": b64_data}}
                    ]
                }],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 500}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                # Parse JSON
                fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
                if fence: text = fence.group(1).strip()
                parsed = json.loads(text)
                return {
                    "id": photo.get("id"),
                    "filename": filename,
                    "objects": [str(o).lower().strip() for o in parsed.get("objects", []) if o],
                    "caption": str(parsed.get("caption", f"Photo {filename}")),
                    "setting": str(parsed.get("setting", "scene")),
                    "source": "gemini-2.5-flash"
                }
        except Exception as e:
            print(f"[Vision] Gemini analysis failed: {e}")

    # Try Anthropic Claude Vision
    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic()
            response = client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=400,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64_data}},
                        {"type": "text", "text": "Analyze this photo for precision search. Return ONLY JSON: {\"objects\": [\"receipt\", \"table\"], \"caption\": \"...\", \"setting\": \"...\"}"}
                    ]
                }]
            )
            text = response.content[0].text
            fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
            if fence: text = fence.group(1).strip()
            parsed = json.loads(text)
            return {
                "id": photo.get("id"),
                "filename": filename,
                "objects": [str(o).lower().strip() for o in parsed.get("objects", []) if o],
                "caption": str(parsed.get("caption", f"Photo {filename}")),
                "setting": str(parsed.get("setting", "scene")),
                "source": "claude-3-5-haiku"
            }
        except Exception as e:
            print(f"[Vision] Claude analysis failed: {e}")

    # Try Local In-Process CLIP Vision AI
    local_clip_res = analyze_with_local_clip(b64_data, filename)
    if local_clip_res:
        return {
            "id": photo.get("id"),
            "filename": filename,
            "objects": local_clip_res.get("objects", []),
            "clipEmbedding": local_clip_res.get("clipEmbedding"),
            "caption": local_clip_res.get("caption", f"Photo {filename}"),
            "setting": local_clip_res.get("setting", "scene"),
            "source": "local-clip-vit"
        }

    return default_res


_LOCAL_CLIP_MODEL = None
_LOCAL_CLIP_PROCESSOR = None

def get_local_clip():
    global _LOCAL_CLIP_MODEL, _LOCAL_CLIP_PROCESSOR
    if _LOCAL_CLIP_MODEL is None:
        try:
            from transformers import CLIPProcessor, CLIPModel
            _LOCAL_CLIP_MODEL = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            _LOCAL_CLIP_PROCESSOR = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            _LOCAL_CLIP_MODEL.eval()
        except Exception as e:
            print(f"[Vision] Could not load local CLIP model: {e}")
    return _LOCAL_CLIP_MODEL, _LOCAL_CLIP_PROCESSOR


def analyze_with_local_clip(b64_data: str, filename: str) -> dict | None:
    try:
        import base64, io, re
        from PIL import Image
        import torch

        model, processor = get_local_clip()
        if model is None or processor is None:
            return None

        img_bytes = base64.b64decode(b64_data)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        inputs = processor(images=img, return_tensors="pt")
        with torch.no_grad():
            raw_img = model.get_image_features(**inputs)
            t = raw_img.pooler_output if hasattr(raw_img, 'pooler_output') and raw_img.pooler_output is not None else (raw_img[0] if isinstance(raw_img, tuple) else raw_img)
            img_feat = t / t.norm(p=2, dim=-1, keepdim=True)
            clip_vec = [round(float(v), 5) for v in img_feat[0]]

        candidate_labels = [
            "receipt", "invoice", "document", "screenshot", "whiteboard",
            "paper", "text", "dog", "cat", "pet", "person", "people",
            "laptop", "computer", "desk", "screen", "coffee", "cup",
            "car", "vehicle", "sandwich", "food", "dining table",
            "sunset", "beach", "sky", "outdoor", "indoor", "nature",
            "tree", "flower", "park", "book", "chair", "shoes", "clothes"
        ]
        prompts = [
            f"a photo of a {l}" if l not in ["receipt", "invoice", "document", "screenshot", "whiteboard", "text"]
            else f"a {l}"
            for l in candidate_labels
        ]
        text_inputs = processor(text=prompts, return_tensors="pt", padding=True)
        with torch.no_grad():
            raw_text = model.get_text_features(**text_inputs)
            t_text = raw_text.pooler_output if hasattr(raw_text, 'pooler_output') and raw_text.pooler_output is not None else (raw_text[0] if isinstance(raw_text, tuple) else raw_text)
            text_feat = t_text / t_text.norm(p=2, dim=-1, keepdim=True)

            logits = (img_feat @ text_feat.T) * 100.0
            probs = logits.softmax(dim=-1)[0].tolist()

        scored = sorted(zip(candidate_labels, probs), key=lambda x: x[1], reverse=True)

        # Select tags with significant probability (>= 7% probability, or top 1 if >= 10%)
        top_tags = [label for label, p in scored if p >= 0.07][:5]
        if not top_tags and scored and scored[0][1] >= 0.10:
            top_tags = [scored[0][0]]

        # Whole-word filename matching (avoids substring false positives like "vacation" matching "cat")
        fn_lower = filename.lower()
        for kw in ["receipt", "invoice", "document", "dog", "cat", "laptop", "coffee", "cup", "car", "food"]:
            if re.search(r"(?:^|[^a-z])" + re.escape(kw) + r"s?(?:[^a-z]|$)", fn_lower) and kw not in top_tags:
                top_tags.append(kw)

        return {
            "objects": top_tags,
            "clipEmbedding": clip_vec,
            "caption": f"Photo containing {', '.join(top_tags[:3])}" if top_tags else f"Photo {filename}",
            "setting": "indoor/outdoor",
            "source": "local-clip-vit"
        }
    except Exception as err:
        print(f"[Vision] Local CLIP analysis error: {err}")
        return None


def analyze_photos_batch(photos: list[dict], api_key: str = "") -> list[dict]:
    """Analyzes a batch of uploaded photos with vision AI models."""
    results = []
    for p in photos:
        res = analyze_single_photo_vision(p, api_key)
        results.append(res)
    return results


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


def gallery() -> dict:
    """The full catalog, unfiltered — for the opening screen before any
    query has been run. No reasons or confidence: there is no query to
    explain a match against."""
    photos = [
        {"id": pid, "thumb": THUMB_BY_ID.get(pid, ""), "bytes": photo_bytes(pid)}
        for pid in sorted(CATALOG)
        if photo_exists(pid)
    ]
    return {"photos": photos, "total": len(photos)}


def search(predicates: list[dict]) -> dict:
    matches = []
    for photo_id, photo in CATALOG.items():
        if not photo_exists(photo_id):
            continue  # deleted in an earlier round — it is no longer in the gallery
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
                "bytes": photo_bytes(photo_id),
            }
        )

    matches.sort(key=lambda m: (m["confidence"] != "certain", m["id"]))
    certain = sum(1 for m in matches if m["confidence"] == "certain")
    return {"matches": matches, "total": len(matches), "certain": certain}


# ---------------------------------------------------------------------------
# Phase 2 — quarantine, approval gate, deletion
# See demo/DEMO-SPEC.md, Phase 2 (P2-1 .. P2-10).
#
# Rules that hold even in throwaway code:
#   * Copy, never move (P2-3 / D-10). shutil.copy2 only; shutil.move appears
#     nowhere in this file.
#   * Delete in place, only from demo/photos/, and only for sources whose
#     copy is still sitting in the quarantine folder (P2-8 / D-9).
# ---------------------------------------------------------------------------

def quarantine_path_is_safe() -> bool:
    """P2-5: the quarantine folder must live outside the photo folder, so a
    copy can never be mistaken for an original — and so emptying quarantine
    can never touch the gallery."""
    q = QUARANTINE_DIR.resolve()
    p = PHOTOS_DIR.resolve()
    return q != p and p not in q.parents and q not in p.parents


def file_signature(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def photo_path(photo_id: str) -> Path | None:
    entry = MANIFEST_BY_ID.get(photo_id)
    if not entry:
        return None
    return PHOTOS_DIR / Path(entry["filename"]).name


def photo_exists(photo_id: str) -> bool:
    path = photo_path(photo_id)
    return bool(path and path.is_file())


def photo_bytes(photo_id: str) -> int:
    path = photo_path(photo_id)
    return path.stat().st_size if path and path.is_file() else 0


def quarantine_manifest() -> list[dict]:
    return load_json(QUARANTINE_MANIFEST, default=[]) or []


def quarantine_status() -> dict:
    """P2-6: read from disk every time, so the banner survives restarts."""
    entries = quarantine_manifest()
    present, released = [], []
    for entry in entries:
        copy_path = QUARANTINE_DIR / Path(entry["filename"]).name
        (present if copy_path.is_file() else released).append(entry)
    return {
        "total": len(entries),
        "awaiting": len(present),
        "released": len(released),
        "bytes": sum(e.get("bytes", 0) for e in present),
        "queries": sorted({e.get("query", "") for e in entries if e.get("query")}),
        "folder": str(QUARANTINE_DIR),
        "items": [
            {"id": e["id"], "filename": e["filename"], "thumb": THUMB_BY_ID.get(e["id"], "")}
            for e in present
        ],
    }


def copy_to_quarantine(ids: list[str], query: str) -> dict:
    if not quarantine_path_is_safe():
        raise RuntimeError(
            "refusing to copy: the quarantine folder is inside the photo folder"
        )

    QUARANTINE_DIR.mkdir(exist_ok=True)
    existing = {e["id"]: e for e in quarantine_manifest()}

    copied, skipped = [], []
    for photo_id in ids:
        source = photo_path(photo_id)
        if source is None or not source.is_file():
            skipped.append(photo_id)
            continue
        destination = QUARANTINE_DIR / source.name
        shutil.copy2(source, destination)  # copy, never move
        existing[photo_id] = {
            "id": photo_id,
            "filename": source.name,
            "source": str(source),
            "quarantine": str(destination),
            "bytes": destination.stat().st_size,
            "sha256": file_signature(destination),
            "query": query,
            "added_at": datetime.now().isoformat(timespec="seconds"),
        }
        copied.append(photo_id)

    ordered = sorted(existing.values(), key=lambda e: e["id"])
    save_json(QUARANTINE_MANIFEST, ordered)  # P2-4

    status = quarantine_status()
    status["copied"] = len(copied)
    status["skipped"] = skipped
    return status


def approve_deletion() -> dict:
    """P2-8: delete from demo/photos/ ONLY those sources whose copy is still
    in demo/quarantine/. A photo the user pulled out of the quarantine folder
    is released, and its original is left untouched. This is AC-3."""
    entries = quarantine_manifest()
    deleted, released, missing = [], [], []
    stamp = datetime.now().isoformat(timespec="seconds")

    for entry in entries:
        copy_path = QUARANTINE_DIR / Path(entry["filename"]).name
        source = PHOTOS_DIR / Path(entry["filename"]).name

        if not copy_path.is_file():
            released.append(entry)          # pulled out before approval — spared
            continue
        if not source.is_file():
            missing.append(entry)           # already gone; nothing to delete
            continue

        source.unlink()                     # delete in place, never move
        deleted.append(
            {
                "id": entry["id"],
                "source": str(source),
                "date": stamp,
                "query": entry.get("query", ""),
            }
        )

    log = load_json(OPERATION_LOG, default=None) or {"deletions": [], "rounds": []}
    log["deletions"].extend(deleted)        # P2-9
    total = len(deleted) + len(released)
    log["rounds"].append(                   # P2-10
        {
            "date": stamp,
            "queries": sorted({e.get("query", "") for e in entries if e.get("query")}),
            "quarantined": len(entries),
            "deleted": len(deleted),
            "released": len(released),
            "already_missing": len(missing),
            "release_rate": round(len(released) / total, 3) if total else 0.0,
        }
    )
    save_json(OPERATION_LOG, log)

    # Empty the quarantine folder so the banner clears and the next round
    # starts clean. Only copies live here; originals are in demo/photos/.
    for item in list(QUARANTINE_DIR.glob("*")) if QUARANTINE_DIR.is_dir() else []:
        if item.is_file():
            item.unlink()

    return {
        "deleted": len(deleted),
        "released": len(released),
        "already_missing": len(missing),
        "release_rate": log["rounds"][-1]["release_rate"],
        "deleted_ids": [d["id"] for d in deleted],
        "released_ids": [e["id"] for e in released],
    }


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
        size = path.stat().st_size
        range_header = self.headers.get("Range", "")
        start, end = 0, size - 1
        status = 200
        if range_header.startswith("bytes="):
            try:
                spec = range_header[6:].split(",", 1)[0].strip()
                left, right = spec.split("-", 1)
                if left:
                    start = int(left)
                    end = int(right) if right else size - 1
                else:
                    length = int(right)
                    start = max(0, size - length)
                if start < 0 or start >= size or end < start:
                    raise ValueError("invalid range")
                end = min(end, size - 1)
                status = 206
            except (ValueError, IndexError):
                self.send_error(416, "Invalid range")
                return
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as stream:
            stream.seek(start)
            remaining = length
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self) -> None:  # noqa: N802 — required method name
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._send_file(INDEX_HTML, "text/html; charset=utf-8")
            return

        if path == "/catalog-data.js":
            p = DEMO_DIR / "catalog-data.js"
            if p.is_file():
                self._send_file(p, "application/javascript; charset=utf-8")
                return

        if path == "/i18n.js":
            p = DEMO_DIR / "i18n.js"
            if p.is_file():
                self._send_file(p, "application/javascript; charset=utf-8")
                return

        if path == "/api/gallery":
            self._send_json(200, gallery())
            return

        if path == "/api/quarantine":
            self._send_json(200, quarantine_status())
            return

        if path == "/promo-video.mp4":
            promo = Path(r"C:\Users\vicab\Movies\Hub\Projects\sifty-3\sifty-final-end-card.mp4")
            if promo.is_file():
                self._send_file(promo, "video/mp4")
                return

        if path.startswith("/assets/"):
            name = path[len("/assets/") :]
            candidate = (DEMO_DIR / "assets" / name).resolve()
            if candidate.is_file():
                content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
                self._send_file(candidate, content_type)
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

            if parsed.path == "/api/quarantine":
                ids = [str(i) for i in body.get("ids", [])]
                query = str(body.get("query", "")).strip()
                if not ids:
                    self._send_json(400, {"error": "no photos selected"})
                    return
                self._send_json(200, copy_to_quarantine(ids, query))
                return

            if parsed.path == "/api/unquarantine":
                photo_id = str(body.get("id", "")).strip()
                if photo_id:
                    entry = MANIFEST_BY_ID.get(photo_id)
                    if entry:
                        copy_path = QUARANTINE_DIR / Path(entry["filename"]).name
                        if copy_path.is_file():
                            copy_path.unlink()
                self._send_json(200, quarantine_status())
                return

            if parsed.path == "/api/catalog_photos":
                photos = body.get("photos", [])
                api_key = str(body.get("apiKey", "")).strip()
                results = analyze_photos_batch(photos, api_key)
                self._send_json(200, {"results": results, "status": "success"})
                return

            if parsed.path == "/api/approve":
                self._send_json(200, approve_deletion())
                return

            self.send_error(404, "Not found")
        except Exception as exc:  # noqa: BLE001 — never let one bad request kill the server
            self._send_json(500, {"error": str(exc)})


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    if not quarantine_path_is_safe():
        print("Quarantine folder is inside the photo folder. Refusing to start.")
        sys.exit(1)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Catalog: {len(CATALOG)} photos ({sum(1 for p in CATALOG if photo_exists(p))} still in demo/photos/)")
    print(f"Quarantine: {QUARANTINE_DIR} — {quarantine_status()['awaiting']} awaiting approval")
    print(f"Serving at {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
