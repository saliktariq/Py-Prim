"""Operators return plain values, and in-place operators keep the type lock."""
import math
import operator
from decimal import Decimal

import pytest

from primitives import Boolean, Bytes, Float, Integer, PrimitiveTypeError, String
from samples import same

PLAIN_RESULTS = [
    # Integer arithmetic
    ("int_add", lambda: Integer(2) + 3, 5),
    ("int_radd", lambda: 3 + Integer(2), 5),
    ("int_add_wrapper", lambda: Integer(2) + Integer(3), 5),
    ("int_sub", lambda: Integer(5) - 2, 3),
    ("int_rsub", lambda: 5 - Integer(2), 3),
    ("int_mul", lambda: Integer(2) * 3, 6),
    ("int_rmul", lambda: 3 * Integer(2), 6),
    ("int_truediv", lambda: Integer(7) / 2, 3.5),
    ("int_rtruediv", lambda: 7 / Integer(2), 3.5),
    ("int_floordiv", lambda: Integer(7) // 2, 3),
    ("int_rfloordiv", lambda: 7 // Integer(2), 3),
    ("int_mod", lambda: Integer(7) % 4, 3),
    ("int_rmod", lambda: 7 % Integer(4), 3),
    ("int_pow", lambda: Integer(2) ** 3, 8),
    ("int_rpow", lambda: 2 ** Integer(3), 8),
    ("int_pow_modulo", lambda: pow(Integer(2), 3, 5), 3),
    ("int_divmod", lambda: divmod(Integer(7), 2), (3, 1)),
    ("int_rdivmod", lambda: divmod(7, Integer(2)), (3, 1)),
    # Mixed numbers give a plain result
    ("int_add_float", lambda: Integer(2) + 1.5, 3.5),
    ("float_add_int_wrapper", lambda: 1.5 + Integer(2), 3.5),
    ("integer_add_float_wrapper", lambda: Integer(2) + Float(1.5), 3.5),
    ("int_add_decimal", lambda: Integer(2) + Decimal("1.5"), Decimal("3.5")),
    ("decimal_add_int", lambda: Decimal("1.5") + Integer(2), Decimal("3.5")),
    # Integer unary and bitwise
    ("int_neg", lambda: -Integer(2), -2),
    ("int_pos", lambda: +Integer(2), 2),
    ("int_abs", lambda: abs(Integer(-2)), 2),
    ("int_invert", lambda: ~Integer(2), -3),
    ("int_and", lambda: Integer(6) & 3, 2),
    ("int_rand", lambda: 3 & Integer(6), 2),
    ("int_or", lambda: Integer(6) | 1, 7),
    ("int_ror", lambda: 1 | Integer(6), 7),
    ("int_xor", lambda: Integer(6) ^ 3, 5),
    ("int_rxor", lambda: 3 ^ Integer(6), 5),
    ("int_lshift", lambda: Integer(3) << 2, 12),
    ("int_rlshift", lambda: 3 << Integer(2), 12),
    ("int_rshift", lambda: Integer(12) >> 2, 3),
    ("int_rrshift", lambda: 12 >> Integer(2), 3),
    # Integer conversions and indexing
    ("int_to_int", lambda: int(Integer(2)), 2),
    ("int_to_float", lambda: float(Integer(2)), 2.0),
    ("int_round", lambda: round(Integer(2)), 2),
    ("int_floor", lambda: math.floor(Integer(2)), 2),
    ("int_ceil", lambda: math.ceil(Integer(2)), 2),
    ("int_trunc", lambda: math.trunc(Integer(2)), 2),
    ("int_range", lambda: list(range(Integer(2))), [0, 1]),
    ("int_list_index", lambda: [7, 8][Integer(1)], 8),
    ("int_str_index", lambda: "abc"[Integer(1)], "b"),
    ("int_slice", lambda: "abcd"[Integer(1):Integer(3)], "bc"),
    ("int_hex", lambda: hex(Integer(255)), "0xff"),
    ("int_bin", lambda: bin(Integer(2)), "0b10"),
    ("int_percent_format", lambda: "%d" % Integer(5), "5"),
    ("int_format_spec", lambda: f"{Integer(5):03d}", "005"),
    ("str_times_int", lambda: "ab" * Integer(2), "abab"),
    ("int_times_str", lambda: Integer(2) * "ab", "abab"),
    ("list_times_int", lambda: [0] * Integer(2), [0, 0]),
    # Float
    ("float_add", lambda: Float(1.5) + 1, 2.5),
    ("float_radd", lambda: 1 + Float(1.5), 2.5),
    ("float_sub", lambda: Float(1.5) - 1, 0.5),
    ("float_mul", lambda: Float(1.5) * 2, 3.0),
    ("float_truediv", lambda: Float(3.0) / 2, 1.5),
    ("float_floordiv", lambda: Float(3.5) // 2, 1.0),
    ("float_mod", lambda: Float(3.5) % 2, 1.5),
    ("float_pow", lambda: Float(2.0) ** 3, 8.0),
    ("float_neg", lambda: -Float(1.5), -1.5),
    ("float_abs", lambda: abs(Float(-1.5)), 1.5),
    ("float_to_int", lambda: int(Float(1.9)), 1),
    ("float_to_float", lambda: float(Float(1.5)), 1.5),
    ("float_round_digits", lambda: round(Float(2.567), 2), 2.57),
    ("float_round", lambda: round(Float(2.6)), 3),
    ("float_floor", lambda: math.floor(Float(1.5)), 1),
    ("float_ceil", lambda: math.ceil(Float(1.5)), 2),
    ("float_trunc", lambda: math.trunc(Float(1.9)), 1),
    ("float_format_spec", lambda: format(Float(1.5), ".2f"), "1.50"),
    ("float_to_complex", lambda: complex(Float(1.5)), 1.5 + 0j),
    # String
    ("str_add", lambda: String("a") + "b", "ab"),
    ("str_radd", lambda: "b" + String("a"), "ba"),
    ("str_add_wrapper", lambda: String("a") + String("b"), "ab"),
    ("str_mul", lambda: String("ab") * 2, "abab"),
    ("str_rmul", lambda: 2 * String("ab"), "abab"),
    ("str_mul_integer", lambda: String("ab") * Integer(2), "abab"),
    ("str_len", lambda: len(String("abc")), 3),
    ("str_getitem", lambda: String("abc")[1], "b"),
    ("str_slice", lambda: String("abc")[0:2], "ab"),
    ("str_index_integer", lambda: String("abc")[Integer(1)], "b"),
    ("str_iter", lambda: list(String("ab")), ["a", "b"]),
    ("str_reversed", lambda: "".join(reversed(String("ab"))), "ba"),
    ("str_in", lambda: "b" in String("abc"), True),
    ("str_not_in", lambda: "z" in String("abc"), False),
    ("str_wrapper_in", lambda: String("b") in String("abc"), True),
    ("str_format_tuple", lambda: String("%s-%s") % ("a", True), "a-True"),
    ("str_format_bool", lambda: String("%s") % True, "True"),
    ("str_format_none", lambda: String("%s") % None, "None"),
    ("str_format_wrapper", lambda: String("%d") % Integer(5), "5"),
    ("plain_format_wrapper", lambda: "%s" % String("a"), "a"),
    ("str_format_spec", lambda: format(String("a"), ">3"), "  a"),
    ("str_fstring", lambda: f"{String('a')}", "a"),
    # Bytes
    ("bytes_add", lambda: Bytes(b"a") + b"b", b"ab"),
    ("bytes_radd", lambda: b"b" + Bytes(b"a"), b"ba"),
    ("bytes_mul", lambda: Bytes(b"ab") * 2, b"abab"),
    ("bytes_len", lambda: len(Bytes(b"ab")), 2),
    ("bytes_getitem", lambda: Bytes(b"ab")[0], 97),
    ("bytes_slice", lambda: Bytes(b"abc")[0:2], b"ab"),
    ("bytes_iter", lambda: list(Bytes(b"ab")), [97, 98]),
    ("bytes_convert", lambda: bytes(Bytes(b"ab")), b"ab"),
    ("bytes_int_in", lambda: 65 in Bytes(b"A"), True),
    ("bytes_in", lambda: b"B" in Bytes(b"ABC"), True),
    ("bytes_format", lambda: Bytes(b"%d") % 5, b"5"),
    # Boolean
    ("bool_and", lambda: Boolean(True) & False, False),
    ("bool_or", lambda: Boolean(False) | True, True),
    ("bool_xor", lambda: Boolean(True) ^ True, False),
    ("bool_rand", lambda: True & Boolean(False), False),
    ("bool_ror", lambda: False | Boolean(True), True),
    ("bool_rxor", lambda: True ^ Boolean(True), False),
    ("bool_and_wrapper", lambda: Boolean(True) & Boolean(True), True),
    ("bool_not", lambda: not Boolean(True), False),
]

REFUSED = [
    ("integer_add_bool", lambda: Integer(2) + True),
    ("bool_add_integer", lambda: True + Integer(2)),
    ("integer_add_boolean", lambda: Integer(2) + Boolean(True)),
    ("boolean_add_integer", lambda: Boolean(True) + Integer(2)),
    ("float_add_bool", lambda: Float(1.5) + True),
    ("integer_add_str", lambda: Integer(2) + "x"),
    ("integer_add_none", lambda: Integer(2) + None),
    ("null_add", lambda: Integer() + 1),
    ("add_null", lambda: 1 + Integer()),
    ("integer_add_null", lambda: Integer(1) + Integer()),
    ("null_neg", lambda: -Integer()),
    ("null_abs", lambda: abs(Float())),
    ("null_to_int", lambda: int(Integer())),
    ("null_to_float", lambda: float(Float())),
    ("null_as_index", lambda: "abc"[Integer()]),
    ("null_len", lambda: len(String())),
    ("null_iter", lambda: iter(String())),
    ("in_null", lambda: "a" in String()),
    ("null_getitem", lambda: String()[0]),
    ("null_format", lambda: String() % 1),
    ("null_to_bytes", lambda: bytes(Bytes())),
    ("float_as_range", lambda: range(Float(2.0))),
    ("float_as_index", lambda: "abc"[Float(1.0)]),
    ("float_bitwise", lambda: Float(1.0) & 1),
    ("float_invert", lambda: ~Float(1.0)),
    ("boolean_add", lambda: Boolean(True) + 1),
    ("add_boolean", lambda: 1 + Boolean(True)),
    ("boolean_and_int", lambda: Boolean(True) & 1),
    ("int_and_boolean", lambda: 1 & Boolean(True)),
    ("integer_and_bool", lambda: Integer(1) & True),
    ("boolean_to_int", lambda: int(Boolean(True))),
    ("string_add_int", lambda: String("a") + 1),
    ("string_add_bytes", lambda: String("a") + b"b"),
    ("bytes_add_str", lambda: Bytes(b"a") + "b"),
    ("string_mul_bool", lambda: String("a") * True),
    ("string_mul_float", lambda: String("a") * 1.5),
]

IN_PLACE = [
    (Integer, 5, "iadd", 1, 6),
    (Integer, 5, "isub", 1, 4),
    (Integer, 5, "imul", 2, 10),
    (Integer, 7, "ifloordiv", 2, 3),
    (Integer, 7, "imod", 4, 3),
    (Integer, 2, "ipow", 3, 8),
    (Integer, 6, "iand", 3, 2),
    (Integer, 6, "ior", 1, 7),
    (Integer, 6, "ixor", 3, 5),
    (Integer, 3, "ilshift", 2, 12),
    (Integer, 12, "irshift", 2, 3),
    (Float, 1.5, "iadd", 1, 2.5),
    (Float, 1.5, "isub", 0.5, 1.0),
    (Float, 1.5, "imul", 2, 3.0),
    (Float, 3.0, "itruediv", 2, 1.5),
    (Float, 3.5, "ifloordiv", 2, 1.0),
    (Float, 3.5, "imod", 2, 1.5),
    (Float, 2.0, "ipow", 3, 8.0),
    (String, "a", "iadd", "b", "ab"),
    (String, "ab", "imul", 2, "abab"),
    (String, "%s!", "imod", "x", "x!"),
    (Bytes, b"a", "iadd", b"b", b"ab"),
    (Bytes, b"ab", "imul", 2, b"abab"),
    (Bytes, b"%d", "imod", 5, b"5"),
    (Boolean, True, "iand", False, False),
    (Boolean, False, "ior", True, True),
    (Boolean, True, "ixor", True, False),
]

IN_PLACE_REFUSED = [
    (Integer, 5, "iadd", 0.5),
    (Integer, 5, "iadd", True),
    (Integer, 5, "iadd", "x"),
    (Integer, 5, "iadd", None),
    (Integer, 5, "iadd", Float(1.5)),
    (Integer, 5, "itruediv", 2),
    (Integer, 2, "ipow", -1),
    (Integer, 5, "imul", "x"),
    (Integer, 5, "imul", 1.5),
    (Float, 1.5, "iadd", True),
    (Float, 1.5, "iadd", "x"),
    (Float, 1.5, "iadd", 10 ** 400),
    (Float, -8.0, "ipow", 0.5),
    (String, "a", "iadd", 1),
    (String, "a", "iadd", b"b"),
    (String, "a", "imul", True),
    (String, "a", "imul", 1.5),
    (Bytes, b"a", "iadd", "b"),
    (Bytes, b"a", "iadd", 1),
    (Boolean, True, "iand", 1),
    (Boolean, True, "ior", 0),
    (Boolean, True, "ixor", 1),
]


@pytest.mark.parametrize(
    "expression, expected",
    [row[1:] for row in PLAIN_RESULTS],
    ids=[row[0] for row in PLAIN_RESULTS],
)
def test_operator_returns_plain_value(expression, expected):
    assert same(expression(), expected)


@pytest.mark.parametrize(
    "expression",
    [row[1] for row in REFUSED],
    ids=[row[0] for row in REFUSED],
)
def test_operator_is_refused(expression):
    with pytest.raises(TypeError):
        expression()


def test_binary_operator_leaves_the_wrapper_unchanged():
    wrapper = Integer(5)
    assert wrapper + 1 == 6
    assert wrapper.value == 5


@pytest.mark.parametrize("cls, start, op, argument, expected", IN_PLACE)
def test_in_place_keeps_the_wrapper(cls, start, op, argument, expected):
    wrapper = cls(start)
    result = getattr(operator, op)(wrapper, argument)
    assert result is wrapper
    assert type(result) is cls
    assert same(wrapper.value, expected)


@pytest.mark.parametrize(
    "cls, start, op, argument",
    IN_PLACE_REFUSED,
    ids=lambda item: type(item).__name__ if not isinstance(item, (str, type)) else str(item),
)
def test_in_place_refusal_changes_nothing(cls, start, op, argument):
    wrapper = cls(start)
    with pytest.raises((TypeError, ValueError, OverflowError)):
        getattr(operator, op)(wrapper, argument)
    assert same(wrapper.value, start)


def test_in_place_with_itself_and_with_a_wrapper():
    wrapper = Integer(2)
    wrapper += wrapper
    assert wrapper.value == 4
    wrapper += Integer(3)
    assert wrapper.value == 7
    assert type(wrapper) is Integer


def test_in_place_on_null_is_refused():
    wrapper = Integer()
    with pytest.raises(TypeError):
        wrapper += 1
    assert wrapper.is_null()


def test_integer_division_in_place_raises_the_type_error():
    wrapper = Integer(6)
    with pytest.raises(PrimitiveTypeError):
        wrapper /= 2
    assert same(wrapper.value, 6)
