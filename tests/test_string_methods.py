"""String methods, including UTF-16 indexing, regex and formatting."""
import datetime
import decimal
import functools
import math
import os

import pytest

from primitives import Boolean, Bytes, Float, Integer, PrimitiveTypeError, String

EMOJI = "\U0001F600"  # two UTF-16 units


def texts(items):
    items = list(items)
    assert all(type(item) is String for item in items)
    return [item.value for item in items]


# --- UTF-16 ---

def test_length_counts_utf16_units():
    assert String("abc").length() == 3 and String(EMOJI).length() == 2
    assert len(String(EMOJI)) == 1  # Python's own len() is unchanged


def test_char_at_and_code_points():
    text = String("a" + EMOJI + "b")
    assert text.charAt(0) == "a" and text.charAt(1) == "\ud83d" and text.charAt(2) == "\ude00"
    assert text.codePointAt(1) == 0x1F600 and text.codePointAt(2) == 0xDE00
    assert text.codePointBefore(3) == 0x1F600 and text.codePointBefore(2) == 0xD83D
    assert text.codePointCount(0, 4) == 3 and text.codePointCount(1, 2) == 1
    assert text.offsetByCodePoints(0, 2) == 3 and text.offsetByCodePoints(4, -2) == 1
    assert list(text.chars()) == [0x61, 0xD83D, 0xDE00, 0x62]
    assert list(text.codePoints()) == [0x61, 0x1F600, 0x62]
    assert text.toCharArray() == ["a", "\ud83d", "\ude00", "b"]


@pytest.mark.parametrize("call", [
    lambda s: s.charAt(3), lambda s: s.charAt(-1), lambda s: s.codePointAt(3),
    lambda s: s.codePointBefore(0), lambda s: s.codePointBefore(4), lambda s: s.codePointCount(2, 1),
    lambda s: s.substring(4), lambda s: s.substring(-1), lambda s: s.substring(2, 1),
    lambda s: s.subSequence(0, 4), lambda s: s.offsetByCodePoints(0, 4), lambda s: s.offsetByCodePoints(0, -1),
    lambda s: s.indexOf("a", 2, 1),
])
def test_out_of_bounds(call):
    with pytest.raises(IndexError):
        call(String("abc"))


def test_substring_can_split_surrogates():
    text = String(EMOJI + "x")
    assert text.substring(2) == "x"
    assert text.substring(0, 1) == "\ud83d"
    assert text.substring(0, 2) == EMOJI


# --- Comparison ---

@pytest.mark.parametrize("text, expected", [
    ("", 0), ("a", 97), ("abc", 96354), ("hello", 99162322), ("The quick brown fox", -1739336029),
    (EMOJI, 1772899),
])
def test_hash_code(text, expected):
    assert String(text).hashCode() == expected


@pytest.mark.parametrize("left, right, expected", [
    ("a", "a", 0), ("a", "b", -1), ("b", "a", 1), ("apple", "app", 2), ("app", "apple", -2),
    ("A", "a", -32), ("", "x", -1), (EMOJI, "\uffff", 0xD83D - 0xFFFF),
])
def test_compare_to(left, right, expected):
    assert String(left).compareTo(right) == expected


@pytest.mark.parametrize("left, right, expected", [
    ("ABC", "abc", 0), ("a", "B", -1), ("B", "a", 1), ("abc", "ABCD", -1), ("\xdf", "\xdf", 0),
    ("\u03c3", "\u03a3", 0), ("\u03c2", "\u03a3", 0),
])
def test_compare_to_ignore_case(left, right, expected):
    assert String(left).compareToIgnoreCase(right) == expected
    assert String.CASE_INSENSITIVE_ORDER.compare(left, right) == expected
    assert String.CASE_INSENSITIVE_ORDER(left, right) == expected


def test_case_insensitive_order_sorts():
    key = functools.cmp_to_key(String.CASE_INSENSITIVE_ORDER)
    assert sorted(["b", "A", "c"], key=key) == ["A", "b", "c"]


