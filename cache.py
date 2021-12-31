import math
import random
from time import time
from word import Word

class CacheLine:
    """
    A helper class representing a cache line in a cache.

    It may be used if no additional data is needed to
    implement the cache replacement policy. An example of
    this is the random replacement policy.

    If additional information, such as the last time of
    access, is needed by the replacement policy, this
    class should be extended accordingly.
    """
    data: list
    tag: int
    line_size: int

    def __init__(self, line_size: int):
        self.data = [None] * line_size
        self.tag = None
        self.line_size = line_size

    def isInUse(self):
        """
        Returns true if the current cache line is
        in use by checking if the tag is set.
        """
        return self.tag is not None

    def checkTag(self, tag: int) -> bool:
        """
        Returns if the given tag matches this cache
        line's tag.

        Parameters:
            tag (int) -- the tag to compare

        Returns:
            bool: True if the cache line's tag matches
        """
        return self.isInUse() and self.tag == tag

    def setTag(self, tag: int) -> None:
        """
        Sets the cache line's tag.

        Parameters:
            tag (int) -- the new tag

        Returns:
            This function does not have a return value.
        """
        self.tag = tag

    def clearData(self) -> None:
        """
        Removes all data of this cache line and clears
        the tag.
        """
        for i in range(self.line_size):
            self.data[i] = None

        self.setTag(None)

    def read(self, offset: int) -> int:
        """
        Reads from the cache line at index 'offset'.
        Note that this function does NOT check for
        any tags.

        Parameters:
            offset (int) -- the offset at which to read

        Returns:
            int: The data saved at 'offset'.
            Returns 'None' if no data is present.
        """
        return self.data[offset]

    def write(self, offset: int, data: int) -> None:
        """
        Writes data to the cache line at index 'offset'.

        Parameters:
            offset (int) -- the offset to which to write
            data (int)   -- the data to write

        Returns:
            This function does not have a return value.
        """
        if data is None: return
        self.data[offset] = data

    def flush(self, offset: int) -> None:
        """
        Flushes the data written at the index 'offset'.
        This means that further reads to this index
        return 'None'.

        If no more data is saved in this cache line,
        the tag will be cleared as well.

        Parameters:
            offset (int) -- the offset at which to flush

        Returns:
            This function does not have a return value.
        """
        self.data[offset] = None

        # clear tag if no more data is stored in this line
        for i in range(self.line_size):
            if self.data[i] is not None:
                return

        self.setTag(None)

class Cache:
    """
    An abstract class implementing a cache. Using this class directly is not possible, as it
    does not implement any cache replacement policies.

    Instead, use any of the following classes: CacheRR, CacheLRU, CacheFIFO
    """

    num_sets:int
    num_lines: int
    sets: list[list[CacheLine]]

    def __init__(self, num_sets: int, num_lines: int, line_size: int):
        self.sets = [[CacheLine(line_size) for a in range(num_lines)] for b in range(num_sets)]
        self.num_sets = num_sets
        self.num_lines = num_lines
        self.line_size = line_size

    def __parseAddr__(self, addr: int) -> tuple[int, int, int]:
        """
        Parses the given address and returns a 3-tuple consisting of
        tag, index, and offset to access the cache.

        Parameters:
            addr (int) -- the address to parse

        Returns:
            tuple[int, int, int]: tag, index, offset
        """
        num_offset_bits = math.floor(math.log2(self.line_size))
        num_index_bits = math.floor(math.log2(self.num_sets))
        num_tag_bits = Word.WIDTH - num_offset_bits - num_index_bits

        addr_bits = bin(addr)[2:].zfill(Word.WIDTH)
        tag = int(addr_bits[:num_tag_bits], base=2)
        index = int(addr_bits[num_tag_bits:num_tag_bits + num_index_bits], base=2)
        offset = int(addr_bits[num_tag_bits + num_index_bits:], base=2)

        return tag, index, offset

    def __applyReplacementPolicy__(self, addr: int, data: int) -> None:
        """
        Applies the corresponding replacement policy by choosing a cache line that
        is to be replaced.
        When called, all cache lines of a cache set must be already in use.

        Parameters:
            addr (int) -- the full address of the new cache line's entries.
                          Note that the offset does not matter.
            data (int) -- the data to be saved in the cache line.

        Returns:
            This function does not have a return value.
        """
        raise Exception("Cache Replacement Policy not implemented.")

    def read(self, addr: int) -> int:
        """
        Returns the data at address addr as an integer.
        If no data is cached for this address, None is returned.

        Parameters:
            addr (int) -- the address from which to read

        Returns:
            int: The cached data.
            Returns 'None' if 'addr' is not cached.
        """

        tag, index, offset = self.__parseAddr__(addr)

        for i in range(self.num_lines):
            if self.sets[index][i].checkTag(tag):
                return self.sets[index][i].read(offset)

        return None

    def write(self, addr: int, data: int) -> None:
        """
        Adds 'data' to the cache, indexed by 'addr'.
        If required, the replacement policy is applied.

        Parameters:
            addr (int) -- the address to which to write
            data (int) -- the data to cache

        Returns:
            This function does not have a return value.
        """
        tag, index, offset = self.__parseAddr__(addr)

        # check if all cache lines of the corresponding cache
        # set are already in use.
        for i in range(self.num_lines):
            if not self.sets[index][i].isInUse():
                self.sets[index][i].setTag(tag)
            if self.sets[index][i].checkTag(tag):
                self.sets[index][i].write(offset, data)
                return

        # apply replacement policy of all cache lines are in use
        self.__applyReplacementPolicy__(addr, data)

    def flush(self, addr: int) -> None:
        """
        Removes the data indexed by 'addr' from the cache.

        Parameters:
            addr (int) -- the address to be flushed from the cache

        Returns:
            This function does not have a return value.
        """

        tag, index, offset = self.__parseAddr__(addr)

        for i in range(self.num_lines):
            if self.sets[index][i].checkTag(tag):
                self.sets[index][i].flush(offset)
                return

    def printCache(self) -> None:
        """Prints the cache. Only to be used during development."""
        for i in range(len(self.sets)):
            print(i, end=' ')
            for j in range(len(self.sets[i])):
                if self.sets[i][j].isInUse():
                    print("*", end='')
                for a in range(len(self.sets[i][j].data)):
                    print(self.sets[i][j].data[a], end='')
                # print(self.sets[i][j].data)
                print(' ', end='')
            print('')

