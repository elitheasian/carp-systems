# 0004: Predict base variety plus attribute tags

**Status:** Accepted, 2026-09-16

## Context

The Shopify `variety` field combines a base variety with modifiers ("Ginrin Showa", "Doitsu
Kohaku"). Treating every combination as its own class splits the data into many rare classes.
ChampKoi already stores the parts separately: `variety_ref` / `base_variety`, `scale_type`,
`scale_trait`, `fin_type` and `pattern`.

## Decision

- **Base variety head** (single-label softmax): target is the variety metaobject handle.
- **Attribute head** (multi-label sigmoid): `scale:*`, `fin:*`, `pattern:*` tags.
- The display name is composed from the predictions, e.g. `scale:ginrin` + `showa` → "Ginrin Showa".

## Consequences

- Rare combinations still benefit from all Showa photos and all ginrin photos.
- Hard pairs (Showa vs. Sanke, Shiro Utsuri vs. Shiro Bekko) are reported as a confusion matrix.
  The metaobject's `confusion_points` text can be shown in the app when confidence is low.
- If the metaobject list changes, the label map must be versioned alongside the model.
