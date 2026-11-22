"""Integer, Float, Boolean and Bytes methods."""
import functools
import math

import pytest

from primitives import Boolean, Bytes, Float, Integer, PrimitiveTypeError, String
from samples import same

MAX, MIN = 2147483647, -2147483648

INTEGER = [
    ("bitCount", (255,), 8), ("bitCount", (-1,), 32), ("bitCount", (MIN,), 1),
    ("compare", (1, 2), -1), ("compare", (2, 2), 0), ("compare", (3, 2), 1),
    ("compareUnsigned", (-1, 1), 1), ("compareUnsigned", (1, -1), -1),
    ("compress", (0b10110, 0b11100), 0b101), ("expand", (0b101, 0b11100), 0b10100),
    ("compress", (-1, -1), -1), ("expand", (-1, MIN), MIN),
    ("divideUnsigned", (-1, 2), MAX), ("remainderUnsigned", (-1, 2), 1),
    ("divideUnsigned", (-2, -1), 0), ("remainderUnsigned", (-2, -1), -2),
    ("highestOneBit", (100,), 64), ("highestOneBit", (-1,), MIN), ("highestOneBit", (0,), 0),
    ("lowestOneBit", (100,), 4), ("lowestOneBit", (MIN,), MIN), ("lowestOneBit", (0,), 0),
    ("max", (3, 9), 9), ("min", (3, 9), 3),
    ("numberOfLeadingZeros", (1,), 31), ("numberOfLeadingZeros", (0,), 32), ("numberOfLeadingZeros", (-1,), 0),
    ("numberOfTrailingZeros", (8,), 3), ("numberOfTrailingZeros", (0,), 32), ("numberOfTrailingZeros", (MIN,), 31),
    ("reverse", (1,), MIN), ("reverse", (-1,), -1), ("reverse", (0x0F,), -268435456),
    ("reverseBytes", (0x01020304,), 0x04030201), ("reverseBytes", (0xFF,), -16777216),
    ("rotateLeft", (1, 1), 2), ("rotateLeft", (MIN, 1), 1), ("rotateLeft", (1, 33), 2), ("rotateLeft", (1, -1), MIN),
    ("rotateRight", (1, 1), MIN), ("rotateRight", (2, 1), 1), ("rotateRight", (1, 32), 1),
    ("signum", (-9,), -1), ("signum", (0,), 0), ("signum", (9,), 1),
    ("sum", (MAX, 1), MIN), ("sum", (2, 3), 5),
    ("toUnsignedLong", (-1,), 4294967295), ("hashCode", (42,), 42),
]

INTEGER_TEXT = [
    ("toBinaryString", (5,), "101"), ("toBinaryString", (-1,), "1" * 32),
    ("toHexString", (255,), "ff"), ("toHexString", (-1,), "ffffffff"), ("toHexString", (MIN,), "80000000"),
    ("toOctalString", (8,), "10"), ("toOctalString", (-1,), "37777777777"),
    ("toString", (255,), "255"), ("toString", (255, 16), "ff"), ("toString", (-255, 16), "-ff"),
    ("toString", (35, 36), "z"), ("toString", (10, 99), "10"), ("toString", (MIN, 2), "-1" + "0" * 31),
    ("toUnsignedString", (-1,), "4294967295"), ("toUnsignedString", (-1, 16), "ffffffff"),
]

PARSE_INT = [
    (("0",), 0), (("473",), 473), (("+42",), 42), (("-0",), 0), (("-FF", 16), -255),
    (("1100110", 2), 102), (("2147483647",), MAX), (("-2147483648",), MIN),
    (("-80000000", 16), MIN), (("Kona", 27), 411787), (("\u0663",), 3), (("\uff46", 16), 15),
    (("xx42yy", 2, 4, 10), 42),
]
PARSE_INT_BAD = [
    ("",), ("-",), ("+",), ("2147483648",), ("-2147483649",), ("99", 8), ("Kona", 10),
    (" 5",), ("5 ",), ("1.5",), ("0x10",), (None,), ("5", 1), ("5", 37),
]


@pytest.mark.parametrize("name, args, expected", INTEGER)
def test_integer_static(name, args, expected):
    assert same(getattr(Integer, name)(*args), expected)


