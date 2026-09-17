# 0002: Identify fish by embedding retrieval, not classification

**Status:** Accepted, 2026-09-16

## Context

ChampKoi's inventory changes constantly: fish are listed, sold, relisted and moved. Most fish
have one or a few photos. A classifier with one class per fish would need retraining for every
change and has almost no examples per class.

## Decision

- Train an **embedder** that maps a head-down crop to a vector where the same fish lands close
  and different fish land far apart.
- Keep a **gallery** of vectors for known fish. Identification is a cosine top-k search.
- Baseline: frozen DINOv2 features. Then fine-tune with metric learning (ArcFace or triplet
  loss) on fish with multiple photos.
- Filter or re-rank candidates with the variety classifier (a Kohaku probe shouldn't match a
  Chagoi).
- Report **unknown** below a similarity threshold and **ambiguous** when the top two are too
  close, instead of always naming a fish.

## Consequences

- Adding or removing a fish is a gallery update, with no retraining.
- The model is only as good as its hardest cases: glare, bent bodies, and patterns that change
  as koi grow (sumi developing, hi fading). Evaluation must include time-separated photos
  (relistings) and pond captures, not just listing-to-listing matches.
- Thresholds must be tuned on validation data and revisited as the gallery grows.
