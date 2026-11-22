"""Exact fixed-width arithmetic: 32-bit ints, 32-bit floats, UTF-16 and number text."""
import math
import re
import struct
import unicodedata
from fractions import Fraction
from typing import Optional, Tuple

INT_MIN = -(2 ** 31)
INT_MAX = 2 ** 31 - 1
UINT_MAX = 2 ** 32 - 1
LONG_MIN = -(2 ** 63)
LONG_MAX = 2 ** 63 - 1
BYTE_MIN = -128
BYTE_MAX = 127

FLOAT_MAX = float.fromhex("0x1.fffffep127")
FLOAT_MIN_NORMAL = float.fromhex("0x1.0p-126")
FLOAT_MIN = float.fromhex("0x0.000002p-126")

_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"
_PAIR = re.compile("[\ud800-\udbff][\udc00-\udfff]")
# Everything String.trim() and Float.parseFloat() remove: U+0000 to U+0020.
TRIM_CHARS = "".join(chr(code) for code in range(0x21))


# ==========================================
# Integers
# ==========================================

def wrap(value: int, bits: int) -> int:
    """Two's complement overflow."""
    half = 1 << (bits - 1)
    return ((value + half) & ((1 << bits) - 1)) - half


def digit_value(char: str, radix: int) -> int:
    """The value of one UTF-16 unit as a digit in this radix, or -1."""
    code = ord(char)
    if 48 <= code <= 57:
        value = code - 48
    elif 97 <= code <= 122:
        value = code - 87
    elif 65 <= code <= 90:
        value = code - 55
    elif 0xFF21 <= code <= 0xFF3A:
        value = code - 0xFF21 + 10
    elif 0xFF41 <= code <= 0xFF5A:
        value = code - 0xFF41 + 10
    elif code > 0xFFFF:
        return -1
    else:
        value = unicodedata.decimal(char, -1)
    return value if 0 <= value < radix else -1


def parse_integral(text: Optional[str], radix: int, low: int, high: int, unsigned: bool = False) -> int:
    """Integer.parseInt and its relatives. Malformed or out-of-range text raises ValueError."""
    if text is None:
        raise ValueError("Cannot parse null string")
    if not 2 <= radix <= 36:
        raise ValueError(f"radix {radix} is out of range 2 to 36")
    body = text
    negative = False
    if body[:1] in ("+", "-"):
        negative = body[0] == "-"
        body = body[1:]
    if not body or (negative and unsigned):
        raise ValueError(f"For input string: {text!r}")
    limit = -low if negative else high
    result = 0
    for char in body:
        digit = digit_value(char, radix)
        if digit < 0:
            raise ValueError(f"For input string: {text!r}")
        result = result * radix + digit
        if result > limit:
            raise ValueError(f"Value out of range: {text!r}")
    return -result if negative else result


def decode_integral(text: Optional[str], low: int, high: int) -> int:
    """Integer.decode: accepts a sign and the prefixes 0x, 0X, # and 0."""
    if text is None:
        raise TypeError("cannot decode null")
    if not text:
        raise ValueError("Zero length string")
    index = 1 if text[0] in "+-" else 0
    sign = "-" if text[0] == "-" else ""
    radix = 10
    if text.startswith(("0x", "0X"), index):
        radix, index = 16, index + 2
    elif text.startswith("#", index):
        radix, index = 16, index + 1
    elif text.startswith("0", index) and len(text) > index + 1:
        radix, index = 8, index + 1
    if text.startswith(("+", "-"), index):
        raise ValueError("Sign character in wrong position")
    return parse_integral(sign + text[index:], radix, low, high)


def to_radix(value: int, radix: int = 10) -> str:
    """Text in the given radix. An invalid radix falls back to 10."""
    if not 2 <= radix <= 36:
        radix = 10
    if radix == 10:
        return str(value)
    if value == 0:
        return "0"
    magnitude = abs(value)
    digits = []
    while magnitude:
        magnitude, remainder = divmod(magnitude, radix)
        digits.append(_DIGITS[remainder])
    if value < 0:
        digits.append("-")
    return "".join(reversed(digits))


# ==========================================
# 32-bit Floats
# ==========================================

def narrow(value: float) -> float:
    """Round to binary32, returned as a Python float."""
    try:
        return float(struct.unpack("<f", struct.pack("<f", value))[0])
    except OverflowError:
        return math.copysign(math.inf, value)


def float_to_raw_bits(value: float) -> int:
    return int(struct.unpack("<i", struct.pack("<f", narrow(value)))[0])


def float_to_bits(value: float) -> int:
    return 0x7FC00000 if math.isnan(value) else float_to_raw_bits(value)


def bits_to_float(bits: int) -> float:
    return float(struct.unpack("<f", struct.pack("<I", bits & UINT_MAX))[0])