@pytest.mark.parametrize("name, args, expected", INTEGER)
def test_integer_static_fills_first_argument_from_the_instance(name, args, expected):
    assert same(getattr(Integer(args[0]), name)(*args[1:]), expected)


@pytest.mark.parametrize("name, args, expected", INTEGER_TEXT)
def test_integer_text_returns_a_string_wrapper(name, args, expected):
    result = getattr(Integer, name)(*args)
    assert type(result) is String and result == expected


@pytest.mark.parametrize("args, expected", PARSE_INT)
def test_parse_int(args, expected):
    assert same(Integer.parseInt(*args), expected)


@pytest.mark.parametrize("args", PARSE_INT_BAD, ids=repr)
def test_parse_int_rejects(args):
    with pytest.raises(ValueError):
        Integer.parseInt(*args)


@pytest.mark.parametrize("text, expected", [("0", 0), ("4294967295", -1), ("+1", 1), ("2147483648", MIN)])
def test_parse_unsigned_int(text, expected):
    assert same(Integer.parseUnsignedInt(text), expected)


@pytest.mark.parametrize("text", ["-1", "4294967296", ""])
def test_parse_unsigned_int_rejects(text):
    with pytest.raises(ValueError):
        Integer.parseUnsignedInt(text)


@pytest.mark.parametrize("text, expected", [
    ("0", 0), ("10", 10), ("-10", -10), ("+10", 10), ("0x1F", 31), ("0X1f", 31), ("#1F", 31),
    ("010", 8), ("-0x80000000", MIN), ("-010", -8),
])
def test_decode(text, expected):
    result = Integer.decode(text)
    assert type(result) is Integer and result.value == expected


@pytest.mark.parametrize("text", ["", "0x", "#", "-", "0x-5", "08", "0x80000000", "2147483648"])
def test_decode_rejects(text):
    with pytest.raises(ValueError):
        Integer.decode(text)


def test_integer_number_conversions():
    number = Integer(0x12345678)
    assert number.byteValue() == 0x78 and number.shortValue() == 0x5678
    assert number.intValue() == number.longValue() == 0x12345678
    assert same(number.doubleValue(), 305419896.0)
    assert same(number.floatValue(), 305419904.0)  # rounded to 24 bits
    assert Integer(200).byteValue() == -56 and Integer(40000).shortValue() == -25536


def test_integer_equals_is_type_strict():
    assert Integer(5).equals(5) and Integer(5).equals(Integer(5))
    assert not Integer(5).equals(5.0) and not Integer(1).equals(True)
    assert not Integer(5).equals(Float(5.0)) and not Integer(5).equals(None)


def test_integer_value_of_returns_the_calling_class():
    class Age(Integer):
        def is_valid(self):
            return self._value >= 0

    assert type(Age.valueOf("5")) is Age
    with pytest.raises(ValueError):
        Age.valueOf(-1)


def test_integer_outside_32_bits_is_refused_rather_than_wrapped():
    big = Integer(2 ** 40)
    assert big + 1 == 2 ** 40 + 1
    for call in (big.bitCount, big.intValue, big.toString):
        with pytest.raises(OverflowError):
            call()


@pytest.mark.parametrize("bad", [True, 1.5, "1", None, Boolean(True)], ids=repr)
def test_integer_static_arguments_are_type_locked(bad):
    with pytest.raises(PrimitiveTypeError):
        Integer.bitCount(bad)


def test_unsigned_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        Integer.divideUnsigned(1, 0)
    with pytest.raises(ZeroDivisionError):
        Integer.remainderUnsigned(1, 0)


def test_get_integer_reads_the_environment(monkeypatch):
    monkeypatch.setenv("PRIM_NUM", "0x10")
    monkeypatch.setenv("PRIM_BAD", "nope")
    monkeypatch.delenv("PRIM_NONE", raising=False)
    assert Integer.getInteger("PRIM_NUM").value == 16
    assert Integer.getInteger("PRIM_BAD") is None
    assert Integer.getInteger("PRIM_BAD", 7).value == 7
    assert Integer.getInteger("PRIM_NONE", Integer(9)).value == 9
    assert Integer.getInteger("") is None and Integer.getInteger(None) is None


# --- Float ---

