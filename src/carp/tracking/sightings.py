"""Turn per-frame observations of tracked fish into one identification per track.

Identifying every frame is wasteful on a Pi and noisy (glare, ripples, a fish turning). Instead
each track collects embeddings, and when it ends the best-quality views are averaged and matched
once against the gallery.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from carp.index.gallery import Gallery
from carp.types import Match, Sighting, SightingStatus

# Placeholder thresholds: tune on the validation split before trusting sighting statuses.
DEFAULT_ACCEPT_SCORE = 0.75
DEFAULT_MIN_MARGIN = 0.05


@dataclass
class _Track:
    first_seen: datetime
    last_seen: datetime
    embeddings: list[np.ndarray] = field(default_factory=list)
    qualities: list[float] = field(default_factory=list)
    variety_votes: Counter[str] = field(default_factory=Counter)


class SightingAggregator:
    def __init__(
        self,
        gallery: Gallery,
        pond_id: str,
        min_frames: int = 5,
        top_views: int = 8,
        accept_score: float = DEFAULT_ACCEPT_SCORE,
        min_margin: float = DEFAULT_MIN_MARGIN,
        k: int = 5,
    ):
        self.gallery = gallery
        self.pond_id = pond_id
        self.min_frames = min_frames
        self.top_views = top_views
        self.accept_score = accept_score
        self.min_margin = min_margin
        self.k = k
        self._tracks: dict[int, _Track] = {}

    def observe(
        self,
        track_id: int,
        embedding: np.ndarray,
        quality: float,
        timestamp: datetime,
        base_variety: str | None = None,
    ) -> None:
        """Record one view. `quality` ranks views, e.g. detection score times sharpness."""
        track = self._tracks.setdefault(track_id, _Track(timestamp, timestamp))
        track.last_seen = timestamp
        track.embeddings.append(np.asarray(embedding, dtype=np.float32))
        track.qualities.append(quality)
        if base_variety:
            track.variety_votes[base_variety] += 1

    def end_track(self, track_id: int) -> Sighting | None:
        """Close a track. Returns None for tracks too short to identify."""
        track = self._tracks.pop(track_id, None)
        if track is None or len(track.embeddings) < self.min_frames:
            return None

        best = np.argsort(track.qualities)[::-1][: self.top_views]
        probe = np.mean([track.embeddings[i] for i in best], axis=0)
        matches = tuple(self.gallery.search(probe, k=self.k))
        variety = track.variety_votes.most_common(1)[0][0] if track.variety_votes else None

        return Sighting(
            pond_id=self.pond_id,
            track_id=track_id,
            first_seen=track.first_seen,
            last_seen=track.last_seen,
            frames=len(track.embeddings),
            status=self._status(matches),
            matches=matches,
            base_variety=variety,
        )

    def end_stale(self, now: datetime, max_idle: timedelta) -> list[Sighting]:
        stale = [tid for tid, t in self._tracks.items() if now - t.last_seen > max_idle]
        return [s for tid in stale if (s := self.end_track(tid)) is not None]

    def _status(self, matches: tuple[Match, ...]) -> SightingStatus:
        if not matches or matches[0].score < self.accept_score:
            return "unknown"
        if len(matches) > 1 and matches[0].score - matches[1].score < self.min_margin:
            return "ambiguous"
        return "identified"


def sighting_to_dict(sighting: Sighting) -> dict[str, Any]:
    return {
        "pond_id": sighting.pond_id,
        "track_id": sighting.track_id,
        "first_seen": sighting.first_seen.isoformat(),
        "last_seen": sighting.last_seen.isoformat(),
        "frames": sighting.frames,
        "status": sighting.status,
        "matches": [{"fish_id": m.fish_id, "score": m.score} for m in sighting.matches],
        "base_variety": sighting.base_variety,
    }
