# py-prim
A robust, validated, and state-aware base class architecture for standard Python primitive data types.

In standard Python, primitives like int and str are loose and allow for silent state changes or type mixing. This package provides wrapper classes (Integer, String, etc.) that enforce strict type validation, provide standardized empty/null checks, and offer a consistent API across all basic data types.

## Features
Strict Type Validation: Fails fast if you try to assign a string to an integer, or mix up booleans and ints.

Standardized API: Every type implements .is_empty(), .is_null(), and .reset().

Magic Methods Support: Compares cleanly with standard Python types using == and integrates seamlessly with if statements.

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

#### This will raise a ValueError: "Invalid value for Integer: 100.5"
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

## License
MIT License