FLOAT_TEXT = [
    (1.0, "1.0"), (0.1, "0.1"), (-0.0, "-0.0"), (0.0, "0.0"), (100.0, "100.0"),
    (1.5, "1.5"), (3.14159274, "3.1415927"), (1e7, "1.0E7"), (9999999.0, "9999999.0"),
    (1e-3, "0.001"), (9.999e-4, "9.999E-4"), (1.17549435e-38, "1.1754944E-38"),
    (3.4028235e38, "3.4028235E38"), (1.4e-45, "1.4E-45"), (3e-45, "2.8E-45"),
    (33554432.0, "3.3554432E7"), (1.0e10, "1.0E10"), (123456.7, "123456.7"),
    (math.inf, "Infinity"), (-math.inf, "-Infinity"), (math.nan, "NaN"),
]

FLOAT_HEX = [
    (1.0, "0x1.0p0"), (-1.0, "-0x1.0p0"), (2.0, "0x1.0p1"), (3.0, "0x1.8p1"), (0.5, "0x1.0p-1"),
    (0.25, "0x1.0p-2"), (Float.MAX_VALUE, "0x1.fffffep127"), (Float.MIN_NORMAL, "0x1.0p-126"),
    (Float.MIN_VALUE, "0x0.000002p-126"), (Float.MIN_NORMAL / 2, "0x0.8p-126"),
    (0.0, "0x0.0p0"), (-0.0, "-0x0.0p0"), (math.inf, "Infinity"), (math.nan, "NaN"),
]

PARSE_FLOAT = [
    ("1", 1.0), ("1.5", 1.5), ("-1.5", -1.5), ("+2", 2.0), (".5", 0.5), ("5.", 5.0),
    ("1e3", 1000.0), ("1E-1", Float.intBitsToFloat(0x3DCCCCCD)), ("1.5f", 1.5), ("1.5F", 1.5),
    ("2.5d", 2.5), ("2.5D", 2.5), ("  7 \n", 7.0), ("Infinity", math.inf), ("-Infinity", -math.inf),
    ("0x1.8p1", 3.0), ("0X1P-1", 0.5), ("0x.8p1", 1.0), ("0x1.p0f", 1.0), ("1e39", math.inf),
    ("1e-50", 0.0), ("3.4028235e38", Float.MAX_VALUE), ("1.4e-45", Float.MIN_VALUE),
    ("1" + "0" * 5000 + "e-5000", 1.0), ("1e99999999999999", math.inf), ("0e99999999999999", 0.0),
]


@pytest.mark.parametrize("value, expected", FLOAT_TEXT, ids=repr)
def test_float_to_string(value, expected):
    result = Float.toString(value)
    assert type(result) is String and result == expected


@pytest.mark.parametrize("value, expected", FLOAT_HEX, ids=repr)
def test_float_to_hex_string(value, expected):
    assert Float.toHexString(value) == expected


@pytest.mark.parametrize("text, expected", PARSE_FLOAT, ids=lambda item: repr(item)[:24])
def test_parse_float(text, expected):
    assert same(Float.parseFloat(text), expected)


def test_parse_float_rounds_exactly_without_double_rounding():
    # Just above the halfway point between 1 and the next float.
    assert Float.floatToIntBits(Float.parseFloat("1.00000005960464477539062500001")) == 0x3F800001
    assert Float.floatToIntBits(Float.parseFloat("1.000000059604644775390625")) == 0x3F800000


def test_parse_float_nan_and_negative_zero():
    assert math.isnan(Float.parseFloat("NaN")) and math.isnan(Float.parseFloat("-NaN"))
    assert math.copysign(1.0, Float.parseFloat("-0")) == -1.0


@pytest.mark.parametrize("text", ["", " ", "abc", "1e", "1.5x", "0x1.8", "NaNf", "Infinityf", "1_000", "\u0661"])
def test_parse_float_rejects(text):
    with pytest.raises(ValueError):
        Float.parseFloat(text)


def test_parse_float_null():
    with pytest.raises(TypeError):
        Float.parseFloat(None)


@pytest.mark.parametrize("value, bits", [
    (1.0, 0x3F800000), (-2.0, -0x40000000), (0.0, 0), (-0.0, MIN), (math.inf, 0x7F800000),
    (-math.inf, -0x800000), (math.nan, 0x7FC00000), (0.1, 0x3DCCCCCD), (1e300, 0x7F800000),
])
def test_float_bits(value, bits):
    assert Float.floatToIntBits(value) == bits
    assert Float.hashCode(value) == bits


