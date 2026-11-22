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

### Built-in Methods

Every type comes with parsing, conversion, comparison, bit manipulation and text methods, plus constants such as `Integer.MAX_VALUE`. Method names are camelCase.

```python
from primitives import Boolean, Float, Integer, String

Integer.parseInt("ff", 16)         # 255
Integer.MAX_VALUE                  # 2147483647
Integer(12).bitCount()             # 2, the instance fills the first argument
Integer.toHexString(-1)            # String('ffffffff')
Float.floatToIntBits(1.0)          # 1065353216
Boolean.parseBoolean("TRUE")       # True

String("  Hello ").trim().toUpperCase()         # String('HELLO')
String("a1b22").replaceAll(r"\d+", "#")         # String('a#b#')
String("boo:and:foo").split(":", 2)             # [String('boo'), String('and:foo')]
String.format("%05d|%,.2f", 42, 1234.5)         # String('00042|1,234.50')
```

Numbers, booleans and single characters come back as plain Python values. Text and boxed values such as `Integer.valueOf("5")` come back as wrappers, so calls can be chained.

These methods read each value at a fixed width:

- `Integer` is 32-bit. Arithmetic wraps on overflow, and a stored value outside the 32-bit range raises `OverflowError` instead of giving a wrong answer.
- `Float` is 32-bit, while `.value` keeps the full Python float. `Float(0.1).doubleValue()` is `0.10000000149011612`, and `Float(1e300).isInfinite()` is `True`.
- `String` indexes count UTF-16 units, so `String("😀").length()` is 2 while `len()` stays 1.
- `Bytes` numeric methods need a value of exactly one byte, read as signed.

Malformed input and invalid format or regex patterns raise `ValueError`. Out-of-range indexes raise `IndexError`, null arguments raise `TypeError`, and division by zero raises `ZeroDivisionError`.

A few details to keep in mind:

- Constructors stay type-locked, so use `Integer.valueOf("5")` to parse text. `String.fromBytes` and `String.fromCodePoints` build a `String` from bytes or code points.
- `String.isEmpty()` is true only for length 0, while `is_empty()` also treats whitespace as empty.
- `Integer.getInteger` and `Boolean.getBoolean` read environment variables.
- `String.format` uses English formatting and raises `ValueError` for other locales. Pass a locale with `locale="en-US"`.
- Regex patterns are translated to Python's `re`. Possessive quantifiers and atomic groups need Python 3.11+. `\G`, `\X`, `\b{g}`, `(?U)`, and Unicode script or block properties raise `ValueError` rather than matching differently.

### Native Python Methods

Every public method and attribute of `int`, `float`, `str`, `bytes` and `bool` also works on the matching type, with the same arguments and the same plain Python result. Wrappers can be passed as arguments.

```python
from primitives import Bytes, Float, Integer, String

String("hello world").title()      # 'Hello World'
String("a b c").split()            # ['a', 'b', 'c']
String("report.txt").removesuffix(".txt")  # 'report'
Integer(255).bit_length()          # 8
Integer(5).to_bytes(2, "big")      # b'\x00\x05'
Float(1.5).as_integer_ratio()      # (3, 2)
Bytes(b"abc").hex()                # '616263'
```

Newer methods such as `removeprefix` and `bit_count` work on every supported Python version.

A few names have two forms, chosen by how they are called:

| Call | Result |
| --- | --- |
| `String("{}").format(1)` | Python's `str.format`, returns `str` |
| `String.format("%d", 1)` | printf-style, returns `String` |
| `String(",").join(items)` | Python's `str.join`, returns `str` |
| `String.join(",", "a", "b")` | delimiter first, returns `String` |
| `String(s).split()`, or with `sep=` or `maxsplit=` | Python's `str.split`, returns a list of `str` |
| `String(s).split(pattern, limit)` | regex split, returns a list of `String` |
| `String(s).strip(chars)` | Python's `str.strip`, returns `str` |
| `String(s).strip()` | strips whitespace except non-breaking spaces, returns `String` |
| `String(s).replace(old, new, count)` | Python's `str.replace`, returns `str` |
| `String(s).replace(old, new)` | replaces all, returns `String` |
| `Bytes(b).decode()` | Python's `bytes.decode`, returns `str` |
| `Bytes.decode("0x7f")` | parses a number, returns `Bytes` |

A positional `split` argument is a regex, so `String("a.b").split(".")` returns `[]` because `.` matches every character. Use `split(sep=".")` for a literal separator.

For the plain Python behavior in every case, call the method on `.value`, as in `String("a.b").value.split(".")`.

Two native behaviors are left out on purpose. Wrappers are mutable, so they stay unhashable and can't be dictionary keys. `Boolean` still refuses arithmetic, so `Boolean(True) + 1` raises `TypeError`.

### Limits

Python never calls a class when a variable is rebound, so `count = "hello"` cannot be blocked at runtime. The package ships type hints, so a type checker such as mypy will flag it.

## License
MIT License