def test_equals():
    assert String("a").equals("a") and String("a").equals(String("a"))
    assert not String("a").equals("A") and not String("1").equals(1) and not String("a").equals(None)
    assert String("a").contentEquals("a") and not String("a").contentEquals("b")
    assert String(EMOJI).equals("\U0001f600")


@pytest.mark.parametrize("left, right, expected", [
    ("HeLLo", "hello", True), ("a", "b", False), ("a", "ab", False), ("a", None, False),
    ("\xc9", "\xe9", True), ("\u017f", "S", True), ("\u212a", "k", True), ("\xdf", "SS", False),
])
def test_equals_ignore_case(left, right, expected):
    assert String(left).equalsIgnoreCase(right) is expected


def test_is_empty_and_is_blank():
    assert String("").isEmpty() and not String(" ").isEmpty()
    assert String(" \t\n").isBlank() and not String("a").isBlank()
    assert not String("\xa0").isBlank()  # a non-breaking space doesn't count as whitespace
    assert String(" ").is_empty()  # the existing helper keeps its whitespace rule


# --- Searching ---

@pytest.mark.parametrize("args, expected", [
    (("l",), 2), (("l", 3), 3), (("l", 4), -1), (("z",), -1), (("lo",), 3), ((108,), 2), ((108, 3), 3),
    (("",), 0), (("", 3), 3), (("", 99), 5), (("h", -5), 0), (("l", 0, 2), -1), (("l", 0, 3), 2),
    ((-1,), -1), ((0x110000,), -1),
])
def test_index_of(args, expected):
    assert String("hello").indexOf(*args) == expected


@pytest.mark.parametrize("args, expected", [
    (("l",), 3), (("l", 2), 2), (("l", 1), -1), (("z",), -1), (("lo",), 3), (("lo", 2), -1),
    ((108,), 3), (("",), 5), (("", 2), 2), (("", 99), 5), (("l", -1), -1), (("hello", 99), 0),
])
def test_last_index_of(args, expected):
    assert String("hello").lastIndexOf(*args) == expected


def test_index_of_supplementary_code_point():
    text = String("a" + EMOJI + "b" + EMOJI)
    assert text.indexOf(0x1F600) == 1 and text.lastIndexOf(0x1F600) == 4
    assert text.indexOf(0x1F600, 2) == 4 and text.indexOf(0xD83D) == 1


def test_starts_and_ends_with():
    text = String("hello")
    assert text.startsWith("he") and text.startsWith("ll", 2) and text.startsWith("", 5)
    assert not text.startsWith("he", -1) and not text.startsWith("", 6) and not text.startsWith("x")
    assert text.endsWith("lo") and text.endsWith("") and not text.endsWith("x")
    assert text.contains("ell") and text.contains("") and not text.contains("z")


@pytest.mark.parametrize("args, expected", [
    ((0, "hello", 0, 5), True), ((1, "xell", 1, 3), True), ((0, "HE", 0, 2), False),
    ((True, 0, "HE", 0, 2), True), ((False, 0, "HE", 0, 2), False), ((-1, "h", 0, 1), False),
    ((0, "h", -1, 1), False), ((4, "oo", 0, 2), False), ((5, "", 0, 0), True),
    ((0, "x", 0, -1), True), ((7, "x", 0, -1), False),
])
def test_region_matches(args, expected):
    assert String("hello").regionMatches(*args) is expected


# --- Building Strings ---

def test_results_are_chainable_wrappers():
    result = String("  Hello  ").trim().toUpperCase().concat("!").replace("L", "1")
    assert type(result) is String and result == "HE11O!"


