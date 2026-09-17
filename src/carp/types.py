"""Core types shared by training, the pond nodes, the API and the mobile app contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Point = tuple[float, float]


@dataclass(frozen=True)
class BBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> Point:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def diagonal(self) -> float:
        return ((self.x2 - self.x1) ** 2 + (self.y2 - self.y1) ** 2) ** 0.5

    def distance_to(self, point: Point) -> float:
        """Distance from a point to the box edge (0 when the point is inside)."""
        dx = max(self.x1 - point[0], 0.0, point[0] - self.x2)
        dy = max(self.y1 - point[1], 0.0, point[1] - self.y2)
        return (dx * dx + dy * dy) ** 0.5


@dataclass(frozen=True)
class Detection:
    """One koi found in a frame. Head and tail keypoints drive head-down alignment."""

    bbox: BBox
    score: float
    head: Point | None = None
    tail: Point | None = None
    track_id: int | None = None


@dataclass(frozen=True)
class VarietyPrediction:
    base_variety: str
    """Variety metaobject handle, e.g. "showa"."""
    score: float
    attributes: dict[str, float] = field(default_factory=dict)
    """Multi-label tag probabilities, e.g. {"scale:ginrin": 0.91, "fin:butterfly": 0.02}."""


@dataclass(frozen=True)
class Match:
    fish_id: str
    score: float
    """Cosine similarity in [-1, 1]."""


SightingStatus = Literal["identified", "ambiguous", "unknown"]


@dataclass(frozen=True)
class Sighting:
    """A tracked fish in a pond, summarised once its track ends."""

    pond_id: str
    track_id: int
    first_seen: datetime
    last_seen: datetime
    frames: int
    status: SightingStatus
    matches: tuple[Match, ...]
    base_variety: str | None = None
