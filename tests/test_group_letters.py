from carp.types import BBox, Detection
from carp.vision.group_letters import LetterMark, assign_letters


def _fish(x1, y1, x2, y2):
    return Detection(BBox(x1, y1, x2, y2), score=0.9)


def test_letters_match_nearest_fish():
    fish = [_fish(0, 0, 100, 400), _fish(300, 0, 400, 400), _fish(600, 0, 700, 400)]
    marks = [LetterMark("B", (350, 430)), LetterMark("A", (50, 430)), LetterMark("C", (650, 430))]
    result = {a.letter: a for a in assign_letters(marks, fish)}
    assert {k: v.detection_index for k, v in result.items()} == {"A": 0, "B": 1, "C": 2}
    assert not any(a.ambiguous for a in result.values())


def test_letter_between_two_fish_is_flagged():
    fish = [_fish(0, 0, 100, 400), _fish(120, 0, 220, 400)]
    result = assign_letters([LetterMark("A", (110, 200))], fish)
    assert result[0].ambiguous


def test_extra_letters_are_unassigned():
    result = assign_letters([LetterMark("A", (0, 0)), LetterMark("B", (5, 5))], [_fish(0, 0, 9, 9)])
    assert sum(a.detection_index is None for a in result) == 1
