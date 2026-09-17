# CARP mobile app (planned, M5)

The customer-facing app for shopping at ChampKoi.

## What it does

1. Live camera preview detects koi and shows each fish's predicted variety.
2. Tap a fish to identify it against available ChampKoi inventory.
3. Show the matching listing(s) with a link to champkoi.com, plus variety info from the
   variety metaobject.

## Contract with the Python side

- **Models:** detector (box + head/tail keypoints), classifier (base variety + attributes) and
  embedder as TFLite files, plus a versioned label map.
- **Alignment:** must reproduce `carp.vision.align.head_down_transform` exactly (same crop size,
  margin, no mirroring).
- **Gallery:** `gallery.npz` (float16 vectors) + `gallery.json` (fish IDs, varieties), plus
  listing metadata, downloaded from the API.

Framework choice is open. See [ADR 0005](../../docs/adr/0005-edge-deployment.md).
