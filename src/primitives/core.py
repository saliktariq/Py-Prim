import math
import operator
from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    cast,
    overload,
)

T = TypeVar("T")
_Method = Callable[..., Any]

# Only the validated setter may change these.
_PROTECTED = frozenset({"_value", "_field", "__class__"})


class PrimitiveTypeError(TypeError, ValueError):
    """Wrong type. Also a ValueError, so existing `except ValueError` keeps working."""


# ==========================================
# Operator Helpers
# ==========================================

def _raw(value: Any) -> Any:
    """Unwrap a Primitive and leave anything else as it is."""
    return value._value if isinstance(value, Primitive) else value


def _forward(op: _Method) -> _Method:
    """`x + y`: returns a plain Python value and leaves the wrapper unchanged."""
    def method(self: "Primitive[Any]", *others: Any) -> Any:
        values = self._operands(self, *others)
        return NotImplemented if values is None else op(*values)
    return method


def _reflected(op: _Method) -> _Method:
    """`y + x`, used when the left side is a plain value."""
    def method(self: "Primitive[Any]", other: Any, *rest: Any) -> Any:
        values = self._operands(other, self, *rest)
        return NotImplemented if values is None else op(*values)
    return method


def _inplace(op: _Method) -> _Method:
    """`x += y`: keeps the wrapper and sends the result through the type check."""
    def method(self: "Primitive[Any]", other: Any) -> Any:
        self.value = op(self, other)
        return self
    return method


def _operators(op: _Method) -> Tuple[_Method, _Method, _Method]:
    return _forward(op), _reflected(op), _inplace(op)


def _unary(op: _Method) -> _Method:
    """`-x`, `int(x)`, `len(x)` and similar. A null wrapper has nothing to operate on."""
    def method(self: "Primitive[Any]", *args: Any) -> Any:
        if self._value is None:
            raise TypeError(f"null {type(self).__name__} has no value")
        return op(self._value, *args)
    return method


def _ordering(op: _Method) -> _Method:
    """`x < y`. Follows the same type rules as `==`."""
    def method(self: "Primitive[Any]", other: Any) -> Any:
        right = _raw(other)
        if self._value is None or right is None or not self._comparable(other):
            return NotImplemented
        return op(self._value, right)
    return method


# ==========================================
# Base Class
# ==========================================

