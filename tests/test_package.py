"""The public API, text output and the examples documented in the README."""
import operator
import pathlib

import pytest

import primitives
from primitives import Float, Integer, PrimitiveTypeError, String
from samples import ALL_TYPES, GOOD, same


def test_public_api():
    expected = {"Primitive", "PrimitiveTypeError", "Integer", "Float", "String", "Boolean", "Bytes"}
    assert set(primitives.__all__) == expected
    assert all(hasattr(primitives, name) for name in expected)


def test_type_hint_marker_is_shipped():
    assert pathlib.Path(primitives.__file__).with_name("py.typed").is_file()


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_repr(cls):
    assert repr(cls(GOOD[cls])) == "{}({!r})".format(cls.__name__, GOOD[cls])
    assert repr(cls()) == "{}(None)".format(cls.__name__)


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_str(cls):
    assert str(cls(GOOD[cls])) == str(GOOD[cls])
    assert str(cls()) == "None"


# --- README examples ---


def test_readme_usage():
    age = Integer(25)
    assert age.value == 25
    age.value = 26
    assert age.value == 26


def test_readme_strict_validation():
    score = Integer(100)
    with pytest.raises(ValueError, match="Integer requires int, got float"):
        score.value = 100.5
    with pytest.raises(ValueError):
        score.value = True
    assert score.value == 100


def test_readme_state_checks():
    name = String("")
    assert name.is_empty()
    name.value = "Alice"
    assert not name.is_empty()
    name.reset()
    assert name.value == ""
    assert Float(None).is_null()


def test_readme_type_lock():
    count = Integer(5)
    with pytest.raises(PrimitiveTypeError):
        count.value = None
    count.clear()
    assert count.is_null()
    assert same(Float(5).value, 5.0)


def test_readme_class_attributes():
    class User:
        age = Integer(0)

    user = User()
    user.age = 30
    user.age += 1
    assert user.age == 31
    with pytest.raises(PrimitiveTypeError):
        user.age = "hello"


def test_readme_operators():
    count = Integer(5)
    assert same(count + 1.5, 6.5)
    count += 1
    assert type(count) is Integer and count.value == 6
    with pytest.raises(PrimitiveTypeError):
        operator.iadd(count, 0.5)
    with pytest.raises(PrimitiveTypeError):
        operator.itruediv(count, 2)
    assert (Integer(1) == True) is False
    with pytest.raises(TypeError):
        Integer(1) < 1.5
    assert Float(5) == 5 and Float(1.5) < 2


def test_readme_custom_type():
    class Age(Integer):
        def is_valid(self):
            return self._value >= 0

    assert Age(5).value == 5
    with pytest.raises(ValueError):
        Age(-1)
