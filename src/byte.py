from .word import Word

class Byte(Word):

    def __init__(self, value):
        super().__init__(value)
        self._value = value % (1 << 8)
