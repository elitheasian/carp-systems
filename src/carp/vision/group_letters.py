"""Match the letter marks on a group listing photo to detected fish.

Letter positions come from OCR or from someone clicking each letter in a labelling tool.
Anything uncertain is flagged for human review rather than guessed. One wrong letter swaps two
fish's identities and poisons both the classifier and the re-ID data.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import median

from carp.types import Detection, Point


@dataclass(frozen=True)
class LetterMark:
    letter: str
    position: Point


@dataclass(frozen=True)
class LetterAssignment:
    letter: str
    detection_index: int | None
    distance: float | None
    ambiguous: bool


def assign_letters(
    marks: Sequence[LetterMark],
    detections: Sequence[Detection],
    ambiguity_fraction: float = 0.1,
) -> list[LetterAssignment]:
    """Greedy global matching by letter-to-box distance.

    A match is ambiguous when another fish is nearly as close to the letter, meaning within
    `ambiguity_fraction` of the median fish box diagonal.
    """
    if not detections:
        return [LetterAssignment(m.letter, None, None, True) for m in marks]

    tolerance = ambiguity_fraction * median(d.bbox.diagonal for d in detections)
    distances = [[d.bbox.distance_to(m.position) for d in detections] for m in marks]
    pairs = sorted(
        (dist, mi, di) for mi, row in enumerate(distances) for di, dist in enumerate(row)
    )

    taken_marks: set[int] = set()
    taken_fish: set[int] = set()
    chosen: dict[int, tuple[int, float]] = {}
    for dist, mi, di in pairs:
        if mi in taken_marks or di in taken_fish:
            continue
        chosen[mi] = (di, dist)
        taken_marks.add(mi)
        taken_fish.add(di)

    results = []
    for mi, mark in enumerate(marks):
        if mi not in chosen:
            results.append(LetterAssignment(mark.letter, None, None, True))
            continue
        di, dist = chosen[mi]
        runner_up = min((d for i, d in enumerate(distances[mi]) if i != di), default=None)
        ambiguous = runner_up is not None and runner_up - dist < tolerance
        results.append(LetterAssignment(mark.letter, di, dist, ambiguous))
    return results
