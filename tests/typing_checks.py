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

# --- Method API ---

parsed: int = Integer.parseInt("5") + Integer.bitCount(7) + Integer(5).bitCount()
boxed: Integer = Integer.valueOf("5")
hex_text: String = Integer.toHexString(255)
chained: String = String("  a ").trim().toUpperCase().concat("!")
width: int = chained.length()
pieces = String("a,b").split(",")
single: float = Float.parseFloat("1.5") + Float.MAX_VALUE
truth: bool = Boolean.parseBoolean("true") and Boolean.TRUE.booleanValue()
small: Bytes = Bytes.valueOf(-1)

# --- Native Python methods ---

shout: str = String("a").upper()
position: int = String("a").find("a")
first_word: str = String("a b").split()[0]
first_piece: String = String("a,b").split(",")[0]
kept_piece: str = String("a,b").split(",", maxsplit=1)[0]
chopped: str = String("xa").strip("x")
trimmed: String = String(" a ").strip()
replaced_once: str = String("aa").replace("a", "b", 1)
replaced_all: String = String("aa").replace("a", "b")
braces: str = String("{}").format(1)
printf: String = String.format("%d", 1)
joined: str = String(",").join(["a", "b"])
bit_width: int = Integer(5).bit_length()
real_part: int = Integer(5).real
packed: bytes = Integer(5).to_bytes(2, "big")
unpacked: int = Integer.from_bytes(b"\x01", "big")
float_hex: str = Float(1.5).hex()
upper_bytes: bytes = Bytes(b"a").upper()
decoded: str = Bytes(b"a").decode()
parsed_byte: Bytes = Bytes.decode("0x7f")
view = memoryview(Bytes(b"a"))

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