class CacheRR(Cache):
    """A cache implementing the random replacement policy."""

    def __init__(self, num_sets: int, num_lines: int, line_size: int):
        super().__init__(num_sets, num_lines, line_size)

    def __applyReplacementPolicy__(self, addr: int, data: int):
        tag, index, offset = self.__parseAddr__(addr)

        replaceIndex = random.randrange(self.num_lines)
        self.sets[index][replaceIndex].clearData()
        self.sets[index][replaceIndex].setTag(tag)
        self.sets[index][replaceIndex].write(offset, data)


class CacheLineLRU(CacheLine):
    """
    A helper class representing a cache line in a cache that
    implements the least-recently-used replacement policy.
    """

    # update this variable each time we read/write.
    lru_timestamp: float

    def __init__(self, line_size: int):
        super().__init__(line_size)
        self.lru_timestamp = time()

    def read(self, offset: int) -> int:
        data = super().read(offset)
        if data is not None:
            self.lru_timestamp = time()
        return data

    def write(self, offset, data: int) -> None:
        super().write(offset, data)
        self.lru_timestamp = time()

    def getLRUTime(self):
        return self.lru_timestamp

    # Should flushing count as an access to a cache line?
    # If not, remove the following method:
    def flush(self, offset: int) -> None:
        super().flush(offset)
        self.lru_timestamp = time()

class CacheLRU(Cache):
    """A cache implementing the least-recently-used replacement policy."""

    def __init__(self, num_sets: int, num_lines: int, line_size: int):
        super().__init__(num_sets, num_lines, line_size)
        self.sets = [[CacheLineLRU(line_size) for a in range(num_lines)] for b in range(num_sets)]

    def __applyReplacementPolicy__(self, addr: int, data: int):
        """
        Implements a least-recently-used policy by using the lru_timestamp variable
        from CacheLineLRU.
        """

        tag, index, offset = self.__parseAddr__(addr)

        lru_index = 0
        lru_time = self.sets[index][0].getLRUTime()
        for i in range(self.line_size):
            if self.sets[index][i].getLRUTime() < lru_time:
                lru_index = i
                lru_time = self.sets[index][i].getLRUTime()

        self.sets[index][lru_index].clearData()
        self.sets[index][lru_index].setTag(tag)
        self.sets[index][lru_index].write(offset, data)

class CacheLineFIFO(CacheLine):
    """
    A helper class representing a cache line in a cache that
    implements the first-in-first-out replacement policy.
    """

    # update this variable on the first write/on initialization.
    first_write: float

    def __init__(self, line_size: int):
        super().__init__(line_size)
        self.first_write = time()

    def write(self, offset: int, data: int) -> None:
        empty = True
        for i in range(self.line_size):
            if self.data[i] is not None:
                empty = False
                break

        if empty:
            self.first_write = time()

        super().write(offset, data)

    def getFIFOTime(self):
        return self.first_write

class CacheFIFO(Cache):
    """A Cache implementing the first-in-first-out replacement policy."""

    def __init__(self, num_sets: int, num_lines: int, line_size: int):
        super().__init__(num_sets, num_lines, line_size)
        self.sets = [[CacheLineFIFO(line_size) for a in range(num_lines)] for b in range(num_sets)]

    def __applyReplacementPolicy__(self, addr: int, data: int):
        """
        Implements a least-recently-used policy by using the first_write variable
        from CacheLineFIFO.
        """

        tag, index, offset = self.__parseAddr__(addr)

        fifo_index = 0
        fifo_time = self.sets[index][0].getFIFOTime()
        for i in range(self.line_size):
            if self.sets[index][i].getFIFOTime() < fifo_time:
                fifo_index = i
                fifo_time = self.sets[index][i].getFIFOTime()

        self.sets[index][fifo_index].clearData()
        self.sets[index][fifo_index].setTag(tag)
        self.sets[index][fifo_index].write(offset, data)

"""
c = CacheFIFO(2, 2, 2)
c.write(40, 40)
c.write(0, 1)
c.printCache()
c.write(100, 99)
c.write(0, 1)
c.printCache()
"""
