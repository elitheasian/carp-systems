import numpy as np
import pytest

from carp.vision.align import head_down_transform, transform_points


@pytest.mark.parametrize(
    ("head", "tail"),
    [((300, 100), (100, 100)), ((100, 100), (100, 400)), ((50, 500), (400, 20))],
)
def test_head_ends_up_bottom_centre_and_tail_top_centre(head, tail):
    matrix = head_down_transform(head, tail, out_size=(224, 448), margin=0.1)
    mapped = transform_points(matrix, np.array([head, tail]))
    np.testing.assert_allclose(mapped[0], [112, 403.2], atol=1e-6)
    np.testing.assert_allclose(mapped[1], [112, 44.8], atol=1e-6)


def test_transform_never_mirrors():
    matrix = head_down_transform((300, 100), (100, 100))
    assert np.linalg.det(matrix[:, :2]) > 0


def test_rejects_coincident_keypoints():
    with pytest.raises(ValueError):
        head_down_transform((5, 5), (5, 5))
