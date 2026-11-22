# py-prim
A robust, validated, and state-aware base class architecture for standard Python primitive data types.

In standard Python, primitives like int and str are loose and allow for silent state changes or type mixing. This package provides wrapper classes (Integer, String, etc.) that enforce strict type validation, provide standardized empty/null checks, and offer a consistent API across all basic data types.

## Features
Strict Type Validation: Fails fast if you try to assign a string to an integer, or mix up booleans and ints.

Standardized API: Every type implements .is_empty(), .is_null(), and .reset().

Magic Methods Support: Compares cleanly with standard Python types, supports the usual operators, and integrates seamlessly with if statements.

Zero Dependencies: Built entirely on the Python standard library.

## Installation
You can install this package directly from GitHub using either pip or uv.

Using pip:

pip install git+[https://github.com/saliktariq/Py-Prim.git](https://github.com/saliktariq/Py-Prim.git)

Using uv:

uv pip install git+[https://github.com/saliktariq/Py-Prim.git](https://github.com/saliktariq/Py-Prim.git)


## Available Types
All types inherit from the Primitive abstract base class:

-   Integer
-   Float
-   String
-   Boolean
-   Bytes

## Usage:

Access and mutate the underlying data using the .value property.

from primitives import Integer, String

### Initialize with a value
age = Integer(25)
print(age.value)  # 25

### Change the value
age.value = 26
Strict Type Validation
The classes automatically validate types upon initialization and assignment, preventing accidental type mixing.

from primitives import Integer

score = Integer(100)

#### This will raise a PrimitiveTypeError, which is also a ValueError: "Integer requires int, got float"
score.value = 100.5 

### This library strictly isolates Booleans from Integers.
score.value = True # Raises ValueError
State Checks and Resets
Every type knows what its "empty" and "default" states are.

from primitives import String, Float

name = String("")
print(name.is_empty())  # True

name.value = "Alice"
print(name.is_empty())  # False

### Reset back to the type's default value
name.reset()
print(name.value)       # ""

### Null checking
balance = Float(None)
print(balance.is_null()) # True

## Type Lock

A rejected assignment raises `PrimitiveTypeError`, which is both a `TypeError` and a `ValueError`, and leaves the stored value unchanged.

```python
from primitives import Float, Integer

count = Integer(5)
count.value = None  # Raises PrimitiveTypeError
count.clear()       # The explicit way back to null

price = Float(5)    # Ints are converted, so price.value is 5.0
```

### Typed class attributes

Declare a type on a class to lock the attribute itself. It reads and writes as a plain value.

```python
from primitives import Integer

class User:
    age = Integer(0)

user = User()
user.age = 30
user.age += 1       # 31
user.age = "hello"  # Raises PrimitiveTypeError
```

### Operators

Operators return plain Python values. In-place operators keep the wrapper and its type lock.

```python
from primitives import Integer

count = Integer(5)
count + 1.5   # 6.5, a plain float
count += 1    # count is still an Integer, now holding 6
count += 0.5  # Raises PrimitiveTypeError
count /= 2    # Raises PrimitiveTypeError, because the result is a float
```

`==` and ordering only work between matching types, so `Integer(1) == True` is `False` and `Integer(1) < 1.5` raises `TypeError`. `Float` also compares with plain ints.

### Custom types

Override `is_valid` to add rules. The exact type is always checked first. Set any attributes before calling `super().__init__()`.

```python
from primitives import Integer

class Age(Integer):
    def is_valid(self):
        return self._value >= 0
```

### Limits

Python never calls a class when a variable is rebound, so `count = "hello"` cannot be blocked at runtime. The package ships type hints, so a type checker such as mypy will flag it.

## License
MIT License