class Word:
    WIDTH: int = 16
    value: int

    def __init__(self, value: int):
        self.value = value % (1 << self.WIDTH)

    @classmethod
    def from_int(cls, value: int):
        return cls(value)

    @classmethod
    def from_bytes(cls, b: bytes[2]):
        ...

    # careful: operations on differently sized ints results in an object of the lhs type
    # also, we have no idea what happens if you use bitwise operations on a Word and a Byte

    def __add__(self, rhs: "Word"):
        return self.from_int(self.value + rhs.value)

    def __sub__(self, rhs: "Word"):
        return Word(self.value - rhs.value)

    def __lshift__(self, rhs: "Word"):
        return Word(self.value << rhs.value)

    def __rshift__(self, rhs: "Word"):
        return Word(self.value >> rhs.value)

    def __and__(self, rhs: "Word"):
        return Word(self.value & rhs.value)

    def __or__(self, rhs: "Word"):
        return Word(self.value | rhs.value)

    def __xor__(self, rhs: "Word"):
        return Word(self.value ^ rhs.value)

    def __invert__(self):
        return Word(~self.value)

    def __eq__(self, rhs: "Word"):
        return self.value == rhs.value

    def __ne__(self, rhs: "Word"):
        return self.value != rhs.value