def double_to_bits(value: float) -> int:
    """The IEEE 754 bits of a 64-bit float, as a signed integer."""
    if math.isnan(value):
        return 0x7FF8000000000000
    return int(struct.unpack("<q", struct.pack("<d", value))[0])


def fraction_to_float32(value: Fraction) -> float:
    """Round a positive exact value straight to binary32, ties to even."""
    exponent = value.numerator.bit_length() - value.denominator.bit_length() - 24
    if value >= Fraction(2) ** (exponent + 24):
        exponent += 1
    exponent = max(exponent, -149)
    scaled = value / Fraction(2) ** exponent
    whole = scaled.numerator // scaled.denominator
    remainder = scaled - whole
    if remainder > Fraction(1, 2) or (remainder == Fraction(1, 2) and whole & 1):
        whole += 1
    result = math.ldexp(whole, exponent)
    return math.inf if result >= 2.0 ** 128 else result


def int_to_float32(value: int) -> float:
    """Round an integer to binary32, without double rounding."""
    if value == 0:
        return 0.0
    result = fraction_to_float32(Fraction(abs(value)))
    return -result if value < 0 else result


def float_to_integral(value: float, bits: int) -> int:
    """Truncate to a fixed-width integer: NaN is 0 and overflow saturates."""
    if math.isnan(value):
        return 0
    low, high = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    if math.isinf(value):
        return high if value > 0 else low
    return max(low, min(high, int(value)))


def float16_to_float(bits: int) -> float:
    """Float.float16ToFloat: widen an IEEE binary16 value."""
    raw = bits & 0xFFFF
    sign, exponent, significand = raw & 0x8000, (raw >> 10) & 0x1F, raw & 0x3FF
    factor = -1.0 if sign else 1.0
    if exponent == 0:
        return factor * math.ldexp(significand, -24)
    if exponent == 31:
        if significand == 0:
            return factor * math.inf
        return bits_to_float((sign << 16) | 0x7F800000 | (significand << 13))
    return factor * math.ldexp(0x400 | significand, exponent - 25)


def float_to_float16(value: float) -> int:
    """Float.floatToFloat16: narrow to IEEE binary16, ties to even."""
    raw = float_to_raw_bits(value) & UINT_MAX
    sign = (raw >> 16) & 0x8000
    if math.isnan(value):
        payload = ((raw & 0x007FE000) >> 13) | ((raw & 0x00001FF0) >> 4) | (raw & 0xF)
        return wrap(sign | 0x7C00 | payload, 16)
    try:
        return int(struct.unpack("<h", struct.pack("<e", value))[0])
    except OverflowError:
        return wrap(sign | 0x7C00, 16)


# ==========================================
# Decimal and Hexadecimal Text
# ==========================================

def _shortest(value: float, precision: int, lowest: int) -> Tuple[str, int]:
    """The digits to print, and the exponent of the first digit.

    Picks the shortest decimal that rounds back to `value`, using at least two
    digits, closest to `value`, ties to an even digit.
    """
    _, binary = math.frexp(value)
    shift = max(binary - precision, lowest)
    mantissa = int(math.ldexp(value, -shift))
    unit = Fraction(2) ** shift
    exact = mantissa * unit
    high = exact + unit / 2
    # Just above a power of two, the gap below is half the size of the gap above.
    tight = mantissa == 1 << (precision - 1) and shift > lowest
    low = exact - (unit / 4 if tight else unit / 2)
    inclusive = mantissa % 2 == 0

    power = len(str(exact.numerator)) - len(str(exact.denominator))
    if Fraction(10) ** power > exact:
        power -= 1

    length = 2
    while True:
        scale = Fraction(10) ** (power - length + 1)
        floor = exact // scale
        best = None
        for candidate in (floor, floor + 1):
            decimal = candidate * scale
            if not (low < decimal < high or (inclusive and decimal in (low, high))):
                continue
            if best is None:
                best = candidate
                continue
            gap, best_gap = abs(decimal - exact), abs(best * scale - exact)
            if gap < best_gap or (gap == best_gap and candidate % 2 == 0):
                best = candidate
        if best is not None:
            text = str(best)
            return text.rstrip("0") or "0", power - length + len(text)
        length += 1


def _render(value: float, digits: str, exponent: int) -> str:
    sign = "-" if math.copysign(1.0, value) < 0 else ""
    if -3 <= exponent < 7:
        if exponent >= 0:
            whole = digits[:exponent + 1].ljust(exponent + 1, "0")
            return f"{sign}{whole}.{digits[exponent + 1:] or '0'}"
        return f"{sign}0.{'0' * (-exponent - 1)}{digits}"
    return f"{sign}{digits[0]}.{digits[1:] or '0'}E{exponent}"


def _special(value: float) -> Optional[str]:
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if value == 0:
        return "-0.0" if math.copysign(1.0, value) < 0 else "0.0"
    return None


def double_digits(value: float) -> Tuple[str, int]:
    return _shortest(abs(value), 53, -1074)


