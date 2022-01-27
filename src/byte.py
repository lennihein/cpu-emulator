class Byte:
    value: int

    def __init__(self, value):
        self.value = value % (1 << 8)