@pytest.mark.parametrize("bits", [0, 1, 0x3F800000, MIN, -1 ^ 0x7FFFFF, 0x7F7FFFFF, 0x00800000])
def test_float_bits_round_trip(bits):
    assert Float.floatToRawIntBits(Float.intBitsToFloat(bits)) == bits


def test_float_compare_total_order():
    ordered = [-math.inf, -1.0, -0.0, 0.0, 1.0, math.inf, math.nan]
    for i, left in enumerate(ordered):
        for j, right in enumerate(ordered):
            assert Float.compare(left, right) == (i > j) - (i < j)


def test_float_equals_uses_bits():
    assert Float(math.nan).equals(Float(math.nan)) and not Float(0.0).equals(-0.0)
    assert Float(1.5).equals(1.5) and not Float(1.0).equals(1) and not Float(1.0).equals(None)


def test_float_min_max_sum():
    assert math.copysign(1.0, Float.max(-0.0, 0.0)) == 1.0
    assert math.copysign(1.0, Float.min(0.0, -0.0)) == -1.0
    assert math.isnan(Float.max(math.nan, 1.0)) and math.isnan(Float.min(1.0, math.nan))
    assert Float.max(1.0, 2.0) == 2.0 and Float.min(1.0, 2.0) == 1.0
    assert Float.floatToIntBits(Float.sum(0.1, 0.2)) == 0x3E99999A
    assert Float.sum(Float.MAX_VALUE, Float.MAX_VALUE) == math.inf


@pytest.mark.parametrize("value, as_int, as_long, as_short, as_byte", [
    (3.9, 3, 3, 3, 3), (-3.9, -3, -3, -3, -3), (math.nan, 0, 0, 0, 0),
    (1e10, MAX, 10000000000, -1, -1), (-1e10, MIN, -10000000000, 0, 0),
    (math.inf, MAX, 2 ** 63 - 1, -1, -1), (-math.inf, MIN, -2 ** 63, 0, 0), (300.0, 300, 300, 300, 44),
])
def test_float_narrowing(value, as_int, as_long, as_short, as_byte):
    number = Float(value)
    assert number.intValue() == as_int and number.shortValue() == as_short and number.byteValue() == as_byte
    if abs(value) != 1e10:
        assert number.longValue() == as_long


def test_float_value_is_seen_as_32_bits_but_stored_unchanged():
    number = Float(0.1)
    assert number.value == 0.1
    assert number.floatValue() == number.doubleValue() == 0.10000000149011612
    assert number.toString() == "0.1"
    assert Float(1e300).isInfinite() and Float(1e300).value == 1e300


def test_float_classification():
    assert Float(math.nan).isNaN() and Float.isNaN(math.nan) and not Float.isNaN(1.0)
    assert Float.isInfinite(math.inf) and not Float.isInfinite(1.0)
    assert Float.isFinite(1.0) and not Float.isFinite(math.nan) and not Float.isFinite(math.inf)


def test_float_constants():
    assert Float.MAX_VALUE == float.fromhex("0x1.fffffep127")
    assert Float.MIN_NORMAL == 2.0 ** -126 and Float.MIN_VALUE == 2.0 ** -149
    assert (Float.SIZE, Float.BYTES, Float.PRECISION, Float.MAX_EXPONENT, Float.MIN_EXPONENT) == (32, 4, 24, 127, -126)
    assert math.isnan(Float.NaN) and Float.POSITIVE_INFINITY == math.inf and Float.NEGATIVE_INFINITY == -math.inf


@pytest.mark.parametrize("bits, value", [
    (0x0000, 0.0), (0x3C00, 1.0), (0xC000 - 0x10000, -2.0), (0x7C00, math.inf), (0xFC00 - 0x10000, -math.inf),
    (0x0001, 2.0 ** -24), (0x03FF, 1023 * 2.0 ** -24), (0x0400, 2.0 ** -14), (0x7BFF, 65504.0), (0x3555, 0.333251953125),
])
def test_float16_conversions(bits, value):
    assert Float.float16ToFloat(bits) == value
    assert Float.floatToFloat16(value) == bits


def test_float16_rounding_and_nan():
    assert Float.floatToFloat16(65520.0) == 0x7C00  # halfway to overflow rounds up
    assert Float.floatToFloat16(1e-10) == 0
    assert math.isnan(Float.float16ToFloat(0x7E00))
    assert Float.floatToFloat16(math.nan) == 0x7E00


