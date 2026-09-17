from pathlib import Path

from carp.data.manifest import build_manifest
from carp.shopify.listings import (
    METAFIELDS,
    CatalogConfig,
    build_bulk_query,
    parse_bulk_export,
    resolve_fish_ids,
)

CONFIG = CatalogConfig(
    single_product_type="Single_Fish",
    group_product_type="Group Fish",
    metafields={name: f"test_ns.{name}_key" for name in METAFIELDS},
    not_a_variety=frozenset({"koi"}),
)


def _mf(value):
    return {"value": value} if value is not None else None


def _variant(vid, parent, title, variety, base, handle, **extra):
    return {
        "id": f"gid://shopify/ProductVariant/{vid}",
        "__parentId": parent,
        "title": title,
        "availableForSale": True,
        "variety": _mf(variety),
        "base_variety": _mf(base),
        "variety_ref": {"reference": {"handle": handle}} if handle else None,
        "scale_type": _mf(extra.get("scale_type")),
        "scale_trait": _mf(extra.get("scale_trait")),
        "fin_type": _mf(extra.get("fin_type", "Standard")),
        "pattern": _mf(extra.get("pattern")),
        "size_cm": _mf(extra.get("size_cm")),
        "pond_id": _mf(extra.get("pond_id")),
        "replaces": _mf(extra.get("replaces")),
    }


GROUP = "gid://shopify/Product/1"
SINGLE = "gid://shopify/Product/2"

BULK_LINES = [
    {"id": GROUP, "handle": "group-1", "title": "GROUP-1", "productType": "Group Fish",
     "status": "ACTIVE", "onlineStoreUrl": None},
    {"id": "gid://shopify/MediaImage/10", "__parentId": GROUP,
     "image": {"url": "https://cdn.example/group.jpg", "width": 3000, "height": 4000}},
    _variant(100, GROUP, 'A: 8-9" (20-23cm) Mukashi Ogon', "Mukashi Ogon", "Mukashi Ogon",
             "mukashi-ogon"),
    _variant(101, GROUP, 'C: 8-9" (20-23cm) Ginrin Showa', "Ginrin Showa", "Showa",
             "showa", scale_type="Wagoi (Standard)",
             scale_trait='["Ginrin (Reflective / Diamond)"]', pond_id="pond-1"),
    {"id": SINGLE, "handle": "single-1", "title": "Single 1 Kohaku",
     "productType": "Single_Fish", "status": "ACTIVE", "onlineStoreUrl": "https://shop.example/x"},
    {"id": "gid://shopify/MediaImage/20", "__parentId": SINGLE,
     "image": {"url": "https://cdn.example/single.jpg", "width": 1600, "height": 2100}},
    {"__parentId": SINGLE},  # non-image media (e.g. video) comes through as an empty node
    _variant(200, SINGLE, '21" (54cm) Female Kohaku', "Kohaku", "Kohaku", "kohaku",
             size_cm="54", replaces="gid://shopify/ProductVariant/150"),
    {"id": "gid://shopify/Product/3", "productType": "Pond Supplies", "title": "Pump"},
]


def test_parses_group_and_single_listings():
    listings = {listing.product_id: listing for listing in parse_bulk_export(BULK_LINES, CONFIG)}
    assert set(listings) == {GROUP, SINGLE}

    group = listings[GROUP]
    assert group.kind == "group"
    assert [v.letter for v in group.variants] == ["A", "C"]
    showa = group.variants[1]
    assert showa.label == "showa"
    assert showa.variety == "Ginrin Showa"
    assert showa.attribute_tags() == ["fin:standard", "scale:ginrin", "scale:wagoi"]
    assert showa.pond_id == "pond-1"

    single = listings[SINGLE]
    assert single.kind == "single"
    assert len(single.images) == 1
    assert single.variants[0].letter is None
    assert single.variants[0].size_cm == 54


def test_relistings_share_a_fish_id():
    variants = [v for listing in parse_bulk_export(BULK_LINES, CONFIG) for v in listing.variants]
    ids = resolve_fish_ids(variants)
    assert ids["gid://shopify/ProductVariant/200"] == "v150"
    assert ids["gid://shopify/ProductVariant/100"] == "v100"


def test_manifest_flags_group_rows_for_review():
    listings = parse_bulk_export(BULK_LINES, CONFIG)
    variants = [v for listing in listings for v in listing.variants]
    rows = build_manifest(listings, resolve_fish_ids(variants))
    assert len(rows) == 3
    assert {r.letter: r.needs_review for r in rows} == {"A": True, "C": True, None: False}


def test_sold_fish_are_not_available_and_fish_without_a_variety_are_skipped():
    archived = "gid://shopify/Product/9"
    lines = [
        {"id": archived, "handle": "old", "title": "Old group", "productType": "Group Fish",
         "status": "ARCHIVED", "onlineStoreUrl": None},
        {"id": "gid://shopify/MediaImage/90", "__parentId": archived,
         "image": {"url": "https://cdn.example/old.jpg", "width": 600, "height": 600}},
        _variant(900, archived, "A: Golden Corn", "Golden Corn", "Golden Corn", None),
        _variant(901, archived, "B: Koi", "Koi", "Koi", None),
    ]
    listings = parse_bulk_export(lines, CONFIG)
    rows = build_manifest(listings, {})
    assert listings[0].variants[1].label is None
    assert [r.label for r in rows] == ["golden-corn"]
    assert not any(r.available for r in rows)
    assert all(r.needs_review for r in rows)


def test_bulk_query_uses_configured_names():
    query = build_bulk_query(CONFIG)
    assert 'product_type:\\"Single_Fish\\" OR product_type:\\"Group Fish\\"' in query
    assert 'variety_ref: metafield(namespace: "test_ns", key: "variety_ref_key") ' \
           '{ reference { ... on Metaobject { handle } } }' in query
    assert 'pond_id: metafield(namespace: "test_ns", key: "pond_id_key") { value }' in query


def test_example_config_is_complete():
    config = CatalogConfig.load(Path(__file__).parents[1] / "config" / "shopify.example.toml")
    assert set(config.metafields) == set(METAFIELDS)
    build_bulk_query(config)
