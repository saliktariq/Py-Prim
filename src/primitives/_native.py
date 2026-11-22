"""Python's own int, float, bool, str and bytes methods on the wrapper types.

Each method gives the same plain result as calling it on the stored value.
Wrapper arguments are unwrapped first, and methods newer than the running
Python are filled in, so the API is the same on every supported version.
"""
import functools
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar, overload

from . import core as _core

R = TypeVar("R")
C = TypeVar("C")
V = TypeVar("V")

# Marks an argument that was not passed, where None is itself a meaningful value.
UNSET: Any = object()


def _plain(item: Any) -> Any:
    if type(item) is tuple:
        return tuple(_plain(part) for part in item)
    return _core._raw(item)


def _present(obj: Any) -> Any:
    if obj._value is None:
        raise TypeError(f"null {type(obj).__name__} has no value")
    return obj._value


def unwrapped(method: Callable[..., R]) -> Callable[..., R]:
    """Call `method` with any wrapper arguments replaced by their plain values."""
    def call(*args: Any, **kwargs: Any) -> R:
        return method(*map(_plain, args), **{key: _plain(item) for key, item in kwargs.items()})
    return call


def join_items(separator: Any, items: Any) -> Any:
    return separator.join([_core._raw(item) for item in items])


# --- Methods Added in Newer Python Versions ---

def _remove_prefix(value: Any, prefix: Any) -> Any:
    if isinstance(prefix, tuple):
        raise TypeError("prefix must not be a tuple")
    return value[len(prefix):] if value.startswith(prefix) else value


def _remove_suffix(value: Any, suffix: Any) -> Any:
    if isinstance(suffix, tuple):
        raise TypeError("suffix must not be a tuple")
    return value[:len(value) - len(suffix)] if value.endswith(suffix) else value


def _from_number(number: Any) -> float:
    kind = type(number)
    if not hasattr(kind, "__float__") and not hasattr(kind, "__index__"):
        raise TypeError(f"must be a real number, not {kind.__name__}")
    return float(number)


def _as_integer_ratio(value: int) -> Tuple[int, int]:
    return int(value), 1


def _bit_count(value: int) -> int:
    return bin(value).count("1")


def _is_integer(value: int) -> bool:
    return True


_FILLED_IN: Dict[str, Callable[..., Any]] = {
    "as_integer_ratio": _as_integer_ratio,
    "bit_count": _bit_count,
    "from_number": _from_number,
    "is_integer": _is_integer,
    "removeprefix": _remove_prefix,
    "removesuffix": _remove_suffix,
}


def _resolve(kind: type, name: str) -> Callable[..., Any]:
    method = getattr(kind, name, None)
    if method is None:
        method = _FILLED_IN.get(name)
    if method is None:
        raise AttributeError(f"{kind.__name__} has no attribute {name!r}")
    return unwrapped(method)


# ==========================================
# Descriptors
# ==========================================

class _Method(Generic[R]):
    """A method of the stored value. On the class it takes the value first, like `str.upper(text)`."""

    def __init__(self, function: Optional[Callable[..., R]] = None) -> None:
        self._function = function
        self._name = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, obj: Any, owner: Any = None) -> Callable[..., R]:
        kind = type(obj) if owner is None else owner
        method = self._function or _resolve(kind._type, self._name)
        if obj is None:
            return lambda value, *args, **kwargs: method(_core._raw(value), *args, **kwargs)
        return lambda *args, **kwargs: method(_present(obj), *args, **kwargs)


class _ClassCall(Generic[R]):
    """A native class or static method, such as `int.from_bytes`."""

    def __init__(self) -> None:
        self._name = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self, obj: Any, owner: Any = None) -> Callable[..., R]:
        kind = type(obj) if owner is None else owner
        return _resolve(kind._type, self._name)


class _Attribute(Generic[R]):
    """A read-only attribute of the stored value, such as `real`."""

    def __init__(self) -> None:
        self._name = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    @overload
    def __get__(self, obj: None, owner: Any = None) -> "_Attribute[R]": ...
    @overload
    def __get__(self, obj: object, owner: Any = None) -> R: ...
    def __get__(self, obj: Any, owner: Any = None) -> Any:
        if obj is None:
            return self
        # AttributeError, so hasattr() and inspection tools keep working on a null wrapper.
        if obj._value is None:
            raise AttributeError(f"null {type(obj).__name__} has no value")
        return getattr(obj._value, self._name)


class Dual(Generic[C, V]):
    """One name with two uses: `on_class` when called on the class, `on_value` on an instance."""

    def __init__(self, on_class: Callable[..., C], on_value: Callable[..., V]) -> None:
        self._on_class = on_class
        self._on_value = on_value

    @overload
    def __get__(self, obj: None, owner: Any = None) -> Callable[..., C]: ...
    @overload
    def __get__(self, obj: object, owner: Any = None) -> Callable[..., V]: ...
    def __get__(self, obj: Any, owner: Any = None) -> Any:
        if obj is None:
            return functools.partial(self._on_class, owner)
        on_value = self._on_value
        return lambda *args, **kwargs: on_value(_present(obj), *args, **kwargs)


