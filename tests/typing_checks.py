"""Checked by `mypy --strict` in CI and never executed.

Each `type: ignore` marks a mistake mypy must catch. Strict mode reports unused
ignores, so this file fails if the type hints ever stop flagging one of them.
"""
from primitives import Boolean, Bytes, Float, Integer, PrimitiveTypeError, String


class User:
    age = Integer(0)


# --- Valid usage must produce no errors ---

number = Integer(5)
number += 1
total = number + 1
smaller = number < 3
number.clear()

decimal = Float(5)
decimal.value = 3
decimal += 1

text = String("a") + "b"
size = len(String("abc"))
letter = String("abc")[0]
for character in String("ab"):
    print(character)

print("abc"[Integer(1)], list(range(Integer(2))), int(number), float(decimal), round(decimal, 2))
flag = Boolean(True) & False
raw = Bytes(b"a") + b"b"
ordered = sorted([Integer(2), Integer(1)])

user = User()
user.age = 30

try:
    number.value = 1
except PrimitiveTypeError:
    pass

# --- Mistakes that must be flagged ---

rebound = Integer(5)
rebound = "hello"  # type: ignore[assignment]

assigned = Integer(5)
assigned.value = "hello"  # type: ignore[assignment]
assigned.value = None  # type: ignore[assignment]

label = String("x")
wrong_read: int = label.value  # type: ignore[assignment]

wrong_constructor = Integer("nope")  # type: ignore[arg-type]

user.age = "hello"  # type: ignore[assignment]
