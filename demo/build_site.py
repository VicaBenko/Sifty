"""Build the publishable version of Sifty from demo/index.html.

Outputs:
  index.html (project root) -> one self-contained file ready for GitHub Pages

Usage:  python demo\build_site.py
"""
import base64, io, os, re, shutil
from pathlib import Path

DEMO = Path(__file__).parent.resolve()
ROOT = DEMO.parent
PAGE_ASSETS = ["owl_mascot.jpg", "sifty_key_visual.jpg", "promo_scene1.jpg", "promo_scene2.jpg", "promo_scene3.jpg"]

src = (DEMO / "index.html").read_text(encoding="utf-8")

# the local server resolves both tags; a static host needs exactly one
src = src.replace('<script src="demo/catalog-data.js"></script>', "")
src = src.replace('src="/assets/', 'src="assets/')

# ---- single-file build -------------------------------------------------
single = src.replace(
    '<script src="catalog-data.js"></script>',
    "<script>\n" + (DEMO / "catalog-data.js").read_text(encoding="utf-8") + "\n</script>",
)
try:
    from PIL import Image  # recompress so the single file stays small
    for name in PAGE_ASSETS:
        im = Image.open(DEMO / "assets" / name).convert("RGB")
        im.thumbnail((1200, 1200))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85, optimize=True, progressive=True)
        data = buf.getvalue()
        single = single.replace("assets/" + name, "data:image/jpeg;base64," + base64.b64encode(data).decode())
except ImportError:
    for name in PAGE_ASSETS:
        data = (DEMO / "assets" / name).read_bytes()
        single = single.replace("assets/" + name, "data:image/jpeg;base64," + base64.b64encode(data).decode())

(ROOT / "index.html").write_text(single, encoding="utf-8")

mb = lambda p: round(p.stat().st_size / 1e6, 2)
print(f"index.html -> {mb(ROOT / 'index.html')} MB (self-contained, ready for GitHub Pages)")
