"""Every documented constant and method exists on its type."""
import pytest

from primitives import Boolean, Bytes, Float, Integer, String

OBJECT = "equals hashCode toString getClass"

MEMBERS = {
    Integer: f"""
        BYTES MAX_VALUE MIN_VALUE SIZE TYPE
        bitCount byteValue compare compareTo compareUnsigned compress decode divideUnsigned
        doubleValue expand floatValue getInteger highestOneBit intValue longValue lowestOneBit
        max min numberOfLeadingZeros numberOfTrailingZeros parseInt parseUnsignedInt
        remainderUnsigned reverse reverseBytes rotateLeft rotateRight shortValue signum sum
        toBinaryString toHexString toOctalString toUnsignedLong toUnsignedString valueOf {OBJECT}
    """,
    Float: f"""
        BYTES MAX_EXPONENT MAX_VALUE MIN_EXPONENT MIN_NORMAL MIN_VALUE NaN NEGATIVE_INFINITY
        POSITIVE_INFINITY PRECISION SIZE TYPE
        byteValue compare compareTo doubleValue float16ToFloat floatToFloat16 floatToIntBits
        floatToRawIntBits floatValue intBitsToFloat intValue isFinite isInfinite isNaN longValue
        max min parseFloat shortValue sum toHexString valueOf {OBJECT}
    """,
    String: f"""
        CASE_INSENSITIVE_ORDER
        charAt chars codePointAt codePointBefore codePointCount codePoints compareTo
        compareToIgnoreCase concat contains contentEquals copyValueOf endsWith equalsIgnoreCase
        format formatted getBytes getChars indent indexOf intern isBlank isEmpty join lastIndexOf
        length lines matches offsetByCodePoints regionMatches repeat replace replaceAll
        replaceFirst split splitWithDelimiters startsWith strip stripIndent stripLeading
        stripTrailing subSequence substring toCharArray toLowerCase toUpperCase transform
        translateEscapes trim valueOf {OBJECT}
    """,
    Boolean: f"""
        FALSE TRUE TYPE
        booleanValue compare compareTo getBoolean logicalAnd logicalOr logicalXor parseBoolean
        valueOf {OBJECT}
    """,
    Bytes: f"""
        BYTES MAX_VALUE MIN_VALUE SIZE TYPE
        byteValue compare compareTo compareUnsigned decode doubleValue floatValue intValue
        longValue parseByte shortValue toUnsignedInt toUnsignedLong valueOf {OBJECT}
    """,
}

CASES = [(cls, name) for cls, names in MEMBERS.items() for name in names.split()]


@pytest.mark.parametrize("cls, name", CASES, ids=[f"{c.__name__}.{n}" for c, n in CASES])
def test_member_exists(cls, name):
    assert hasattr(cls, name)


@pytest.mark.parametrize("cls", list(MEMBERS))
def test_instances_stay_slotted(cls):
    assert not hasattr(cls(), "__dict__")


@pytest.mark.parametrize("cls", list(MEMBERS))
def test_static_members_do_not_break_attribute_lookup_on_null(cls):
    assert hasattr(cls(), "hashCode") and hasattr(cls(), "toString")
    with pytest.raises(TypeError):
        cls().hashCode()
