"""Python's native methods give identical results on the wrappers and on plain values."""
import hashlib
import sys

import pytest

from primitives import Boolean, Bytes, Float, Integer, String, _native
from samples import same

PAIRS = [(int, Integer), (float, Float), (str, String), (bool, Boolean), (bytes, Bytes)]

EMOJI = chr(0x1F600)

# The wrappers pickle through __getstate__. The other two names are a CPython test hook
# that changes float behavior for the whole interpreter, spelled differently by version.
NOT_NEEDED = {"__getnewargs__", "__set_format__", "__setformat__"}
# These would let a bool act as a number, which the type lock refuses on purpose.
BOOLEAN_REFUSED = {
    "__abs__", "__add__", "__ceil__", "__divmod__", "__float__", "__floor__", "__floordiv__",
    "__index__", "__int__", "__invert__", "__lshift__", "__mod__", "__mul__", "__neg__", "__pos__",
    "__pow__", "__radd__", "__rdivmod__", "__rfloordiv__", "__rlshift__", "__rmod__", "__rmul__",
    "__round__", "__rpow__", "__rrshift__", "__rshift__", "__rsub__", "__rtruediv__", "__sub__",
    "__truediv__", "__trunc__",
}


def outcome(call):
    """What a call did: its exact result type and repr, or the type of error it raised."""
    try:
        result = call()
    except Exception as error:
        return "raised", type(error)
    return "returned", type(result), repr(result)


def assert_same_as_native(native, wrapper, name, args=(), kwargs=None):
    kwargs = kwargs or {}
    expected = outcome(lambda: getattr(native, name)(*args, **kwargs))
    assert outcome(lambda: getattr(wrapper, name)(*args, **kwargs)) == expected
    assert repr(wrapper.value) == repr(native)


# --- Nothing Is Missing ---

@pytest.mark.parametrize("native, wrapper", PAIRS, ids=lambda item: item.__name__)
def test_every_public_native_name_exists(native, wrapper):
    public = [name for name in dir(native) if not name.startswith("_")]
    assert [name for name in public if not hasattr(wrapper, name)] == []


@pytest.mark.parametrize("native, wrapper", PAIRS, ids=lambda item: item.__name__)
def test_every_special_method_exists_or_is_refused_on_purpose(native, wrapper):
    allowed = NOT_NEEDED | (BOOLEAN_REFUSED if native is bool else set())
    special = [name for name in dir(native) if name.startswith("_")]
    assert [name for name in special if not hasattr(wrapper, name) and name not in allowed] == []


# --- str ---

TEXTS = [
    "", "a", "Hello World", "  spaced out  ", "a,b,,c", "line1\nline2\r\nend", "\xc0\xe9\xee",
    "stra\xdfe", "123", "x1_y", "\ttab\tbed", "Title Case", "UPPER", "lower", EMOJI + " emoji",
    "a b  c", chr(0x3A3) + "IGMA", "\xb2", chr(0x663), "\x00\x1f", "-42", "aaa",
]

TEXT_CALLS = {
    "capitalize": [()], "casefold": [()], "center": [(12,), (12, "*"), (0,), (5, "ab")],
    "count": [("a",), ("a", 1), ("a", 1, 5), ("",), (5,)],
    "encode": [(), ("ascii",), ("ascii", "ignore"), ("ascii", "replace"), ("utf-16-le",), ("no-such-codec",)],
    "endswith": [("d",), (("d", "e"),), ("a", 0, 1), (5,)], "expandtabs": [(), (4,), (0,)],
    "find": [("a",), ("a", 2), ("a", 1, 3), ("zz",), ("",)],
    "format_map": [({},), ({"a": 1},)], "index": [("a",), ("a", 1), ("zz",)],
    "isalnum": [()], "isalpha": [()], "isascii": [()], "isdecimal": [()], "isdigit": [()],
    "isidentifier": [()], "islower": [()], "isnumeric": [()], "isprintable": [()], "isspace": [()],
    "istitle": [()], "isupper": [()], "ljust": [(12,), (12, "*"), (0,)], "lower": [()],
    "lstrip": [(), ("a ",), (None,), (5,)], "partition": [(",",), (" ",), ("",), (5,)],
    "removeprefix": [("a",), ("",), ("Hello",), (5,), (("a",),)],
    "removesuffix": [("a",), ("",), ("World",), (5,), (("a",),)],
    "rfind": [("a",), ("a", 0, 2), ("zz",)], "rindex": [("a",), ("zz",)],
    "rjust": [(12,), (12, "*")], "rpartition": [(",",), (" ",), ("",)],
    "rsplit": [(), (",",), (",", 1), (None, 1), ("",)], "rstrip": [(), ("c ",), (None,)],
    "splitlines": [(), (True,)], "startswith": [("a",), (("a", "H"),), ("b", 1), (5,)],
    "swapcase": [()], "title": [()], "translate": [({97: "A"},), ({97: None},), (str.maketrans("ab", "xy"),)],
    "upper": [()], "zfill": [(8,), (0,)],
}

