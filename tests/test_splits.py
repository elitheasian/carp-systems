from carp.data.manifest import FishImage
from carp.data.splits import assign_splits


def _row(fish_id, product_id):
    return FishImage(
        fish_id=fish_id, variant_id=fish_id, product_id=product_id, listing_kind="single",
        media_id="m", image_url="u", letter=None, label="kohaku", variety="Kohaku",
    )


def test_fish_in_the_same_photo_or_relisted_share_a_split():
    rows = [
        _row("a", "group1"), _row("b", "group1"), _row("c", "group1"),
        _row("a", "single9"),  # fish a relisted on its own
    ] + [_row(f"x{i}", f"p{i}") for i in range(200)]
    splits = assign_splits(rows)
    assert len({splits[0], splits[1], splits[2], splits[3]}) == 1


def test_splits_are_deterministic_and_roughly_proportional():
    rows = [_row(f"x{i}", f"p{i}") for i in range(2000)]
    first = assign_splits(rows)
    assert first == assign_splits(rows)
    assert 0.75 < first.count("train") / len(rows) < 0.85