class Primitive(ABC, Generic[T]):
    """A value locked to one exact Python type.

    Use it as a wrapper (`age = Integer(5)`, then `age.value = 6`) or declare it on
    a class (`class User: age = Integer(0)`), where `user.age` reads and writes the
    plain value with the same checks.

    Subclasses add rules by overriding `is_valid`. Any attributes they need must be
    set before calling `super().__init__()`.
    """

    __slots__ = ("_value", "_field", "__weakref__")

    _value: Optional[T]
    _field: Optional[str]
    _type: ClassVar[type]
    # Plain types that may also be compared with this one.
    _also_equal: ClassVar[Tuple[type, ...]] = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__dict__.get("__slots__"):
            raise TypeError(f"{cls.__name__}: use normal attributes instead of __slots__")

    def __init__(self, value: Optional[T] = None) -> None:
        if hasattr(self, "_value"):
            raise TypeError(f"{type(self).__name__} is already initialized")
        if not hasattr(self, "_type"):
            raise TypeError(f"{type(self).__name__} must define _type")
        checked = None if value is None else self._check(value)
        object.__setattr__(self, "_field", None)
        object.__setattr__(self, "_value", checked)

    # --- The Single Gate Every Write Passes Through ---

    def _coerce(self, value: Any) -> Any:
        """Convert an accepted input before the type check. Float uses this for ints."""
        return value

    def _check(self, value: Any) -> T:
        """Return a safe value or raise. Never touches the stored value."""
        value = self._coerce(value)
        # type() rather than isinstance(): rejects bool for int, subclasses,
        # and objects that fake their __class__.
        if type(value) is not self._type:
            raise PrimitiveTypeError(
                f"{type(self).__name__} requires {self._type.__name__}, "
                f"got {type(value).__name__}"
            )
        # Run subclass rules on a throwaway object so a failure changes nothing.
        trial = object.__new__(type(self))
        object.__setattr__(trial, "_value", value)
        if hasattr(self, "__dict__"):
            object.__setattr__(trial, "__dict__", self.__dict__)
        if not trial.is_valid():
            raise ValueError(f"{type(self).__name__} rejected this {self._type.__name__} value")
        return cast(T, value)

    @property
    def value(self) -> Optional[T]:
        return self._value

    @value.setter
    def value(self, new_value: T) -> None:
        object.__setattr__(self, "_value", self._check(new_value))

    # --- Instance Lock ---

    def __setattr__(self, name: str, value: Any) -> None:
        is_new = name not in getattr(self, "__dict__", ())
        if name in _PROTECTED or (name != "value" and is_new and hasattr(self, "_value")):
            raise AttributeError(
                f"{type(self).__name__}: cannot set {name!r}. Use .value, or set "
                "subclass attributes before calling super().__init__()"
            )
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        if name in _PROTECTED:
            raise AttributeError(f"{type(self).__name__}: cannot delete {name!r}")
        object.__delattr__(self, name)

    # --- Copy and Pickle (restored values are validated again) ---

    def __getstate__(self) -> Tuple[Optional[T], Optional[Dict[str, Any]]]:
        return (self._value, getattr(self, "__dict__", None))

    def __setstate__(self, state: Tuple[Optional[T], Optional[Dict[str, Any]]]) -> None:
        if hasattr(self, "_value"):
            raise TypeError(f"{type(self).__name__} is already initialized")
        value, attributes = state
        object.__setattr__(self, "_field", None)
        object.__setattr__(self, "_value", None)
        if attributes:
            self.__dict__.update(attributes)
        if value is not None:
            self.value = value

    # --- Typed Class Attributes (`class User: age = Integer(0)`) ---

    def __set_name__(self, owner: type, name: str) -> None:
        if self._field not in (None, name):
            raise TypeError(f"one {type(self).__name__} cannot back two attributes")
        object.__setattr__(self, "_field", name)

    def _key(self) -> str:
        if self._field is None:
            raise AttributeError("typed attributes must be declared in the class body")
        return self._field

    @overload
    def __get__(self, obj: None, owner: Optional[type] = None) -> "Primitive[T]": ...
    @overload
    def __get__(self, obj: object, owner: Optional[type] = None) -> Optional[T]: ...
    def __get__(self, obj: Optional[object], owner: Optional[type] = None) -> Any:
        if obj is None:
            return self
        return obj.__dict__.get(self._key(), self._value)

    def __set__(self, obj: object, new_value: T) -> None:
        obj.__dict__[self._key()] = self._check(new_value)

    def __delete__(self, obj: object) -> None:
        raise AttributeError(f"cannot delete typed attribute {self._field!r}")

    # --- Abstract Methods (Must be overridden) ---

    @abstractmethod
    def default_value(self) -> T:
        """Return the default value for the type."""

    # --- Generic Methods (Inherited by all) ---

    def is_empty(self) -> bool:
        """Return True if the value is null or equal to the type's default."""
        return self._value is None or bool(self._value == self.default_value())

    def is_valid(self) -> bool:
        """Override to add rules. The exact type is enforced before this runs."""
        return type(self._value) is self._type

    def is_null(self) -> bool:
        return self._value is None

    def validate(self) -> None:
        if not self.is_null() and not self.is_valid():
            raise ValueError(f"Invalid value for {type(self).__name__}")

    def reset(self) -> None:
        self.value = self.default_value()

    def clear(self) -> None:
        """The one explicit way back to the null state."""
        object.__setattr__(self, "_value", None)

    # --- Operator Rules ---

    def _operands(self, *operands: Any) -> Optional[List[Any]]:
        """Plain values for an operator, or None if they must not be mixed."""
        values = [_raw(item) for item in operands]
        for item in values:
            if item is None or (type(item) is bool) != (self._type is bool):
                return None
        return values

    def _comparable(self, other: object) -> bool:
        """Return True if `other` holds the same kind of value."""
        if isinstance(other, Primitive):
            return self._type is other._type
        return type(other) is self._type or type(other) in self._also_equal

    # --- Python Magic Methods ---

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._value!r})"

    def __str__(self) -> str:
        return str(self._value)

    def __format__(self, spec: str) -> str:
        return format(self._value, spec)

    # Defining __eq__ leaves the class unhashable, which is right for a mutable wrapper.
    def __eq__(self, other: object) -> bool:
        if other is None:
            return self._value is None
        if not self._comparable(other):
            return NotImplemented
        return bool(self._value == _raw(other))

    __lt__ = _ordering(operator.lt)
    __le__ = _ordering(operator.le)
    __gt__ = _ordering(operator.gt)
    __ge__ = _ordering(operator.ge)

    def __bool__(self) -> bool:
        return not self.is_empty()


