"""The printf-style engine behind String.format and String.formatted."""
import datetime as _dt
import decimal
import math
import os
import re
import struct
from typing import Any, List, Optional, Sequence, Tuple

from . import _numbers as num
from . import core as _core

_SPEC = re.compile(r"%(?:([0-9]+)\$)?([-#+ 0,(<]*)([0-9]+)?(?:\.([0-9]+))?([tT])?([a-zA-Z%])")
_CONVERSIONS = frozenset("bBhHsScCdoxXeEfgGaA%n")
_MONTHS = (
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
)
_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_ENGLISH = {"", "root", "en", "en-us", "en_us", "en-gb", "en_gb", "en-ca", "en_ca"}


def to_text(value: Any) -> str:
    """The text form of any value, as returned by String.valueOf."""
    if isinstance(value, _core.Primitive):
        raw = value._value
        if raw is None:
            return "null"
        if isinstance(value, _core.Float):
            return num.float_to_string(num.narrow(raw))
        if isinstance(value, _core.Bytes) and len(raw) == 1:
            return str(num.wrap(raw[0], 8))
        value = raw
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if type(value) is float:
        return num.double_to_string(value)
    return str(value)


def hash_code(value: Any) -> int:
    """The hashCode() of a value, using the formula for its type."""
    if isinstance(value, _core.Float) and value._value is not None:
        return num.float_to_bits(num.narrow(value._value))
    if isinstance(value, _core.Bytes) and value._value is not None and len(value._value) == 1:
        return num.wrap(value._value[0], 8)
    raw = _core._raw(value)
    if raw is True:
        return 1231
    if raw is False:
        return 1237
    if type(raw) is str:
        return num.string_hash(raw)
    if type(raw) is float:
        bits = num.double_to_bits(raw) & (2 ** 64 - 1)
        return num.wrap(bits ^ (bits >> 32), 32)
    if type(raw) is int:
        if num.INT_MIN <= raw <= num.INT_MAX:
            return raw
        if num.LONG_MIN <= raw <= num.LONG_MAX:
            bits = raw & (2 ** 64 - 1)
            return num.wrap(bits ^ (bits >> 32), 32)
        return _big_integer_hash(raw)
    try:
        return num.wrap(hash(raw), 32)
    except TypeError:
        return num.wrap(id(raw), 32)


def _big_integer_hash(value: int) -> int:
    magnitude = abs(value)
    words = []
    while magnitude:
        words.append(magnitude & num.UINT_MAX)
        magnitude >>= 32
    result = 0
    for word in reversed(words):
        result = (31 * result + word) & num.UINT_MAX
    return num.wrap(-result if value < 0 else result, 32)


def _check_locale(locale: Optional[str]) -> None:
    if locale is not None and locale.lower() not in _ENGLISH:
        raise ValueError(
            f"locale {locale!r} is not supported by format. Use None, 'ROOT' or an English locale"
        )


def _bad_flags(flags: str, forbidden: str, spec: str) -> None:
    for flag in forbidden:
        if flag in flags:
            raise ValueError(f"Flag {flag!r} is not valid for {spec!r}")


def _needs_width(flags: str, width: Optional[int], spec: str) -> None:
    if width is None and ("-" in flags or "0" in flags):
        raise ValueError(f"Missing format width in {spec!r}")


def _check_numeric(flags: str, width: Optional[int], spec: str) -> None:
    _needs_width(flags, width, spec)
    if ("+" in flags and " " in flags) or ("-" in flags and "0" in flags):
        raise ValueError(f"Illegal flag combination in {spec!r}")


def _justify(text: str, width: Optional[int], flags: str) -> str:
    if width is None:
        return text
    padding = width - len(num.to_units(text))
    if padding <= 0:
        return text
    return text + " " * padding if "-" in flags else " " * padding + text


def _group(whole: str) -> str:
    head = len(whole) % 3
    parts = [whole[:head]] if head else []
    parts.extend(whole[i:i + 3] for i in range(head, len(whole), 3))
    return ",".join(parts)


