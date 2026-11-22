"""The String method API.

Indexes and lengths count UTF-16 units, so an emoji has length 2.
"""
import codecs
import re
import sys
from typing import Any, Callable, Iterator, List, Optional, Tuple, TypeVar, overload

from . import _formatter as formatter
from . import _numbers as num
from . import _regex as rx
from . import core as _core
from ._methods import _BaseMethods, int_arg
from ._native import UNSET, Dual, join_items

R = TypeVar("R")

# Whitespace for strip() and isBlank(): excludes the non-breaking spaces U+00A0, U+2007 and U+202F.
_WHITESPACE = (
    "\t\n\x0b\x0c\r\x1c\x1d\x1e\x1f \u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
    "\u2008\u2009\u200a\u2028\u2029\u205f\u3000"
)
_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_LONE_SURROGATE = re.compile("[\ud800-\udfff]")


def _new(value: str) -> "_core.String":
    return _core.String(value)


def _str_arg(value: Any) -> str:
    raw = _core._raw(value)
    if type(raw) is not str:
        raise _core.PrimitiveTypeError(f"expected a String, got {type(raw).__name__}")
    return raw


def _needle(target: Any) -> Optional[str]:
    """A search target as UTF-16 units. An int is a code point; None means it can't occur."""
    raw = _core._raw(target)
    if type(raw) is str:
        return num.to_units(raw)
    if type(raw) is not int:
        raise _core.PrimitiveTypeError(f"expected a String or code point, got {type(raw).__name__}")
    return num.to_units(chr(raw)) if 0 <= raw <= 0x10FFFF else None


# --- Case Rules for the *IgnoreCase Methods ---

def _simple_upper(char: str) -> str:
    """A one-to-one uppercase mapping, unlike str.upper()."""
    upper = char.upper()
    if len(upper) == 1:
        return upper
    title = char.title()
    return title if len(title) == 1 else char


def _simple_lower(char: str) -> str:
    if char == "\u0130":
        return "i"
    lower = char.lower()
    return lower if len(lower) == 1 else char


def _fold(char: str) -> str:
    return _simple_lower(_simple_upper(char))


def _compare_ignore_case(left: str, right: str) -> int:
    for a, b in zip(num.from_units(num.to_units(left)), num.from_units(num.to_units(right))):
        if a != b:
            first, second = _fold(a), _fold(b)
            if first != second:
                return ord(first) - ord(second)
    return len(num.to_units(left)) - len(num.to_units(right))


def _equal_ignore_case(left: str, right: str) -> bool:
    return len(left) == len(right) and all(
        a == b or _fold(a) == _fold(b) for a, b in zip(left, right)
    )


class _CaseInsensitiveOrder:
    """String.CASE_INSENSITIVE_ORDER. Use with functools.cmp_to_key to sort."""

    __slots__ = ()

    def compare(self, a: Any, b: Any) -> int:
        return _compare_ignore_case(_str_arg(a), _str_arg(b))

    def __call__(self, a: Any, b: Any) -> int:
        return self.compare(a, b)

    def __repr__(self) -> str:
        return "String.CASE_INSENSITIVE_ORDER"


# --- Charsets ---

def _codec(charset: Any) -> str:
    name = _str_arg(charset)
    try:
        return codecs.lookup(name).name
    except LookupError:
        raise LookupError(f"Unsupported charset: {name}") from None


def _encode(text: str, charset: Any) -> bytes:
    codec = _codec(charset)
    if codec.startswith(("utf-16", "utf-32")):
        clean = _LONE_SURROGATE.sub("\ufffd", text)
        if codec == "utf-16":
            return b"\xfe\xff" + clean.encode("utf-16-be")
        if codec == "utf-32":
            return clean.encode("utf-32-be")
        return clean.encode(codec)
    if codec == "utf-8":
        return _LONE_SURROGATE.sub("?", text).encode("utf-8")
    return text.encode(codec, "replace")


def _decode(data: bytes, charset: Any) -> str:
    codec = _codec(charset)
    if codec == "utf-16" and data[:2] not in (b"\xfe\xff", b"\xff\xfe"):
        codec = "utf-16-be"
    elif codec == "utf-32" and data[:4] not in (b"\x00\x00\xfe\xff", b"\xff\xfe\x00\x00"):
        codec = "utf-32-be"
    return data.decode(codec, "replace")


