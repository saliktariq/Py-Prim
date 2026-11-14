from abc import ABC, abstractmethod
from typing import Any

class Primitive(ABC):
    def __init__(self, value: Any = None):
        self._value = value
        # Run initial validation if a value is provided
        if value is not None:
            self.validate()

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, new_value: Any):
        self._value = new_value
        self.validate()

    # --- Abstract Methods (Must be overridden) ---
    
    @abstractmethod
    def default_value(self) -> Any:
        """Return the default value for the type."""
        pass

    @abstractmethod
    def is_empty(self) -> bool:
        """Determine if the value is functionally empty."""
        pass

    @abstractmethod
    def is_valid(self) -> bool:
        """Return True if the value meets all type constraints."""
        pass

    # --- Generic Methods (Inherited by all) ---

    def is_null(self) -> bool:
        return self._value is None

    def validate(self) -> None:
        if not self.is_null() and not self.is_valid():
            raise ValueError(f"Invalid value for {self.__class__.__name__}: {self._value}")

    def reset(self) -> None:
        self.value = self.default_value()

    # --- Python Magic Methods ---

    def __str__(self) -> str:
        return str(self.default_value() if self.is_null() else self._value)

    def __eq__(self, other: Any) -> bool:
        # Allow comparison with raw primitive types or other Enhanced primitives
        if isinstance(other, Primitive):
            return self._value == other.value
        return self._value == other

    def __bool__(self) -> bool:
        return not self.is_empty() and not self.is_null()


# ==========================================
# Derived Classes
# ==========================================

class Integer(Primitive):
    def default_value(self) -> int:
        return 0

    def is_empty(self) -> bool:
        return self._value == 0

    def is_valid(self) -> bool:
        # Explicitly exclude booleans since bool is a subclass of int in Python
        return isinstance(self._value, int) and not isinstance(self._value, bool)


class Float(Primitive):
    def default_value(self) -> float:
        return 0.0

    def is_empty(self) -> bool:
        return self._value == 0.0

    def is_valid(self) -> bool:
        return isinstance(self._value, (float, int)) and not isinstance(self._value, bool)

    # Optional override: ensure the value is always stored as a float internally
    @Primitive.value.setter
    def value(self, new_value):
        if isinstance(new_value, int) and not isinstance(new_value, bool):
            new_value = float(new_value)
        super(Float, type(self)).value.fset(self, new_value)


class String(Primitive):
    def default_value(self) -> str:
        return ""

    def is_empty(self) -> bool:
        # Empty if it is length 0 or contains only whitespace
        return self._value == "" or str(self._value).isspace()

    def is_valid(self) -> bool:
        return isinstance(self._value, str)


class Boolean(Primitive):
    def default_value(self) -> bool:
        return False
        
    def is_empty(self) -> bool:
        return self._value is False
        
    def is_valid(self) -> bool:
        return isinstance(self._value, bool)


class Bytes(Primitive):
    def default_value(self) -> bytes:
        return b""

    def is_empty(self) -> bool:
        return self._value == b""

    def is_valid(self) -> bool:
        return isinstance(self._value, bytes)