"""Attempts to get a wrong value past the type lock."""
import enum
import pickle
from unittest import mock

import pytest

from primitives import Boolean, Integer, PrimitiveTypeError
from samples import ALL_TYPES, EXACT_TYPE, GOOD, OTHER, WRONG, holds


def fake_instance(cls):
    """An object that is not the type but makes isinstance() return True."""
    target = EXACT_TYPE[cls]

    class Fake:
        @property
        def __class__(self):
            return target

    return Fake()


def set_private_value(wrapper, cls):
    wrapper._value = WRONG[cls]


def set_private_field(wrapper, cls):
    wrapper._field = "x"


def write_instance_dict(wrapper, cls):
    vars(wrapper)["_value"] = WRONG[cls]


def swap_class(wrapper, cls):
    wrapper.__class__ = OTHER[cls]


def rerun_init_with_wrong_type(wrapper, cls):
    wrapper.__init__(WRONG[cls])


def rerun_init_with_none(wrapper, cls):
    wrapper.__init__(None)


def rerun_init_with_valid_value(wrapper, cls):
    wrapper.__init__(GOOD[cls])


def restore_state_on_live_object(wrapper, cls):
    wrapper.__setstate__((WRONG[cls], None))


def clear_through_restore(wrapper, cls):
    wrapper.__setstate__((None, None))


def delete_private_value(wrapper, cls):
    del wrapper._value


def delete_public_value(wrapper, cls):
    del wrapper.value


def set_misspelled_attribute(wrapper, cls):
    wrapper.vlaue = GOOD[cls]


def replace_a_method(wrapper, cls):
    wrapper.is_valid = lambda: True


def assign_fake_instance(wrapper, cls):
    wrapper.value = fake_instance(cls)


def assign_mock_with_spec(wrapper, cls):
    wrapper.value = mock.Mock(spec=EXACT_TYPE[cls])


ATTACKS = [
    set_private_value,
    set_private_field,
    write_instance_dict,
    swap_class,
    rerun_init_with_wrong_type,
    rerun_init_with_none,
    rerun_init_with_valid_value,
    restore_state_on_live_object,
    clear_through_restore,
    delete_private_value,
    delete_public_value,
    set_misspelled_attribute,
    replace_a_method,
    assign_fake_instance,
    assign_mock_with_spec,
]


@pytest.mark.parametrize("cls", ALL_TYPES)
@pytest.mark.parametrize("attack", ATTACKS, ids=lambda attack: attack.__name__)
def test_attack_is_refused_and_changes_nothing(attack, cls):
    wrapper = cls(GOOD[cls])
    with pytest.raises((AttributeError, TypeError, ValueError)):
        attack(wrapper, cls)
    assert holds(wrapper, cls)


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_constructor_refuses_fake_instance(cls):
    with pytest.raises(PrimitiveTypeError):
        cls(fake_instance(cls))


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_constructor_refuses_mock_with_spec(cls):
    with pytest.raises(PrimitiveTypeError):
        cls(mock.Mock(spec=EXACT_TYPE[cls]))


@pytest.mark.parametrize("cls", [c for c in ALL_TYPES if c is not Boolean])
def test_subclass_of_the_type_is_refused(cls):
    subclass = type("Subclass", (EXACT_TYPE[cls],), {})
    with pytest.raises(PrimitiveTypeError):
        cls(subclass(GOOD[cls]))
    wrapper = cls(GOOD[cls])
    with pytest.raises(PrimitiveTypeError):
        wrapper.value = subclass(GOOD[cls])
    assert holds(wrapper, cls)


def test_int_enum_is_refused():
    class Color(enum.IntEnum):
        RED = 1

    with pytest.raises(PrimitiveTypeError):
        Integer(Color.RED)


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_patching_is_valid_cannot_widen_the_type(cls, monkeypatch):
    wrapper = cls(GOOD[cls])
    monkeypatch.setattr(cls, "is_valid", lambda self: True)
    with pytest.raises(PrimitiveTypeError):
        wrapper.value = WRONG[cls]
    assert holds(wrapper, cls)


def blank(cls):
    return cls.__new__(cls)


class CraftedPickle:
    def __init__(self, cls, state):
        self.cls = cls
        self.state = state

    def __reduce__(self):
        return (blank, (self.cls,), self.state)


@pytest.mark.parametrize("cls", ALL_TYPES)
@pytest.mark.parametrize("shape", ["instance_dict", "slot_state", "value_state"])
def test_crafted_pickle_cannot_restore_a_wrong_value(cls, shape):
    wrong = WRONG[cls]
    state = {
        "instance_dict": {"_value": wrong},
        "slot_state": (None, {"_value": wrong}),
        "value_state": (wrong, None),
    }[shape]
    payload = pickle.dumps(CraftedPickle(cls, state))
    with pytest.raises((AttributeError, TypeError, ValueError)):
        pickle.loads(payload)
