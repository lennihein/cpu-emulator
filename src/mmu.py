from dataclasses import dataclass

from .cache import CacheRR, CacheLRU, CacheFIFO
from .word import Word
from .byte import Byte

@dataclass
class MemResult:
    """Result of a memory operation."""

    # Value returned by the memory operation
    value: Word
    # Whether the operation causes a fault
    fault: bool
    # Number of cycles we wait before returning the value
    cycles_value: int
    # Number of cycles we wait before signaling whether we fault, after we returned the value
    cycles_fault: int

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
    num_write_cycles: int
    num_fault_cycles: int

    memory: list
    mem_size: int
    cache: CacheLRU
    cache_replacement_policy: str

    def __init__(self, mem_size: int = 1 << Word.WIDTH, cache_hit_cycles: int = 2,
                 cache_miss_cycles: int = 5, num_write_cycles: int = 5,
                 num_fault_cycles: int = 8, cache_config: tuple = (4, 4, 4),
                 replacement_policy="RR"):
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

        self.num_write_cycles = num_write_cycles
        self.num_fault_cycles = num_fault_cycles

        if replacement_policy == "RR":
            self.cache = CacheRR(*cache_config)
        elif replacement_policy == "LRU":
            self.cache = CacheLRU(*cache_config)
        elif replacement_policy == "FIFO":
            self.cache = CacheFIFO(*cache_config)

    def read_byte(self, address: Word) -> MemResult:
        """
        Reads one byte from memory and returns it along with
        the number of cycles it takes to load it.

        Parameters:
            address (int) -- the memory address from which to read

        Returns:
            MemResult: Class containing the results of the memory
                operation.
        """

        data = self.cache.read(address)
        cycles = self.cache_hit_cycles

        if data is None:
            data = self.memory[address]
            cycles = self.cache_miss_cycles
            self.cache.write(address, data)

        return MemResult(Byte(data), False, cycles,
                         self.num_fault_cycles)

    def write_byte(self, address: Word, data: Byte) -> None:
        """
        Writes a byte to memory.

        Parameters:
            address (int) -- the memory address to which to write
            data (Byte) -- the Byte to write to this address

        Returns:
            This function does not have a return value.
        """

        # value = data._value % (1 << 8)

        self.memory[address] = data.value
        self.cache.write(address, data.value)

    def read_word(self, address: Word) -> MemResult:
        """
        Reads one word from memory and returns it along with
        the number of cycles it takes to load it.
        The architecture is assumed to be little-endian.

        Parameters:
            address (int) -- the memory address from which to read

        Returns:
            MemResult: Class containing the results of the memory
                operation.
        """

        # little endian
        lower_half_result = self.read_byte(address)
        lower_half = lower_half_result.value.value
        cycles_lower = lower_half_result.cycles_value

        upper_half_result = self.read_byte(address + 1)
        upper_half = upper_half_result.value.value
        cycles_upper = upper_half_result.cycles_value

        result = (upper_half << (Word.WIDTH // 2)) + lower_half

        return MemResult(Word(result), False,
                         max(cycles_lower, cycles_upper),
                         self.num_fault_cycles)

    def write_word(self, address: Word, data: Word) -> None:
        """
        Writes a word to memory. The architecture is assumed to be little-endian.

        Parameters:
            address (int) -- the memory address to which to write
            data (Word) -- the Word to write to this address

        Returns:
            This function does not have a return value.
        """

        data = data.value
        data_bits = bin(data)[2:].zfill(Word.WIDTH)

        lower_half = int(data_bits[Word.WIDTH // 2:], base=2)
        upper_half = int(data_bits[:Word.WIDTH // 2], base=2)

        self.write_byte(address, Byte(lower_half))
        self.write_byte(address + 1, Byte(upper_half))

    def flush_line(self, address: Word) -> None:
        """
        Flushes an address from the cache.

        Parameters:
            address (int) -- the memory address to which to write

        Returns:
            This function does not have a return value.
        """
        self.cache.flush(address)

    def is_addr_cached(self, address: Word) -> bool:
        """
        Returns whether the data at an address is cached.

        Parameters:
            address (int) -- the memory address of the data

        Returns:
            bool: True if data at address is cached
        """
        return self.cache.read(address) is not None

    def write_cycles(self) -> int:
        """
        Returns the number of cycles needed to write to memory.
        """
        return self.num_write_cycles
