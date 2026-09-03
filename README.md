# 🦉 Sifty

**Natural-Language Search & Curation for Photo Galleries.**

> **Stop scrolling. Start asking.** 🔎✨  
> Tell Sifty what you want to find. Review what it found. Keep full control of your gallery.

---

## 🌐 Live Demo

Try Sifty directly in your browser with zero installation:  
🔗 **[https://vicabenko.github.io/Sifty/](https://vicabenko.github.io/Sifty/)**

---

## ✨ Key Capabilities

* **💬 Contextual Natural-Language Search:** Query photos using everyday open-vocabulary descriptions (e.g. *"whiteboard notes"*, *"parking ticket receipt"*, *"golden retriever puppy"*, *"blurry concert shots"*, *"coffee on wooden desk"*).
* **🧠 Transformers.js (CLIP) Vision AI:** Powered by multi-modal Vision-Language embeddings. Translates text and images into a shared 512-dimensional vector space for instant, sub-millisecond semantic search.
* **🧾 Smart Document & Artifact Detection:** Instantly surfaces receipts, tax invoices, contracts, whiteboards, and screenshots without relying on manual tagging.
* **🛡️ Safe Quarantine & Human-in-the-Loop Review:** Matches are **copied** (never moved) into an approval quarantine folder. Review what was found and take back anything you want before confirming any batch actions.
* **🔒 100% Privacy-First (Zero Data Retention):** All processing runs locally in the browser or on your local machine. No photos or personal media ever leave your device.
* **⚡ Instant Pre-Indexed Demo Gallery:** 128 curated photos with pre-computed vector embeddings for instant zero-latency exploration.

---

## 🚀 Run Locally

### Prerequisites
* Python 3.8+ (with PyTorch and Transformers for local AI acceleration)
* Modern web browser (Chrome, Safari, Edge, Firefox)

### Quickstart on Windows
Double-click:
```cmd
RUN-DEMO.bat
```

Or from the terminal:
```bash
python demo/serve.py --port 8091
```

Then open:
```text
http://127.0.0.1:8091
```

---

## 📁 Repository Structure

```text
├── index.html                   # Standalone single-file production build (for GitHub Pages)
├── RUN-DEMO.bat                 # One-click Windows local demo launcher
├── README.md                    # This document
│
├── demo/                        # Working interactive demo application
│   ├── index.html               # Source web application & UI
│   ├── serve.py                 # Local HTTP server with built-in CLIP AI vision API
│   ├── catalog-data.js          # Demo catalog with pre-computed 512-D CLIP embeddings
│   ├── generate_clip_embeddings.py # Tool to generate & refresh CLIP embeddings
│   ├── build_site.py            # Bundles source into standalone index.html
│   ├── reset.py                 # Resets demo state and quarantine baseline
│   ├── test_matching.py         # Regression tests for search matching engine
│   └── _ws/                     # Demo workspace (catalog, manifest, thumbnails)
│
├── docs/                        # Complete project documentation (14 numbered specs)
│   ├── 00-README.md             # Documentation map & reading order
│   ├── 01-product-brief.md      # Product brief and scope
│   ├── 02-decision-memo-001-architecture.md # Core architectural decisions
│   ├── 03-decision-memo-002-platform.md     # Platform decisions (local engine + browser)
│   ├── 04-validation-gate-protocol.md       # Validation protocols
│   ├── 05-validation-gate-result.md         # Gate results & risk logs
│   ├── 06-prd.md                # 44 numbered requirements (PRD)
│   ├── 07-process-summary.md    # Planning phase summary
│   ├── 08-handover-to-development.md        # Handover guide
│   ├── 09-ux-decisions.md       # Results screen & UX decisions
│   ├── 10-superpowers-runbook.md            # Build loop runbook
│   ├── 11-monday-demo-status.md             # Demo status & metrics
│   ├── 12-process-retrospective.md          # 18-step project retrospective
│   ├── 13-demo-script.md        # Presentation & demonstration script
│   └── 14-clip-search-engine-upgrade.md     # Transformers.js (CLIP) upgrade specs
│
└── specs/                       # Technical implementation specifications
    ├── 00-global-constraints.md # Global invariants & safety rules
    ├── 01-indexing.md           # Photo indexing specifications
    ├── 02-query.md              # Query decomposition & matching rules
    ├── 03-server-ui.md          # Local server & UI specifications
    ├── 04-quarantine-delete.md  # Quarantine, approval & deletion loop
    └── 05-settings-cost-log.md  # Settings and operation logs
```

---

## 📚 Where to Start in the Docs

* **Full Story & Process:** [`docs/12-process-retrospective.md`](docs/12-process-retrospective.md)
* **Search Engine Upgrade (CLIP):** [`docs/14-clip-search-engine-upgrade.md`](docs/14-clip-search-engine-upgrade.md)
* **Product Requirements (PRD):** [`docs/06-prd.md`](docs/06-prd.md)
* **Presenting / Demo Script:** [`docs/13-demo-script.md`](docs/13-demo-script.md)

---

## 🦉 Why Sifty?

Because your camera roll should be a library — not a junk drawer.  
Made as a personal creative project with curiosity, code, and way too many photos.
