"""Translate the extended regex syntax to Python `re`.

Anything that cannot be translated faithfully raises ValueError instead of
quietly matching something different.
"""
import functools
import re
import sys
import unicodedata
from typing import Dict, List, Match, Optional, Pattern, Tuple, Union

Ranges = List[Tuple[int, int]]

_MAX = 0x10FFFF
_TERMINATORS = r"\r\x85\u2028\u2029"
_NATIVE_POSSESSIVE = sys.version_info >= (3, 11)

_DIGIT: Ranges = [(0x30, 0x39)]
_WORD: Ranges = [(0x30, 0x39), (0x41, 0x5A), (0x5F, 0x5F), (0x61, 0x7A)]
_SPACE: Ranges = [(0x09, 0x0D), (0x20, 0x20)]
_HORIZONTAL: Ranges = [
    (0x09, 0x09), (0x20, 0x20), (0xA0, 0xA0), (0x1680, 0x1680), (0x180E, 0x180E),
    (0x2000, 0x200A), (0x202F, 0x202F), (0x205F, 0x205F), (0x3000, 0x3000),
]
_VERTICAL: Ranges = [(0x0A, 0x0D), (0x85, 0x85), (0x2028, 0x2029)]

_POSIX: Dict[str, Ranges] = {
    "Lower": [(0x61, 0x7A)],
    "Upper": [(0x41, 0x5A)],
    "ASCII": [(0x00, 0x7F)],
    "Alpha": [(0x41, 0x5A), (0x61, 0x7A)],
    "Digit": _DIGIT,
    "Alnum": [(0x30, 0x39), (0x41, 0x5A), (0x61, 0x7A)],
    "Punct": [(0x21, 0x2F), (0x3A, 0x40), (0x5B, 0x60), (0x7B, 0x7E)],
    "Graph": [(0x21, 0x7E)],
    "Print": [(0x20, 0x7E)],
    "Blank": [(0x09, 0x09), (0x20, 0x20)],
    "Cntrl": [(0x00, 0x1F), (0x7F, 0x7F)],
    "XDigit": [(0x30, 0x39), (0x41, 0x46), (0x61, 0x66)],
    "Space": _SPACE,
    "L1": [(0x00, 0xFF)],
    "all": [(0, _MAX)],
}
_WHITESPACE: Ranges = [
    (0x09, 0x0D), (0x1C, 0x20), (0x1680, 0x1680), (0x2000, 0x2006),
    (0x2008, 0x200A), (0x2028, 0x2029), (0x205F, 0x205F), (0x3000, 0x3000),
]

_categories: Dict[str, Ranges] = {}


def _normalize(ranges: Ranges) -> Ranges:
    merged: Ranges = []
    for low, high in sorted(ranges):
        if merged and low <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    return merged


def _negate(ranges: Ranges) -> Ranges:
    result: Ranges = []
    start = 0
    for low, high in _normalize(ranges):
        if low > start:
            result.append((start, low - 1))
        start = high + 1
    if start <= _MAX:
        result.append((start, _MAX))
    return result


def _intersect(left: Ranges, right: Ranges) -> Ranges:
    first, second = _normalize(left), _normalize(right)
    result: Ranges = []
    i = j = 0
    while i < len(first) and j < len(second):
        low, high = max(first[i][0], second[j][0]), min(first[i][1], second[j][1])
        if low <= high:
            result.append((low, high))
        if first[i][1] < second[j][1]:
            i += 1
        else:
            j += 1
    return result


def _load_categories() -> None:
    """Build the Unicode category tables once, on the first \\p{...} that needs them."""
    current = ""
    start = 0
    found: Dict[str, Ranges] = {}
    for code in range(_MAX + 1):
        category = unicodedata.category(chr(code))
        if category != current:
            if current:
                found.setdefault(current, []).append((start, code - 1))
            current, start = category, code
    found.setdefault(current, []).append((start, _MAX))
    groups: Dict[str, Ranges] = {}
    for name, ranges in found.items():
        groups.setdefault(name[0], []).extend(ranges)
    found.update({name: _normalize(ranges) for name, ranges in groups.items()})
    found["LC"] = _normalize(found.get("Lu", []) + found.get("Ll", []) + found.get("Lt", []))
    _categories.update(found)