TEXT_CASES = [(text, name, args) for text in TEXTS for name, calls in TEXT_CALLS.items() for args in calls]


@pytest.mark.parametrize("text, name, args", TEXT_CASES)
def test_str_method(text, name, args):
    if not hasattr(str, name):
        pytest.skip("not in this Python version")
    assert_same_as_native(text, String(text), name, args)


@pytest.mark.parametrize("name, args, kwargs", [
    ("rsplit", (), {"sep": ",", "maxsplit": 1}), ("splitlines", (), {"keepends": True}),
    ("encode", (), {"encoding": "ascii", "errors": "replace"}), ("expandtabs", (), {"tabsize": 3}),
])
@pytest.mark.parametrize("text", TEXTS)
def test_str_keyword_arguments(text, name, args, kwargs):
    assert_same_as_native(text, String(text), name, args, kwargs)


# --- Names With a Second Use on String ---

@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("args, kwargs", [
    ((), {}), ((None,), {}), ((None, 1), {}), ((), {"sep": ","}), ((), {"maxsplit": 1}),
    ((), {"sep": ",", "maxsplit": 1}), ((",",), {"maxsplit": 1}), ((None,), {"maxsplit": 0}),
    ((), {"sep": ""}), ((5,), {"maxsplit": 1}),
])
def test_split_native_forms(text, args, kwargs):
    assert_same_as_native(text, String(text), "split", args, kwargs)


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("args", [("a",), ("a ",), (None,), ("",), (5,)])
def test_strip_with_an_argument_is_native(text, args):
    assert_same_as_native(text, String(text), "strip", args)


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("args", [("a", "X", 1), ("a", "X", 0), ("a", "X", -1), ("", "-", 2), ("a", "X", None)])
def test_replace_with_a_count_is_native(text, args):
    assert_same_as_native(text, String(text), "replace", args)


@pytest.mark.parametrize("template, args, kwargs", [
    ("{} {}", ("a", 1), {}), ("{0}{0}", ("x",), {}), ("{name}", (), {"name": "n"}), ("{:>5}", ("a",), {}),
    ("{:05.2f}", (1.5,), {}), ("{}", (), {}), ("{", (), {}), ("%d", (5,), {}), ("plain", (), {}),
])
def test_format_on_an_instance_is_native(template, args, kwargs):
    assert_same_as_native(template, String(template), "format", args, kwargs)


def test_format_on_an_instance_passes_wrappers_through():
    assert String("{:03d}").format(Integer(5)) == "005"
    assert String("{0.value}").format(Integer(5)) == "5"


@pytest.mark.parametrize("separator", ["", ",", ", "])
@pytest.mark.parametrize("items", [[], ["a"], ["a", "b"], "abc", ("x", "y"), [1], 5, ["a", None]], ids=repr)
def test_join_on_an_instance_is_native(separator, items):
    assert_same_as_native(separator, String(separator), "join", (items,))


def test_join_on_an_instance_unwraps_items_and_takes_generators():
    assert same(String(",").join([String("a"), "b"]), "a,b")
    assert same(String("-").join(c for c in "ab"), "a-b")


def test_existing_calls_keep_their_behavior():
    assert [part.value for part in String("a.b").split(r"\.")] == ["a", "b"]
    assert String("a.b").split(".") == []  # a regex, where . matches everything
    assert [part.value for part in String("boo:and:foo").split(":", 2)] == ["boo", "and:foo"]
    assert type(String("a,b").split(",")[0]) is String
    assert type(String(" a ").strip()) is String and String("\xa0a").strip() == "\xa0a"
    assert type(String("a").replace("a", "b")) is String
    assert String.format("%05d", 42) == "00042" and type(String.format("%d", 1)) is String
    assert String.join(",", "a", "b") == "a,b" and String.join(",", ["a", None]) == "a,null"
    assert Bytes.decode("0x7f").value == b"\x7f" and type(Bytes.decode("1")) is Bytes


@pytest.mark.parametrize("call", [
    lambda: String("a").split(",", 1, maxsplit=1), lambda: String("a").split(",", sep=","),
    lambda: String("a").split(limit=1),
])
def test_split_rejects_conflicting_arguments(call):
    with pytest.raises(TypeError):
        call()