def _signed(body: str, negative: bool, flags: str, width: Optional[int], prefix: str = "") -> str:
    """Apply the sign flags, then zero padding between the sign/prefix and the digits."""
    lead, trail = "", ""
    if negative:
        lead, trail = ("(", ")") if "(" in flags else ("-", "")
    elif "+" in flags:
        lead = "+"
    elif " " in flags:
        lead = " "
    if "0" in flags and width is not None:
        body = body.rjust(width - len(lead) - len(trail) - len(prefix), "0")
    return f"{lead}{prefix}{body}{trail}"


# --- Integers ---

def _integral(arg: Any, spec: str) -> Tuple[int, Optional[int]]:
    """The value and its width in bits. None means arbitrary precision."""
    if isinstance(arg, _core.Bytes) and arg._value is not None and len(arg._value) == 1:
        return num.wrap(arg._value[0], 8), 8
    raw = _core._raw(arg)
    if type(raw) is not int:
        raise ValueError(f"{spec!r} cannot format {type(raw).__name__}")
    if num.INT_MIN <= raw <= num.INT_MAX:
        return raw, 32
    if num.LONG_MIN <= raw <= num.LONG_MAX:
        return raw, 64
    return raw, None


def _format_integer(arg: Any, kind: str, flags: str, width: Optional[int], spec: str) -> str:
    value, bits = _integral(arg, spec)
    if kind == "d":
        body = str(abs(value))
        if "," in flags:
            body = _group(body)
        return _signed(body, value < 0, flags, width)
    base = "o" if kind == "o" else "x"
    prefix = ("0" if kind == "o" else "0x") if "#" in flags else ""
    if bits is None:
        return _signed(format(abs(value), base), value < 0, flags, width, prefix)
    _bad_flags(flags, "( +", spec)
    unsigned = value + (1 << bits) if value < 0 else value
    return _signed(format(unsigned, base), False, flags, width, prefix)


# --- Floating Point ---

def _bump(digits: str) -> str:
    """Add one to a digit string. The result can be one digit longer."""
    chars = list(digits)
    for i in range(len(chars) - 1, -1, -1):
        if chars[i] != "9":
            chars[i] = chr(ord(chars[i]) + 1)
            return "".join(chars)
        chars[i] = "0"
    return "1" + "".join(chars)


def _round_half_up(digits: str, point: int, keep: int) -> Tuple[str, int]:
    """Round to `keep` digits. The value is 0.DIGITS x 10^point."""
    if keep >= len(digits):
        return digits, point
    if keep < 0:
        return "", point
    kept = digits[:keep]
    if digits[keep] < "5":
        return kept, point
    if not kept:
        return "1", point + 1
    bumped = _bump(kept)
    return bumped, point + 1 if len(bumped) > keep else point


def _fixed(digits: str, point: int, precision: int) -> Tuple[str, str]:
    digits, point = _round_half_up(digits, point, point + precision)
    if point <= 0:
        whole, fraction = "0", "0" * -point + digits
    else:
        whole, fraction = digits[:point].ljust(point, "0"), digits[point:]
    return whole, fraction[:precision].ljust(precision, "0")


def _scientific(digits: str, point: int, precision: int) -> str:
    if not digits.strip("0"):
        mantissa, exponent = "0" * (precision + 1), 0
    else:
        digits, point = _round_half_up(digits, point, precision + 1)
        mantissa, exponent = digits.ljust(precision + 1, "0"), point - 1
    head = mantissa[0] + ("." + mantissa[1:precision + 1] if precision else "")
    return f"{head}e{'-' if exponent < 0 else '+'}{abs(exponent):02d}"


