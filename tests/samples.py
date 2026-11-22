"""Sample values shared by the test modules."""
from primitives import Boolean, Bytes, Float, Integer, String

ALL_TYPES = [Integer, Float, String, Boolean, Bytes]
EXACT_TYPE = {Integer: int, Float: float, String: str, Boolean: bool, Bytes: bytes}
GOOD = {Integer: 5, Float: 1.5, String: "hi", Boolean: True, Bytes: b"hi"}
WRONG = {Integer: "wrong", Float: "wrong", String: 123, Boolean: "wrong", Bytes: "wrong"}
DEFAULT = {Integer: 0, Float: 0.0, String: "", Boolean: False, Bytes: b""}
OTHER = {Integer: String, Float: String, String: Integer, Boolean: String, Bytes: String}


def same(actual, expected):
    """Equal and exactly the same type, so 1 never passes for 1.0 or True."""
    return type(actual) is type(expected) and actual == expected


def holds(wrapper, cls):
    """Return True if the wrapper still holds its original sample value."""
    return type(wrapper) is cls and same(wrapper.value, GOOD[cls])