def _span(offset: Any, count: Any, size: int) -> Tuple[int, int]:
    start, length = int_arg(offset), int_arg(count)
    if start < 0 or length < 0 or start > size - length:
        raise IndexError(f"offset {start}, count {length}, length {size}")
    return start, start + length


def _chars_text(data: Any, bounds: Tuple[Any, ...]) -> str:
    """Build text from a list of one-unit strings."""
    if not isinstance(data, (list, tuple)):
        raise _core.PrimitiveTypeError(f"expected a list of chars, got {type(data).__name__}")
    if len(bounds) not in (0, 2):
        raise TypeError("expected (data) or (data, offset, count)")
    start, stop = _span(bounds[0], bounds[1], len(data)) if bounds else (0, len(data))
    chars = []
    for item in data[start:stop]:
        if type(item) is not str or len(num.to_units(item)) != 1:
            raise _core.PrimitiveTypeError("expected a list of single chars")
        chars.append(item)
    return num.from_units("".join(chars))


def _code_point_at(units: str, index: int) -> int:
    high = ord(units[index])
    if 0xD800 <= high <= 0xDBFF and index + 1 < len(units):
        low = ord(units[index + 1])
        if 0xDC00 <= low <= 0xDFFF:
            return 0x10000 + ((high - 0xD800) << 10) + (low - 0xDC00)
    return high


def _leading_whitespace(line: str) -> int:
    return len(line) - len(line.lstrip(_WHITESPACE))


def _split_lines(text: str) -> List[str]:
    if not text:
        return []
    parts = _LINE_BREAK.split(text)
    if parts[-1] == "":
        parts.pop()
    return parts


def _printf(cls: Any, template: Any, *args: Any, locale: Optional[str] = None) -> "_core.String":
    return _new(formatter.format_text(_str_arg(template), args, locale))


def _join_text(cls: Any, delimiter: Any, *elements: Any) -> "_core.String":
    separator = _str_arg(delimiter)
    items: Any = elements
    if len(elements) == 1 and not isinstance(elements[0], (str, _core.String)) and elements[0] is not None:
        items = elements[0]
    parts = []
    for item in items:
        raw = _core._raw(item)
        if raw is not None and type(raw) is not str:
            raise _core.PrimitiveTypeError(f"expected a String, got {type(raw).__name__}")
        parts.append("null" if raw is None else raw)
    return _new(separator.join(parts))