def test_simple_transformations():
    assert String("abc").concat("d") == "abcd"
    assert String("ab").repeat(3) == "ababab" and String("ab").repeat(0) == ""
    assert String("aXbX").replace("X", "--") == "a--b--"
    assert String("abc").replace("", "-") == "-a-b-c-"
    assert String("Hello").toLowerCase() == "hello" and String("Hello").toUpperCase() == "HELLO"
    assert String("stra\xdfe").toUpperCase() == "STRASSE"
    assert String("\u0391\u03a3").toLowerCase() == "\u03b1\u03c2"  # final sigma
    assert String("abc").substring(1) == "bc" and String("abc").subSequence(1, 2) == "b"
    assert String("x").toString() == "x" and String("x").intern() == "x"
    assert String("5").transform(lambda s: Integer.parseInt(s)) == 5


def test_turkish_case_rules():
    assert String("TITLE").toLowerCase("tr") == "t\u0131tle"
    assert String("title").toUpperCase("tr-TR") == "T\u0130TLE"
    assert String("I").toLowerCase("en") == "i"
    with pytest.raises(ValueError):
        String("I").toLowerCase("lt")


def test_repeat_negative():
    with pytest.raises(ValueError):
        String("a").repeat(-1)


def test_trim_and_strip_differ():
    text = "\u2003 x \u2003"
    assert String(text).trim() == text
    assert String(text).strip() == "x"
    assert String(text).stripLeading() == "x \u2003" and String(text).stripTrailing() == "\u2003 x"
    assert String("\x01 x \x1f").trim() == "x"
    assert String("\xa0x").strip() == "\xa0x"


@pytest.mark.parametrize("text, expected", [
    ("", []), ("a", ["a"]), ("a\n", ["a"]), ("a\nb", ["a", "b"]), ("a\r\nb\rc", ["a", "b", "c"]),
    ("\n", [""]), ("\n\n", ["", ""]), ("a\n\nb", ["a", "", "b"]), ("a\u2028b", ["a\u2028b"]),
])
def test_lines(text, expected):
    assert texts(String(text).lines()) == expected


@pytest.mark.parametrize("text, n, expected", [
    ("", 2, ""), ("a", 2, "  a\n"), ("a\nb\n", 1, " a\n b\n"), ("   a\n b", -2, " a\nb\n"),
    ("  a", 0, "  a\n"), ("  a", -2147483648, "a\n"), ("a\r\nb", 0, "a\nb\n"),
])
def test_indent(text, n, expected):
    assert String(text).indent(n) == expected


@pytest.mark.parametrize("text, expected", [
    ("", ""), ("  a\n    b\n  c", "a\n  b\nc"), ("  a  \n  b", "a\nb"), ("  a\n  b\n", "  a\n  b\n"),
    ("    a\n  ", "  a\n"), ("  a\n\n  b", "a\n\nb"), ("   ", ""),
])
def test_strip_indent(text, expected):
    assert String(text).stripIndent() == expected


@pytest.mark.parametrize("text, expected", [
    (r"a\tb", "a\tb"), (r"\b\f\n\r\s", "\b\f\n\r "), (r"\'\"\\", "'\"\\"), (r"\101", "A"),
    (r"\7", "\x07"), (r"\377", "\xff"), (r"\400", " 0"), (r"\08", "\x008"), ("a\\\nb", "ab"), ("a\\\r\nb", "ab"),
])
def test_translate_escapes(text, expected):
    assert String(text).translateEscapes() == expected


@pytest.mark.parametrize("text", ["\\", r"\q", r"a\u0041"])
def test_translate_escapes_rejects(text):
    with pytest.raises(ValueError):
        String(text).translateEscapes()


# --- Static Methods ---

@pytest.mark.parametrize("value, expected", [
    (True, "true"), (False, "false"), (5, "5"), (10 ** 12, "1000000000000"), (1.5, "1.5"),
    (0.1, "0.1"), (1e21, "1.0E21"), (5e-324, "4.9E-324"), (1.7976931348623157e308, "1.7976931348623157E308"),
    (2e-323, "2.0E-323"), (1e23, "1.0E23"), (None, "null"), ("x", "x"), (["a", "b"], "ab"),
    (Integer(7), "7"), (Float(0.1), "0.1"), (Boolean(True), "true"), (String("s"), "s"),
    (Bytes(b"\xff"), "-1"), (Integer(), "null"), (math.nan, "NaN"), (-math.inf, "-Infinity"),
])
def test_value_of(value, expected):
    result = String.valueOf(value)
    assert type(result) is String and result == expected


