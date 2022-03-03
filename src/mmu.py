from dataclasses import dataclass
from typing import Union

from .word import Word
from .byte import Byte
from .cache import Cache, CacheFIFO, CacheLRU, CacheRR

import copy


@dataclass
class MemResult:
    """Result of a memory operation."""

    # Value returned by the memory operation
    value: Union[Word, Byte]
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
    cache: Cache
    cache_replacement_policy: str

    def __init__(
        self,
        mem_size: int = 1 << Word.WIDTH,
        cache_hit_cycles: int = 2,
        cache_miss_cycles: int = 5,
        num_write_cycles: int = 5,
        num_fault_cycles: int = 8,
        cache_config: tuple = (4, 4, 4),
        replacement_policy="LRU",
    ):
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

        # We assume the upper half of the address space is inaccessible
        for i in range(self.mem_size // 2, self.mem_size):
            self.memory[i] = 42

        self.cache_hit_cycles = cache_hit_cycles
        self.cache_miss_cycles = cache_miss_cycles

        self.num_write_cycles = num_write_cycles
        self.num_fault_cycles = num_fault_cycles

        self.cache_replacement_policy = replacement_policy

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
            address (Word) -- the memory address from which to read

        Returns:
            MemResult: Class containing the results of the memory
                operation.
        """

        data = self.cache.read(address.value)
        cycles = self.cache_hit_cycles

        if data is None:
            data = self.memory[address.value]
            cycles = self.cache_miss_cycles
            self._load_line(address)

        # Notice this check is done after the data was already read from
        # memory and written to the cache. Doing so and returning the data
        # to the execution even though the address should be inaccessible
        # is precisely what enables the meltdown vulnerability.
        fault = self.is_illegal_access(address)

        return MemResult(Byte(data), fault, cycles, self.num_fault_cycles)

    def write_byte(self, address: Word, data: Byte) -> MemResult:
        """
        Writes a byte to memory.

        Parameters:
            address (Word) -- the memory address to which to write
            data (Byte) -- the Byte to write to this address

        Returns:
            This function does not have a return value.
        """

        # value = data.value % 256
        value = data.value
        self.memory[address.value] = value

        self._load_line(address)

        # See self.read_byte() for comments on this check.
        fault = self.is_illegal_access(address)

        return MemResult(Byte(0), fault, self.num_write_cycles, self.num_fault_cycles)

    def read_word(self, address: Word) -> MemResult:
        """
        Reads one word from memory and returns it along with
        the number of cycles it takes to load it.
        The architecture is assumed to be little-endian.

        Parameters:
            address (Word) -- the memory address from which to read

        Returns:
            MemResult: Class containing the results of the memory
                operation.
        """

        # Read individual bytes
        bytes_read = []
        fault = False
        cycles_value = 0
        cycles_fault = 0
        for i in range(Word.WIDTH_BYTES):
            byte = self.read_byte(address + Word(i))
            assert isinstance(byte.value, Byte)

            bytes_read.append(byte.value)
            if byte.fault:
                fault = True
            cycles_value = max(cycles_value, byte.cycles_value)
            cycles_fault = max(cycles_fault, byte.cycles_fault)

        return MemResult(Word.from_bytes(bytes_read), fault, cycles_value, cycles_fault)

    def edit_word(self, address: Word, data: Word) -> None:
        """
        Edits a word in memory WITHOUT affecting the cache.
        The architecture is assumed to be little-endian.

        Parameters:
            address (Word) -- the memory address to which to edit
            data (Word) -- the Word the address shall be overwritten with

        Returns:
            This function does not have a return value.
        """

        # Write individual bytes
        for i, byte in enumerate(data.as_bytes()):
            self.edit_byte(address + Word(i), byte)

    def edit_byte(self, address: Word, data: Byte) -> None:
        """
        Edits a byte in memory WITHOUT affecting the cache.

        Parameters:
            address (Word) -- the memory address to which to edit
            data (Byte) -- the Byte the address shall be overwritten with

        Returns:
            This function does not have a return value.
        """

        # value = data.value % 256
        value = data.value
        self.memory[address.value] = value

    def write_word(self, address: Word, data: Word) -> MemResult:
        """
        Writes a word to memory. The architecture is assumed to be little-endian.

        Parameters:
            address (Word) -- the memory address to which to write
            data (Word) -- the Word to write to this address

        Returns:
            This function does not have a return value.
        """

        # Write individual bytes
        fault = False
        cycles_value = 0
        cycles_fault = 0
        for i, byte in enumerate(data.as_bytes()):
            result = self.write_byte(address + Word(i), byte)

            if result.fault:
                fault = True
            cycles_value = max(cycles_value, result.cycles_value)
            cycles_fault = max(cycles_fault, result.cycles_fault)

        return MemResult(Word(0), fault, cycles_value, cycles_fault)

    def _load_line(self, address: Word) -> None:
        """
        Loads the entire cache line corresponding to 'addr'
        into the cache. Note that 'addr' needs to be any
        address within the cache line, it does not need
        to be the first one with offset = 0.

        Parameters:
            addr (Word) -- the address to be loaded

        Returns:
            This function does not have a return value.
        """
        addr = address.value
        tag, index, offset = self.cache.parse_addr(addr)
        base_addr = addr - offset

        for i in range(self.cache.line_size):
            current_addr = base_addr + i
            self.cache.write(current_addr, self.memory[current_addr])

    def flush_line(self, address: Word) -> MemResult:
        """
        Flushes an address from the cache.

        Parameters:
            address (Word) -- the memory address to which to write

        Returns:
            This function does not have a return value.
        """
        self.cache.flush(address.value)
        return MemResult(Word(0), False, self.num_write_cycles, self.num_fault_cycles)

    def flush_all(self) -> None:
        """
        Flushes the entire cache.

        Returns:
            This function does not have a return value.
        """
        i = 0
        while i < self.mem_size:
            self.flush_line(Word(i))
            i += self.cache.line_size

    def is_addr_cached(self, address: Word) -> bool:
        """
        Returns whether the data at an address is cached.

        Parameters:
            address (Word) -- the memory address of the data

        Returns:
            bool: True if data at address is cached
        """
        return self.cache.read(address.value) is not None

    def write_cycles(self) -> int:
        """
        Returns the number of cycles needed to write to memory.
        """
        return self.num_write_cycles

    def is_illegal_access(self, address: Word) -> bool:
        """
        Returns whether an acess to address is illegal.

        Parameters:
            address (Word) -- the memory address

        Returns:
            bool: True if access would raise a fault
        """
        return address.value >= self.mem_size // 2

    def deepcopy(self):
        """
        Returns a deepcopy of the MMU.
        """
        mmu_copy = MMU(
            self.mem_size,
            self.cache_hit_cycles,
            self.cache_miss_cycles,
            self.num_write_cycles,
            self.num_fault_cycles,
            (self.cache.num_sets, self.cache.num_lines, self.cache.line_size),
            self.cache_replacement_policy
        )

        mmu_copy.memory = copy.copy(self.memory)
        mmu_copy.cache = self.cache.deepcopy()

        return mmu_copy
