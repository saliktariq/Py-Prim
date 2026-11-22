"""Equality and ordering only work between matching types."""
import itertools

import pytest

from primitives import Boolean, Bytes, Float, Integer, String
from samples import ALL_TYPES, GOOD


class Age(Integer):
    pass


@pytest.mark.parametrize(
    "left, right",
    [
        (Integer(5), 5),
        (Integer(5), Integer(5)),
        (Integer(5), Age(5)),
        (Float(1.5), 1.5),
        (Float(5), 5),
        (Float(1.5), Float(1.5)),
        (String("a"), "a"),
        (String("a"), String("a")),
        (Boolean(True), True),
        (Boolean(False), Boolean(False)),
        (Bytes(b"a"), b"a"),
        (Bytes(b"a"), Bytes(b"a")),
        (Integer(), Integer()),
        (Integer(), None),
        (String(), None),
    ],
    ids=repr,
)
def test_equal(left, right):
    assert left == right
    assert right == left
    assert not left != right


@pytest.mark.parametrize(
    "left, right",
    [
        (Integer(1), True),
        (Integer(0), False),
        (Integer(1), Boolean(True)),
        (Integer(1), Float(1.0)),
        (Integer(1), 1.0),
        (Float(1.0), True),
        (Float(1.0), Boolean(True)),
        (Integer(1), "1"),
        (String("a"), b"a"),
        (String("a"), Bytes(b"a")),
        (Integer(), String()),
        (Integer(), Boolean()),
        (Integer(0), None),
        (Integer(), 0),
        (Integer(5), 6),
    ],
    ids=repr,
)
def test_not_equal(left, right):
    assert left != right
    assert right != left
    assert not left == right


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_wrappers_are_unhashable(cls):
    with pytest.raises(TypeError):
        hash(cls(GOOD[cls]))


def test_ordering_with_plain_values():
    assert Integer(1) < 2
    assert Integer(2) <= 2
    assert Integer(3) > 2
    assert Integer(2) >= 2
    assert not Integer(2) < 1


def test_reflected_ordering():
    assert 1 < Integer(2)
    assert 3 > Integer(2)
    assert 2 > Float(1.5)


@pytest.mark.parametrize(
    "smaller, larger",
    [
        (Integer(1), Integer(2)),
        (Age(1), Integer(2)),
        (Float(1.5), 2),
        (Float(1.5), Float(2.5)),
        (String("a"), "b"),
        (String("a"), String("b")),
        (Bytes(b"a"), b"b"),
        (Bytes(b"a"), Bytes(b"b")),
        (Boolean(False), True),
        (Boolean(False), Boolean(True)),
    ],
    ids=repr,
)
def test_ordering_between_matching_types(smaller, larger):
    assert smaller < larger
    assert smaller <= larger
    assert larger > smaller
    assert larger >= smaller


@pytest.mark.parametrize(
    "left, right",
    [
        (Integer(2), True),
        (True, Integer(2)),
        (Integer(2), 2.5),
        (Integer(2), Float(2.5)),
        (Float(2.5), Integer(3)),
        (Float(1.5), True),
        (Integer(1), "a"),
        (String("a"), 1),
        (Bytes(b"a"), "a"),
        (Boolean(False), 1),
        (Integer(), 1),
        (1, Integer()),
        (Integer(), Integer()),
        (Integer(1), None),
    ],
    ids=repr,
)
def test_ordering_between_mismatched_types_is_refused(left, right):
    with pytest.raises(TypeError):
        left < right


ORDER_POOLS = [
    (Integer, [0, 1, 2]),
    (Float, [0.0, 1.0, 2.5]),
    (String, ["", "a", "b"]),
    (Bytes, [b"", b"a", b"b"]),
    (Boolean, [False, True]),
]


@pytest.mark.parametrize(
    "cls, left, right",
    [
        (cls, left, right)
        for cls, pool in ORDER_POOLS
        for left, right in itertools.product(pool, repeat=2)
    ],
)
def test_ordering_agrees_with_equality(cls, left, right):
    a, b = cls(left), cls(right)
    assert (a <= b and a >= b) == (a == b)
    assert (a < b) == (not a >= b)
    assert (a > b) == (not a <= b)


def test_sorting_and_max():
    assert [x.value for x in sorted([Integer(2), Integer(1)])] == [1, 2]
    assert [x.value for x in sorted([String("b"), String("a")])] == ["a", "b"]
    assert [x.value for x in sorted([Boolean(True), Boolean(False)])] == [False, True]
    assert max(Integer(1), Integer(3)).value == 3
