import math
import random
from time import time

class CacheLine:
    data: list
    tag: int
    line_size: int

    def __init__(self, line_size: int):
        self.data = [None] * line_size
        self.tag = None
        self.line_size = line_size

    def isInUse(self):
        return self.tag is not None

    def checkTag(self, tag: int) -> bool:
        return self.isInUse() and self.tag == tag

    def setTag(self, tag: int) -> None:
        self.tag = tag

    def clearData(self) -> None:
        for i in range(self.line_size):
            self.data[i] = None

        self.setTag(None)

    def read(self, offset: int) -> int:
        return self.data[offset]

    def write(self, offset: int, data: int) -> None:
        if data is None: return
        self.data[offset] = data

    def flush(self, offset: int) -> None:
        self.data[offset] = None

        # clear tag if no more data is stored in this line
        for i in range(self.line_size):
            if self.data[i] is not None:
                return

        self.setTag(None)

class Cache:

    num_sets:int
    num_lines: int
    sets: list[list[CacheLine]]

    def __init__(self, num_sets: int, num_lines: int, line_size: int):
        self.sets = [[CacheLine(line_size) for a in range(num_lines)] for b in range(num_sets)]
        self.num_sets = num_sets
        self.num_lines = num_lines
        self.line_size = line_size

    def __parseAddr__(self, addr: int) -> tuple:
        num_offset_bits = math.floor(math.log2(self.line_size))
        num_index_bits = math.floor(math.log2(self.num_sets))
        num_tag_bits = 16 - num_offset_bits - num_index_bits

        addr_bits = bin(addr)[2:].zfill(16)
        tag = int(addr_bits[:num_tag_bits], base=2)
        index = int(addr_bits[num_tag_bits:num_tag_bits + num_index_bits], base=2)
        offset = int(addr_bits[num_tag_bits + num_index_bits:], base=2)

        return tag, index, offset

    def __applyReplacementPolicy__(self, addr: int, data: int) -> None:
        raise Exception("Cache Replacement Policy not implemented.")

    def read(self, addr) -> int:

        tag, index, offset = self.__parseAddr__(addr)

        for i in range(self.num_lines):
            if self.sets[index][i].checkTag(tag):
                return self.sets[index][i].read(offset)

        return None

    def write(self, addr: int, data: int) -> None:

        tag, index, offset = self.__parseAddr__(addr)
        print('T', tag, "i", index, 'o', offset)

        for i in range(self.num_lines):
            if not self.sets[index][i].isInUse():
                self.sets[index][i].setTag(tag)
            if self.sets[index][i].checkTag(tag):
                self.sets[index][i].write(offset, data)
                return

        self.__applyReplacementPolicy__(addr, data)

    def flush(self, addr: int) -> None:

        tag, index, offset = self.__parseAddr__(addr)

        for i in range(self.num_lines):
            if self.sets[index][i].checkTag(tag):
                self.sets[index][i].flush(offset)
                return

    def printCache(self) -> None:
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

    def __init__(self, num_sets: int, num_lines: int, line_size: int):
        super().__init__(num_sets, num_lines, line_size)

    def __applyReplacementPolicy__(self, addr: int, data: int):
        tag, index, offset = self.__parseAddr__(addr)

        replaceIndex = random.randrange(self.num_lines)
        self.sets[index][replaceIndex].clearData()
        self.sets[index][replaceIndex].setTag(tag)
        self.sets[index][replaceIndex].write(offset, data)


class CacheLineLRU(CacheLine):

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

class CacheLRU(Cache):

    def __init__(self, num_sets: int, num_lines: int, line_size: int):
        super().__init__(num_sets, num_lines, line_size)
        self.sets = [[CacheLineLRU(line_size) for a in range(num_lines)] for b in range(num_sets)]

    def __applyReplacementPolicy__(self, addr: int, data: int):

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

    first_write: float

    def __init__(self, line_size: int):
        super().__init__(line_size)

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

    def __init__(self, num_sets: int, num_lines: int, line_size: int):
        super().__init__(num_sets, num_lines, line_size)
        self.sets = [[CacheLineFIFO(line_size) for a in range(num_lines)] for b in range(num_sets)]

    def __applyReplacementPolicy__(self, addr: int, data: int):

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


c = CacheFIFO(2, 2, 2)
c.write(40, 40)
c.write(0, 1)
c.printCache()
c.write(100, 99)
c.write(0, 1)
c.printCache()