def test_value_of_and_copy_value_of_char_arrays():
    chars = ["a", "b", "c", "d"]
    assert String.valueOf(chars, 1, 2) == "bc" and String.copyValueOf(chars) == "abcd"
    assert String.copyValueOf(chars, 2, 2) == "cd"
    with pytest.raises(IndexError):
        String.copyValueOf(chars, 3, 2)
    with pytest.raises(PrimitiveTypeError):
        String.copyValueOf(["ab"])


def test_join():
    assert String.join(",", "a", "b") == "a,b" and String.join(",", ["a", "b"]) == "a,b"
    assert String.join("-", ("x",)) == "x" and String.join(",") == ""
    assert String.join(",", "a", None) == "a,null" and String.join(",", String("a"), "b") == "a,b"
    assert String.join(", ", (c for c in "ab")) == "a, b" and String.join(",", "abc") == "abc"
    with pytest.raises(TypeError):
        String.join(",", ["a", 1])


def test_constructors_stay_type_locked_and_factories_cover_them():
    with pytest.raises(PrimitiveTypeError):
        String(b"abc")
    assert String.fromBytes(b"h\xc3\xa9") == "h\xe9"
    assert String.fromBytes(b"abcd", 1, 2) == "bc"
    assert String.fromBytes(b"\xe9", charset="ISO-8859-1") == "\xe9"
    assert String.fromBytes(b"\x00a") == "\x00a" and String.fromBytes(b"\xff") == "\ufffd"
    assert String.fromBytes(b"\x00a", charset="UTF-16") == "a"
    assert String.fromBytes(b"\xff\xfea\x00", charset="UTF-16") == "a"
    assert String.fromCodePoints([0x61, 0x1F600, 0x62], 1, 2) == EMOJI + "b"
    with pytest.raises(ValueError):
        String.fromCodePoints([-1], 0, 1)


# --- Bytes ---

@pytest.mark.parametrize("text, charset, expected", [
    ("h\xe9", "UTF-8", b"h\xc3\xa9"), ("\xe9", "ISO-8859-1", b"\xe9"), ("\xe9", "US-ASCII", b"?"),
    ("a", "UTF-16", b"\xfe\xff\x00a"), ("a", "UTF-16BE", b"\x00a"), ("a", "UTF-16LE", b"a\x00"),
    ("a", "UTF-32", b"\x00\x00\x00a"), ("\ud800", "UTF-8", b"?"), ("\ud800", "UTF-16BE", b"\xff\xfd"),
])
def test_get_bytes(text, charset, expected):
    assert String(text).getBytes(charset) == expected


def test_get_bytes_default_and_bad_charset():
    assert String("\xe9").getBytes() == b"\xc3\xa9"
    with pytest.raises(LookupError):
        String("a").getBytes("no-such-charset")


def test_get_chars_and_low_byte_copy():
    chars = ["-"] * 4
    String("abcd").getChars(1, 3, chars, 1)
    assert chars == ["-", "b", "c", "-"]
    data = bytearray(3)
    String("\u0141bc").getBytes(0, 2, data, 1)
    assert data == bytearray([0, 0x41, 0x62])
    with pytest.raises(IndexError):
        String("abcd").getChars(0, 4, ["-"], 0)


# --- Regex ---

