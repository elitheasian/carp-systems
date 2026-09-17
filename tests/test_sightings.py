from datetime import UTC, datetime, timedelta

import numpy as np

from carp.index.gallery import Gallery
from carp.tracking.sightings import SightingAggregator

T0 = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def _aggregator():
    g = Gallery(dim=4)
    g.add("fish-a", np.array([1, 0, 0, 0]))
    g.add("fish-b", np.array([0, 1, 0, 0]))
    return SightingAggregator(g, pond_id="pond-1", min_frames=3)


def _observe(agg, track_id, vector, n=5):
    rng = np.random.default_rng(0)
    for i in range(n):
        noisy = np.asarray(vector, dtype=float) + rng.normal(0, 0.05, 4)
        agg.observe(track_id, noisy, quality=1.0, timestamp=T0 + timedelta(seconds=i),
                    base_variety="kohaku")


def test_identifies_known_fish():
    agg = _aggregator()
    _observe(agg, 1, [1, 0, 0, 0])
    sighting = agg.end_track(1)
    assert sighting.status == "identified"
    assert sighting.matches[0].fish_id == "fish-a"
    assert sighting.base_variety == "kohaku"


def test_unknown_and_ambiguous():
    agg = _aggregator()
    _observe(agg, 1, [0, 0, 1, 0])
    assert agg.end_track(1).status == "unknown"

    agg = SightingAggregator(agg.gallery, pond_id="pond-1", min_frames=3, accept_score=0.5)
    _observe(agg, 2, [1, 1, 0, 0])
    assert agg.end_track(2).status == "ambiguous"


def test_short_tracks_are_dropped_and_stale_tracks_close():
    agg = _aggregator()
    _observe(agg, 1, [1, 0, 0, 0], n=2)
    assert agg.end_track(1) is None

    _observe(agg, 2, [0, 1, 0, 0])
    assert agg.end_stale(T0 + timedelta(seconds=5), max_idle=timedelta(seconds=10)) == []
    closed = agg.end_stale(T0 + timedelta(seconds=30), max_idle=timedelta(seconds=10))
    assert [s.matches[0].fish_id for s in closed] == ["fish-b"]
