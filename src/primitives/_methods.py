"""The method API for Integer, Float, Boolean and Bytes.

These methods read the value at a fixed width: Integer as a 32-bit int,
Float as a 32-bit float, Bytes as a single signed byte.
"""
import functools
import math
import os
from typing import Any, Callable, Generic, Optional, Type, TypeVar, cast

from . import _numbers as num
from . import core as _core
from ._native import Dual, unwrapped

R = TypeVar("R")
W = TypeVar("W")


class _static(Generic[R]):
    """Callable on the class, or on an instance whose value becomes the first argument."""

    def __init__(self, function: Callable[..., R]) -> None:
        self._function = function
        self.__doc__ = function.__doc__

    def __get__(self, obj: Any, owner: Optional[type] = None) -> Callable[..., R]:
        function = self._function
        kind = type(obj) if owner is None else owner
        if obj is None:
            return functools.partial(function, kind)

        def bound(*args: Any, **kwargs: Any) -> R:
            if obj._value is None:
                raise TypeError(f"null {kind.__name__} has no value")
            return function(kind, obj._value, *args, **kwargs)
        return bound


class _Constant:
    """Boolean.TRUE and FALSE. Each read is a new wrapper, so a constant can't be mutated."""

    def __init__(self, value: bool) -> None:
        self._constant = value

    def __get__(self, obj: Any, owner: Optional[type] = None) -> Any:
        kind = type(obj) if owner is None else owner
        return kind(self._constant)


def _make(kind: Type[W], value: Any) -> W:
    return cast(Callable[[Any], W], kind)(value)


def _text(value: str) -> "_core.String":
    return _core.String(value)


# ==========================================
# Argument Checks
# ==========================================

def int_arg(value: Any) -> int:
    raw = _core._raw(value)
    if type(raw) is not int:
        raise _core.PrimitiveTypeError(f"expected a 32-bit int, got {type(raw).__name__}")
    if not num.INT_MIN <= raw <= num.INT_MAX:
        raise OverflowError(f"{raw} does not fit in a 32-bit int")
    return raw


def _float_arg(value: Any) -> float:
    raw = _core._raw(value)
    if type(raw) is int:
        return num.int_to_float32(raw)
    if type(raw) is not float:
        raise _core.PrimitiveTypeError(f"expected a float, got {type(raw).__name__}")
    return num.narrow(raw)


def _byte_arg(value: Any) -> int:
    raw = _core._raw(value)
    if type(raw) is bytes:
        if len(raw) != 1:
            raise ValueError(f"expected exactly one byte, this value has {len(raw)}")
        return num.wrap(raw[0], 8)
    if type(raw) is not int:
        raise _core.PrimitiveTypeError(f"expected a single byte, got {type(raw).__name__}")
    if not num.BYTE_MIN <= raw <= num.BYTE_MAX:
        raise OverflowError(f"{raw} does not fit in a signed byte")
    return raw


def _bool_arg(value: Any) -> bool:
    raw = _core._raw(value)
    if type(raw) is not bool:
        raise _core.PrimitiveTypeError(f"expected a boolean, got {type(raw).__name__}")
    return raw


def _optional_text(value: Any) -> Optional[str]:
    raw = _core._raw(value)
    if raw is not None and type(raw) is not str:
        raise _core.PrimitiveTypeError(f"expected a String, got {type(raw).__name__}")
    return raw


def _compare(left: Any, right: Any) -> int:
    return int(left > right) - int(left < right)


class _BaseMethods:
    __slots__ = ()
    _value: Any

    def _present(self) -> Any:
        if self._value is None:
            raise TypeError(f"null {type(self).__name__} has no value")
        return self._value

    def getClass(self) -> type:
        return type(self)


# ==========================================
# Integer
# ==========================================