class _StringMethods(_BaseMethods):
    __slots__ = ()

    CASE_INSENSITIVE_ORDER = _CaseInsensitiveOrder()

    def _units(self) -> str:
        return num.to_units(self._present())

    # --- Length and Characters ---

    def length(self) -> int:
        return len(self._units())

    def isEmpty(self) -> bool:
        """True only for length 0. `is_empty()` also counts whitespace as empty."""
        return not self._present()

    def isBlank(self) -> bool:
        return not self._units().strip(_WHITESPACE)

    def charAt(self, index: Any) -> str:
        units, i = self._units(), int_arg(index)
        if not 0 <= i < len(units):
            raise IndexError(f"index {i}, length {len(units)}")
        return units[i]

    def codePointAt(self, index: Any) -> int:
        units, i = self._units(), int_arg(index)
        if not 0 <= i < len(units):
            raise IndexError(f"index {i}, length {len(units)}")
        return _code_point_at(units, i)

    def codePointBefore(self, index: Any) -> int:
        units, i = self._units(), int_arg(index)
        if not 1 <= i <= len(units):
            raise IndexError(f"index {i}, length {len(units)}")
        low = ord(units[i - 1])
        if 0xDC00 <= low <= 0xDFFF and i >= 2 and 0xD800 <= ord(units[i - 2]) <= 0xDBFF:
            return _code_point_at(units, i - 2)
        return low

    def codePointCount(self, beginIndex: Any, endIndex: Any) -> int:
        units, begin, end = self._units(), int_arg(beginIndex), int_arg(endIndex)
        if begin < 0 or begin > end or end > len(units):
            raise IndexError(f"begin {begin}, end {end}, length {len(units)}")
        return len(num.from_units(units[begin:end]))

    def offsetByCodePoints(self, index: Any, codePointOffset: Any) -> int:
        units, position, offset = self._units(), int_arg(index), int_arg(codePointOffset)
        if not 0 <= position <= len(units):
            raise IndexError(f"index {position}, length {len(units)}")
        for _ in range(abs(offset)):
            if offset > 0:
                if position >= len(units):
                    raise IndexError("code point offset is out of range")
                position += 2 if _code_point_at(units, position) > 0xFFFF else 1
            else:
                if position <= 0:
                    raise IndexError("code point offset is out of range")
                paired = (
                    position >= 2 and 0xDC00 <= ord(units[position - 1]) <= 0xDFFF
                    and 0xD800 <= ord(units[position - 2]) <= 0xDBFF
                )
                position -= 2 if paired else 1
        return position

    def chars(self) -> Iterator[int]:
        return map(ord, self._units())

    def codePoints(self) -> Iterator[int]:
        return map(ord, num.from_units(self._units()))

    def toCharArray(self) -> List[str]:
        return list(self._units())

    def getChars(self, srcBegin: Any, srcEnd: Any, dst: List[str], dstBegin: Any) -> None:
        units, begin, end, at = self._units(), int_arg(srcBegin), int_arg(srcEnd), int_arg(dstBegin)
        if begin < 0 or begin > end or end > len(units):
            raise IndexError(f"begin {begin}, end {end}, length {len(units)}")
        if at < 0 or at + end - begin > len(dst):
            raise IndexError(f"destination offset {at} is out of range")
        dst[at:at + end - begin] = list(units[begin:end])

    # --- Comparison ---

    def equals(self, other: Any) -> bool:
        raw = _core._raw(other)
        return type(raw) is str and num.to_units(raw) == self._units()

    def equalsIgnoreCase(self, other: Any) -> bool:
        raw = _core._raw(other)
        if raw is None:
            self._present()
            return False
        left, right = self._units(), num.to_units(_str_arg(raw))
        return len(left) == len(right) and _equal_ignore_case(num.from_units(left), num.from_units(right))

    def contentEquals(self, cs: Any) -> bool:
        return self._units() == num.to_units(_str_arg(cs))

    def compareTo(self, other: Any) -> int:
        left, right = self._units(), num.to_units(_str_arg(other))
        for a, b in zip(left, right):
            if a != b:
                return ord(a) - ord(b)
        return len(left) - len(right)

    def compareToIgnoreCase(self, other: Any) -> int:
        return _compare_ignore_case(self._present(), _str_arg(other))

    def hashCode(self) -> int:
        return num.string_hash(self._present())

    def toString(self) -> "_core.String":
        return _new(self._present())

    # --- Searching ---

    def contains(self, s: Any) -> bool:
        return num.to_units(_str_arg(s)) in self._units()

    def startsWith(self, prefix: Any, toffset: Any = 0) -> bool:
        units, start, offset = self._units(), num.to_units(_str_arg(prefix)), int_arg(toffset)
        return 0 <= offset <= len(units) - len(start) and units.startswith(start, offset)

    def endsWith(self, suffix: Any) -> bool:
        return self._units().endswith(num.to_units(_str_arg(suffix)))

    def indexOf(self, target: Any, *bounds: Any) -> int:
        units = self._units()
        needle = _needle(target)
        if len(bounds) == 0:
            begin, end = 0, len(units)
        elif len(bounds) == 1:
            begin, end = max(0, min(int_arg(bounds[0]), len(units))), len(units)
        elif len(bounds) == 2:
            begin, end = int_arg(bounds[0]), int_arg(bounds[1])
            if begin < 0 or begin > end or end > len(units):
                raise IndexError(f"begin {begin}, end {end}, length {len(units)}")
        else:
            raise TypeError("expected (target), (target, fromIndex) or (target, begin, end)")
        return -1 if needle is None else units.find(needle, begin, end)

    def lastIndexOf(self, target: Any, fromIndex: Any = None) -> int:
        units = self._units()
        needle = _needle(target)
        start = len(units) if fromIndex is None else int_arg(fromIndex)
        if needle is None or start < 0:
            return -1
        start = min(start, len(units) - len(needle))
        return -1 if start < 0 else units.rfind(needle, 0, start + len(needle))

    def regionMatches(self, *args: Any) -> bool:
        if len(args) == 5:
            ignore, toffset, other, ooffset, length = args
            if type(_core._raw(ignore)) is not bool:
                raise _core.PrimitiveTypeError("ignoreCase must be a boolean")
            ignore = _core._raw(ignore)
        elif len(args) == 4:
            ignore = False
            toffset, other, ooffset, length = args
        else:
            raise TypeError("expected (toffset, other, ooffset, len) or (ignoreCase, ...)")
        units, theirs = self._units(), num.to_units(_str_arg(other))
        mine, their, size = int_arg(toffset), int_arg(ooffset), int_arg(length)
        if their < 0 or mine < 0 or mine > len(units) - size or their > len(theirs) - size:
            return False
        if size <= 0:
            return True
        left, right = units[mine:mine + size], theirs[their:their + size]
        if not ignore:
            return left == right
        return _equal_ignore_case(num.from_units(left), num.from_units(right))

    def matches(self, regex: Any) -> bool:
        pattern = rx.compile_regex(_str_arg(regex))
        return pattern.fullmatch(num.from_units(self._units())) is not None

    # --- Building New Strings ---

    def concat(self, s: Any) -> "_core.String":
        return _new(num.from_units(self._units() + num.to_units(_str_arg(s))))

    def substring(self, beginIndex: Any, endIndex: Any = None) -> "_core.String":
        units = self._units()
        begin = int_arg(beginIndex)
        end = len(units) if endIndex is None else int_arg(endIndex)
        if begin < 0 or begin > end or end > len(units):
            raise IndexError(f"begin {begin}, end {end}, length {len(units)}")
        return _new(num.from_units(units[begin:end]))

    def subSequence(self, beginIndex: Any, endIndex: Any) -> "_core.String":
        return self.substring(beginIndex, endIndex)

    def repeat(self, count: Any) -> "_core.String":
        times = int_arg(count)
        if times < 0:
            raise ValueError(f"count is negative: {times}")
        return _new(self._present() * times)

    @overload
    def replace(self, target: Any, replacement: Any) -> "_core.String": ...
    @overload
    def replace(self, target: Any, replacement: Any, count: Any) -> str: ...
    def replace(self, target: Any, replacement: Any, count: Any = UNSET) -> Any:
        """With a count this is `str.replace` and returns a plain str."""
        if count is not UNSET:
            return self._present().replace(_core._raw(target), _core._raw(replacement), _core._raw(count))
        old, new = num.to_units(_str_arg(target)), num.to_units(_str_arg(replacement))
        return _new(num.from_units(self._units().replace(old, new)))

    def replaceAll(self, regex: Any, replacement: Any) -> "_core.String":
        pattern, template = rx.compile_regex(_str_arg(regex)), _str_arg(replacement)
        text = num.from_units(self._units())
        return _new(pattern.sub(lambda match: rx.expand_replacement(template, match), text))

    def replaceFirst(self, regex: Any, replacement: Any) -> "_core.String":
        pattern, template = rx.compile_regex(_str_arg(regex)), _str_arg(replacement)
        text = num.from_units(self._units())
        return _new(pattern.sub(lambda match: rx.expand_replacement(template, match), text, count=1))

    def _split(self, regex: Any, limit: Any, with_delimiters: bool) -> List["_core.String"]:
        pattern = rx.compile_regex(_str_arg(regex))
        maximum = int_arg(limit)
        text = num.from_units(self._units())
        parts: List[str] = []
        index = count = 0
        for match in pattern.finditer(text):
            if maximum <= 0 or count < maximum - 1:
                if index == 0 and match.start() == 0 and match.end() == 0:
                    continue
                parts.append(text[index:match.start()])
                index = match.end()
                if with_delimiters:
                    parts.append(text[match.start():index])
                count += 1
            elif count == maximum - 1:
                parts.append(text[index:])
                index = match.end()
                count += 1
        if index == 0:
            return [_new(text)]
        if maximum <= 0 or count < maximum:
            parts.append(text[index:])
        if maximum == 0:
            while parts and not parts[-1]:
                parts.pop()
        return [_new(part) for part in parts]

    @overload
    def split(self, *, sep: Any = ..., maxsplit: Any = ...) -> List[str]: ...
    @overload
    def split(self, regex: None, limit: Any = ...) -> List[str]: ...
    @overload
    def split(self, regex: Any, *, maxsplit: Any) -> List[str]: ...
    @overload
    def split(self, regex: Any, limit: Any = ...) -> List["_core.String"]: ...
    def split(self, regex: Any = UNSET, limit: Any = UNSET, *, sep: Any = UNSET, maxsplit: Any = UNSET) -> Any:
        """`split(pattern, limit)` uses a regex. `split()`, `sep=` and `maxsplit=` are `str.split`."""
        if regex is not UNSET and regex is not None and sep is UNSET and maxsplit is UNSET:
            return self._split(regex, 0 if limit is UNSET else limit, False)
        if regex is not UNSET and sep is not UNSET:
            raise TypeError("split() got multiple values for the separator")
        if limit is not UNSET and maxsplit is not UNSET:
            raise TypeError("split() got multiple values for maxsplit")
        if regex is UNSET and limit is not UNSET:
            raise TypeError("split() got a limit without a pattern")
        separator = sep if sep is not UNSET else (None if regex is UNSET else regex)
        most = maxsplit if maxsplit is not UNSET else (-1 if limit is UNSET else limit)
        return self._present().split(_core._raw(separator), _core._raw(most))

    def splitWithDelimiters(self, regex: Any, limit: Any) -> List["_core.String"]:
        return self._split(regex, limit, True)

    def lines(self) -> Iterator["_core.String"]:
        return map(_new, _split_lines(num.from_units(self._units())))

    def trim(self) -> "_core.String":
        return _new(self._present().strip(num.TRIM_CHARS))

    @overload
    def strip(self) -> "_core.String": ...
    @overload
    def strip(self, chars: Any) -> str: ...
    def strip(self, chars: Any = UNSET) -> Any:
        """With an argument this is `str.strip` and returns a plain str."""
        if chars is not UNSET:
            return self._present().strip(_core._raw(chars))
        return _new(self._present().strip(_WHITESPACE))

    def stripLeading(self) -> "_core.String":
        return _new(self._present().lstrip(_WHITESPACE))

    def stripTrailing(self) -> "_core.String":
        return _new(self._present().rstrip(_WHITESPACE))

    def indent(self, n: Any) -> "_core.String":
        text, amount = self._present(), int_arg(n)
        if not text:
            return _new("")
        lines = _split_lines(text)
        if amount > 0:
            lines = [" " * amount + line for line in lines]
        elif amount == num.INT_MIN:
            lines = [line.lstrip(_WHITESPACE) for line in lines]
        elif amount < 0:
            lines = [line[min(-amount, _leading_whitespace(line)):] for line in lines]
        return _new("\n".join(lines) + "\n")

    def stripIndent(self) -> "_core.String":
        text = self._present()
        if not text:
            return _new("")
        keep_end = text[-1] in "\r\n"
        lines = _split_lines(text)
        outdent = 0
        if not keep_end:
            widths = [_leading_whitespace(line) for line in lines if line.strip(_WHITESPACE)]
            if not lines[-1].strip(_WHITESPACE):
                widths.append(len(lines[-1]))
            outdent = min(widths)
        result = []
        for line in lines:
            body = line.rstrip(_WHITESPACE)
            result.append(body[min(outdent, _leading_whitespace(line)):] if body else "")
        return _new("\n".join(result) + ("\n" if keep_end else ""))

    def translateEscapes(self) -> "_core.String":
        text = self._units()
        out: List[str] = []
        simple = {"b": "\b", "f": "\f", "n": "\n", "r": "\r", "s": " ", "t": "\t",
                  "'": "'", '"': '"', "\\": "\\"}
        i = 0
        while i < len(text):
            c = text[i]
            i += 1
            if c != "\\":
                out.append(c)
                continue
            if i >= len(text):
                raise ValueError("Invalid escape sequence: trailing backslash")
            c = text[i]
            i += 1
            if c in simple:
                out.append(simple[c])
            elif c in "01234567":
                limit = min(i + (2 if c <= "3" else 1), len(text))
                code = int(c)
                while i < limit and text[i] in "01234567":
                    code = code * 8 + int(text[i])
                    i += 1
                out.append(chr(code))
            elif c == "\n":
                continue
            elif c == "\r":
                if i < len(text) and text[i] == "\n":
                    i += 1
            else:
                raise ValueError(f"Invalid escape sequence: \\{c}")
        return _new(num.from_units("".join(out)))

    def toLowerCase(self, locale: Any = None) -> "_core.String":
        text = self._present()
        language = _language(locale)
        if language in ("tr", "az"):
            text = text.replace("I\u0307", "i").replace("\u0130", "i").replace("I", "\u0131")
        return _new(text.lower())

    def toUpperCase(self, locale: Any = None) -> "_core.String":
        text = self._present()
        if _language(locale) in ("tr", "az"):
            text = text.replace("i", "\u0130")
        return _new(text.upper())

    def intern(self) -> "_core.String":
        return _new(sys.intern(self._present()))

    def transform(self, f: Callable[[Any], R]) -> R:
        self._present()
        return f(self)

    def formatted(self, *args: Any, locale: Optional[str] = None) -> "_core.String":
        return _new(formatter.format_text(self._present(), args, locale))

    # --- Bytes ---

    def getBytes(self, *args: Any) -> Any:
        """getBytes(), getBytes(charset), or a low-byte copy (srcBegin, srcEnd, dst, dstBegin)."""
        if len(args) == 4:
            return self._copy_low_bytes(*args)
        if len(args) > 1:
            raise TypeError("expected (), (charset) or (srcBegin, srcEnd, dst, dstBegin)")
        return _encode(num.from_units(self._units()), args[0] if args else "utf-8")

    def _copy_low_bytes(self, srcBegin: Any, srcEnd: Any, dst: bytearray, dstBegin: Any) -> None:
        units, begin, end, at = self._units(), int_arg(srcBegin), int_arg(srcEnd), int_arg(dstBegin)
        if begin < 0 or begin > end or end > len(units):
            raise IndexError(f"begin {begin}, end {end}, length {len(units)}")
        if at < 0 or at + end - begin > len(dst):
            raise IndexError(f"destination offset {at} is out of range")
        dst[at:at + end - begin] = bytes(ord(unit) & 0xFF for unit in units[begin:end])

    # --- Static Methods ---

    # On the class these are printf-style and delimiter-first. On an instance they are
    # `str.format` and `str.join`, returning plain str.
    format = Dual["_core.String", str](_printf, str.format)
    join = Dual["_core.String", str](_join_text, join_items)

    @staticmethod
    def valueOf(value: Any, *bounds: Any) -> "_core.String":
        if bounds or isinstance(value, (list, tuple)):
            return _new(_chars_text(value, bounds))
        return _new(formatter.to_text(value))

    @staticmethod
    def copyValueOf(data: Any, *bounds: Any) -> "_core.String":
        return _new(_chars_text(data, bounds))

    # --- Alternate Constructors (the String(...) call stays type-locked to str) ---

    @staticmethod
    def fromBytes(data: Any, offset: Any = None, length: Any = None, charset: Any = "UTF-8") -> "_core.String":
        """Decode bytes, or a slice of them, into a String."""
        raw = _core._raw(data)
        if type(raw) not in (bytes, bytearray):
            raise _core.PrimitiveTypeError(f"expected bytes, got {type(raw).__name__}")
        if (offset is None) != (length is None):
            raise TypeError("offset and length must be given together")
        start, stop = (0, len(raw)) if offset is None else _span(offset, length, len(raw))
        return _new(_decode(bytes(raw[start:stop]), charset))

    @staticmethod
    def fromCodePoints(codePoints: Any, offset: Any, count: Any) -> "_core.String":
        """Build a String from a slice of a list of code points."""
        start, stop = _span(offset, count, len(codePoints))
        chars = []
        for code in codePoints[start:stop]:
            number = int_arg(code)
            if not 0 <= number <= 0x10FFFF:
                raise ValueError(f"Not a valid code point: {number}")
            chars.append(chr(number))
        return _new("".join(chars))


def _language(locale: Any) -> str:
    """The language of a locale tag, for the case rules that depend on it."""
    if locale is None:
        return ""
    tag = _str_arg(locale).replace("_", "-").split("-")[0].lower()
    if tag == "lt":
        raise ValueError("Lithuanian case conversion is not supported")
    return tag
