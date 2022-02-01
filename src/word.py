from typing import Sequence


class Word:
    WIDTH: int = 16

    # Always positive
    _value: int

    def __init__(self, value: int):
        self._value = value % (1 << self.WIDTH)

    @classmethod
    def from_bytes(cls, b: Sequence[int]) -> "Word":
        if len(b) != 2:
            raise ValueError(f"Invalid number of bytes: {b:r}")
        return Word(b[0] + b[1] * 0x100)

    @property
    def value(self):
        return self._value

    def __eq__(self, rhs: object) -> bool:
        if not isinstance(rhs, Word):
            return False
        return self.value == rhs.value

    def __ne__(self, rhs: object) -> bool:
        return not self == rhs

    def __add__(self, rhs: "Word") -> "Word":
        return Word(self.value + rhs.value)

    def __sub__(self, rhs: "Word") -> "Word":
        return Word(self.value - rhs.value)

    def __lshift__(self, rhs: "Word") -> "Word":
        return Word(self.value << rhs.value)

    def __and__(self, rhs: "Word") -> "Word":
        return Word(self.value & rhs.value)

    def __or__(self, rhs: "Word") -> "Word":
        return Word(self.value | rhs.value)

    def __xor__(self, rhs: "Word") -> "Word":
        return Word(self.value ^ rhs.value)

    def __invert__(self) -> "Word":
        return Word(~self.value)

    def __repr__(self) -> str:
        fmt = "Word({:#0" + str(self.WIDTH // 4 + 2) + "x})"
        return fmt.format(self.value)

    def signed_value(self) -> int:
        if self.value < (1 << (self.WIDTH - 1)):
            return self.value
        return self.value - (1 << self.WIDTH)

    def as_bytes(self) -> bytes:
        """Return the bytes used to represent this value in memory."""
        return bytes((self.value >> i) & 0xFF for i in range(0, self.WIDTH, 8))

    def shift_right_logical(self, amount: int) -> "Word":
        return Word(self.value >> amount)

    def shift_right_arithmetic(self, amount: int) -> "Word":
        return Word(self.signed_value() >> amount)

    def unsigned_lt(self, rhs: "Word") -> bool:
        return self.value < rhs.value

    def unsigned_le(self, rhs: "Word") -> bool:
        return self.value <= rhs.value

    def unsigned_gt(self, rhs: "Word") -> bool:
        return self.value > rhs.value

    def unsigned_ge(self, rhs: "Word") -> bool:
        return self.value >= rhs.value

    def signed_lt(self, rhs: "Word") -> bool:
        return self.signed_value() < rhs.signed_value()

    def signed_le(self, rhs: "Word") -> bool:
        return self.signed_value() <= rhs.signed_value()

    def signed_gt(self, rhs: "Word") -> bool:
        return self.signed_value() > rhs.signed_value()

    def signed_ge(self, rhs: "Word") -> bool:
        return self.signed_value() >= rhs.signed_value()