class _IntegerMethods(_BaseMethods):
    __slots__ = ()

    MIN_VALUE = num.INT_MIN
    MAX_VALUE = num.INT_MAX
    SIZE = 32
    BYTES = 4
    TYPE = int

    # --- Number ---

    def byteValue(self) -> int:
        return num.wrap(int_arg(self._present()), 8)

    def shortValue(self) -> int:
        return num.wrap(int_arg(self._present()), 16)

    def intValue(self) -> int:
        return int_arg(self._present())

    def longValue(self) -> int:
        return int_arg(self._present())

    def floatValue(self) -> float:
        return num.int_to_float32(int_arg(self._present()))

    def doubleValue(self) -> float:
        return float(int_arg(self._present()))

    # --- Equality and Ordering ---

    def equals(self, other: Any) -> bool:
        value = self._present()
        raw = _core._raw(other)
        return type(raw) is int and raw == value

    def compareTo(self, other: Any) -> int:
        return _compare(int_arg(self._present()), int_arg(other))

    @_static
    def hashCode(cls: Any, value: Any) -> int:
        return int_arg(value)

    @_static
    def toString(cls: Any, value: Any, radix: Any = 10) -> "_core.String":
        return _text(num.to_radix(int_arg(value), int_arg(radix)))

    # --- Parsing ---

    @classmethod
    def parseInt(cls, s: Any, *rest: Any) -> int:
        return _parse(s, rest, num.INT_MIN, num.INT_MAX, False)

    @classmethod
    def parseUnsignedInt(cls, s: Any, *rest: Any) -> int:
        return num.wrap(_parse(s, rest, 0, num.UINT_MAX, True), 32)

    @classmethod
    def valueOf(cls: Type[W], value: Any, radix: Any = None) -> W:
        raw = _core._raw(value)
        if type(raw) is str or raw is None:
            base = 10 if radix is None else int_arg(radix)
            return _make(cls, num.parse_integral(raw, base, num.INT_MIN, num.INT_MAX))
        if radix is not None:
            raise _core.PrimitiveTypeError("a radix is only valid with a String")
        return _make(cls, int_arg(raw))

    @classmethod
    def decode(cls: Type[W], nm: Any) -> W:
        return _make(cls, num.decode_integral(_optional_text(nm), num.INT_MIN, num.INT_MAX))

    @classmethod
    def getInteger(cls: Type[W], nm: Any, val: Any = None) -> Optional[W]:
        """Read a setting from the environment."""
        fallback = None if _core._raw(val) is None else _make(cls, int_arg(val))
        name = _optional_text(nm)
        setting = os.environ.get(name) if name else None
        if setting is None:
            return fallback
        try:
            return _make(cls, num.decode_integral(setting, num.INT_MIN, num.INT_MAX))
        except ValueError:
            return fallback

    # --- Arithmetic ---

    @_static
    def compare(cls: Any, x: Any, y: Any) -> int:
        return _compare(int_arg(x), int_arg(y))

    @_static
    def compareUnsigned(cls: Any, x: Any, y: Any) -> int:
        return _compare(int_arg(x) & num.UINT_MAX, int_arg(y) & num.UINT_MAX)

    @_static
    def sum(cls: Any, a: Any, b: Any) -> int:
        return num.wrap(int_arg(a) + int_arg(b), 32)

    @_static
    def max(cls: Any, a: Any, b: Any) -> int:
        left, right = int_arg(a), int_arg(b)
        return left if left >= right else right

    @_static
    def min(cls: Any, a: Any, b: Any) -> int:
        left, right = int_arg(a), int_arg(b)
        return left if left <= right else right

    @_static
    def signum(cls: Any, i: Any) -> int:
        return _compare(int_arg(i), 0)

    @_static
    def divideUnsigned(cls: Any, dividend: Any, divisor: Any) -> int:
        top, bottom = int_arg(dividend) & num.UINT_MAX, int_arg(divisor) & num.UINT_MAX
        if bottom == 0:
            raise ZeroDivisionError("/ by zero")
        return num.wrap(top // bottom, 32)

    @_static
    def remainderUnsigned(cls: Any, dividend: Any, divisor: Any) -> int:
        top, bottom = int_arg(dividend) & num.UINT_MAX, int_arg(divisor) & num.UINT_MAX
        if bottom == 0:
            raise ZeroDivisionError("/ by zero")
        return num.wrap(top % bottom, 32)

    @_static
    def toUnsignedLong(cls: Any, x: Any) -> int:
        return int_arg(x) & num.UINT_MAX

    # --- Bits ---

    @_static
    def bitCount(cls: Any, i: Any) -> int:
        return bin(int_arg(i) & num.UINT_MAX).count("1")

    @_static
    def highestOneBit(cls: Any, i: Any) -> int:
        bits = int_arg(i) & num.UINT_MAX
        return num.wrap(1 << (bits.bit_length() - 1), 32) if bits else 0

    @_static
    def lowestOneBit(cls: Any, i: Any) -> int:
        bits = int_arg(i) & num.UINT_MAX
        return num.wrap(bits & -bits, 32)

    @_static
    def numberOfLeadingZeros(cls: Any, i: Any) -> int:
        return 32 - (int_arg(i) & num.UINT_MAX).bit_length()

    @_static
    def numberOfTrailingZeros(cls: Any, i: Any) -> int:
        bits = int_arg(i) & num.UINT_MAX
        return (bits & -bits).bit_length() - 1 if bits else 32

    @_static
    def reverse(cls: Any, i: Any) -> int:
        return num.wrap(int(format(int_arg(i) & num.UINT_MAX, "032b")[::-1], 2), 32)

    @_static
    def reverseBytes(cls: Any, i: Any) -> int:
        raw = (int_arg(i) & num.UINT_MAX).to_bytes(4, "big")
        return num.wrap(int.from_bytes(raw, "little"), 32)

    @_static
    def rotateLeft(cls: Any, i: Any, distance: Any) -> int:
        bits, turn = int_arg(i) & num.UINT_MAX, int_arg(distance) & 31
        return num.wrap(((bits << turn) | (bits >> (32 - turn))) & num.UINT_MAX, 32)

    @_static
    def rotateRight(cls: Any, i: Any, distance: Any) -> int:
        bits, turn = int_arg(i) & num.UINT_MAX, int_arg(distance) & 31
        return num.wrap(((bits >> turn) | (bits << (32 - turn))) & num.UINT_MAX, 32)

    @_static
    def compress(cls: Any, i: Any, mask: Any) -> int:
        bits, selector = int_arg(i) & num.UINT_MAX, int_arg(mask) & num.UINT_MAX
        result = position = 0
        for bit in range(32):
            if selector >> bit & 1:
                result |= (bits >> bit & 1) << position
                position += 1
        return num.wrap(result, 32)

    @_static
    def expand(cls: Any, i: Any, mask: Any) -> int:
        bits, selector = int_arg(i) & num.UINT_MAX, int_arg(mask) & num.UINT_MAX
        result = position = 0
        for bit in range(32):
            if selector >> bit & 1:
                result |= (bits >> position & 1) << bit
                position += 1
        return num.wrap(result, 32)

    # --- Text ---

    @_static
    def toBinaryString(cls: Any, i: Any) -> "_core.String":
        return _text(format(int_arg(i) & num.UINT_MAX, "b"))

    @_static
    def toOctalString(cls: Any, i: Any) -> "_core.String":
        return _text(format(int_arg(i) & num.UINT_MAX, "o"))

    @_static
    def toHexString(cls: Any, i: Any) -> "_core.String":
        return _text(format(int_arg(i) & num.UINT_MAX, "x"))

    @_static
    def toUnsignedString(cls: Any, i: Any, radix: Any = 10) -> "_core.String":
        return _text(num.to_radix(int_arg(i) & num.UINT_MAX, int_arg(radix)))


def _parse(s: Any, rest: Any, low: int, high: int, unsigned: bool) -> int:
    """parseInt(s), parseInt(s, radix) and parseInt(s, begin, end, radix)."""
    text = _optional_text(s)
    if len(rest) == 0:
        return num.parse_integral(text, 10, low, high, unsigned)
    if len(rest) == 1:
        return num.parse_integral(text, int_arg(rest[0]), low, high, unsigned)
    if len(rest) != 3:
        raise TypeError("expected (s), (s, radix) or (s, beginIndex, endIndex, radix)")
    if text is None:
        raise TypeError("cannot parse null")
    begin, end, radix = int_arg(rest[0]), int_arg(rest[1]), int_arg(rest[2])
    units = num.to_units(text)
    if begin < 0 or begin > end or end > len(units):
        raise IndexError(f"begin {begin}, end {end}, length {len(units)}")
    return num.parse_integral(num.from_units(units[begin:end]), radix, low, high, unsigned)


# ==========================================
# Float
# ==========================================

def _compare_float(left: float, right: float) -> int:
    if left < right:
        return -1
    if left > right:
        return 1
    return _compare(num.float_to_bits(left), num.float_to_bits(right))


class _FloatMethods(_BaseMethods):
    __slots__ = ()

    SIZE = 32
    BYTES = 4
    PRECISION = 24
    MAX_EXPONENT = 127
    MIN_EXPONENT = -126
    MAX_VALUE = num.FLOAT_MAX
    MIN_NORMAL = num.FLOAT_MIN_NORMAL
    MIN_VALUE = num.FLOAT_MIN
    NaN = math.nan
    POSITIVE_INFINITY = math.inf
    NEGATIVE_INFINITY = -math.inf
    TYPE = float

    def _float(self) -> float:
        return _float_arg(self._present())

    # --- Number ---

    def byteValue(self) -> int:
        return num.wrap(num.float_to_integral(self._float(), 32), 8)

    def shortValue(self) -> int:
        return num.wrap(num.float_to_integral(self._float(), 32), 16)

    def intValue(self) -> int:
        return num.float_to_integral(self._float(), 32)

    def longValue(self) -> int:
        return num.float_to_integral(self._float(), 64)

    def floatValue(self) -> float:
        return self._float()

    def doubleValue(self) -> float:
        return self._float()

    # --- Equality and Ordering ---

    def equals(self, other: Any) -> bool:
        value = self._float()
        raw = _core._raw(other)
        if type(raw) is not float:
            return False
        return num.float_to_bits(value) == num.float_to_bits(num.narrow(raw))

    def compareTo(self, other: Any) -> int:
        return _compare_float(self._float(), _float_arg(other))

    @_static
    def hashCode(cls: Any, value: Any) -> int:
        return num.float_to_bits(_float_arg(value))

    @_static
    def toString(cls: Any, value: Any) -> "_core.String":
        return _text(num.float_to_string(_float_arg(value)))

    @_static
    def toHexString(cls: Any, value: Any) -> "_core.String":
        return _text(num.float_to_hex(_float_arg(value)))

    # --- Parsing ---

    @classmethod
    def parseFloat(cls, s: Any) -> float:
        return num.parse_float(_optional_text(s))

    @classmethod
    def valueOf(cls: Type[W], value: Any) -> W:
        raw = _core._raw(value)
        if type(raw) is str or raw is None:
            return _make(cls, num.parse_float(raw))
        return _make(cls, _float_arg(raw))

    # --- Classification ---

    @_static
    def isNaN(cls: Any, value: Any) -> bool:
        return math.isnan(_float_arg(value))

    @_static
    def isInfinite(cls: Any, value: Any) -> bool:
        return math.isinf(_float_arg(value))

    @_static
    def isFinite(cls: Any, value: Any) -> bool:
        return math.isfinite(_float_arg(value))

    # --- Arithmetic ---

    @_static
    def compare(cls: Any, f1: Any, f2: Any) -> int:
        return _compare_float(_float_arg(f1), _float_arg(f2))

    @_static
    def sum(cls: Any, a: Any, b: Any) -> float:
        return num.narrow(_float_arg(a) + _float_arg(b))

    @_static
    def max(cls: Any, a: Any, b: Any) -> float:
        left, right = _float_arg(a), _float_arg(b)
        if math.isnan(left) or math.isnan(right):
            return math.nan
        if left == right == 0:
            return left if math.copysign(1.0, left) > 0 else right
        return left if left >= right else right

    @_static
    def min(cls: Any, a: Any, b: Any) -> float:
        left, right = _float_arg(a), _float_arg(b)
        if math.isnan(left) or math.isnan(right):
            return math.nan
        if left == right == 0:
            return left if math.copysign(1.0, left) < 0 else right
        return left if left <= right else right

    # --- Bits ---

    @_static
    def floatToIntBits(cls: Any, value: Any) -> int:
        return num.float_to_bits(_float_arg(value))

    @_static
    def floatToRawIntBits(cls: Any, value: Any) -> int:
        return num.float_to_raw_bits(_float_arg(value))

    @staticmethod
    def intBitsToFloat(bits: Any) -> float:
        return num.bits_to_float(int_arg(bits))

    @staticmethod
    def float16ToFloat(bits: Any) -> float:
        raw = _core._raw(bits)
        if type(raw) is not int:
            raise _core.PrimitiveTypeError(f"expected a 16-bit int, got {type(raw).__name__}")
        if not -32768 <= raw <= 32767:
            raise OverflowError(f"{raw} does not fit in a 16-bit int")
        return num.float16_to_float(raw)

    @_static
    def floatToFloat16(cls: Any, value: Any) -> int:
        return num.float_to_float16(_float_arg(value))


# ==========================================
# Boolean
# ==========================================

class _BooleanMethods(_BaseMethods):
    __slots__ = ()

    TRUE = _Constant(True)
    FALSE = _Constant(False)
    TYPE = bool

    def booleanValue(self) -> bool:
        return _bool_arg(self._present())

    def equals(self, other: Any) -> bool:
        value = self._present()
        raw = _core._raw(other)
        return type(raw) is bool and raw == value

    def compareTo(self, other: Any) -> int:
        return _compare(_bool_arg(self._present()), _bool_arg(other))

    @_static
    def hashCode(cls: Any, value: Any) -> int:
        return 1231 if _bool_arg(value) else 1237

    @_static
    def toString(cls: Any, value: Any) -> "_core.String":
        return _text("true" if _bool_arg(value) else "false")

    @_static
    def compare(cls: Any, x: Any, y: Any) -> int:
        return _compare(_bool_arg(x), _bool_arg(y))

    @_static
    def logicalAnd(cls: Any, a: Any, b: Any) -> bool:
        return _bool_arg(a) & _bool_arg(b)

    @_static
    def logicalOr(cls: Any, a: Any, b: Any) -> bool:
        return _bool_arg(a) | _bool_arg(b)

    @_static
    def logicalXor(cls: Any, a: Any, b: Any) -> bool:
        return _bool_arg(a) ^ _bool_arg(b)

    @classmethod
    def parseBoolean(cls, s: Any) -> bool:
        text = _optional_text(s)
        return text is not None and len(text) == 4 and text.lower() == "true"

    @classmethod
    def valueOf(cls: Type[W], value: Any) -> W:
        raw = _core._raw(value)
        if type(raw) is bool:
            return _make(cls, raw)
        return _make(cls, _BooleanMethods.parseBoolean(raw))

    @classmethod
    def getBoolean(cls, name: Any) -> bool:
        """Read a setting from the environment."""
        key = _optional_text(name)
        return bool(key) and cls.parseBoolean(os.environ.get(cast(str, key)))


# ==========================================
# Bytes
# ==========================================

def _decode_number(cls: Any, nm: Any) -> Any:
    number = num.decode_integral(_optional_text(nm), num.BYTE_MIN, num.BYTE_MAX)
    return _make(cls, bytes([number & 0xFF]))


class _BytesMethods(_BaseMethods):
    """The numeric methods read one signed byte, so they need a length-1 value."""

    __slots__ = ()

    MIN_VALUE = num.BYTE_MIN
    MAX_VALUE = num.BYTE_MAX
    SIZE = 8
    BYTES = 1
    TYPE = bytes

    def _byte(self) -> int:
        return _byte_arg(self._present())

    def byteValue(self) -> int:
        return self._byte()

    def shortValue(self) -> int:
        return self._byte()

    def intValue(self) -> int:
        return self._byte()

    def longValue(self) -> int:
        return self._byte()

    def floatValue(self) -> float:
        return float(self._byte())

    def doubleValue(self) -> float:
        return float(self._byte())

    def equals(self, other: Any) -> bool:
        value = self._present()
        raw = _core._raw(other)
        return type(raw) is bytes and raw == value

    def compareTo(self, other: Any) -> int:
        return self._byte() - _byte_arg(other)

    @_static
    def hashCode(cls: Any, value: Any) -> int:
        return _byte_arg(value)

    @_static
    def toString(cls: Any, value: Any) -> "_core.String":
        return _text(str(_byte_arg(value)))

    @_static
    def compare(cls: Any, x: Any, y: Any) -> int:
        return _byte_arg(x) - _byte_arg(y)

    @_static
    def compareUnsigned(cls: Any, x: Any, y: Any) -> int:
        return (_byte_arg(x) & 0xFF) - (_byte_arg(y) & 0xFF)

    @_static
    def toUnsignedInt(cls: Any, x: Any) -> int:
        return _byte_arg(x) & 0xFF

    @_static
    def toUnsignedLong(cls: Any, x: Any) -> int:
        return _byte_arg(x) & 0xFF

    @classmethod
    def parseByte(cls, s: Any, radix: Any = 10) -> int:
        return num.parse_integral(_optional_text(s), int_arg(radix), num.BYTE_MIN, num.BYTE_MAX)

    @classmethod
    def valueOf(cls: Type[W], value: Any, radix: Any = None) -> W:
        raw = _core._raw(value)
        if type(raw) is str or raw is None:
            base = 10 if radix is None else int_arg(radix)
            number = num.parse_integral(raw, base, num.BYTE_MIN, num.BYTE_MAX)
        elif radix is not None:
            raise _core.PrimitiveTypeError("a radix is only valid with a String")
        else:
            number = _byte_arg(raw)
        return _make(cls, bytes([number & 0xFF]))

    # `Bytes.decode("0x7f")` parses a number. `Bytes(b"abc").decode()` decodes text.
    decode = Dual["_core.Bytes", str](_decode_number, unwrapped(bytes.decode))
