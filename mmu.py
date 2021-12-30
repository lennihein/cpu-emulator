from cache import Cache
from byte import Byte
from word import Word

class MMU:

    cache_hit_cycles: int = 2
    cache_miss_cycles: int = 5

    memory: list
    mem_size: int
    cache: Cache

    def __init__(self, mem_size: int):
        self.memory = [0] * mem_size
        self.mem_size = mem_size
        self.cache = Cache(4, 4, 4)

    def read_byte(self, index: int) -> tuple[Byte, int]:

        data = self.cache.read(index)
        cycles = self.cache_hit_cycles

        if data is None:
            data = self.memory[index]
            cycles = self.cache_miss_cycles
            self.cache.write(index, data)

        return Byte(data), cycles

    def write_byte(self, index: int, data: Byte) -> None:

        self.memory[index] = data.value
        self.cache.write(index, data.value)

    def read_word(self, index: int) -> tuple[Word, int]:

        # little endian
        lower_half, cycles_lower = self.read_byte(index)
        upper_half, cycles_upper = self.read_byte(index + 1)

        result = (upper_half.value << 8) + lower_half.value

        return result, max(cycles_lower, cycles_upper)

    def write_word(self, index: int, data: Word) -> None:

        data = data.value
        data_bits = bin(data)[2:].zfill(16)

        lower_half = int(data_bits[8:], base=2)
        upper_half = int(data_bits[:8], base=2)

        self.write_byte(index, Byte(lower_half))
        self.write_byte(index + 1, Byte(upper_half))

    def flush(self, index: int) -> None:
        self.cache.flush(index)

mmu = MMU(1024)
mmu.write_word(4, Word(820))
print(mmu.read_word(4))
mmu.flush(5)
print(mmu.read_word(4))
