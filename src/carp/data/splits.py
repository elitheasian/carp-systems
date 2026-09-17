"""Leak-free train/val/test splits.

Rows are grouped so that every photo of a fish, and every fish sharing a group photo, land in the
same split. Otherwise the model can "recognise" a fish in test from the same photo or relisting
it trained on, and the accuracy numbers mean nothing.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from carp.data.manifest import FishImage

DEFAULT_RATIOS: tuple[tuple[str, float], ...] = (("train", 0.8), ("val", 0.1), ("test", 0.1))


def assign_splits(
    rows: Sequence[FishImage],
    ratios: tuple[tuple[str, float], ...] = DEFAULT_RATIOS,
    salt: str = "carp-v1",
) -> list[str]:
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for row in rows:
        parent[find(f"fish:{row.fish_id}")] = find(f"product:{row.product_id}")

    # Key each component by its smallest member so splits stay stable as new data arrives.
    members: dict[str, list[str]] = {}
    for node in list(parent):
        members.setdefault(find(node), []).append(node)
    component_key = {root: min(nodes) for root, nodes in members.items()}

    return [_bucket(component_key[find(f"fish:{row.fish_id}")], ratios, salt) for row in rows]


def _bucket(key: str, ratios: tuple[tuple[str, float], ...], salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{key}".encode()).digest()
    u = int.from_bytes(digest[:8], "big") / 2**64
    total = sum(weight for _, weight in ratios)
    cumulative = 0.0
    for name, weight in ratios:
        cumulative += weight / total
        if u < cumulative:
            return name
    return ratios[-1][0]