# --- bytes ---

DATA = [
    b"", b"a", b"Hello World", b"  spaced out  ", b"a,b,,c", b"line1\nline2\r\nend", b"\xc0\xff\x00",
    b"123", b"x1_y", b"\ttab\tbed", b"Title Case", b"UPPER", b"lower", b"-42", b"aaa", "h\xe9".encode(),
]

DATA_CALLS = {
    "capitalize": [()], "center": [(12,), (12, b"*"), (0,)], "count": [(b"a",), (97,), (b"a", 1, 5), (b"",)],
    "decode": [(), ("ascii",), ("ascii", "ignore"), ("latin-1",), ("no-such-codec",)],
    "endswith": [(b"d",), ((b"d", b"e"),), (b"a", 0, 1), ("a",)], "expandtabs": [(), (4,)],
    "find": [(b"a",), (97,), (b"a", 2), (b"zz",), (b"",)], "hex": [(), (":",), ("-", 2)],
    "index": [(b"a",), (b"zz",)], "isalnum": [()], "isalpha": [()], "isascii": [()], "isdigit": [()],
    "islower": [()], "isspace": [()], "istitle": [()], "isupper": [()],
    "join": [([b"x", b"y"],), ([],), (["x"],), ([b"x", None],), (5,)], "ljust": [(12,), (12, b"*")],
    "lower": [()], "lstrip": [(), (b"a ",), (None,)], "partition": [(b",",), (b" ",), (b"",)],
    "removeprefix": [(b"a",), (b"",), (b"Hello",), ("a",)], "removesuffix": [(b"a",), (b"",), (b"World",), ("a",)],
    "replace": [(b"a", b"X"), (b"a", b"X", 1), (b"", b"-"), ("a", "b")], "rfind": [(b"a",), (b"zz",)],
    "rindex": [(b"a",), (b"zz",)], "rjust": [(12,), (12, b"*")], "rpartition": [(b",",), (b" ",)],
    "rsplit": [(), (b",",), (b",", 1), (None, 1)], "rstrip": [(), (b"c ",)],
    "split": [(), (b",",), (b",", 1), (None, 1), (b"",)], "splitlines": [(), (True,)],
    "startswith": [(b"a",), ((b"a", b"H"),), (b"b", 1), ("a",)], "strip": [(), (b"a ",), (None,)],
    "swapcase": [()], "title": [()], "translate": [(bytes.maketrans(b"ab", b"xy"),), (None, b"a")],
    "upper": [()], "zfill": [(8,), (0,)],
}

DATA_CASES = [(data, name, args) for data in DATA for name, calls in DATA_CALLS.items() for args in calls]


@pytest.mark.parametrize("data, name, args", DATA_CASES)
def test_bytes_method(data, name, args):
    if not hasattr(bytes, name):
        pytest.skip("not in this Python version")
    assert_same_as_native(data, Bytes(data), name, args)


def test_bytes_join_unwraps_items():
    assert same(Bytes(b",").join([Bytes(b"a"), b"b"]), b"a,b")


def test_bytes_decode_keywords_and_wrapper_arguments():
    assert same(Bytes(b"h\xc3\xa9").decode(encoding="utf-8", errors="strict"), "h\xe9")
    assert same(Bytes(b"abc").decode(String("ascii")), "abc")


@pytest.mark.skipif(sys.version_info < (3, 12), reason="__buffer__ needs Python 3.12")
def test_bytes_works_where_a_buffer_is_expected():
    value = Bytes(b"abc")
    assert bytes(memoryview(value)) == b"abc"
    assert bytearray(value) == bytearray(b"abc")
    assert hashlib.sha256(value).digest() == hashlib.sha256(b"abc").digest()
    with pytest.raises(TypeError):
        memoryview(Bytes())


# --- int and bool ---

INTS = [0, 1, -1, 5, 255, -255, 2 ** 31, 2 ** 64, -(2 ** 70)]
BOOLS = [True, False]
NUMBER_CALLS = [
    ("as_integer_ratio", ()), ("bit_count", ()), ("bit_length", ()), ("conjugate", ()), ("is_integer", ()),
    ("to_bytes", (16, "big")), ("to_bytes", (16, "little")), ("to_bytes", (1, "big")), ("to_bytes", ("x",)),
]


@pytest.mark.parametrize("native, wrapper, value, name, args", [
    (kind, cls, value, name, args)
    for kind, cls, values in ((int, Integer, INTS), (bool, Boolean, BOOLS))
    for value in values for name, args in NUMBER_CALLS
])
def test_number_method(native, wrapper, value, name, args):
    if not hasattr(native, name):
        pytest.skip("not in this Python version")
    assert_same_as_native(value, wrapper(value), name, args)