@pytest.mark.parametrize("text, regex, expected", [
    ("abc", "abc", True), ("abc", "ab", False), ("abc", "a.c", True), ("a\nc", "a.c", False),
    ("a\rc", "a.c", False), ("a\nc", "(?s)a.c", True), ("a\u2028c", "a.c", False),
    ("ABC", "(?i)abc", True), ("\xc9", "(?i)\xe9", False), ("\xc9", "(?iu)\xe9", True),
    ("aBc", "a(?i)bc", True), ("Abc", "a(?i)bc", False), ("aB", "a(?i:b)", True), ("AB", "a(?i:b)", False),
    ("xB", "(?:x(?i)b|c)", True), ("C", "(?:x(?i)b|c)", True),
    ("123", r"\d+", True), ("\u0663", r"\d", False), ("a_1", r"\w+", True), ("\xe9", r"\w", False),
    (" \t", r"\s+", True), ("\xa0", r"\h", True), ("\n", r"\v", True), ("\r\n", r"\R", True),
    ("abcabc", r"(abc)\1", True), ("aa", r"(?<x>a)\k<x>", True), ("a1", r"(a)\11?", False),
    ("a+b", r"\Qa+b\E", True), ("a+b", r"\Qa+b", True), ("aab", r"\Qa\E+b", True),
    ("b", "[a-c]", True), ("d", "[a-c]", False), ("d", "[^a-c]", True), ("\n", "[^a]", True),
    ("e", "[a-z&&[^aeiou]]", False), ("b", "[a-z&&[^aeiou]]", True), ("c", "[a-c&&c-e]", True),
    ("b", "[a-c&&[^b]]", False), ("x", "[a[x]]", True), ("-", "[a-]", True), ("]", "[]a]", True),
    ("A", "(?i)[^a]", False), ("Z", r"\p{Upper}", True), ("a", r"\p{Upper}", False), ("a", r"\P{Upper}", True),
    ("!", r"\p{Punct}", True), ("f", r"\p{XDigit}", True), ("\xe9", r"\p{L}", True), ("\xc9", r"\p{Lu}", True),
    ("\xe9", r"\p{IsLl}", True), ("5", r"\p{gc=Nd}", True), ("a", r"\p{Whitespace}", False),
    ("A", r"\x41", True), ("A", r"\u0041", True), ("A", r"\x{41}", True), ("A", r"\0101", True),
    (EMOJI, r"\uD83D\uDE00", True), (EMOJI, ".", True), ("\t", r"\cI", True), ("\x1b", r"\e", True),
    ("A", r"\N{LATIN CAPITAL LETTER A}", True), ("aaa", "a{3}", True), ("aaa", "a{1,2}", False), ("aaa", "a{2,}", True),
    ("ab", "(?x) a  b # comment", True), ("a b", "(?x) a\\ b", True), ("ab", "(?x)[a b]+", True),
    ("foobar", "foo(?=bar).*", True), ("foobar", "foo(?!baz).*", True), ("ab", "a(?<=a)b", True),
    ("a", "a|b", True), ("b", "a|b", True), ("", "a*", True), ("a\n", "a$\n", True),
])
def test_matches(text, regex, expected):
    assert String(text).matches(regex) is expected


@pytest.mark.parametrize("text, regex, replacement, expected", [
    ("a1b22", r"\d+", "#", "a#b#"), ("abc", "x*", "-", "-a-b-c-"), ("baaac", "a*", "X", "XbXXcX"),
    ("John Smith", r"(\w+) (\w+)", "$2, $1", "Smith, John"),
    ("ab", "(?<first>a)(?<second>b)", "${second}${first}", "ba"), ("a", "a", r"\$1", "$1"),
    ("a", "a", r"\\", "\\"), ("a", "(a)", "$10", "a0"), ("a", "(a)|(b)", "[$2]", "[]"), ("a", "a", "$0$0", "aa"),
    ("line\n", "$", "!", "line!\n!"), ("a\nb", "(?m)^", ">", ">a\n>b"), ("a\nb\n", "(?m)^", ">", ">a\n>b\n"),
    ("a\r\nb", "(?m)$", "!", "a!\r\nb!"), ("", "(?m)^", ">", ""), ("", "^", ">", ">"),
    ("x", "z", "$", "x"),  # an invalid replacement is only an error when something matches
])
def test_replace_all(text, regex, replacement, expected):
    assert String(text).replaceAll(regex, replacement) == expected


