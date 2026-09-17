"""Model interfaces. Training code, pond nodes and the API depend on these, not on a framework.

Implementations (PyTorch for training, ONNX Runtime on the Pi, TFLite on phones) live behind
these protocols so a model can be swapped without touching the pipeline.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np

from carp.types import Detection, VarietyPrediction


class KoiDetector(Protocol):
    def __call__(self, image: np.ndarray) -> list[Detection]:
        """Find koi in an RGB image (H, W, 3), with head and tail keypoints where visible."""
        ...


class KoiTracker(Protocol):
    def update(self, detections: list[Detection]) -> list[Detection]:
        """Return the detections with a stable `track_id` assigned across frames."""
        ...


class VarietyClassifier(Protocol):
    def __call__(self, crop: np.ndarray) -> VarietyPrediction:
        """Classify a head-down canonical crop (see carp.vision.align)."""
        ...


class Embedder(Protocol):
    dim: int

    def __call__(self, crops: Sequence[np.ndarray]) -> np.ndarray:
        """Embed head-down canonical crops into an (n, dim) array of L2-normalised vectors."""
        ...
