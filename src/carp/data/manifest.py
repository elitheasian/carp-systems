"""The dataset manifest: one row per fish per photo, stored as JSONL next to the images."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from carp.shopify.listings import KoiListing, fish_id_for


@dataclass
class FishImage:
    fish_id: str
    variant_id: str
    product_id: str
    listing_kind: str
    media_id: str
    image_url: str
    letter: str | None
    label: str | None
    """Base variety handle, the classifier target."""
    variety: str | None
    """Full display name, e.g. "Ginrin Showa"."""
    attributes: list[str] = field(default_factory=list)
    size_cm: int | None = None
    pond_id: str | None = None
    available: bool = False
    """For sale right now: an ACTIVE listing whose variant is available. Gallery membership."""
    image_path: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    """Fish location in the photo. None until detected or labelled."""
    needs_review: bool = False


def build_manifest(listings: Iterable[KoiListing], fish_ids: dict[str, str]) -> list[FishImage]:
    """One row per fish per photo. Fish without a real variety (e.g. "Koi") are skipped."""
    rows = []
    for listing in listings:
        for variant in listing.variants:
            if variant.label is None:
                continue
            for image in listing.images:
                rows.append(
                    FishImage(
                        fish_id=fish_ids.get(variant.variant_id, fish_id_for(variant.variant_id)),
                        variant_id=variant.variant_id,
                        product_id=listing.product_id,
                        listing_kind=listing.kind,
                        media_id=image.media_id,
                        image_url=image.url,
                        letter=variant.letter,
                        label=variant.label,
                        variety=variant.variety,
                        attributes=variant.attribute_tags(),
                        size_cm=variant.size_cm,
                        pond_id=variant.pond_id,
                        # Archived (sold) listings can still report availableForSale.
                        available=listing.status == "ACTIVE" and variant.available,
                        # Group photos need each letter matched to a fish before use.
                        needs_review=listing.kind == "group",
                    )
                )
    return rows


def write_manifest(rows: Iterable[FishImage], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(asdict(row)) + "\n")


def read_manifest(path: Path) -> list[FishImage]:
    rows = []
    with path.open() as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                if data.get("bbox") is not None:
                    data["bbox"] = tuple(data["bbox"])
                rows.append(FishImage(**data))
    return rows