def test_replace_first():
    assert String("aaa").replaceFirst("a", "b") == "baa"
    assert String("abab").replaceFirst("(a)(b)", "$2$1") == "baab"
    assert String("x").replaceFirst("y", "z") == "x"


@pytest.mark.parametrize("replacement, error", [
    ("$", ValueError), ("\\", ValueError), ("$x", ValueError), ("$2", IndexError),
    ("${nope}", ValueError), ("${1a}", ValueError),
])
def test_bad_replacement(replacement, error):
    with pytest.raises(error):
        String("a").replaceAll("(a)", replacement)


@pytest.mark.parametrize("regex", [
    "(", ")", "[", "a{", "*a", r"\y", r"(?<1a>b)", r"\p{NoSuchProperty}", "[z-a]", r"\2(a)", "(?U)a", r"\G", r"\X",
])
def test_bad_or_unsupported_regex_fails_loudly(regex):
    with pytest.raises(ValueError):
        String("a").matches(regex)


@pytest.mark.parametrize("text, regex, limit, expected", [
    ("boo:and:foo", ":", 2, ["boo", "and:foo"]), ("boo:and:foo", ":", 5, ["boo", "and", "foo"]),
    ("boo:and:foo", ":", -2, ["boo", "and", "foo"]), ("boo:and:foo", "o", 5, ["b", "", ":and:f", "", ""]),
    ("boo:and:foo", "o", -2, ["b", "", ":and:f", "", ""]), ("boo:and:foo", "o", 0, ["b", "", ":and:f"]),
    ("", ",", 0, [""]), (",", ",", 0, []), (",a", ",", 0, ["", "a"]), ("a,", ",", 0, ["a"]),
    ("abc", "", 0, ["a", "b", "c"]), ("abc", "", 2, ["a", "bc"]), ("abc", "x", 0, ["abc"]),
    ("a1b2c", r"\d", 1, ["a1b2c"]), ("a.b", r"\.", 0, ["a", "b"]),
])
def test_split(text, regex, limit, expected):
    assert texts(String(text).split(regex, limit)) == expected


@pytest.mark.parametrize("text, limit, expected", [
    ("b:a:c", 0, ["b", ":", "a", ":", "c"]), ("b:a:c", 2, ["b", ":", "a:c"]),
    ("b:", 0, ["b", ":"]), ("b:", -1, ["b", ":", ""]), ("abc", 0, ["abc"]),
])
def test_split_with_delimiters(text, limit, expected):
    assert texts(String(text).splitWithDelimiters(":", limit)) == expected


# --- Formatting ---