@pytest.mark.parametrize("value", INTS)
def test_to_bytes_signed_keyword(value):
    assert_same_as_native(value, Integer(value), "to_bytes", (16, "big"), {"signed": True})


@pytest.mark.parametrize("wrapper, value", [(Integer, v) for v in INTS] + [(Boolean, v) for v in BOOLS])
@pytest.mark.parametrize("name", ["real", "imag", "numerator", "denominator"])
def test_number_attributes(wrapper, value, name):
    result = getattr(wrapper(value), name)
    assert same(result, getattr(value, name))


# --- float ---

FLOATS = [0.0, -0.0, 1.5, -2.5, 3.0, 1e300, 5e-324, float("nan"), float("inf"), float("-inf")]


@pytest.mark.parametrize("value", FLOATS, ids=repr)
@pytest.mark.parametrize("name", ["as_integer_ratio", "conjugate", "hex", "is_integer"])
def test_float_method(value, name):
    assert_same_as_native(value, Float(value), name)


@pytest.mark.parametrize("value", FLOATS, ids=repr)
@pytest.mark.parametrize("name", ["real", "imag"])
def test_float_attributes(value, name):
    assert repr(getattr(Float(value), name)) == repr(getattr(value, name))


# --- Class-Level Calls ---

@pytest.mark.parametrize("native, wrapper, name, args, kwargs", [
    (int, Integer, "from_bytes", (b"\x01\x00", "big"), {}),
    (int, Integer, "from_bytes", (b"\xff", "big"), {"signed": True}),
    (bool, Boolean, "from_bytes", (b"\x01", "big"), {}), (bool, Boolean, "from_bytes", (b"\x00", "big"), {}),
    (float, Float, "fromhex", ("0x1.8p1",), {}), (float, Float, "fromhex", ("nope",), {}),
    (bytes, Bytes, "fromhex", ("ab cd",), {}), (bytes, Bytes, "fromhex", ("zz",), {}),
    (bytes, Bytes, "maketrans", (b"ab", b"xy"), {}), (str, String, "maketrans", ("ab", "xy"), {}),
    (str, String, "maketrans", ("ab", "xy", "z"), {}), (str, String, "maketrans", ({"a": "b"},), {}),
    (float, Float, "__getformat__", ("double",), {}),
])
def test_class_level_calls(native, wrapper, name, args, kwargs):
    expected = outcome(lambda: getattr(native, name)(*args, **kwargs))
    assert outcome(lambda: getattr(wrapper, name)(*args, **kwargs)) == expected


@pytest.mark.parametrize("native, wrapper, name, value, args", [
    (str, String, "upper", "ab", ()), (str, String, "center", "a", (5, "*")), (bytes, Bytes, "upper", b"ab", ()),
    (int, Integer, "bit_length", 255, ()), (int, Integer, "to_bytes", 5, (2, "big")), (float, Float, "hex", 1.5, ()),
])
def test_method_called_through_the_class(native, wrapper, name, value, args):
    expected = getattr(native, name)(value, *args)
    assert same(getattr(wrapper, name)(value, *args), expected)
    assert same(getattr(wrapper, name)(wrapper(value), *args), expected)


def test_method_through_the_class_works_with_map():
    assert list(map(String.upper, ["a", "b"])) == ["A", "B"]


def test_method_through_the_class_rejects_the_wrong_type():
    with pytest.raises(TypeError):
        String.upper(5)


# --- Methods That Older Python Versions Lack ---

def test_filled_in_methods_on_every_version():
    assert same(Integer(5).as_integer_ratio(), (5, 1)) and same(Boolean(True).as_integer_ratio(), (1, 1))
    assert same(Integer(255).bit_count(), 8) and same(Integer(-3).bit_count(), 2)
    assert same(Boolean(True).bit_count(), 1)
    assert Integer(5).is_integer() is True and Boolean(False).is_integer() is True
    assert same(String("prefix-a").removeprefix("prefix-"), "a") and same(String("a").removeprefix("x"), "a")
    assert same(String("a.txt").removesuffix(".txt"), "a") and same(String("a").removesuffix(""), "a")
    assert same(Bytes(b"ab").removeprefix(b"a"), b"b") and same(Bytes(b"ab").removesuffix(b"b"), b"a")
    assert same(Float.from_number(5), 5.0) and same(Float.from_number(1.5), 1.5)
    assert same(Float.from_number(Integer(2)), 2.0)
    for bad in ("1.5", b"1", None, []):
        with pytest.raises(TypeError):
            Float.from_number(bad)