class _Numeric(Primitive[T]):
    __slots__ = ()

    __add__, __radd__, __iadd__ = _operators(operator.add)
    __sub__, __rsub__, __isub__ = _operators(operator.sub)
    __mul__, __rmul__, __imul__ = _operators(operator.mul)
    __truediv__, __rtruediv__, __itruediv__ = _operators(operator.truediv)
    __floordiv__, __rfloordiv__, __ifloordiv__ = _operators(operator.floordiv)
    __mod__, __rmod__, __imod__ = _operators(operator.mod)
    __pow__, __rpow__, __ipow__ = _operators(pow)
    __divmod__, __rdivmod__ = _forward(divmod), _reflected(divmod)

    __neg__ = _unary(operator.neg)
    __pos__ = _unary(operator.pos)
    __abs__ = _unary(abs)
    __int__ = _unary(int)
    __float__ = _unary(float)
    __round__ = _unary(round)
    __trunc__ = _unary(math.trunc)
    __floor__ = _unary(math.floor)
    __ceil__ = _unary(math.ceil)


class _Sequence(Primitive[T]):
    __slots__ = ()

    __add__, __radd__, __iadd__ = _operators(operator.add)
    __mul__, __rmul__, __imul__ = _operators(operator.mul)
    # printf-style formatting accepts any argument, including bool and None.
    __mod__ = _unary(lambda text, args: text % _raw(args))
    __imod__ = _inplace(operator.mod)

    __len__ = _unary(len)
    __iter__ = _unary(iter)
    __getitem__ = _unary(operator.getitem)
    __contains__ = _unary(lambda text, item: _raw(item) in text)


# ==========================================
# Derived Classes
# ==========================================

class Integer(_Numeric[int]):
    __slots__ = ()
    _type = int

    __and__, __rand__, __iand__ = _operators(operator.and_)
    __or__, __ror__, __ior__ = _operators(operator.or_)
    __xor__, __rxor__, __ixor__ = _operators(operator.xor)
    __lshift__, __rlshift__, __ilshift__ = _operators(operator.lshift)
    __rshift__, __rrshift__, __irshift__ = _operators(operator.rshift)
    __invert__ = _unary(operator.invert)
    __index__ = _unary(operator.index)

    def default_value(self) -> int:
        return 0


class Float(_Numeric[float]):
    __slots__ = ()
    _type = float
    _also_equal = (int,)

    def default_value(self) -> float:
        return 0.0

    def _coerce(self, value: Any) -> Any:
        # Ints are accepted and stored as floats. bool is not treated as an int.
        if type(value) is int:
            try:
                return float(value)
            except OverflowError:
                raise ValueError("int is too large for Float") from None
        return value


class String(_Sequence[str]):
    __slots__ = ()
    _type = str

    def default_value(self) -> str:
        return ""

    def is_empty(self) -> bool:
        # Empty if it is null, length 0 or contains only whitespace
        return self._value is None or not self._value.strip()


class Boolean(Primitive[bool]):
    __slots__ = ()
    _type = bool

    __and__, __rand__, __iand__ = _operators(operator.and_)
    __or__, __ror__, __ior__ = _operators(operator.or_)
    __xor__, __rxor__, __ixor__ = _operators(operator.xor)

    def default_value(self) -> bool:
        return False


class Bytes(_Sequence[bytes]):
    __slots__ = ()
    _type = bytes

    __bytes__ = _unary(bytes)

    def default_value(self) -> bytes:
        return b""
