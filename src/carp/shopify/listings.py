"""Turn a Shopify koi catalog into per-fish records.

Expected catalog shape (details in docs/data.md):

- Single-fish products: one fish and one variant, photographed top-down, head pointing down.
- Group products: several fish in one photo, each marked with a letter. Each fish is a variant
  whose title starts with its letter, e.g. 'A: 8-9" (20-23cm) Showa'.
- Each fish variant has metafields for its variety, traits, size, pond and relisting link.

Store-specific names (product types, metafield keys, title pattern) come from a git-ignored
config file. See config/shopify.example.toml.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

ListingKind = Literal["single", "group"]

# Logical fields read from each variant. The config maps each to a "namespace.key" metafield.
METAFIELDS = (
    "variety",
    "base_variety",
    "variety_ref",
    "scale_type",
    "scale_trait",
    "fin_type",
    "pattern",
    "size_cm",
    "pond_id",
    "replaces",
)
REFERENCE_FIELDS = frozenset({"variety_ref"})
DEFAULT_LETTER_PATTERN = r"^\s*([A-Z]{1,2})\s*:"


@dataclass(frozen=True)
class CatalogConfig:
    single_product_type: str
    group_product_type: str
    metafields: dict[str, str]
    letter_pattern: str = DEFAULT_LETTER_PATTERN
    not_a_variety: frozenset[str] = frozenset()
    """Slugged base varieties that describe a fish without naming its variety (e.g. "koi")."""

    @classmethod
    def load(cls, path: Path) -> CatalogConfig:
        data = tomllib.loads(path.read_text())
        metafields = dict(data["variant_metafields"])
        missing = set(METAFIELDS) - set(metafields)
        if missing:
            raise ValueError(f"{path}: variant_metafields is missing {sorted(missing)}")
        return cls(
            single_product_type=data["products"]["single_type"],
            group_product_type=data["products"]["group_type"],
            metafields=metafields,
            letter_pattern=data.get("group", {}).get("letter_pattern", DEFAULT_LETTER_PATTERN),
            not_a_variety=frozenset(data.get("labels", {}).get("not_a_variety", [])),
        )

    @property
    def kinds(self) -> dict[str, ListingKind]:
        return {self.single_product_type: "single", self.group_product_type: "group"}


def build_bulk_query(config: CatalogConfig) -> str:
    """Bulk query for every koi listing, including archived and draft (sold fish are still
    valuable training data)."""
    search = " OR ".join(f'product_type:"{t}"' for t in config.kinds)
    selections = "\n".join(
        _metafield_selection(name, config.metafields[name]) for name in METAFIELDS
    )
    return f"""
{{
  products(query: {json.dumps(search)}) {{
    edges {{
      node {{
        id
        handle
        title
        productType
        status
        onlineStoreUrl
        media {{
          edges {{ node {{ ... on MediaImage {{ id image {{ url width height }} }} }} }}
        }}
        variants {{
          edges {{
            node {{
              id
              title
              availableForSale
{selections}
            }}
          }}
        }}
      }}
    }}
  }}
}}
"""


def _metafield_selection(alias: str, qualified_key: str) -> str:
    namespace, _, key = qualified_key.rpartition(".")
    if not namespace:
        raise ValueError(f"metafield for {alias!r} must be 'namespace.key', got {qualified_key!r}")
    body = "reference { ... on Metaobject { handle } }" if alias in REFERENCE_FIELDS else "value"
    return f"              {alias}: metafield(namespace: {json.dumps(namespace)}, " \
           f"key: {json.dumps(key)}) {{ {body} }}"


@dataclass(frozen=True)
class ListingImage:
    media_id: str
    url: str
    width: int | None
    height: int | None


@dataclass(frozen=True)
class KoiVariant:
    variant_id: str
    title: str
    available: bool
    letter: str | None
    label: str | None
    """Classifier target: the variety metaobject handle, else a slug of base_variety."""
    variety: str | None
    base_variety: str | None
    variety_handle: str | None
    scale_type: str | None
    scale_traits: tuple[str, ...]
    fin_type: str | None
    patterns: tuple[str, ...]
    size_cm: int | None
    pond_id: str | None
    replaces_variant_id: str | None

    def attribute_tags(self) -> list[str]:
        """Multi-label attributes, e.g. ["fin:butterfly", "scale:ginrin"]."""
        tags = {f"scale:{_slug(self.scale_type)}"} if self.scale_type else set()
        tags.update(f"scale:{_slug(t)}" for t in self.scale_traits)
        if self.fin_type:
            tags.add(f"fin:{_slug(self.fin_type)}")
        tags.update(f"pattern:{_slug(p)}" for p in self.patterns)
        return sorted(tags)


@dataclass(frozen=True)
class KoiListing:
    product_id: str
    handle: str
    title: str
    kind: ListingKind
    status: str
    url: str | None
    images: list[ListingImage] = field(default_factory=list)
    variants: list[KoiVariant] = field(default_factory=list)


def parse_bulk_export(lines: Iterable[dict[str, Any]], config: CatalogConfig) -> list[KoiListing]:
    """Rebuild listings from build_bulk_query's JSONL output."""
    letter_re = re.compile(config.letter_pattern)
    products: dict[str, dict[str, Any]] = {}
    images: defaultdict[str, list[ListingImage]] = defaultdict(list)
    variants: defaultdict[str, list[KoiVariant]] = defaultdict(list)

    for obj in lines:
        gid = obj.get("id", "")
        parent = obj.get("__parentId")
        if gid.startswith("gid://shopify/Product/"):
            products[gid] = obj
        elif gid.startswith("gid://shopify/MediaImage/") and parent and obj.get("image"):
            img = obj["image"]
            image = ListingImage(gid, img["url"], img.get("width"), img.get("height"))
            images[parent].append(image)
        elif gid.startswith("gid://shopify/ProductVariant/") and parent:
            variants[parent].append(_parse_variant(obj, letter_re, config.not_a_variety))

    listings = []
    for gid, p in products.items():
        kind = config.kinds.get(p.get("productType", ""))
        if kind is None:
            continue
        listings.append(
            KoiListing(
                product_id=gid,
                handle=p.get("handle", ""),
                title=p.get("title", ""),
                kind=kind,
                status=p.get("status", ""),
                url=p.get("onlineStoreUrl"),
                images=images[gid],
                variants=variants[gid],
            )
        )
    return listings