def float_to_string(value: float) -> str:
    """Float.toString for a value already narrowed to binary32."""
    special = _special(value)
    if special is not None:
        return special
    digits, exponent = _shortest(abs(value), 24, -149)
    return _render(value, digits, exponent)


def double_to_string(value: float) -> str:
    """Shortest decimal text for a 64-bit float."""
    special = _special(value)
    if special is not None:
        return special
    digits, exponent = double_digits(value)
    return _render(value, digits, exponent)


def double_to_hex(value: float) -> str:
    """Hexadecimal text for a 64-bit float."""
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    head, exponent = value.hex().split("p")
    whole, fraction = head.split(".")
    return f"{whole}.{fraction.rstrip('0') or '0'}p{int(exponent)}"


def float_to_hex(value: float) -> str:
    """Float.toHexString for a value already narrowed to binary32."""
    if value != 0 and abs(value) < FLOAT_MIN_NORMAL:
        # Scale into the double subnormal range, then relabel the exponent.
        return double_to_hex(math.ldexp(value, -896)).replace("p-1022", "p-126")
    return double_to_hex(value)


_FLOAT_TEXT = re.compile(
    r"([+-]?)(?:(NaN)|(Infinity)"
    r"|(?:([0-9]+)(?:\.([0-9]*))?|\.([0-9]+))(?:[eE]([+-]?[0-9]+))?[fFdD]?"
    r"|0[xX](?:([0-9a-fA-F]+)\.?|([0-9a-fA-F]*)\.([0-9a-fA-F]+))[pP]([+-]?[0-9]+)[fFdD]?)"
)


def _clamped_exponent(text: Optional[str]) -> int:
    """Read an exponent of any length without hitting Python's int-parsing limit."""
    if not text:
        return 0
    negative = text[0] == "-"
    digits = text.lstrip("+-").lstrip("0")
    magnitude = 10 ** 12 if len(digits) > 12 else int(digits or "0")
    return -magnitude if negative else magnitude


def parse_float(text: Optional[str]) -> float:
    """Float.parseFloat, rounding the exact decimal or hex value straight to binary32."""
    if text is None:
        raise TypeError("cannot parse null")
    match = _FLOAT_TEXT.fullmatch(text.strip(TRIM_CHARS))
    if match is None:
        raise ValueError(f"For input string: {text!r}")
    sign, nan, infinity, whole, fraction, bare, exponent, hex_whole, hex_left, hex_right, binary = match.groups()
    factor = -1.0 if sign == "-" else 1.0
    if nan:
        return math.nan
    if infinity:
        return factor * math.inf
    if binary is not None:
        left, right = hex_whole or hex_left or "", hex_right or ""
        mantissa = int(left + right or "0", 16)
        if mantissa == 0:
            return factor * 0.0
        shift = _clamped_exponent(binary) - 4 * len(right)
        size = mantissa.bit_length() + shift
        if size > 200:
            return factor * math.inf
        if size < -200:
            return factor * 0.0
        return factor * fraction_to_float32(Fraction(mantissa) * Fraction(2) ** shift)
    decimals = fraction if fraction is not None else (bare or "")
    digits = ((whole or "") + decimals).lstrip("0")
    if not digits:
        return factor * 0.0
    power = _clamped_exponent(exponent) - len(decimals)
    if len(digits) > 200:
        # A nonzero tail only matters as a tie-breaker, so one sticky digit keeps it exact.
        sticky = "1" if digits[200:].strip("0") else "0"
        power += len(digits) - 201
        digits = digits[:200] + sticky
    size = len(digits) + power
    if size > 60:
        return factor * math.inf
    if size < -60:
        return factor * 0.0
    return factor * fraction_to_float32(Fraction(int(digits)) * Fraction(10) ** power)


# ==========================================
# UTF-16 (String methods index by 16-bit unit)
# ==========================================

def to_units(text: str) -> str:
    """Rewrite text so each Python character is one UTF-16 unit."""
    if text.isascii() or max(text) <= "\uffff":
        return text
    units = []
    for char in text:
        code = ord(char)
        if code > 0xFFFF:
            code -= 0x10000
            units.append(chr(0xD800 + (code >> 10)))
            units.append(chr(0xDC00 + (code & 0x3FF)))
        else:
            units.append(char)
    return "".join(units)


def _join_pair(match: "re.Match[str]") -> str:
    pair = match.group()
    return chr(0x10000 + ((ord(pair[0]) - 0xD800) << 10) + (ord(pair[1]) - 0xDC00))


def from_units(units: str) -> str:
    """Undo `to_units`, joining surrogate pairs and leaving lone surrogates alone."""
    return _PAIR.sub(_join_pair, units)


def string_hash(text: str) -> int:
    """String.hashCode."""
    result = 0
    for unit in to_units(text):
        result = (31 * result + ord(unit)) & UINT_MAX
    return wrap(result, 32)
