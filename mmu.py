from cache import CacheRR, CacheLRU, CacheFIFO
from byte import Byte
from word import Word

class MMU:
    """
    The memory management unit (MMU).

    In our model, the MMU includes the main memory and
    cache. Contrary  to the Skylake architecture, our
    MMU does not contain load- and store-buffers, and
    for the sake of simplicity, there is one cache only.
    Therefore, whether our cache is an L3 or L1 cache
    does not matter.
    """

    cache_hit_cycles: int = 2
    cache_miss_cycles: int = 5

    memory: list
    mem_size: int
    cache: CacheRR

    def __init__(self, mem_size: int):
        self.memory = [0] * mem_size
        self.mem_size = mem_size
        self.cache = CacheRR(4, 4, 4)

    def read_byte(self, index: int) -> tuple[Byte, int]:
        """
        Reads one byte from memory and returns it along with
        the number of cycles it takes to load it.

        Parameters:
            index (int) -- the memory address from which to read

        Returns:
            tuple[Byte, int]: Byte class that contains
            data and the number of cycles needed to load it.
        """
        data = self.cache.read(index)
        cycles = self.cache_hit_cycles

        if data is None:
            data = self.memory[index]
            cycles = self.cache_miss_cycles
            self.cache.write(index, data)

        return Byte(data), cycles


    def write_byte(self, index: int, data: Byte) -> None:
        """
        Writes a byte to memory.

        Parameters:
            index (int) -- the memory address to which to write
            data (Byte) -- the Byte to write to this address

        Returns:
            This function does not have a return value.
        """

        self.memory[index] = data.value
        self.cache.write(index, data.value)

    def read_word(self, index: int) -> tuple[Word, int]:
        """
        Reads one word from memory and returns it along with
        the number of cycles it takes to load it.
        The architecture is assumed to be little-endian.

        Parameters:
            index (int) -- the memory address from which to read

        Returns:
            tuple[Word, int]: Word class that contains the
            data and the number of cycles needed to laod it.
        """

        # little endian
        lower_half, cycles_lower = self.read_byte(index)
        upper_half, cycles_upper = self.read_byte(index + 1)

        result = (upper_half.value << (Word.WIDTH // 2)) + lower_half.value

        return result, max(cycles_lower, cycles_upper)

    def write_word(self, index: int, data: Word) -> None:
        """
        Writes a word to memory. The architecture is assumed to be little-endian.

        Parameters:
            index (int) -- the memory address to which to write
            data (Word) -- the Word to write to this address

        Returns:
            This function does not have a return value.
        """

        data = data.value
        data_bits = bin(data)[2:].zfill(Word.WIDTH)

        lower_half = int(data_bits[Word.WIDTH // 2:], base=2)
        upper_half = int(data_bits[:Word.WIDTH // 2], base=2)

        self.write_byte(index, Byte(lower_half))
        self.write_byte(index + 1, Byte(upper_half))

    def flush_addr(self, index: int) -> None:
        """
        Flushes an address from the cache.

        Parameters:
            index (int) -- the memory address to which to write

        Returns:
            This function does not have a return value.
        """
        self.cache.flush(index)

    def is_addr_cached(self, index: int) -> bool:
        """
        Returns whether the data at an address is cached.

        Parameters:
            index (int) -- the memory address of the data

        Returns:
            bool: True if data at address is cached
        """
        return self.read_byte(index)[1] == self.cache_hit_cycles

mmu = MMU(1024)
print("Cached?", mmu.is_addr_cached(4))
mmu.write_word(4, Word(820))
print(mmu.read_word(4))
print("Cached?", mmu.is_addr_cached(4))
mmu.flush_addr(5)
print("Cached?", mmu.is_addr_cached(5))
print(mmu.read_word(4))
