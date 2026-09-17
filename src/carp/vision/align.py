"""Rotate and scale each fish into ChampKoi's listing pose: top-down, head pointing down.

Every model sees fish in the same canonical orientation as the listing photos, whether the
source is a listing, a phone photo or a pond camera. Orientation then stops being something
the models have to learn.

The transform is a similarity (rotation + uniform scale + translation) and never mirrors.
A mirrored koi is a different pattern, so horizontal-flip augmentation is also off-limits for
identification models.
"""

from __future__ import annotations

import numpy as np

from carp.types import Point

DEFAULT_CROP_SIZE = (224, 448)  # (width, height); koi are long
DEFAULT_MARGIN = 0.12


def head_down_transform(
    head: Point,
    tail: Point,
    out_size: tuple[int, int] = DEFAULT_CROP_SIZE,
    margin: float = DEFAULT_MARGIN,
) -> np.ndarray:
    """2x3 affine matrix mapping the tail to top-centre and the head to bottom-centre."""
    width, height = out_size
    src_head, src_tail = complex(*head), complex(*tail)
    if abs(src_head - src_tail) < 1e-6:
        raise ValueError("head and tail keypoints coincide")
    dst_tail = complex(width / 2, height * margin)
    dst_head = complex(width / 2, height * (1 - margin))

    a = (dst_head - dst_tail) / (src_head - src_tail)
    b = dst_tail - a * src_tail
    return np.array(
        [[a.real, -a.imag, b.real], [a.imag, a.real, b.imag]],
        dtype=np.float64,
    )


def transform_points(matrix: np.ndarray, points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    return points @ matrix[:, :2].T + matrix[:, 2]


def warp_head_down(
    image: np.ndarray,
    head: Point,
    tail: Point,
    out_size: tuple[int, int] = DEFAULT_CROP_SIZE,
    margin: float = DEFAULT_MARGIN,
) -> np.ndarray:
    import cv2

    matrix = head_down_transform(head, tail, out_size, margin)
    return cv2.warpAffine(image, matrix, out_size, flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REFLECT_101)
