"""Generate CLIP embeddings for demo photos and common search queries.

Uses openai/clip-vit-base-patch32 (same architecture and weights as Xenova/clip-vit-base-patch32).
Updates demo/catalog-data.js with clipEmbedding for each photo and queryEmbeddings.
"""
import json
import re
import sys
from pathlib import Path
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel

DEMO_DIR = Path(__file__).parent.resolve()
CATALOG_DATA_JS = DEMO_DIR / "catalog-data.js"
THUMBS_DIR = DEMO_DIR / "_ws" / "thumbs"
WORKSPACE_CATALOG = DEMO_DIR / "_ws" / "catalog.json"

MODEL_NAME = "openai/clip-vit-base-patch32"

print(f"Loading CLIP model: {MODEL_NAME}...")
model = CLIPModel.from_pretrained(MODEL_NAME)
processor = CLIPProcessor.from_pretrained(MODEL_NAME)
model.eval()

def extract_tensor(out):
    if hasattr(out, 'pooler_output') and out.pooler_output is not None:
        return out.pooler_output
    if isinstance(out, tuple):
        return out[0]
    return out

# Common queries to pre-cache so demo works with zero download / zero latency
SAMPLE_QUERIES = [
    "dog", "dogs", "cat", "cats", "bird", "birds", "cup", "coffee cup", "coffee",
    "laptop", "computer", "desk", "car", "cars", "sandwich", "food", "dining table",
    "table", "hot dog", "receipt", "receipts", "invoice", "document", "documents",
    "whiteboard", "notes", "screenshot", "screenshots", "sunset", "beach", "sports",
    "baseball", "catcher", "blurry", "blurry photos", "person", "people", "living room",
    "street", "park", "kitchen", "book", "clock", "chair", "pizza", "motorcycle", "train"
]

print(f"Pre-computing text embeddings for {len(SAMPLE_QUERIES)} common queries...")
text_inputs = processor(text=SAMPLE_QUERIES, return_tensors="pt", padding=True)
with torch.no_grad():
    raw_text = model.get_text_features(**text_inputs)
    text_features = extract_tensor(raw_text)
    text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)

query_embeddings = {}
for q, feat in zip(SAMPLE_QUERIES, text_features):
    query_embeddings[q.lower()] = [round(float(v), 5) for v in feat]

# Load catalog data JS
print("Reading catalog-data.js...")
js_content = CATALOG_DATA_JS.read_text(encoding="utf-8")
match = re.search(r"window\.SIFT_CATALOG_DATA\s*=\s*(\{.*\});?", js_content, re.DOTALL)
if not match:
    print("Could not find window.SIFT_CATALOG_DATA in catalog-data.js")
    sys.exit(1)

catalog_data = json.loads(match.group(1))
photos = catalog_data.get("photos", [])
print(f"Found {len(photos)} photos to process...")

for i, p in enumerate(photos):
    pid = p["id"]
    thumb_path = THUMBS_DIR / f"{pid}.jpg"
    if not thumb_path.exists():
        print(f"Warning: {thumb_path} not found")
        continue

    img = Image.open(thumb_path).convert("RGB")
    image_inputs = processor(images=img, return_tensors="pt")
    with torch.no_grad():
        raw_img = model.get_image_features(**image_inputs)
        image_features = extract_tensor(raw_img)
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)

    vec = [round(float(v), 5) for v in image_features[0]]
    p["clipEmbedding"] = vec

    if (i + 1) % 20 == 0 or i == len(photos) - 1:
        print(f"Processed {i + 1}/{len(photos)} photos...")

catalog_data["queryEmbeddings"] = query_embeddings

# Save back to demo/catalog-data.js
print("Writing updated catalog-data.js...")
new_js = f"window.SIFT_CATALOG_DATA = {json.dumps(catalog_data, ensure_ascii=False)};"
CATALOG_DATA_JS.write_text(new_js, encoding="utf-8")

# Also update demo/_ws/catalog.json if exists
if WORKSPACE_CATALOG.exists():
    try:
        ws_data = json.loads(WORKSPACE_CATALOG.read_text(encoding="utf-8"))
        for p in photos:
            pid = p["id"]
            if pid in ws_data:
                ws_data[pid]["clipEmbedding"] = p.get("clipEmbedding")
        WORKSPACE_CATALOG.write_text(json.dumps(ws_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Updated demo/_ws/catalog.json")
    except Exception as e:
        print(f"Note updating workspace catalog: {e}")

print("Done! CLIP embeddings successfully generated.")
