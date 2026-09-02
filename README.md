# 🦉 Sifty — Smart AI Photo Curation & Organization

> **An on-device AI curation platform that filters, sorts, and organizes photo galleries using natural language — with maximum accuracy, zero cloud data retention, and instant clean ZIP export.**

---

## 🌐 Live Demo
✨ **[Experience Sifty Live on GitHub Pages](https://vicab.github.io/Sift/)** ✨

*(If you push to a different repository, your link will be: `https://<YOUR_GITHUB_USERNAME>.github.io/<YOUR_REPO_NAME>/`)*

---

## ✨ Key Features

- ⚡ **On-Device Vision AI**: Powered by in-browser neural computer vision (COCO-SSD / Multimodal Vision) to accurately detect receipts, screenshots, documents, pets, objects, and complex scenes.
- 🛡️ **Zero Data Retention (100% In-Memory)**: Your photos are processed exclusively in local session memory. No images or metadata are ever saved or uploaded to external cloud servers.
- 📦 **Instant Clean ZIP Export**: Quarantine unwanted photos, verify with a transparent approval gate, and download your organized gallery directly to your machine.
- 🌍 **Multilingual Support (11 Languages)**: Seamless localization in English, Hebrew (RTL), Arabic, Russian, Chinese, Spanish, French, Italian, German, Portuguese, and Japanese.
- 🧮 **Interactive Scope & Cost Estimator**: Real-time interactive calculation for time saved, storage freed, and transparent pay-per-batch pricing.
- ♿ **Full Accessibility (WCAG 2.1 AA Compliant)**: Built-in accessibility toolbar with text scaling, high-contrast modes, legible typography, and comprehensive keyboard/screen-reader navigation.

---

## 🚀 Quick Start & Local Setup

Want to run Sifty locally on your machine?

### Easy 1-Click Launch (Windows):
Simply double-click:
```text
RUN-DEMO.bat
```
This restores the sample catalog and launches your default browser at `http://127.0.0.1:8091`.

### Terminal Command:
```bash
python demo/serve.py --port 8091
```

---

## 📂 Repository Structure

| Directory / File | Description |
| :--- | :--- |
| 📁 `demo/` | **Single Source of Truth** — contains `index.html`, `serve.py`, sample photo catalog, and vision engine logic |
| 📁 `dist/` | Production-ready static build for GitHub Pages / web hosting (auto-generated) |
| 📁 `docs/` | Comprehensive architecture specifications, design documents, and project retrospective |
| 📄 `sifty-single.html` | Completely self-contained single-file HTML build with all scripts and image assets embedded |
| 📄 `RUN-DEMO.bat` | 1-click launcher for Windows local demo |

---

## 🛠️ Building & Updating the Site

When modifying the UI, edit **`demo/index.html`** and rebuild the distribution bundles with:

```bash
python demo/build_site.py
```

This automatically regenerates `dist/` and `sifty-single.html`.

---

## 📄 License & Credits
© 2026 Sifty Technologies Ltd. Open demonstration project built as part of the Moshal AI Workshop.