# ==========================================
# Native Methods by Type
# ==========================================

class _NativeInteger:
    __slots__ = ()

    as_integer_ratio = _Method[Tuple[int, int]]()
    bit_count = _Method[int]()
    bit_length = _Method[int]()
    conjugate = _Method[int]()
    from_bytes = _ClassCall[int]()
    is_integer = _Method[bool]()
    to_bytes = _Method[bytes]()
    real = _Attribute[int]()
    imag = _Attribute[int]()
    numerator = _Attribute[int]()
    denominator = _Attribute[int]()


class _NativeBoolean:
    __slots__ = ()

    as_integer_ratio = _Method[Tuple[int, int]]()
    bit_count = _Method[int]()
    bit_length = _Method[int]()
    conjugate = _Method[int]()
    from_bytes = _ClassCall[bool]()
    is_integer = _Method[bool]()
    to_bytes = _Method[bytes]()
    real = _Attribute[int]()
    imag = _Attribute[int]()
    numerator = _Attribute[int]()
    denominator = _Attribute[int]()


class _NativeFloat:
    __slots__ = ()

    as_integer_ratio = _Method[Tuple[int, int]]()
    conjugate = _Method[float]()
    from_number = _ClassCall[float]()
    fromhex = _ClassCall[float]()
    hex = _Method[str]()
    is_integer = _Method[bool]()
    real = _Attribute[float]()
    imag = _Attribute[float]()
    __getformat__ = _ClassCall[str]()


class _NativeString:
    """`format`, `join`, `replace`, `split` and `strip` are in the String method API."""

    __slots__ = ()

    capitalize = _Method[str]()
    casefold = _Method[str]()
    center = _Method[str]()
    count = _Method[int]()
    encode = _Method[bytes]()
    endswith = _Method[bool]()
    expandtabs = _Method[str]()
    find = _Method[int]()
    format_map = _Method[str]()
    index = _Method[int]()
    isalnum = _Method[bool]()
    isalpha = _Method[bool]()
    isascii = _Method[bool]()
    isdecimal = _Method[bool]()
    isdigit = _Method[bool]()
    isidentifier = _Method[bool]()
    islower = _Method[bool]()
    isnumeric = _Method[bool]()
    isprintable = _Method[bool]()
    isspace = _Method[bool]()
    istitle = _Method[bool]()
    isupper = _Method[bool]()
    ljust = _Method[str]()
    lower = _Method[str]()
    lstrip = _Method[str]()
    maketrans = _ClassCall[Dict[int, Any]]()
    partition = _Method[Tuple[str, str, str]]()
    removeprefix = _Method[str]()
    removesuffix = _Method[str]()
    rfind = _Method[int]()
    rindex = _Method[int]()
    rjust = _Method[str]()
    rpartition = _Method[Tuple[str, str, str]]()
    rsplit = _Method[List[str]]()
    rstrip = _Method[str]()
    splitlines = _Method[List[str]]()
    startswith = _Method[bool]()
    swapcase = _Method[str]()
    title = _Method[str]()
    translate = _Method[str]()
    upper = _Method[str]()
    zfill = _Method[str]()


class _NativeBytes:
    """`decode` is in the Bytes method API."""

    __slots__ = ()

    capitalize = _Method[bytes]()
    center = _Method[bytes]()
    count = _Method[int]()
    endswith = _Method[bool]()
    expandtabs = _Method[bytes]()
    find = _Method[int]()
    fromhex = _ClassCall[bytes]()
    hex = _Method[str]()
    index = _Method[int]()
    isalnum = _Method[bool]()
    isalpha = _Method[bool]()
    isascii = _Method[bool]()
    isdigit = _Method[bool]()
    islower = _Method[bool]()
    isspace = _Method[bool]()
    istitle = _Method[bool]()
    isupper = _Method[bool]()
    join = _Method[bytes](join_items)
    ljust = _Method[bytes]()
    lower = _Method[bytes]()
    lstrip = _Method[bytes]()
    maketrans = _ClassCall[bytes]()
    partition = _Method[Tuple[bytes, bytes, bytes]]()
    removeprefix = _Method[bytes]()
    removesuffix = _Method[bytes]()
    replace = _Method[bytes]()
    rfind = _Method[int]()
    rindex = _Method[int]()
    rjust = _Method[bytes]()
    rpartition = _Method[Tuple[bytes, bytes, bytes]]()
    rsplit = _Method[List[bytes]]()
    rstrip = _Method[bytes]()
    split = _Method[List[bytes]]()
    splitlines = _Method[List[bytes]]()
    startswith = _Method[bool]()
    strip = _Method[bytes]()
    swapcase = _Method[bytes]()
    title = _Method[bytes]()
    translate = _Method[bytes]()
    upper = _Method[bytes]()
    zfill = _Method[bytes]()

    def __buffer__(self, flags: int) -> memoryview:
        """Lets memoryview, hashlib and file writes read the value on Python 3.12+."""
        return memoryview(_present(self))