def fish_id_for(variant_id: str) -> str:
    return "v" + variant_id.rsplit("/", 1)[-1]


def resolve_fish_ids(variants: Iterable[KoiVariant]) -> dict[str, str]:
    """Map variant id -> fish id, following relisting links back to the first listing.

    ASSUMPTION (unverified): a relisting link means the same fish was listed again. If so,
    relistings give multiple photos of one fish over time, which is ideal for re-ID.
    """
    variants = list(variants)
    replaces = {v.variant_id: v.replaces_variant_id for v in variants if v.replaces_variant_id}
    resolved = {}
    for v in variants:
        current, seen = v.variant_id, {v.variant_id}
        while current in replaces and replaces[current] not in seen:
            current = replaces[current]
            seen.add(current)
        resolved[v.variant_id] = fish_id_for(current)
    return resolved


def _parse_variant(
    obj: dict[str, Any], letter_re: re.Pattern[str], not_a_variety: frozenset[str]
) -> KoiVariant:
    title = obj.get("title", "")
    letter = letter_re.match(title)
    handle = ((obj.get("variety_ref") or {}).get("reference") or {}).get("handle")
    base_variety = _value(obj, "base_variety")
    size = _value(obj, "size_cm")
    return KoiVariant(
        variant_id=obj["id"],
        title=title,
        available=bool(obj.get("availableForSale")),
        letter=letter.group(1) if letter else None,
        label=_label(handle, base_variety, not_a_variety),
        variety=_value(obj, "variety"),
        base_variety=base_variety,
        variety_handle=handle,
        scale_type=_value(obj, "scale_type"),
        scale_traits=_list_value(obj, "scale_trait"),
        fin_type=_value(obj, "fin_type"),
        patterns=_list_value(obj, "pattern"),
        size_cm=int(size) if size else None,
        pond_id=_value(obj, "pond_id"),
        replaces_variant_id=_value(obj, "replaces"),
    )


def _label(handle: str | None, base_variety: str | None, not_a_variety: frozenset[str]):
    if handle:
        return handle
    if not base_variety:
        return None
    label = _slug(base_variety, sep="-")
    return None if label in not_a_variety else label


def _value(obj: dict[str, Any], alias: str) -> str | None:
    metafield = obj.get(alias)
    return metafield.get("value") if metafield else None


def _list_value(obj: dict[str, Any], alias: str) -> tuple[str, ...]:
    raw = _value(obj, alias)
    return tuple(json.loads(raw)) if raw else ()


def _slug(label: str, sep: str = "_") -> str:
    """'Doitsu (Scaleless / Mirror)' -> 'doitsu', 'Short Fin' -> 'short_fin'."""
    return sep.join(label.split("(")[0].strip().lower().split())
