# C.A.R.P. (Computer-Assisted Recognition & Perception)

Real-time koi **variety classification** and **individual identification** for
[ChampKoi](https://champkoi.com). This is a senior design project.

- **Mobile app (customers):** point a phone at a koi to see its variety and, if it's for sale,
  the matching ChampKoi listing.
- **Pond nodes (ChampKoi staff):** Raspberry Pis mounted over the ponds recognise individual
  fish as they swim, so the system knows which pond each koi is in after fish are moved.

Both run the same pipeline, trained on ChampKoi's Shopify listings:

```
image/frame ─► detect koi + head/tail keypoints ─► align to head-down crop ─┬─► variety classifier ─► "Showa, ginrin"
                                                                            └─► embedder ─► gallery search ─► "fish v5282…, 0.91"
```

Identification is a **similarity search**, not a classifier. Adding or selling a fish updates
the gallery, and nothing needs retraining. Read [docs/architecture.md](docs/architecture.md)
for the full design and [CONTEXT.md](CONTEXT.md) for project vocabulary.

## Repository layout

| Path | What's there |
|---|---|
| `src/carp/shopify/` | Bulk export of koi listings and their variety metafields |
| `src/carp/data/` | Dataset manifest (one row per fish per photo) and leak-free splits |
| `src/carp/vision/` | Model interfaces, head-down alignment, group-photo letter matching |
| `src/carp/index/` | Embedding gallery for identification |
| `src/carp/tracking/` | Per-track aggregation into pond sightings |
| `src/carp/pond/` | Raspberry Pi pond node loop with offline spooling |
| `src/carp/api/` | FastAPI service for sightings (later gallery sync) |
| `apps/shopify/` | Config-only Shopify app granting read-only Admin API scopes |
| `training/` | Training and export plan, experiments |
| `apps/mobile/` | Phone app (planned) |
| `docs/` | Architecture, data, hardware, decision records (`docs/adr/`) |

## Getting started

Requires Python 3.11+.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Extras: `.[train]` (PyTorch, timm, Ultralytics), `.[vision]` (OpenCV, ONNX Runtime), `.[api]`.

### Pull the dataset from Shopify

CARP reads Shopify through a read-only app in [`apps/shopify`](apps/shopify/README.md). You
need three private files, shared by a teammate or created from the committed examples:

| File | From | Holds |
|---|---|---|
| `.env` | `.env.example` | Store domain, app client ID and secret |
| `config/shopify.local.toml` | `config/shopify.example.toml` | The store's product types and metafield keys |
| `apps/shopify/shopify.app.<name>.toml` | `apps/shopify/shopify.app.toml.example` | App config for the Shopify CLI |

```bash
set -a; source .env; set +a
carp ingest-shopify --out data/shopify --download-images
```

This writes `data/shopify/manifest.jsonl` and the images. All three files, `data/` and
`private/` are git-ignored: **never commit photos, inventory data, store config or credentials.**
See [docs/data.md](docs/data.md).

### Run the API

```bash
pip install -e '.[api]'
uvicorn carp.api.app:app --reload
```

## Milestones

| # | Milestone | Done when |
|---|---|---|
| M0 | Dataset | Manifest built, group-photo letters matched, variety counts reviewed |
| M1 | Variety classifier | Base variety + attributes baseline with confusion matrix on test split |
| M2 | Detector + keypoints | Koi boxes and head/tail keypoints on listing and pond images |
| M3 | Identification | Retrieval top-1/top-5 on held-out fish; fine-tuned embedder beats DINOv2 baseline |
| M4 | Pond node | One Pi over one pond posting sightings end to end |
| M5 | Mobile app | On-device classify + identify, links to listing |
| M6 | Field evaluation | Accuracy and latency measured at ChampKoi; final report |

## License

[AGPL-3.0](LICENSE). CARP uses Ultralytics YOLO, which is AGPL-3.0, and Ultralytics treats
software and trained models built with it as AGPL-3.0 too. Anyone distributing CARP, including
an app with a YOLO-trained model or a network service built on it, must share the full source
under the same license. A closed-source deployment would need an Ultralytics enterprise license
or an Apache-licensed detector swapped in behind `KoiDetector`. See
[ADR 0001](docs/adr/0001-python-monorepo.md).
