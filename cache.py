import math
import random

class CacheWay:
    data: list
    tag: int
    lineSize: int

    def __init__(self, lineSize):
        self.data = [None] * lineSize
        self.tag = None
        self.lineSize = lineSize

    def isInUse(self):
        return self.tag is not None

    def checkTag(self, tag: int) -> bool:
        return self.isInUse() and self.tag == tag

    def setTag(self, tag: int) -> None:
        self.tag = tag

class Cache:

    numSets:int
    numLines: int
    sets: list[list[CacheWay]]

    def __init__(self, numSets: int, numLines: int, lineSize: int):
        # self.sets = [[CacheWay(lineSize)] * numLines] * numSets
        self.sets = [[None] * numLines] * numSets
        self.numSets = numSets
        self.numLines = numLines
        self.lineSize = lineSize

        # ???
        for i in range(self.numSets):
            a = []
            for j in range(self.numLines):
                a.append(CacheWay(self.lineSize))
                # self.sets[i][j] = CacheWay(self.lineSize)
            self.sets[i] = a

    def __parseAddr__(self, addr: int) -> tuple:
        numOffsetBits = math.floor(math.log2(self.lineSize))
        numIndexBits = math.floor(math.log2(self.numSets))
        # TODO: get WORD size
        numTagBits = 16 - numOffsetBits - numIndexBits

        addrBits = bin(addr)[2:].zfill(16)
        tag = int(addrBits[:numTagBits], base=2)
        index = int(addrBits[numTagBits:numTagBits + numIndexBits], base=2)
        offset = int(addrBits[numTagBits + numIndexBits:], base=2)

        return tag, index, offset

    def read(self, addr) -> int:

        tag, index, offset = self.__parseAddr__(addr)

        for i in range(self.numLines):
            if self.sets[index][i].checkTag(tag):
                return self.sets[index][i].data[offset]

        return None

    def write(self, addr, data) -> None:

        tag, index, offset = self.__parseAddr__(addr)

        for i in range(self.numLines):
            if not self.sets[index][i].isInUse():
                self.sets[index][i].setTag(tag)
            if self.sets[index][i].checkTag(tag):
                self.sets[index][i].data[offset] = data
                return

        # cache is full. RR for now
        replaceIndex = random.randrange(self.numLines)
        newEntry = CacheWay(self.lineSize)
        newEntry.data[offset] = data
        self.sets[index][replaceIndex] = newEntry

    def printCache(self) -> None:
        for i in range(len(self.sets)):
            print(i, end=' ')
            for j in range(len(self.sets[i])):
                for a in range(len(self.sets[i][j].data)):
                    print(self.sets[i][j].data[a], end='')
                # print(self.sets[i][j].data)
                print(' ', end='')
            print('')

c = Cache(8, 2, 4)
c.printCache()
c.write(0, 1)
c.write(1, 2)
c.write(3, 1)
c.write(2, 1)
for i in range(100):
    c.write(i, 5)
c.write(0, 1)
c.printCache()
