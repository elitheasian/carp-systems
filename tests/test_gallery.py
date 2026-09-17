import numpy as np

from carp.index.gallery import Gallery


def _gallery():
    g = Gallery(dim=3)
    g.add("kohaku-1", np.array([[1, 0, 0], [0.9, 0.1, 0]]), base_variety="kohaku")
    g.add("showa-1", np.array([0, 1, 0]), base_variety="showa")
    g.add("showa-2", np.array([0, 0.7, 0.7]), base_variety="showa")
    return g


def test_search_ranks_by_best_embedding_per_fish():
    matches = _gallery().search(np.array([0.95, 0.05, 0]), k=5)
    assert [m.fish_id for m in matches][0] == "kohaku-1"
    assert len({m.fish_id for m in matches}) == len(matches) == 3


def test_variety_filter_and_remove():
    g = _gallery()
    assert {m.fish_id for m in g.search(np.array([1, 0, 0]), base_varieties={"showa"})} == {
        "showa-1", "showa-2"
    }
    g.remove("showa-1")
    assert "showa-1" not in g
    assert len(g) == 2


def test_save_and_load_round_trip(tmp_path):
    g = _gallery()
    g.save(tmp_path / "gallery")
    loaded = Gallery.load(tmp_path / "gallery")
    query = np.array([0, 0.6, 0.8])
    assert [m.fish_id for m in loaded.search(query)] == [m.fish_id for m in g.search(query)]
