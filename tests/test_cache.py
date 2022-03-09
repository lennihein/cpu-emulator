import unittest
from src import cache


class CacheTests(unittest.TestCase):

    def test_lru(self):
        """
        This cache replacement policy is deterministic and can therefore
        be tested easily. With a cache consisting of 4 sets with 2 lines
        per set, and a line size of 2, we can cache the addresses 0 and
        9, which both go into set 0. Now, caching address 17 is not possible
        without applying the cache replacement policy, as both cache lines
        in set 0 are in use. Since 9 is the address we accessed the longest
        time ago, its cache line is replaced.
        """
        c = cache.CacheLRU(4, 2, 2)
        c.write(0, 0)
        c.write(9, 9)
        c.read(0)
        c.write(17, 17)

        # Now we expect addresses 0 and 17 to be cached.
        self.assertIs(c.read(0), 0)
        self.assertIs(c.read(9), None)
        self.assertIs(c.read(17), 17)

        # If we do not read from address 0, it is going to be evicted
        # from the cache instead.
        c = cache.CacheLRU(4, 2, 2)
        c.write(0, 0)
        c.write(9, 9)
        c.write(17, 17)

        # Now we expect addresses 9 and 17 to be cached.
        self.assertIs(c.read(0), None)
        self.assertIs(c.read(9), 9)
        self.assertIs(c.read(17), 17)

        for i in range(40):
            c.write(i, i)

    def test_fifo(self):
        """
        Using a similar setup as in the LRU test above, we can test the
        FIFO cache.
        """
        c = cache.CacheFIFO(4, 2, 2)
        c.write(0, 0)
        c.write(9, 9)
        c.read(0)
        c.write(17, 17)

        # No matter how many times we read from address 0, it will always
        # be evicted from the cache as it was the first to be written to it.

        self.assertIs(c.read(0), None)
        self.assertIs(c.read(9), 9)
        self.assertIs(c.read(17), 17)

    def test_cache_other(self):
        """
        Since you cannot really test a non-deterministic cache replacement
        policy, we use the RR cache to test some edge cases.
        """

        # It should not be possible to create a cache with 0 sets or lines.
        # Also, the size of a cache line should be greater than 0.
        with self.assertRaises(Exception):
            cache.CacheRR(0, 10, 10)
            cache.CacheRR(10, 0, 10)
            cache.cacheRR(10, 10, 0)
