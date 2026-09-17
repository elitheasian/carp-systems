# Data

## Source: a Shopify koi catalog

CARP trains on ChampKoi's Shopify listings. Store-specific names (product types, metafield keys,
title pattern) live in the git-ignored `config/shopify.local.toml`. Copy
[`config/shopify.example.toml`](../config/shopify.example.toml) to create it.

### Listings

| Kind | Photo | Variants |
|---|---|---|
| Single | One fish, top-down, head pointing down | One |
| Group | Several fish in one photo, each marked with a letter | One per fish, title starts with its letter (`A: ...`) |

Group variants have no image of their own, so each fish's position in the group photo has to
come from letter matching (below).

### Variant fields

| Field | Use |
|---|---|
| `variety` | Display name ("Ginrin Showa") |
| `base_variety` | Fallback classifier label ("Showa") |
| `variety_ref` | Reference to a variety entry. Its handle (`showa`) is the **classifier label** |
| `scale_type`, `scale_trait`, `fin_type`, `pattern` | Attribute tags |
| `size_cm` | Size (patterns change as fish grow) |
| `pond_id` | Where the fish is kept. Ground truth for pond nodes |
| `replaces` | Link to an earlier listing of the same fish (unverified) |

Variety entries also carry reference images (extra classifier training data) and text on
telling similar varieties apart (for the app's "why this variety" UI).

## Export

`carp ingest-shopify` runs one Shopify **bulk operation** (the catalog is too big to page
through quickly), including archived and draft listings, since sold fish are still good
training data.

- **Skipped:** fish whose base variety doesn't name a real variety (`labels.not_a_variety` in
  the config).
- **For sale:** an `ACTIVE` product *and* an available variant. Archived listings can still
  report `availableForSale = true`.
- **Labels without a variety entry** fall back to a slug of `base_variety`. Some fallbacks are
  synonyms or traits and need mapping before training.

Counts and store details from exports are kept in a local, git-ignored note (`private/`), not
in the repo.

## Manifest

`manifest.jsonl` has one row per **fish per photo** (`carp.data.manifest.FishImage`): fish ID,
variant/product/media IDs, letter, label, variety, attributes, size, pond, availability, image
path, bbox and `needs_review`.

## Labelling group photos

Most fish are in group photos. Each group photo needs every letter matched to a fish box:

1. Run the koi detector on the photo (or draw boxes in Label Studio / CVAT to bootstrap).
2. Get letter positions with OCR, or by clicking each letter in the labelling tool.
3. `carp.vision.group_letters.assign_letters` matches letters to boxes and flags ambiguous ones.
4. A person reviews flagged photos. One swapped letter corrupts two fish's labels.

Head/tail keypoints are also labelled here. Listing photos being head-down makes a first pass
nearly free (head ≈ bottom of the box), but it still needs review.

## Splits

`carp.data.splits.assign_splits` keeps every photo of a fish, and every fish in a shared group
photo, in the same split. Splits are hashed and stable as data is added. For identification
evaluation, the test set uses fish with 2+ photos (relistings, multiple listing images, or
pond captures matched to a listing).

## Data handling rules

- Images, manifests, embeddings, real config and credentials stay out of git (`/data/`,
  `/models/`, `/private/`, `.env`, `config/*.local.toml`). CI fails if data or model files are
  committed.
- Share datasets, `.env` and the local config through a private drive the team controls.
- The Shopify app (`apps/shopify`) has read-only scopes. Keep it that way.

## Open questions

- Does a relisting link always mean the same fish was relisted?
- Do group listings ever have more than one photo, and does every photo contain every letter?
- Are single listings' extra images (if any) always head-down top views?