# --- Boolean ---

@pytest.mark.parametrize("text, expected", [
    ("true", True), ("TRUE", True), ("TrUe", True), ("false", False), ("yes", False),
    ("1", False), ("", False), (" true", False), (None, False),
])
def test_parse_boolean(text, expected):
    assert Boolean.parseBoolean(text) is expected
    assert Boolean.valueOf(text).value is expected


def test_boolean_statics():
    assert Boolean.logicalAnd(True, False) is False and Boolean.logicalOr(True, False) is True
    assert Boolean.logicalXor(True, True) is False
    assert Boolean.compare(True, False) == 1 and Boolean.compare(False, True) == -1
    assert Boolean.compare(True, True) == 0
    assert Boolean.hashCode(True) == 1231 and Boolean.hashCode(False) == 1237
    assert Boolean.toString(True) == "true" and Boolean(False).toString() == "false"
    assert Boolean(True).booleanValue() is True and Boolean(True).compareTo(False) == 1


def test_boolean_constants_cannot_be_corrupted():
    flag = Boolean.TRUE
    flag.value = False
    assert Boolean.TRUE.value is True and Boolean.FALSE.value is False
    assert Boolean.TYPE is bool


def test_boolean_equals_is_type_strict():
    assert Boolean(True).equals(True) and Boolean(True).equals(Boolean(True))
    assert not Boolean(True).equals(1)


def test_get_boolean(monkeypatch):
    monkeypatch.setenv("PRIM_FLAG", "TRUE")
    monkeypatch.setenv("PRIM_OTHER", "1")
    monkeypatch.delenv("PRIM_NONE", raising=False)
    assert Boolean.getBoolean("PRIM_FLAG") is True
    assert Boolean.getBoolean("PRIM_OTHER") is False
    assert Boolean.getBoolean("PRIM_NONE") is False
    assert not Boolean.getBoolean("") and not Boolean.getBoolean(None)


# --- Byte ---

def test_byte_constants():
    assert (Bytes.MIN_VALUE, Bytes.MAX_VALUE, Bytes.SIZE, Bytes.BYTES) == (-128, 127, 8, 1)


@pytest.mark.parametrize("raw, signed, unsigned", [(b"\x00", 0, 0), (b"\x7f", 127, 127), (b"\x80", -128, 128), (b"\xff", -1, 255)])
def test_byte_values(raw, signed, unsigned):
    value = Bytes(raw)
    assert value.byteValue() == value.shortValue() == value.intValue() == value.longValue() == signed
    assert same(value.floatValue(), float(signed)) and same(value.doubleValue(), float(signed))
    assert value.toUnsignedInt() == value.toUnsignedLong() == unsigned
    assert value.hashCode() == signed and value.toString() == str(signed)
    assert Bytes.toUnsignedInt(signed) == unsigned


def test_byte_statics():
    assert Bytes.compare(-1, 1) == -2 and Bytes.compareUnsigned(-1, 1) == 254
    assert Bytes(b"\x05").compareTo(b"\x03") == 2
    assert Bytes.parseByte("-128") == -128 and Bytes.parseByte("7f", 16) == 127
    assert Bytes.valueOf("-1").value == b"\xff" and Bytes.valueOf(-1).value == b"\xff"
    assert Bytes.valueOf("10", 16).value == b"\x10"
    assert Bytes.decode("0x7f").value == b"\x7f" and Bytes.decode("-0x80").value == b"\x80"


@pytest.mark.parametrize("call", [
    lambda: Bytes.parseByte("128"), lambda: Bytes.parseByte("-129"), lambda: Bytes.decode("0x80"),
    lambda: Bytes(b"ab").intValue(), lambda: Bytes(b"").toString(),
])
def test_byte_rejects(call):
    with pytest.raises(ValueError):
        call()


def test_byte_range_is_enforced_for_numbers():
    with pytest.raises(OverflowError):
        Bytes.toUnsignedInt(200)


def test_get_class():
    assert Integer(1).getClass() is Integer and String("a").getClass() is String


def test_sorting_with_compare_methods():
    values = [3, -1, 2]
    assert sorted(values, key=functools.cmp_to_key(Integer.compareUnsigned)) == [2, 3, -1]
