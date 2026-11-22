"""Primitives declared on a class lock the attribute itself."""
import copy
import pickle

import pytest

from primitives import Integer, Primitive, PrimitiveTypeError, String


class User:
    age = Integer(0)
    name = String("anon")

    def __init__(self, age=None):
        if age is not None:
            self.age = age


class Admin(User):
    level = Integer(1)


class Unset:
    age = Integer()


def round_trip(obj):
    return pickle.loads(pickle.dumps(obj))


def test_reads_the_default_as_a_plain_value():
    user = User()
    assert user.age == 0 and type(user.age) is int
    assert user.name == "anon" and type(user.name) is str


def test_null_default_reads_as_none():
    assert Unset().age is None


def test_assignment_stores_a_plain_value():
    user = User()
    user.age = 30
    assert user.age == 30 and type(user.age) is int


@pytest.mark.parametrize("bad", ["x", 1.5, True, None, b"x", [1]], ids=repr)
def test_wrong_type_is_refused_and_changes_nothing(bad):
    user = User(age=30)
    with pytest.raises(PrimitiveTypeError):
        user.age = bad
    assert user.age == 30 and type(user.age) is int


def test_augmented_assignment_keeps_the_type():
    user = User(age=30)
    user.age += 1
    assert user.age == 31 and type(user.age) is int


def test_augmented_assignment_to_wrong_type_is_refused():
    user = User(age=31)
    with pytest.raises(PrimitiveTypeError):
        user.age += 0.5
    assert user.age == 31


def test_instances_do_not_share_values():
    first, second = User(), User()
    first.age = 9
    assert second.age == 0


def test_init_assignment_is_checked():
    with pytest.raises(PrimitiveTypeError):
        User(age="x")


def test_class_access_returns_the_primitive():
    assert isinstance(User.age, Primitive)


def test_attribute_cannot_be_deleted():
    user = User()
    with pytest.raises(AttributeError):
        del user.age


def test_inherited_attributes_stay_locked():
    admin = Admin(age=40)
    assert admin.age == 40 and admin.level == 1
    with pytest.raises(PrimitiveTypeError):
        admin.age = "x"
    with pytest.raises(PrimitiveTypeError):
        admin.level = "x"


@pytest.mark.parametrize("clone", [copy.copy, copy.deepcopy, round_trip], ids=["copy", "deepcopy", "pickle"])
def test_copied_owner_keeps_value_and_lock(clone):
    user = User(age=31)
    duplicate = clone(user)
    assert duplicate is not user and duplicate.age == 31
    with pytest.raises(PrimitiveTypeError):
        duplicate.age = "x"


def test_one_primitive_cannot_back_two_attributes():
    shared = Integer(0)
    # Python before 3.12 wraps errors from __set_name__ in RuntimeError.
    with pytest.raises((TypeError, RuntimeError)):
        class Bad:
            first = shared
            second = shared


def test_same_name_on_two_classes_is_allowed():
    shared = Integer(0)

    class First:
        age = shared

    class Second:
        age = shared

    one, two = First(), Second()
    one.age = 1
    assert two.age == 0


def test_attribute_added_after_class_creation_fails_loudly():
    class Late:
        pass

    Late.count = Integer(0)
    with pytest.raises(AttributeError):
        Late().count = 1
    with pytest.raises(AttributeError):
        Late().count
