"""A byte in the range from 0 to 255."""

# Import whole module instead of just `Word` to prevent circular import, because `word` imports
# `byte`
from . import word


class Byte:
    """
    A byte in the range from 0 to 255.

    The memory contents are made up of individual bytes. Instructions always operate one whole
    `Word`s instead.
    """

    # Width in bits
    WIDTH: int = 8

    # Always in range [0, 255]
    _value: int

    def __init__(self, value: int):
        """Create a new byte from the given unsigned or two's complement signed value."""
        self._value = value % (1 << self.WIDTH)

    @property
    def value(self) -> int:
        """Return this value as an unsigned integer."""
        return self._value

    def zero_extend(self) -> "word.Word":
        """Zero-extend this byte to the width of a word."""
        return word.Word(self.value)