def _property(name: str) -> Ranges:
    if name in _POSIX:
        return _POSIX[name]
    if name == "Whitespace":
        return _WHITESPACE
    key = name
    for prefix in ("general_category=", "gc=", "Is"):
        if key.startswith(prefix):
            key = key[len(prefix):]
            break
    if len(key) <= 2:
        if not _categories:
            _load_categories()
        if key in _categories:
            return _categories[key]
    raise ValueError(f"unsupported regex property: \\p{{{name}}}")


def _escape_code(code: int) -> str:
    if code <= 0xFF:
        return f"\\x{code:02x}"
    if code <= 0xFFFF:
        return f"\\u{code:04x}"
    return f"\\U{code:08x}"


def _set_text(ranges: Ranges, negated: bool = False) -> str:
    merged = _normalize(ranges)
    if not merged:
        return "[\\x00-\\U0010ffff]" if negated else "(?!)"
    body = "".join(
        _escape_code(low) if low == high else f"{_escape_code(low)}-{_escape_code(high)}"
        for low, high in merged
    )
    return f"[{'^' if negated else ''}{body}]"


class _Translator:
    def __init__(self, pattern: str) -> None:
        self.p = pattern
        self.i = 0
        self.out: List[str] = []
        self.groups = 0
        self.ignore = self.dotall = self.multiline = self.unix = False
        self.unicode_case = self.comments = False
        # One frame per open group: the flags to restore and the scoped-flag openers in force.
        self.frames: List[Tuple[Tuple[bool, ...], List[str]]] = [(self._flags(), [])]

    def _flags(self) -> Tuple[bool, ...]:
        return (self.ignore, self.dotall, self.multiline, self.unix, self.unicode_case, self.comments)

    def _restore(self, flags: Tuple[bool, ...]) -> None:
        self.ignore, self.dotall, self.multiline, self.unix, self.unicode_case, self.comments = flags

    def _error(self, message: str) -> ValueError:
        return ValueError(f"{message} near index {self.i} in regex {self.p!r}")

    def _case_scope(self) -> str:
        mode = "u" if self.unicode_case else "a"
        return f"(?{mode}i:" if self.ignore else f"(?{mode}-i:"

    # --- Main Loop ---

    def run(self) -> str:
        p = self.p
        while self.i < len(p):
            c = p[self.i]
            if self.comments and self._skip_comment():
                continue
            if c == "\\":
                self._escape()
            elif c == "[":
                self.i += 1
                ranges, negated = self._class_body()
                self.out.append(_set_text(ranges, negated))
            elif c == "(":
                self._open_group()
            elif c == ")":
                self._close_group()
            elif c == "|":
                self.i += 1
                scopes = self.frames[-1][1]
                self.out.append(")" * len(scopes) + "|" + "".join(scopes))
            elif c == ".":
                self.i += 1
                self.out.append(self._dot())
            elif c == "^":
                self.i += 1
                self.out.append(self._caret())
            elif c == "$":
                self.i += 1
                self.out.append(self._dollar(self.multiline))
            elif c in "*+?{":
                self._quantifier()
            else:
                self.i += 1
                self.out.append(re.escape(c))
        if len(self.frames) != 1:
            raise self._error("Unclosed group")
        self.out.append(")" * len(self.frames[0][1]))
        return "".join(self.out)

    def _skip_comment(self) -> bool:
        p = self.p
        c = p[self.i]
        if c in " \t\n\x0b\f\r":
            self.i += 1
            return True
        if c == "#":
            while self.i < len(p) and p[self.i] not in "\n\r\x85\u2028\u2029":
                self.i += 1
            return True
        return False

    # --- Anchors and Dot ---

    def _dot(self) -> str:
        if self.dotall:
            return "[\\x00-\\U0010ffff]"
        return "[^\\n]" if self.unix else f"[^\\n{_TERMINATORS}]"

    def _caret(self) -> str:
        if not self.multiline:
            return r"\A"
        if self.unix:
            return r"(?:(?!\Z)(?:\A|(?<=\n)))"
        return rf"(?:(?!\Z)(?:\A|(?<=\n)|(?<=[{_TERMINATORS}])(?!\n)))"

    def _dollar(self, multiline: bool) -> str:
        if self.unix:
            return r"(?:\Z|(?=\n))" if multiline else r"(?:\Z|(?=\n\Z))"
        if multiline:
            return rf"(?:\Z|(?=[{_TERMINATORS}])|(?<!\r)(?=\n))"
        return rf"(?:\Z|(?=\r\n\Z)|(?<!\r)(?=\n\Z)|(?=[{_TERMINATORS}]\Z))"

    # --- Quantifiers ---

    def _quantifier(self) -> None:
        p = self.p
        if p[self.i] == "{":
            match = re.compile(r"\{[0-9]+(?:,[0-9]*)?\}").match(p, self.i)
            if match is None:
                raise self._error("Illegal repetition")
            token = match.group()
            self.i = match.end()
        else:
            token = p[self.i]
            self.i += 1
        if self.i < len(p) and p[self.i] == "?":
            token += "?"
            self.i += 1
        elif self.i < len(p) and p[self.i] == "+":
            if not _NATIVE_POSSESSIVE:
                raise self._error("Possessive quantifiers need Python 3.11+")
            token += "+"
            self.i += 1
        self.out.append(token)

    # --- Groups and Flags ---

    def _open_group(self) -> None:
        p, i = self.p, self.i
        if not p.startswith("(?", i):
            self.groups += 1
            self.i += 1
            self._push("(")
            return
        for token in ("(?:", "(?=", "(?!", "(?<=", "(?<!"):
            if p.startswith(token, i):
                self.i += len(token)
                self._push(token)
                return
        if p.startswith("(?>", i):
            if not _NATIVE_POSSESSIVE:
                raise self._error("Atomic groups need Python 3.11+")
            self.i += 3
            self._push("(?>")
            return
        if p.startswith("(?<", i):
            match = re.compile(r"\(\?<([a-zA-Z][a-zA-Z0-9]*)>").match(p, i)
            if match is None:
                raise self._error("Invalid named group")
            self.groups += 1
            self.i = match.end()
            self._push(f"(?P<{match.group(1)}>")
            return
        match = re.compile(r"\(\?([a-zA-Z]*)(?:-([a-zA-Z]*))?([:)])").match(p, i)
        if match is None:
            raise self._error("Unknown group construct")
        self.i = match.end()
        saved = self._flags()
        self._apply_flags(match.group(1), True)
        self._apply_flags(match.group(2) or "", False)
        if match.group(3) == ":":
            self.frames.append((saved, []))
            self.out.append(self._case_scope())
        elif (self.ignore, self.unicode_case) != (saved[0], saved[4]):
            scope = self._case_scope()
            self.frames[-1][1].append(scope)
            self.out.append(scope)

    def _push(self, opener: str) -> None:
        self.frames.append((self._flags(), []))
        self.out.append(opener)

    def _close_group(self) -> None:
        if len(self.frames) == 1:
            raise self._error("Unmatched closing ')'")
        flags, scopes = self.frames.pop()
        self.i += 1
        self.out.append(")" * (len(scopes) + 1))
        self._restore(flags)

    def _apply_flags(self, letters: str, state: bool) -> None:
        for letter in letters:
            if letter == "i":
                self.ignore = state
            elif letter == "s":
                self.dotall = state
            elif letter == "m":
                self.multiline = state
            elif letter == "d":
                self.unix = state
            elif letter == "u":
                self.unicode_case = state
            elif letter == "x":
                self.comments = state
            elif letter == "U":
                raise self._error("The UNICODE_CHARACTER_CLASS flag (?U) is not supported")
            else:
                raise self._error(f"Unknown inline flag {letter!r}")

    # --- Escapes Outside a Character Class ---

    def _escape(self) -> None:
        p = self.p
        if self.i + 1 >= len(p):
            raise self._error("Unexpected internal error: trailing backslash")
        c = p[self.i + 1]
        if c == "Q":
            end = p.find("\\E", self.i + 2)
            stop = len(p) if end < 0 else end
            self.out.extend(re.escape(char) for char in p[self.i + 2:stop])
            self.i = len(p) if end < 0 else end + 2
        elif c in "123456789":
            self._backreference()
        elif c == "k":
            match = re.compile(r"\\k<([a-zA-Z][a-zA-Z0-9]*)>").match(p, self.i)
            if match is None:
                raise self._error("Illegal named back-reference")
            self.i = match.end()
            self.out.append(f"(?P={match.group(1)})")
        elif c in "bB":
            if p.startswith("{", self.i + 2):
                raise self._error("\\b{g} is not supported")
            self.i += 2
            self.out.append(f"(?a:\\{c})" if self.unicode_case else f"\\{c}")
        elif c == "A":
            self.i += 2
            self.out.append(r"\A")
        elif c == "z":
            self.i += 2
            self.out.append(r"\Z")
        elif c == "Z":
            self.i += 2
            self.out.append(self._dollar(False))
        elif c == "R":
            self.i += 2
            self.out.append(r"(?:\r\n|[\n\x0b\f\r\x85\u2028\u2029])")
        elif c in "GX":
            raise self._error(f"\\{c} is not supported")
        else:
            self.i += 1
            atom = self._atom()
            if isinstance(atom, int):
                self.out.append(re.escape(chr(atom)))
            else:
                self.out.append(_set_text(atom))

    def _backreference(self) -> None:
        p = self.p
        self.i += 1
        number = int(p[self.i])
        self.i += 1
        while self.i < len(p) and p[self.i].isascii() and p[self.i].isdigit():
            extended = number * 10 + int(p[self.i])
            if extended > self.groups:
                break
            number = extended
            self.i += 1
        if number > self.groups:
            raise self._error(f"Back-reference to undefined group {number}")
        self.out.append(f"(?:\\{number})")

    # --- Escapes Shared With Character Classes ---

    def _atom(self) -> Union[int, Ranges]:
        """Read an escape, with self.i on the character after the backslash."""
        p = self.p
        if self.i >= len(p):
            raise self._error("Trailing backslash")
        c = p[self.i]
        self.i += 1
        simple = {"t": 9, "n": 10, "r": 13, "f": 12, "a": 7, "e": 27}
        if c in simple:
            return simple[c]
        sets: Dict[str, Ranges] = {
            "d": _DIGIT, "w": _WORD, "s": _SPACE, "h": _HORIZONTAL, "v": _VERTICAL,
        }
        if c in sets:
            return sets[c]
        if c.lower() in sets and c.isupper():
            return _negate(sets[c.lower()])
        if c == "0":
            return self._octal()
        if c == "x":
            return self._hex()
        if c == "u":
            return self._unicode_escape()
        if c == "c":
            if self.i >= len(p):
                raise self._error("Illegal control escape sequence")
            self.i += 1
            return ord(p[self.i - 1]) ^ 64
        if c == "N":
            match = re.compile(r"\{([^}]*)\}").match(p, self.i)
            if match is None:
                raise self._error("Illegal character name escape sequence")
            self.i = match.end()
            try:
                return ord(unicodedata.lookup(match.group(1)))
            except KeyError:
                raise self._error("Unknown character name") from None
        if c in "pP":
            ranges = self._read_property()
            return _negate(ranges) if c == "P" else ranges
        if c.isascii() and c.isalnum():
            raise self._error(f"Illegal/unsupported escape sequence \\{c}")
        return ord(c)

    def _read_property(self) -> Ranges:
        p = self.p
        if self.i < len(p) and p[self.i] == "{":
            end = p.find("}", self.i)
            if end < 0:
                raise self._error("Unclosed character family")
            name = p[self.i + 1:end]
            self.i = end + 1
        elif self.i < len(p):
            name = p[self.i]
            self.i += 1
        else:
            raise self._error("Unknown character property")
        return _property(name)

    def _octal(self) -> int:
        p = self.p
        limit = 3 if self.i < len(p) and p[self.i] in "0123" else 2
        start = self.i
        while self.i < len(p) and self.i - start < limit and p[self.i] in "01234567":
            self.i += 1
        if self.i == start:
            raise self._error("Illegal octal escape sequence")
        return int(p[start:self.i], 8)

    def _hex(self) -> int:
        match = re.compile(r"\{([0-9a-fA-F]+)\}|([0-9a-fA-F]{2})").match(self.p, self.i)
        if match is None:
            raise self._error("Illegal hexadecimal escape sequence")
        self.i = match.end()
        code = int(match.group(1) or match.group(2), 16)
        if code > _MAX:
            raise self._error("Hexadecimal codepoint is too big")
        return code

    def _unicode_escape(self) -> int:
        escape = re.compile(r"[0-9a-fA-F]{4}")
        match = escape.match(self.p, self.i)
        if match is None:
            raise self._error("Illegal Unicode escape sequence")
        self.i = match.end()
        code = int(match.group(), 16)
        if 0xD800 <= code <= 0xDBFF and self.p.startswith("\\u", self.i):
            low = escape.match(self.p, self.i + 2)
            if low is not None and 0xDC00 <= int(low.group(), 16) <= 0xDFFF:
                self.i = low.end()
                return 0x10000 + ((code - 0xD800) << 10) + (int(low.group(), 16) - 0xDC00)
        return code

    # --- Character Classes ---

    def _class_body(self) -> Tuple[Ranges, bool]:
        """Parse up to the closing bracket. Union and intersection are resolved here."""
        p = self.p
        negated = p.startswith("^", self.i)
        if negated:
            self.i += 1
        result, seen = self._class_items(True)
        while p.startswith("&&", self.i):
            while p.startswith("&", self.i):
                self.i += 1
            right, has_right = self._class_items(False)
            if has_right:
                result = _intersect(result, right) if seen else right
                seen = True
        if not p.startswith("]", self.i):
            raise self._error("Unclosed character class")
        self.i += 1
        return result, negated

    def _class_items(self, first: bool) -> Tuple[Ranges, bool]:
        p = self.p
        ranges: Ranges = []
        seen = False
        while True:
            if self.i >= len(p):
                raise self._error("Unclosed character class")
            if self.comments and self._skip_comment():
                continue
            c = p[self.i]
            if (c == "]" and (seen or not first)) or p.startswith("&&", self.i):
                return ranges, seen
            seen = True
            if c == "[":
                self.i += 1
                inner, negated = self._class_body()
                ranges.extend(_negate(inner) if negated else inner)
                continue
            low = self._class_atom()
            if not isinstance(low, int):
                ranges.extend(low)
                continue
            following = p[self.i + 1:self.i + 2]
            if p.startswith("-", self.i) and following not in ("]", "[", ""):
                self.i += 1
                high = self._class_atom()
                if not isinstance(high, int) or high < low:
                    raise self._error("Illegal character range")
                ranges.append((low, high))
            else:
                ranges.append((low, low))

    def _class_atom(self) -> Union[int, Ranges]:
        c = self.p[self.i]
        self.i += 1
        return self._atom() if c == "\\" else ord(c)


