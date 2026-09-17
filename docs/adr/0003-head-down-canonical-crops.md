# 0003: Align every fish to a head-down canonical crop

**Status:** Accepted, 2026-09-16

## Context

ChampKoi's listing photos are top-down with the head pointing down. Fish in ponds and in customer
photos point any direction. Rotation-invariant models need more data and are less accurate on
fine patterns.

## Decision

- The detector predicts two keypoints, **head** and **tail**.
- `carp.vision.align` applies a similarity transform so every fish is head-down and roughly the
  same length in a 224×448 crop, matching the listing pose.
- The transform never mirrors, and identification training never uses horizontal flips. A
  mirrored koi has a different pattern and could match the wrong fish.

## Consequences

- Classifier and embedder see the same pose in training (listings) and deployment (ponds,
  phones).
- Keypoints must be labelled. Listing photos give a cheap first pass, since the head is near the
  bottom of the box.
- A swapped head and tail produces an upside-down crop. Detector keypoint accuracy is a
  tracked metric, and the embedder can be evaluated against 180° rotations to measure sensitivity.
