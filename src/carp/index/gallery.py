"""The identification gallery: embeddings of known fish, searched by cosine similarity.

Brute-force search is plenty at ChampKoi scale (thousands of fish, a few MB of vectors). It also
runs the same way on a phone, a Pi and the server. Swap in FAISS or pgvector behind this
interface if the gallery ever outgrows it.
"""

from __future__ import annotations

import json
from collections.abc import Collection
from pathlib import Path

import numpy as np

from carp.types import Match


class Gallery:
    def __init__(self, dim: int):
        self.dim = dim
        self._vectors = np.zeros((0, dim), dtype=np.float32)
        self._fish_ids: list[str] = []
        self._varieties: list[str | None] = []

    def __len__(self) -> int:
        return len(set(self._fish_ids))

    def __contains__(self, fish_id: str) -> bool:
        return fish_id in self._fish_ids

    def add(self, fish_id: str, vectors: np.ndarray, base_variety: str | None = None) -> None:
        """Add one or more embeddings (e.g. several photos) for a fish."""
        vectors = _normalize(np.atleast_2d(np.asarray(vectors, dtype=np.float32)))
        if vectors.shape[1] != self.dim:
            raise ValueError(f"expected dim {self.dim}, got {vectors.shape[1]}")
        self._vectors = np.vstack([self._vectors, vectors])
        self._fish_ids.extend([fish_id] * len(vectors))
        self._varieties.extend([base_variety] * len(vectors))

    def remove(self, fish_id: str) -> None:
        keep = [i for i, f in enumerate(self._fish_ids) if f != fish_id]
        self._vectors = self._vectors[keep]
        self._fish_ids = [self._fish_ids[i] for i in keep]
        self._varieties = [self._varieties[i] for i in keep]

    def search(
        self,
        query: np.ndarray,
        k: int = 5,
        base_varieties: Collection[str] | None = None,
    ) -> list[Match]:
        """Top-k fish, scored by their best-matching embedding.

        Pass `base_varieties` to restrict the search using the classifier's likely varieties.
        """
        if not self._fish_ids:
            return []
        query = _normalize(np.asarray(query, dtype=np.float32).reshape(1, -1))[0]
        scores = self._vectors @ query
        if base_varieties is not None:
            allowed = np.array([v in base_varieties for v in self._varieties])
            scores = np.where(allowed, scores, -np.inf)

        matches: list[Match] = []
        seen: set[str] = set()
        for i in np.argsort(-scores):
            if not np.isfinite(scores[i]):
                break
            fish_id = self._fish_ids[i]
            if fish_id in seen:
                continue
            seen.add(fish_id)
            matches.append(Match(fish_id, float(scores[i])))
            if len(matches) == k:
                break
        return matches

    def save(self, path: Path) -> None:
        """Write `<path>.npz` (vectors) and `<path>.json` (ids), the format phones download."""
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path.with_suffix(".npz"), vectors=self._vectors.astype(np.float16))
        path.with_suffix(".json").write_text(
            json.dumps({"dim": self.dim, "fish_ids": self._fish_ids, "varieties": self._varieties})
        )

    @classmethod
    def load(cls, path: Path) -> Gallery:
        meta = json.loads(path.with_suffix(".json").read_text())
        gallery = cls(meta["dim"])
        gallery._vectors = np.load(path.with_suffix(".npz"))["vectors"].astype(np.float32)
        gallery._fish_ids = meta["fish_ids"]
        gallery._varieties = meta["varieties"]
        return gallery


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.maximum(norms, 1e-12)
