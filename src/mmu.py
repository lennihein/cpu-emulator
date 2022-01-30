# from cache import CacheRR, CacheLRU, CacheFIFO
from .cache import CacheRR, CacheLRU, CacheFIFO
# from byte import Byte
from .byte import Byte
# from word import Word
from .word import Word


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

    cache_hit_cycles: int
    cache_miss_cycles: int
    write_cycles: int

    memory: list
    mem_size: int
    cache: CacheLRU
    cache_replacement_policy: str

    def __init__(self, mem_size: int = Word.WIDTH, cache_hit_cycles: int = 2,
                 cache_miss_cycles: int = 5, write_cycles: int = 5,
                 cache_config: tuple = (4, 4, 4), replacement_policy="RR"):
        """
        A class representing the memory management unit of a CPU.
        It holds the memory itself as well as a cache.

        Parameters (optional):
            mem_size (int) -- the size of the memory (default = 2**(word size))
            cache_hit_cycles (int) -- the number of cycles it takes to read data
                from the cache (default = 2).
            cache_miss_cycles (int) -- the number of cycles it takes to read data
                from the main memory (default = 5).
            write_cycles (int) -- the number of cycles it takes to complete write
                operations (default = 5).
            cache_config(3tuple) -- the configuration of the cache. The first
                number of the number of sets, then comes the number of ways,
                and, finally, the number of entries per cache way.
                (default = (4, 4, 4))
            replacement_policy (str) -- the replacement policy to be used
                by the cache. Options are: RR (random replacement), LRU (least
                recently used), and FIFO (first-in-first-out). (default = "RR")
        """
        self.memory = [0] * mem_size
        self.mem_size = mem_size

        self.cache_hit_cycles = cache_hit_cycles
        self.cache_miss_cycles = cache_miss_cycles

        self.write_cycles = write_cycles

        if replacement_policy == "RR":
            self.cache = CacheRR(*cache_config)
        elif replacement_policy == "LRU":
            self.cache = CacheLRU(*cache_config)
        elif replacement_policy == "FIFO":
            self.cache = CacheFIFO(*cache_config)

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

    def write_byte(self, index: int, data: Byte) -> int:
        """
        Writes a byte to memory.

        Parameters:
            index (int) -- the memory address to which to write
            data (Byte) -- the Byte to write to this address

        Returns:
            int: The number of cycles it takes to complete the write.
        """

        self.memory[index] = data.value
        self.cache.write(index, data.value)
        return self.write_cycles

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

        return Word(result), max(cycles_lower, cycles_upper)

    def write_word(self, index: int, data: Word) -> int:
        """
        Writes a word to memory. The architecture is assumed to be little-endian.

        Parameters:
            index (int) -- the memory address to which to write
            data (Word) -- the Word to write to this address

        Returns:
            int: The number of cycles it takes to complete the write.
        """

        data = data.value
        data_bits = bin(data)[2:].zfill(Word.WIDTH)

        lower_half = int(data_bits[Word.WIDTH // 2:], base=2)
        upper_half = int(data_bits[:Word.WIDTH // 2], base=2)

        self.write_byte(index, Byte(lower_half))
        self.write_byte(index + 1, Byte(upper_half))
        return self.write_cycles

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


"""
mmu = MMU(1024)
print("Cached?", mmu.is_addr_cached(4))
mmu.write_word(4, Word(-820))
print(mmu.read_word(4))
mmu.flush_addr(5)
print(mmu.read_word(4))
"""