def _float_digits(arg: Any, spec: str) -> Tuple[bool, str, int, Optional[float]]:
    """Sign, digits, decimal point position, and the binary value when there is one."""
    raw = _core._raw(arg)
    if isinstance(arg, _core.Float):
        raw = num.narrow(raw)
    if type(raw) is decimal.Decimal:
        if not raw.is_finite():
            raise ValueError(f"{spec!r} cannot format {raw}")
        sign, numerals, exponent = raw.as_tuple()
        text = "".join(map(str, numerals))
        stripped = text.lstrip("0")
        return bool(sign), stripped, len(stripped) + int(exponent), None
    if type(raw) is not float:
        raise ValueError(f"{spec!r} cannot format {type(raw).__name__}")
    negative = math.copysign(1.0, raw) < 0
    if raw == 0 or not math.isfinite(raw):
        return negative, "", 0, raw
    digits, exponent = num.double_digits(raw)
    return negative, digits, exponent + 1, raw


def _hex_float(value: float, precision: Optional[int]) -> str:
    """Hexadecimal floating-point text, without the 0x prefix."""
    places = 0 if precision is None else (precision or 1)
    plain = num.double_to_hex(value)[2:]
    if value == 0 or places == 0 or places >= 13:
        return plain
    scale = 0
    if value < 2.0 ** -1022:
        value, scale = value * 2.0 ** 54, 54
    shift = 53 - (1 + places * 4)
    bits = num.double_to_bits(value)
    kept = bits >> shift
    dropped = bits & ((1 << shift) - 1)
    halfway = 1 << (shift - 1)
    if dropped > halfway or (dropped == halfway and kept & 1):
        kept += 1
    rounded = float(struct.unpack("<d", struct.pack("<q", kept << shift))[0])
    if math.isinf(rounded):
        return "1.0p1024"
    text = num.double_to_hex(rounded)[2:]
    if not scale:
        return text
    head, exponent = text.split("p")
    return f"{head}p{int(exponent) - scale}"


def _format_float(arg: Any, kind: str, flags: str, width: Optional[int], precision: Optional[int], spec: str) -> str:
    negative, digits, point, binary = _float_digits(arg, spec)
    if binary is not None and not math.isfinite(binary):
        text = "NaN" if math.isnan(binary) else "Infinity"
        if math.isnan(binary):
            return text
        return _signed(text, negative, flags.replace("0", ""), width)
    if kind == "a":
        if binary is None:
            raise ValueError(f"{spec!r} cannot format Decimal")
        body = _hex_float(abs(binary), precision)
        head, binary_exponent = body.split("p")
        if precision:
            whole, fraction = head.split(".")
            head = f"{whole}.{fraction.ljust(precision, '0')}"
        return _signed(f"{head}p{binary_exponent}", negative, flags, width, "0x")
    places = 6 if precision is None else precision
    if kind == "e":
        text = _scientific(digits, point, places)
        if "#" in flags and places == 0:
            text = text.replace("e", ".e", 1)
        return _signed(text, negative, flags, width)
    if kind == "g":
        significant = places or 1
        if not digits.strip("0"):
            whole, fraction = _fixed("", 0, significant - 1)
            body = f"{whole}.{fraction}" if fraction else whole
        else:
            rounded, rounded_point = _round_half_up(digits, point, significant)
            exponent = rounded_point - 1
            if -4 <= exponent < significant:
                decimals = significant - exponent - 1
                whole, fraction = _fixed(rounded, rounded_point, decimals)
                if "," in flags:
                    whole = _group(whole)
                body = f"{whole}.{fraction}" if fraction else whole
            else:
                return _signed(_scientific(rounded, rounded_point, significant - 1), negative, flags, width)
        return _signed(body, negative, flags, width)
    whole, fraction = _fixed(digits, point, places)
    if "," in flags:
        whole = _group(whole)
    body = f"{whole}.{fraction}" if fraction or "#" in flags else whole
    return _signed(body, negative, flags, width)


# --- Dates and Times ---

def _moment(arg: Any, spec: str) -> _dt.datetime:
    raw = _core._raw(arg)
    if isinstance(raw, _dt.datetime):
        return raw
    if isinstance(raw, _dt.date):
        return _dt.datetime(raw.year, raw.month, raw.day)
    if isinstance(raw, _dt.time):
        return _dt.datetime.combine(_dt.date(1970, 1, 1), raw)
    if type(raw) is int:
        seconds, millis = divmod(raw, 1000)
        epoch = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)
        return (epoch + _dt.timedelta(seconds=seconds, milliseconds=millis)).astimezone()
    raise ValueError(f"{spec!r} cannot format {type(raw).__name__}")


