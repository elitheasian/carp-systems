# CARP vocabulary

Terms as used in code, docs and conversation. Keep this current as the language sharpens.

## Koi and listings

- **Variety**: the full display name on a listing, e.g. "Ginrin Showa" (`variety` field).
- **Base variety**: the variety without scale or pattern modifiers, e.g. "Showa"
  (`base_variety` field). Identified in code by its variety metaobject **handle**
  (`showa`). This is the classifier's main target, called the **label**.
- **Attributes**: independent traits encoded as tags: `scale:ginrin`, `scale:doitsu`,
  `fin:butterfly`, `pattern:tancho`. Predicted as multi-label outputs, not baked into the variety.
- **Single listing**: a single-fish product. One fish, one variant, top-down photo, head down.
- **Group listing**: a group product. One photo of several fish, each marked with a
  **letter**. Each fish is a variant whose title starts with that letter (`A: 8-9" ...`).
- **Relisting**: a variant whose `replaces` field points at an earlier variant.
  Assumed to be the same fish (unverified).
- **Pond ID**: the `pond_id` field, where the fish is kept.

## Identity

- **Fish**: one individual koi. **Fish ID** is `v<variant number>` of its first listing.
- **Fish image**: one fish in one photo. The unit of the dataset manifest.
- **Gallery**: embeddings of known fish that queries are matched against.
- **Probe**: the embedding being identified (from a phone photo or a pond track).
- **Match**: a gallery fish and its cosine similarity to the probe.

## Vision

- **Head-down orientation**: top-down view, head pointing to the bottom of the image. The
  pose used in ChampKoi's listing photos and the **canonical crop** every model sees.
- **Keypoints**: the head (snout) and tail (tail-fin fork) points used for alignment.
- **Detection**: a koi box and keypoints in one frame.
- **Track**: the same fish followed across consecutive frames by a pond node.

## Ponds

- **Pond node**: a Raspberry Pi with a camera mounted over one pond.
- **Sighting**: a finished track summarised into one result: **identified** (confident
  match), **ambiguous** (two fish too close to call) or **unknown** (no gallery fish is close).