FILL_IN_CASES = (
    [(name, value, ()) for name in ("as_integer_ratio", "bit_count", "is_integer") for value in INTS + BOOLS]
    + [
        (name, value, (affix,))
        for name in ("removeprefix", "removesuffix") for value in TEXTS
        for affix in ("", "a", "Hello", "World", value, 5, None, ("a",), b"a")
    ]
    + [
        (name, value, (affix,))
        for name in ("removeprefix", "removesuffix") for value in DATA
        for affix in (b"", b"a", b"Hello", b"World", value, bytearray(b"a"), 5, None, (b"a",), "a")
    ]
)


@pytest.mark.parametrize("name, value, args", FILL_IN_CASES)
def test_fill_in_matches_the_native_method(name, value, args):
    """Runs the fallback directly, because a newer Python never reaches it on its own."""
    if not hasattr(type(value), name):
        pytest.skip("not in this Python version")
    expected = outcome(lambda: getattr(value, name)(*args))
    assert outcome(lambda: _native._FILLED_IN[name](value, *args)) == expected


# --- Wrappers, Null and the Type Lock ---

def test_wrapper_arguments_are_unwrapped():
    assert same(String("abc").startswith(String("a")), True)
    assert same(String("abc").startswith((String("x"), "a")), True)
    assert same(String("a").center(Integer(3), String("*")), "*a*")
    assert same(String("a,b").split(sep=String(",")), ["a", "b"])
    assert same(String("xax").strip(String("x")), "a")
    assert same(Bytes(b"abc").startswith(Bytes(b"a")), True)
    assert same(Integer(5).to_bytes(Integer(2), String("big")), b"\x00\x05")
    assert same(Integer.from_bytes(Bytes(b"\x01"), "big"), 1)


def test_results_are_plain_values():
    assert same(String("a").upper(), "A") and same(Bytes(b"a").upper(), b"A")
    assert same(String("a b").split(), ["a", "b"])
    assert same(",".join(String("a b").split()), "a,b")
    assert {String("a").upper(): 1} == {"A": 1}


@pytest.mark.parametrize("call", [
    lambda: String().upper(), lambda: String().find("a"), lambda: String().split(),
    lambda: String().strip("a"), lambda: String().replace("a", "b", 1), lambda: String().format(),
    lambda: String().join([]), lambda: Bytes().upper(), lambda: Bytes().decode(), lambda: Bytes().join([]),
    lambda: Integer().bit_length(), lambda: Integer().to_bytes(1, "big"), lambda: Float().hex(),
    lambda: Boolean().bit_length(),
])
def test_null_wrapper_raises_type_error(call):
    with pytest.raises(TypeError):
        call()


@pytest.mark.parametrize("wrapper, name", [
    (Integer, "real"), (Integer, "imag"), (Integer, "numerator"), (Integer, "denominator"),
    (Float, "real"), (Float, "imag"), (Boolean, "real"),
])
def test_null_attribute_keeps_inspection_working(wrapper, name):
    assert not hasattr(wrapper(), name)
    with pytest.raises(AttributeError):
        getattr(wrapper(), name)


@pytest.mark.parametrize("wrapper", [Integer, Float, String, Boolean, Bytes])
def test_method_lookup_on_null_does_not_raise(wrapper):
    names = [name for name in dir(wrapper._type) if not name.startswith("_") and name not in ("real", "imag", "numerator", "denominator")]
    assert all(hasattr(wrapper(), name) for name in names)


def test_attributes_are_read_only():
    with pytest.raises(AttributeError):
        Integer(5).real = 6
    with pytest.raises(AttributeError):
        String("a").upper = None


def test_methods_never_change_the_wrapper():
    text = String("abc")
    text.upper(), text.center(9), text.replace("a", "b", 1), text.split(), text.strip("a")
    assert text.value == "abc"


def test_boolean_still_refuses_arithmetic():
    for call in (lambda: Boolean(True) + 1, lambda: int(Boolean(True)), lambda: -Boolean(True), lambda: 2 * Boolean(True)):
        with pytest.raises(TypeError):
            call()


def test_rmod_matches_native():
    assert same(String("a").__rmod__("%s!"), "a!")
    assert same(Bytes(b"a").__rmod__(b"%b!"), b"a!")
    with pytest.raises(TypeError):
        5 % String("a")
    with pytest.raises(TypeError):
        5 % Bytes(b"a")


def test_subclass_gets_native_methods_without_its_rules_on_results():
    class Name(String):
        def is_valid(self):
            return self._value.islower()

    assert same(Name("bob").upper(), "BOB")
    with pytest.raises(ValueError):
        Name("BOB")