FORMATS = [
    ("%d", (5,), "5"), ("%5d|", (42,), "   42|"), ("%-5d|", (42,), "42   |"), ("%05d", (42,), "00042"),
    ("%05d", (-42,), "-0042"), ("%+d", (5,), "+5"), ("% d", (5,), " 5"), ("%(d", (-5,), "(5)"),
    ("%,d", (1234567,), "1,234,567"), ("%,d", (-1234,), "-1,234"), ("%,010d", (1234,), "000001,234"),
    ("%x", (255,), "ff"), ("%X", (255,), "FF"), ("%#x", (255,), "0xff"), ("%#X", (255,), "0XFF"),
    ("%x", (-1,), "ffffffff"), ("%o", (8,), "10"), ("%#o", (8,), "010"), ("%o", (-1,), "37777777777"),
    ("%x", (-(2 ** 40),), "ffffff0000000000"), ("%x", (Bytes(b"\xff"),), "ff"), ("%x", (2 ** 70,), "400000000000000000"),
    ("%x", (-(2 ** 70),), "-400000000000000000"), ("%d", (2 ** 70,), "1180591620717411303424"),
    ("%#010x", (255,), "0x000000ff"),
    ("%s", ("hi",), "hi"), ("%S", ("hi",), "HI"), ("%5s|", ("a",), "    a|"), ("%-5s|", ("a",), "a    |"),
    ("%.2s", ("hello",), "he"), ("%s", (None,), "null"), ("%s", (True,), "true"), ("%s", (1.5,), "1.5"),
    ("%s", (Integer(7),), "7"), ("%s", (Float(0.1),), "0.1"), ("%S", (None,), "NULL"),
    ("%b", (True,), "true"), ("%b", (False,), "false"), ("%b", (None,), "false"), ("%b", ("x",), "true"),
    ("%B", (True,), "TRUE"), ("%b", (Boolean(False),), "false"), ("%.2b", (True,), "tr"),
    ("%c", ("a",), "a"), ("%C", ("a",), "A"), ("%c", (65,), "A"), ("%c", (0x1F600,), EMOJI), ("%c", (None,), "null"),
    ("%h", ("hello",), "5e918d2"), ("%h", (42,), "2a"), ("%H", (255,), "FF"), ("%h", (None,), "null"),
    ("%h", (True,), "4cf"), ("%h", (1.0,), "3ff00000"),
    ("%f", (1.5,), "1.500000"), ("%.2f", (1.005,), "1.01"), ("%.1f", (0.15,), "0.2"), ("%.0f", (0.5,), "1"),
    ("%.0f", (1.5,), "2"), ("%.0f", (2.5,), "3"), ("%#.0f", (1.0,), "1."), ("%8.2f|", (3.14159,), "    3.14|"),
    ("%-8.2f|", (3.14159,), "3.14    |"), ("%08.2f", (-3.14159,), "-0003.14"), ("%+.1f", (1.0,), "+1.0"),
    ("%(.1f", (-1.0,), "(1.0)"), ("%,.2f", (1234567.891,), "1,234,567.89"), ("%.3f", (0.0,), "0.000"),
    ("%.1f", (-0.0,), "-0.0"), ("%f", (1e20,), "100000000000000000000.000000"), ("%.2f", (0.001,), "0.00"),
    ("%.2f", (0.999,), "1.00"), ("%.10f", (Float(0.1),), "0.1000000015"), ("%f", (float("inf"),), "Infinity"),
    ("%f", (float("-inf"),), "-Infinity"), ("%f", (float("nan"),), "NaN"), ("%+f", (float("inf"),), "+Infinity"),
    ("%(f", (float("-inf"),), "(Infinity)"), ("%010f", (float("inf"),), "  Infinity"), ("%E", (float("inf"),), "INFINITY"),
    ("%.2f", (decimal.Decimal("1.005"),), "1.01"), ("%.1f", (decimal.Decimal("0.05"),), "0.1"),
    ("%e", (1234.5,), "1.234500e+03"), ("%E", (1234.5,), "1.234500E+03"), ("%.2e", (1234.5,), "1.23e+03"),
    ("%.0e", (1234.5,), "1e+03"), ("%#.0e", (1234.5,), "1.e+03"), ("%e", (0.0,), "0.000000e+00"),
    ("%e", (1e-10,), "1.000000e-10"), ("%e", (1e100,), "1.000000e+100"), ("%.1e", (9.96,), "1.0e+01"),
    ("%g", (1234.5,), "1234.50"), ("%g", (0.0,), "0.00000"), ("%g", (0.0001,), "0.000100000"),
    ("%g", (0.00001,), "1.00000e-05"), ("%g", (1e6,), "1.00000e+06"), ("%g", (999999.5,), "1.00000e+06"),
    ("%.3g", (1234.5,), "1.23e+03"), ("%.0g", (5.0,), "5"), ("%G", (1e-10,), "1.00000E-10"),
    ("%a", (1.0,), "0x1.0p0"), ("%a", (-1.5,), "-0x1.8p0"), ("%A", (1.0,), "0X1.0P0"), ("%a", (0.0,), "0x0.0p0"),
    ("%.1a", (1.0,), "0x1.0p0"), ("%.3a", (1.0,), "0x1.000p0"), ("%.1a", (1.96875,), "0x1.0p1"),
    ("%%", (), "%"), ("%5%|", (), "    %|"), ("%-5%|", (), "%    |"), ("a%nb", (), "a" + os.linesep + "b"),
    ("%2$s %1$s", ("a", "b"), "b a"), ("%s %<s", ("a",), "a a"), ("%1$s %s %s", ("a", "b"), "a a b"),
    ("no specifiers", (), "no specifiers"), ("", (), ""),
]


