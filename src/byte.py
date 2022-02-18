from .word import Word


class Byte(Word):

    WIDTH: int = 8

    def __init__(self, value):
        super().__init__(value)
