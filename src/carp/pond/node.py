"""Pond node: a Raspberry Pi over one pond that tracks koi and reports sightings.

Pipeline per frame: detect -> track -> align head-down -> embed (+ classify) -> aggregate.
When a track ends, its sighting is posted to the API. Sightings are spooled to disk first, so a
flaky pond-side network connection never loses data.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import numpy as np

from carp.tracking.sightings import SightingAggregator, sighting_to_dict
from carp.types import Sighting
from carp.vision.align import warp_head_down
from carp.vision.models import Embedder, KoiDetector, KoiTracker, VarietyClassifier


@dataclass(frozen=True)
class PondNodeConfig:
    pond_id: str
    api_url: str
    spool_dir: Path = Path("spool")
    camera_index: int = 0
    track_idle: timedelta = timedelta(seconds=3)

    @classmethod
    def from_env(cls) -> PondNodeConfig:
        return cls(
            pond_id=os.environ["CARP_POND_ID"],
            api_url=os.environ["CARP_API_URL"],
            spool_dir=Path(os.environ.get("CARP_SPOOL_DIR", "spool")),
        )


def camera_frames(index: int = 0) -> Iterator[tuple[datetime, np.ndarray]]:
    """RGB frames from a USB or libcamera-backed camera via OpenCV.

    On a Pi with Camera Module 3, picamera2 gives better exposure control. Swap it in here.
    """
    import cv2

    capture = cv2.VideoCapture(index)
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            yield datetime.now(UTC), cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    finally:
        capture.release()


def run(
    config: PondNodeConfig,
    frames: Iterable[tuple[datetime, np.ndarray]],
    detector: KoiDetector,
    tracker: KoiTracker,
    embedder: Embedder,
    aggregator: SightingAggregator,
    classifier: VarietyClassifier | None = None,
) -> None:
    for timestamp, frame in frames:
        tracked = [d for d in tracker.update(detector(frame)) if d.track_id is not None]
        aligned = [d for d in tracked if d.head is not None and d.tail is not None]
        if aligned:
            crops = [warp_head_down(frame, d.head, d.tail) for d in aligned]
            embeddings = embedder(crops)
            for detection, crop, embedding in zip(aligned, crops, embeddings, strict=True):
                variety = classifier(crop).base_variety if classifier else None
                aggregator.observe(
                    detection.track_id, embedding, detection.score, timestamp, variety
                )

        for sighting in aggregator.end_stale(timestamp, config.track_idle):
            report(config, sighting)


def report(config: PondNodeConfig, sighting: Sighting) -> None:
    spool(config.spool_dir, sighting)
    flush_spool(config)


def spool(spool_dir: Path, sighting: Sighting) -> Path:
    spool_dir.mkdir(parents=True, exist_ok=True)
    name = f"{sighting.last_seen.strftime('%Y%m%dT%H%M%S%f')}-{sighting.track_id}.json"
    path = spool_dir / name
    path.write_text(json.dumps(sighting_to_dict(sighting)))
    return path


def flush_spool(config: PondNodeConfig, http: httpx.Client | None = None) -> int:
    """Post spooled sightings oldest-first. Stops at the first failure and retries next time."""
    client = http or httpx.Client(timeout=10)
    sent = 0
    for path in sorted(config.spool_dir.glob("*.json")):
        try:
            resp = client.post(f"{config.api_url}/sightings", content=path.read_bytes(),
                               headers={"Content-Type": "application/json"})
            resp.raise_for_status()
        except httpx.HTTPError:
            break
        path.unlink()
        sent += 1
    return sent