@pytest.mark.parametrize("template, args, expected", FORMATS)
def test_format(template, args, expected):
    result = String.format(template, *args)
    assert type(result) is String and result == expected
    assert String(template).formatted(*args) == expected


@pytest.mark.parametrize("template, args", [
    ("%", ()), ("%q", (1,)), ("%D", (1,)), ("%s", ()), ("%2$s", ("a",)), ("%<s", ("a",)), ("%0$s", ("a",)),
    ("%d", ("x",)), ("%d", (1.5,)), ("%f", (1,)), ("%c", ("ab",)), ("%c", (-1,)), ("%x", (1.5,)),
    ("%.2d", (1,)), ("%.2c", ("a",)), ("%-d", (1,)), ("%0d", (1,)), ("%-05d", (1,)), ("%+ d", (1,)),
    ("%#d", (1,)), ("%,x", (1,)), ("%+x", (1,)), ("%(x", (1,)), ("% x", (1,)), ("%,e", (1.0,)), ("%#g", (1.0,)),
    ("%(a", (1.0,)), ("%,a", (1.0,)), ("%#s", ("a",)), ("%#b", (True,)), ("%+s", ("a",)), ("%0s", ("a",)),
    ("%--5d", (1,)), ("%5n", ()), ("%.1%", ()), ("%+%", ()), ("%tq", (0,)), ("%ty", ("x",)), ("%.2tY", (0,)),
    ("%a", (decimal.Decimal("1"),)),
])
def test_format_rejects(template, args):
    with pytest.raises(ValueError):
        String.format(template, *args)


MOMENT = datetime.datetime(2026, 3, 5, 15, 7, 9, 123456, tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30), "IST"))


@pytest.mark.parametrize("code, expected", [
    ("tH", "15"), ("tI", "03"), ("tk", "15"), ("tl", "3"), ("tM", "07"), ("tS", "09"), ("tL", "123"),
    ("tN", "123456000"), ("tp", "pm"), ("Tp", "PM"), ("tz", "+0530"), ("tZ", "IST"), ("tB", "March"),
    ("TB", "MARCH"), ("tb", "Mar"), ("th", "Mar"), ("tA", "Thursday"), ("ta", "Thu"), ("tC", "20"),
    ("tY", "2026"), ("ty", "26"), ("tj", "064"), ("tm", "03"), ("td", "05"), ("te", "5"), ("tR", "15:07"),
    ("tT", "15:07:09"), ("tr", "03:07:09 PM"), ("tD", "03/05/26"), ("tF", "2026-03-05"),
    ("tc", "Thu Mar 05 15:07:09 IST 2026"), ("ts", "1772703429"), ("tQ", "1772703429123"),
])
def test_format_dates(code, expected):
    assert String.format("%" + code, MOMENT) == expected


def test_format_date_kinds():
    assert String.format("%tF", datetime.date(2026, 1, 2)) == "2026-01-02"
    assert String.format("%tT", datetime.time(1, 2, 3)) == "01:02:03"
    assert String.format("%tY", None) == "null"
    assert String.format("%tQ", 1000) == "1000"
    assert String.format("%10tY|", MOMENT) == "      2026|"


def test_format_locale():
    assert String.format("%,d", 1000, locale="en-US") == "1,000"
    assert String("%,d").formatted(1000, locale="ROOT") == "1,000"
    with pytest.raises(ValueError):
        String.format("%,d", 1000, locale="de-DE")


def test_null_string_methods_raise():
    for call in (String().length, String().trim, String().hashCode, String().isEmpty):
        with pytest.raises(TypeError):
            call()
