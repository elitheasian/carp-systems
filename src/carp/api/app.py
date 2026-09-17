"""CARP API: receives pond sightings and (later) serves the gallery to phones.

Run with: uvicorn carp.api.app:app --reload

Storage is in-memory for now. See docs/architecture.md for planned endpoints and persistence.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="C.A.R.P. API", version="0.1.0")


class MatchIn(BaseModel):
    fish_id: str
    score: float


class SightingIn(BaseModel):
    pond_id: str
    track_id: int
    first_seen: datetime
    last_seen: datetime
    frames: int
    status: Literal["identified", "ambiguous", "unknown"]
    matches: list[MatchIn]
    base_variety: str | None = None


_sightings: list[SightingIn] = []


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sightings", status_code=202)
def create_sighting(sighting: SightingIn) -> dict[str, int]:
    _sightings.append(sighting)
    return {"stored": len(_sightings)}


@app.get("/ponds/{pond_id}/sightings")
def pond_sightings(pond_id: str, limit: int = 100) -> list[SightingIn]:
    return [s for s in reversed(_sightings) if s.pond_id == pond_id][:limit]


@app.get("/fish/{fish_id}/last-seen")
def last_seen(fish_id: str) -> SightingIn | None:
    for s in reversed(_sightings):
        if s.status == "identified" and s.matches and s.matches[0].fish_id == fish_id:
            return s
    return None
