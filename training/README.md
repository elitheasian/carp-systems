# Training

Install with `pip install -e '.[train]'`. Scripts and configs land here as milestones start.
Datasets and weights live outside git (`data/`, `models/`, `runs/`).

## Order of work

1. **Dataset (M0):** `carp ingest-shopify --download-images`. Review variety counts, and merge or
   drop varieties with too few fish for a first model.
2. **Variety classifier baseline (M1):** single listings only (already one head-down fish per
   photo). timm backbone (ConvNeXt-Tiny or EfficientNet), base variety + attribute heads.
   Report top-1, macro-F1 and a confusion matrix. Add the variety metaobjects' reference images.
3. **Detector + keypoints (M2):** box + head/tail keypoints. Label group photos and pond frames.
   Resolve group-photo letters (`carp.vision.group_letters`).
4. **Identification baseline (M3):** frozen DINOv2 on head-down crops. Evaluate top-1/top-5
   retrieval on test fish with 2+ photos.
5. **Metric learning (M3):** fine-tune the embedder (ArcFace/triplet). No horizontal flips.
   Augment with rotation jitter, colour/glare, blur and water ripple distortion.
6. **Export:** ONNX → TFLite (phones), ONNX Runtime / Hailo HEF (Pi). Re-check accuracy after
   quantisation.

## Rules

- Use `carp.data.splits.assign_splits`. Never split randomly by image.
- Log every run's data manifest hash, label map version and metrics.
- Compare against the previous best on the same test split before replacing a model.
