"""Subclasses can add rules and attributes but cannot widen the type."""
import copy
import operator
import pickle
from decimal import Decimal

import pytest

from primitives import Integer, Primitive, PrimitiveTypeError


class Age(Integer):
    def is_valid(self):
        return self._value >= 0


class Bounded(Integer):
    def __init__(self, value, maximum):
        self.maximum = maximum
        super().__init__(value)

    def is_valid(self):
        return super().is_valid() and self._value <= self.maximum


class Cyclic(Integer):
    def __init__(self, value):
        self.me = self
        super().__init__(value)


class SetsAttributeTooLate(Integer):
    def __init__(self, value):
        super().__init__(value)
        self.label = "x"


class Sealed(Integer):
    __slots__ = ()


class Money(Primitive[Decimal]):
    _type = Decimal

    def default_value(self):
        return Decimal(0)


class MissingType(Primitive[int]):
    def default_value(self):
        return 0


class MissingDefault(Primitive[int]):
    _type = int


class Person:
    age = Age(0)


def clones(obj):
    yield "copy", copy.copy(obj)
    yield "deepcopy", copy.deepcopy(obj)
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        yield "pickle{}".format(protocol), pickle.loads(pickle.dumps(obj, protocol=protocol))


# --- Rules ---


def test_rule_accepts_valid_value():
    assert Age(5).value == 5


def test_rule_rejects_in_constructor():
    with pytest.raises(ValueError):
        Age(-1)


def test_rule_failure_keeps_the_value():
    age = Age(5)
    with pytest.raises(ValueError):
        age.value = -1
    assert age.value == 5


def test_rule_applies_to_in_place_operators():
    age = Age(5)
    with pytest.raises(ValueError):
        operator.isub(age, 10)
    assert age.value == 5


@pytest.mark.parametrize("bad", [1.5, True, "x"], ids=repr)
def test_rule_cannot_widen_the_type(bad):
    with pytest.raises(PrimitiveTypeError):
        Age(bad)


def test_rule_applies_to_class_attributes():
    person = Person()
    person.age = 3
    with pytest.raises(ValueError):
        person.age = -1
    with pytest.raises(PrimitiveTypeError):
        person.age = 1.5
    assert person.age == 3


# --- Subclass attributes ---


def test_subclass_keeps_its_attribute():
    bounded = Bounded(5, 10)
    assert bounded.maximum == 10 and bounded.value == 5


def test_rule_can_use_subclass_attribute():
    with pytest.raises(ValueError):
        Bounded(11, 10)
    bounded = Bounded(5, 10)
    with pytest.raises(ValueError):
        bounded.value = 11
    with pytest.raises(ValueError):
        operator.iadd(bounded, 100)
    assert bounded.value == 5


def test_subclass_type_lock_still_applies():
    bounded = Bounded(5, 10)
    with pytest.raises(PrimitiveTypeError):
        bounded.value = 1.5
    assert bounded.value == 5


def test_existing_attribute_can_be_updated():
    bounded = Bounded(5, 10)
    bounded.maximum = 20
    bounded.value = 15
    assert bounded.value == 15


def test_subclass_attribute_can_be_deleted():
    bounded = Bounded(5, 10)
    del bounded.maximum
    assert not hasattr(bounded, "maximum")


def test_validate_reports_a_value_that_broke_a_rule():
    bounded = Bounded(5, 10)
    bounded.maximum = 1
    with pytest.raises(ValueError):
        bounded.validate()


def test_misspelled_attribute_is_refused():
    bounded = Bounded(5, 10)
    with pytest.raises(AttributeError):
        bounded.maximun = 1


@pytest.mark.parametrize("name, value", [("__class__", Integer), ("_value", "x"), ("_field", "x")])
def test_internals_stay_protected(name, value):
    bounded = Bounded(5, 10)
    with pytest.raises(AttributeError):
        setattr(bounded, name, value)
    assert type(bounded) is Bounded and bounded.value == 5


@pytest.mark.parametrize("name", ["_value", "_field", "__class__", "value"])
def test_internals_cannot_be_deleted(name):
    bounded = Bounded(5, 10)
    with pytest.raises((AttributeError, TypeError)):
        delattr(bounded, name)
    assert bounded.value == 5


def test_instance_dict_cannot_shadow_the_value():
    bounded = Bounded(5, 10)
    vars(bounded)["_value"] = "x"
    assert bounded.value == 5


def test_setting_attribute_after_super_init_fails_loudly():
    with pytest.raises(AttributeError, match="super"):
        SetsAttributeTooLate(1)


def test_empty_slots_subclass_is_sealed():
    sealed = Sealed(1)
    with pytest.raises(AttributeError):
        sealed.extra = 1


def test_non_empty_slots_are_refused():
    with pytest.raises(TypeError):
        class Bad(Integer):
            __slots__ = ("extra",)


# --- Copy and pickle ---


def test_clones_keep_state_and_rules():
    bounded = Bounded(5, 10)
    for label, clone in clones(bounded):
        assert type(clone) is Bounded, label
        assert clone is not bounded, label
        assert clone.value == 5 and clone.maximum == 10, label
        with pytest.raises(ValueError):
            clone.value = 11


def test_deepcopy_handles_reference_cycles():
    cyclic = Cyclic(3)
    duplicate = copy.deepcopy(cyclic)
    assert duplicate.me is duplicate and duplicate.value == 3


def test_pickle_handles_reference_cycles():
    cyclic = Cyclic(3)
    duplicate = pickle.loads(pickle.dumps(cyclic))
    assert duplicate.me is duplicate and duplicate.value == 3


# --- Direct subclasses of Primitive ---


def test_custom_type_works():
    money = Money(Decimal("1.5"))
    assert money.value == Decimal("1.5")
    assert copy.copy(money) == money
    assert pickle.loads(pickle.dumps(money)).value == Decimal("1.5")


def test_custom_type_is_locked():
    with pytest.raises(PrimitiveTypeError):
        Money(1.5)


def test_missing_type_is_a_clear_error():
    with pytest.raises(TypeError, match="_type"):
        MissingType(1)


def test_missing_default_value_cannot_be_instantiated():
    with pytest.raises(TypeError):
        MissingDefault(1)


def test_primitive_itself_is_abstract():
    with pytest.raises(TypeError):
        Primitive()