def _offset(moment: _dt.datetime) -> str:
    aware = moment if moment.tzinfo is not None else moment.astimezone()
    delta = aware.utcoffset() or _dt.timedelta(0)
    minutes = int(delta.total_seconds() // 60)
    sign = "-" if minutes < 0 else "+"
    hours, rest = divmod(abs(minutes), 60)
    return f"{sign}{hours:02d}{rest:02d}"


def _zone(moment: _dt.datetime) -> str:
    aware = moment if moment.tzinfo is not None else moment.astimezone()
    return aware.tzname() or "UTC"


def _date_field(moment: _dt.datetime, code: str, spec: str) -> str:
    hour12 = moment.hour % 12 or 12
    simple = {
        "H": f"{moment.hour:02d}", "I": f"{hour12:02d}", "k": str(moment.hour), "l": str(hour12),
        "M": f"{moment.minute:02d}", "S": f"{moment.second:02d}",
        "L": f"{moment.microsecond // 1000:03d}", "N": f"{moment.microsecond * 1000:09d}",
        "p": "am" if moment.hour < 12 else "pm",
        "B": _MONTHS[moment.month - 1], "b": _MONTHS[moment.month - 1][:3],
        "h": _MONTHS[moment.month - 1][:3], "A": _DAYS[moment.weekday()],
        "a": _DAYS[moment.weekday()][:3], "C": f"{moment.year // 100:02d}",
        "Y": f"{moment.year:04d}", "y": f"{moment.year % 100:02d}",
        "j": f"{moment.timetuple().tm_yday:03d}", "m": f"{moment.month:02d}",
        "d": f"{moment.day:02d}", "e": str(moment.day),
    }
    if code in simple:
        return simple[code]
    if code == "z":
        return _offset(moment)
    if code == "Z":
        return _zone(moment)
    if code in "sQ":
        aware = moment if moment.tzinfo is not None else moment.astimezone()
        epoch = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)
        delta = aware - epoch
        millis = delta.days * 86400000 + delta.seconds * 1000 + delta.microseconds // 1000
        return str(millis // 1000 if code == "s" else millis)
    clock = f"{simple['H']}:{simple['M']}"
    if code == "R":
        return clock
    if code == "T":
        return f"{clock}:{simple['S']}"
    if code == "r":
        return f"{simple['I']}:{simple['M']}:{simple['S']} {simple['p'].upper()}"
    if code == "D":
        return f"{simple['m']}/{simple['d']}/{simple['y']}"
    if code == "F":
        return f"{simple['Y']}-{simple['m']}-{simple['d']}"
    if code == "c":
        return (
            f"{simple['a']} {simple['b']} {simple['d']} {clock}:{simple['S']} "
            f"{_zone(moment)} {simple['Y']}"
        )
    raise ValueError(f"Unknown date/time conversion in {spec!r}")


# --- General, Character and Dispatch ---

def _is_null(arg: Any) -> bool:
    return arg is None or (isinstance(arg, _core.Primitive) and arg._value is None)


def _character(arg: Any, spec: str) -> str:
    if isinstance(arg, _core.Bytes) and arg._value is not None and len(arg._value) == 1:
        code = num.wrap(arg._value[0], 8)
    else:
        raw = _core._raw(arg)
        if type(raw) is str and len(raw) == 1:
            return raw
        if type(raw) is not int:
            raise ValueError(f"{spec!r} cannot format {type(raw).__name__}")
        code = raw
    if not 0 <= code <= 0x10FFFF:
        raise ValueError(f"Code point {code} is not valid")
    return chr(code)


def _format_one(
    spec: str, flags: str, width: Optional[int], precision: Optional[int],
    prefix: Optional[str], conversion: str, arg: Any,
) -> str:
    upper = conversion.isupper() if prefix is None else prefix == "T"
    kind = conversion.lower() if prefix is None else "t"

    if kind in "bhs":
        _bad_flags(flags, "+ 0,(" + ("" if kind == "s" else "#"), spec)
        if "#" in flags:
            raise ValueError(f"Flag '#' is not valid for {spec!r}")
        _needs_width(flags, width, spec)
        if kind == "b":
            raw = _core._raw(arg)
            text = "false" if raw is None or raw is False else "true"
        elif kind == "h":
            text = "null" if _is_null(arg) else format(hash_code(arg) & num.UINT_MAX, "x")
        else:
            text = to_text(arg)
        if precision is not None:
            text = num.from_units(num.to_units(text)[:precision])
    elif kind == "c":
        _reject_precision(precision, spec)
        _bad_flags(flags, "#+ 0,(", spec)
        _needs_width(flags, width, spec)
        text = "null" if _is_null(arg) else _character(arg, spec)
    elif kind in "dox":
        _reject_precision(precision, spec)
        _check_numeric(flags, width, spec)
        _bad_flags(flags, "#" if kind == "d" else ",", spec)
        text = "null" if _is_null(arg) else _format_integer(arg, kind, flags, width, spec)
    elif kind in "efga":
        _check_numeric(flags, width, spec)
        _bad_flags(flags, {"e": ",", "f": "", "g": "#", "a": "(,"}[kind], spec)
        if _is_null(arg):
            text = "null" if precision is None else "null"[:precision]
        else:
            text = _format_float(arg, kind, flags, width, precision, spec)
    else:
        _reject_precision(precision, spec)
        _bad_flags(flags, "#+ 0,(", spec)
        _needs_width(flags, width, spec)
        text = "null" if _is_null(arg) else _date_field(_moment(arg, spec), conversion, spec)
    if upper:
        text = text.upper()
    return _justify(text, width, flags)


def _reject_precision(precision: Optional[int], spec: str) -> None:
    if precision is not None:
        raise ValueError(f"Precision is not allowed in {spec!r}")


def format_text(template: str, args: Sequence[Any], locale: Optional[str] = None) -> str:
    """Format text. Invalid specifiers raise ValueError."""
    _check_locale(locale)
    out: List[str] = []
    position = 0
    ordinary = 0
    last = -1
    while True:
        start = template.find("%", position)
        if start < 0:
            out.append(template[position:])
            return "".join(out)
        out.append(template[position:start])
        match = _SPEC.match(template, start)
        if match is None:
            raise ValueError(f"Unknown format conversion at index {start} in {template!r}")
        position = match.end()
        spec = match.group()
        index, flags, width_text, precision_text, prefix, conversion = match.groups()
        if len(set(flags)) != len(flags):
            raise ValueError(f"Duplicate flag in {spec!r}")
        width = int(width_text) if width_text is not None else None
        precision = int(precision_text) if precision_text is not None else None
        if prefix is None and conversion not in _CONVERSIONS:
            raise ValueError(f"Unknown format conversion {conversion!r} in {spec!r}")

        if prefix is None and conversion == "n":
            if flags or width is not None or precision is not None:
                raise ValueError(f"{spec!r} takes no flags, width or precision")
            out.append(os.linesep)
            continue
        if prefix is None and conversion == "%":
            _reject_precision(precision, spec)
            _bad_flags(flags, "#+ 0,(<", spec)
            _needs_width(flags, width, spec)
            out.append(_justify("%", width, flags))
            continue

        if "<" in flags:
            if index is not None or last < 0:
                raise ValueError(f"Missing format argument for {spec!r}")
            chosen = last
        elif index is not None:
            chosen = int(index) - 1
            if chosen < 0:
                raise ValueError(f"Illegal format argument index in {spec!r}")
        else:
            chosen = ordinary
            ordinary += 1
        if chosen >= len(args):
            raise ValueError(f"Missing format argument for {spec!r}")
        last = chosen
        out.append(_format_one(spec, flags.replace("<", ""), width, precision, prefix, conversion, args[chosen]))
