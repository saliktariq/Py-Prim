"""Copies and pickles keep the value and stay locked."""
import copy
import pickle
import weakref

import pytest

from primitives import PrimitiveTypeError
from samples import ALL_TYPES, GOOD, WRONG, holds

PROTOCOLS = range(pickle.HIGHEST_PROTOCOL + 1)


def round_trip(obj):
    return pickle.loads(pickle.dumps(obj))


CLONERS = [copy.copy, copy.deepcopy, round_trip]
CLONER_IDS = ["copy", "deepcopy", "pickle"]


@pytest.mark.parametrize("cls", ALL_TYPES)
@pytest.mark.parametrize("clone", CLONERS, ids=CLONER_IDS)
def test_clone_keeps_type_and_value(cls, clone):
    wrapper = cls(GOOD[cls])
    duplicate = clone(wrapper)
    assert duplicate is not wrapper
    assert holds(duplicate, cls)


@pytest.mark.parametrize("cls", ALL_TYPES)
@pytest.mark.parametrize("clone", CLONERS, ids=CLONER_IDS)
def test_clone_stays_locked(cls, clone):
    duplicate = clone(cls(GOOD[cls]))
    with pytest.raises(PrimitiveTypeError):
        duplicate.value = WRONG[cls]
    assert holds(duplicate, cls)


@pytest.mark.parametrize("cls", ALL_TYPES)
@pytest.mark.parametrize("clone", CLONERS, ids=CLONER_IDS)
def test_clone_of_null_stays_null(cls, clone):
    assert clone(cls()).is_null()


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_clone_is_independent(cls):
    wrapper = cls(GOOD[cls])
    duplicate = copy.copy(wrapper)
    duplicate.clear()
    assert holds(wrapper, cls)


@pytest.mark.parametrize("cls", ALL_TYPES)
@pytest.mark.parametrize("protocol", PROTOCOLS)
def test_every_pickle_protocol(cls, protocol):
    assert holds(pickle.loads(pickle.dumps(cls(GOOD[cls]), protocol=protocol)), cls)
    assert pickle.loads(pickle.dumps(cls(), protocol=protocol)).is_null()


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_weak_references_work(cls):
    wrapper = cls(GOOD[cls])
    assert weakref.ref(wrapper)() is wrapper
