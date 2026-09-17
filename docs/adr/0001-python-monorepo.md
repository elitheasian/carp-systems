# 0001: Python monorepo for training, pond nodes and API

**Status:** Accepted, 2026-09-16

## Context

CARP has four parts: training, Raspberry Pi pond nodes, an API, and a phone app. The team is
student-sized, and the vision ecosystem (PyTorch, timm, Ultralytics, OpenCV, ONNX) is Python-first.

## Decision

- One repository. Training, pond node and API share the `carp` Python package, so alignment,
  gallery search and data types are written once and tested once.
- Heavy dependencies are optional extras (`train`, `vision`, `api`). The core package stays light
  enough for a Pi.
- The phone app lives in `apps/mobile/` in its own language and consumes exported models plus
  the gallery format, not Python code.

## Consequences

- Performance-critical inference runs through exported models (ONNX/TFLite/HEF), not Python
  loops, so Python speed isn't a bottleneck.
- **Ultralytics is AGPL-3.0, so CARP is licensed AGPL-3.0 too** (decided 2026-09-16). Everything
  stays usable together, including shipped apps, as long as their source is public. A
  closed-source deployment would need an Ultralytics enterprise license or an Apache/MIT-licensed
  detector (e.g. RT-DETR via Hugging Face Transformers). The `KoiDetector` protocol keeps that
  swap local.
