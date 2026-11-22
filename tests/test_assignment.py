"""The constructor and .value accept only the wrapper's exact type."""
from decimal import Decimal
from fractions import Fraction

import pytest

from primitives import Boolean, Bytes, Float, Integer, PrimitiveTypeError, String
from samples import ALL_TYPES, DEFAULT, EXACT_TYPE, GOOD, WRONG, holds, same

VALUES = [
    0, 1, -1, 2 ** 70, 1.5, 0.0, float("inf"), float("nan"), "", "x", " ", b"", b"x",
    True, False, bytearray(b"x"), memoryview(b"x"), [], [1], {}, (), set(), 1j,
    Decimal("1"), Fraction(1, 2), object(), int,
]


def is_allowed(cls, value):
    return type(value) is EXACT_TYPE[cls] or (cls is Float and type(value) is int)


def value_id(value):
    return type(value).__name__


@pytest.mark.parametrize("cls", ALL_TYPES)
@pytest.mark.parametrize("value", VALUES, ids=value_id)
def test_constructor_accepts_only_its_type(cls, value):
    if is_allowed(cls, value):
        assert type(cls(value).value) is EXACT_TYPE[cls]
    else:
        with pytest.raises(PrimitiveTypeError):
            cls(value)


@pytest.mark.parametrize("cls", ALL_TYPES)
@pytest.mark.parametrize("value", VALUES, ids=value_id)
def test_assignment_accepts_only_its_type(cls, value):
    wrapper = cls(GOOD[cls])
    if is_allowed(cls, value):
        wrapper.value = value
        assert type(wrapper.value) is EXACT_TYPE[cls]
    else:
        with pytest.raises(PrimitiveTypeError):
            wrapper.value = value
        assert holds(wrapper, cls)


# --- Errors ---


def test_wrong_type_error_is_both_type_error_and_value_error():
    assert issubclass(PrimitiveTypeError, TypeError)
    assert issubclass(PrimitiveTypeError, ValueError)


def test_error_message_names_both_types():
    with pytest.raises(PrimitiveTypeError, match="^Integer requires int, got float$"):
        Integer(100).value = 100.5


class BrokenStr:
    def __str__(self):
        raise RuntimeError("the rejected value must not be formatted")

    __repr__ = __str__


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_error_does_not_format_the_rejected_value(cls):
    with pytest.raises(PrimitiveTypeError):
        cls(BrokenStr())


def test_huge_int_gets_a_clean_error():
    with pytest.raises(PrimitiveTypeError, match="^String requires str, got int$"):
        String(10 ** 5000)


# --- None, clear and reset ---


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_none_cannot_be_assigned(cls):
    wrapper = cls(GOOD[cls])
    with pytest.raises(PrimitiveTypeError):
        wrapper.value = None
    assert holds(wrapper, cls)


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_wrapper_can_start_null(cls):
    assert cls().is_null()
    assert cls(None).is_null()
    assert cls().value is None


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_clear_returns_to_null_and_can_be_reassigned(cls):
    wrapper = cls(GOOD[cls])
    wrapper.clear()
    assert wrapper.is_null()
    wrapper.value = GOOD[cls]
    assert holds(wrapper, cls)


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_reset_sets_the_default(cls):
    wrapper = cls(GOOD[cls])
    wrapper.reset()
    assert same(wrapper.value, DEFAULT[cls])


# --- Float conversion ---


@pytest.mark.parametrize("value", [5, 0, -3, 2 ** 70])
def test_float_constructor_converts_int(value):
    assert same(Float(value).value, float(value))


@pytest.mark.parametrize("value", [5, 0, -3, 2 ** 70])
def test_float_assignment_converts_int(value):
    wrapper = Float(1.5)
    wrapper.value = value
    assert same(wrapper.value, float(value))


@pytest.mark.parametrize("value", [True, False])
def test_float_rejects_bool(value):
    with pytest.raises(PrimitiveTypeError):
        Float(value)


def test_float_rejects_int_too_large_to_convert():
    with pytest.raises(ValueError):
        Float(10 ** 400)
    wrapper = Float(1.5)
    with pytest.raises(ValueError):
        wrapper.value = 10 ** 400
    assert wrapper.value == 1.5


# --- Empty, null and validity ---


@pytest.mark.parametrize(
    "wrapper",
    [Integer(0), Float(0.0), String(""), String("   "), String("\t\n"), Boolean(False), Bytes(b"")],
    ids=repr,
)
def test_default_like_values_are_empty_and_falsy(wrapper):
    assert wrapper.is_empty()
    assert not wrapper
    assert not wrapper.is_null()


@pytest.mark.parametrize(
    "wrapper",
    [Integer(1), Integer(-1), Float(0.5), String("a"), String(" a "), Boolean(True), Bytes(b"a"), Bytes(b" ")],
    ids=repr,
)
def test_real_values_are_not_empty_and_truthy(wrapper):
    assert not wrapper.is_empty()
    assert wrapper


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_null_is_empty_and_falsy(cls):
    assert cls().is_empty()
    assert not cls()


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_stored_value_is_valid(cls):
    wrapper = cls(GOOD[cls])
    assert wrapper.is_valid()
    wrapper.validate()
    cls().validate()


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_rejected_value_leaves_a_valid_wrapper(cls):
    wrapper = cls(GOOD[cls])
    with pytest.raises(PrimitiveTypeError):
        wrapper.value = WRONG[cls]
    wrapper.validate()
    assert holds(wrapper, cls)
