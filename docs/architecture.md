# Architecture

## Goals

1. **Classify variety** from a photo or live camera: base variety plus attributes
   (ginrin, doitsu, butterfly fin, tancho, ...).
2. **Identify individual fish** against ChampKoi's inventory, both for customers on phones and
   for staff tracking which pond each fish is in.
3. **Run in real time on the edge**: phones and Raspberry Pis, not just a GPU server.

## Components

```
                ┌────────────────────── Training (laptop / GPU / Colab) ──────────────────────┐
Shopify ──bulk──►  manifest ─► label & review ─► detector+keypoints ─► classifier ─► embedder │
  export        │                                                   └──── export: ONNX, TFLite, (Hailo HEF)
                └──────────────────────────────────┬──────────────────────────────────────────┘
                                                   │ models + gallery (vectors of available fish)
                    ┌──────────────────────────────┼──────────────────────────────┐
                    ▼                              ▼                              ▼
             Mobile app                       CARP API                      Pond nodes (Pi)
      on-device detect/classify/embed   gallery + listing metadata     detect → track → embed
      local gallery search              sightings store                sightings → API (spooled)
      link to champkoi.com listing      "where is fish X?"
```

## The shared pipeline

1. **Detect** koi with a box and **head/tail keypoints** (YOLO pose-style model, 2 keypoints).
2. **Align**: rotate and scale each fish to the canonical head-down crop
   (`carp.vision.align`). Listing photos already use this pose, so training data and live
   inputs look alike ([ADR 0003](adr/0003-head-down-canonical-crops.md)).
3. **Classify**: a shared backbone with a base-variety head (softmax) and an attribute head
   (sigmoid) ([ADR 0004](adr/0004-variety-labels.md)).
4. **Embed**: an embedding model maps the crop to an L2-normalised vector.
5. **Search** the gallery by cosine similarity, optionally restricted to the top predicted
   varieties ([ADR 0002](adr/0002-identification-as-retrieval.md)).

## Mobile app

- Runs detection, classification and embedding **on device**. The live camera preview needs
  low latency, and pond-side signal is unreliable.
- Downloads the gallery (embeddings + fish ID + listing URL for fish currently for sale).
  A few thousand fish at float16 is a few MB, so search is local too.
- Shows variety info from the variety metaobject (description, confusion points) and a
  link to the listing.
- Framework decision in [ADR 0005](adr/0005-edge-deployment.md).

## Pond nodes

- Top-down camera over each pond. Detector runs at a modest frame rate (koi are slow, and
  ~5–10 fps is enough for tracking).
- Tracks each fish, keeps its best views and identifies once per track
  (`carp.tracking.sightings`). This is cheaper and more robust than per-frame matching.
- Posts sightings to the API. They're spooled to disk first so outages lose nothing.
- The gallery is **all** ChampKoi fish, not just one pond's, since fish move between ponds.
  Last-known pond can later be used as a prior.
- Fish that aren't listed yet come back as **unknown** sightings. Their embeddings can be
  clustered and labelled to grow the gallery.

## API (planned endpoints)

| Endpoint | Status |
|---|---|
| `POST /sightings`, `GET /ponds/{id}/sightings`, `GET /fish/{id}/last-seen` | Stub, in-memory |
| `GET /gallery` (versioned vectors + metadata for phones and nodes) | Planned (M3) |
| `POST /identify` (server-side fallback for older phones) | Planned (M5) |
| Persistence (Postgres + pgvector) | Planned (M4) |

## Integration points to decide with ChampKoi

- Whether sightings should ever update the `pond_id` field in Shopify (suggested: human-confirmed
  suggestions only, never automatic writes).
- Whether pond movements should sync with ChampKoi's existing pond management records.