@functools.lru_cache(maxsize=256)
def compile_regex(pattern: str) -> "Pattern[str]":
    """Compile a regex. A bad pattern raises ValueError."""
    translated = _Translator(pattern).run()
    try:
        return re.compile(translated, re.ASCII)
    except re.error as error:
        raise ValueError(f"Invalid regex {pattern!r}: {error}") from None


def expand_replacement(template: str, match: "Match[str]") -> str:
    """Expand a replacement template: `$1`, `${name}` and backslash escapes."""
    out: List[str] = []
    i = 0
    count = match.re.groups
    while i < len(template):
        c = template[i]
        if c == "\\":
            i += 1
            if i == len(template):
                raise ValueError("character to be escaped is missing")
            out.append(template[i])
            i += 1
        elif c == "$":
            i += 1
            if i == len(template):
                raise ValueError("Illegal group reference: group index is missing")
            group: Union[int, str]
            if template[i] == "{":
                end = template.find("}", i)
                name = template[i + 1:end] if end > 0 else ""
                if end < 0 or re.fullmatch(r"[a-zA-Z][a-zA-Z0-9]*", name) is None:
                    raise ValueError("Illegal named-capturing group reference")
                if name not in match.re.groupindex:
                    raise ValueError(f"No group with name {{{name}}}")
                group = name
                i = end + 1
            else:
                if template[i] not in "0123456789":
                    raise ValueError("Illegal group reference")
                number = int(template[i])
                i += 1
                if number > count:
                    raise IndexError(f"No group {number}")
                while i < len(template) and template[i] in "0123456789":
                    extended = number * 10 + int(template[i])
                    if extended > count:
                        break
                    number = extended
                    i += 1
                group = number
            text: Optional[str] = match.group(group)
            if text is not None:
                out.append(text)
        else:
            out.append(c)
            i += 1
    return "".join(out)
