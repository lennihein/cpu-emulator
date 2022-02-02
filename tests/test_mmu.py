import unittest
from src import mmu as MMU
from src import byte
from src import word


class MMUTests(unittest.TestCase):

    def test_mmu(self):

        mmu = MMU.MMU(2 ** word.Word.WIDTH)
        import random
        # make sure we do not pick the highest address and try to write a Word (> 1 byte)
        # to this address.
        address = random.randint(
            0, 2 ** word.Word.WIDTH) - (word.Word.WIDTH // 8)

        # TODO: Test MMU with negative numbers

        # Reading / Writing bytes
        # random_byte = byte.Byte(random.randint(0, 2 ** 8))
        random_byte = byte.Byte(240)
        mmu.write_byte(address, random_byte)
        returned_byte = mmu.read_byte(address)
        self.assertEqual(returned_byte[0].value, random_byte.value)
        self.assertEqual(returned_byte[1], mmu.cache_hit_cycles)

        # Reading / Writing words
        random_word = word.Word(
            random.randint(
                2 ** 8 + 1,
                2 ** word.Word.WIDTH))
        mmu.write_word(address, random_word)
        returned_word = mmu.read_word(address)
        self.assertEqual(returned_word[0].value, random_word.value)
        self.assertEqual(returned_word[1], mmu.cache_hit_cycles)

        # Since we are using little endian, flushing address (address + 1) should
        # prevent the MMU from fetching all data from the cache.
        mmu.flush_addr(address + 1)
        self.assertEqual(mmu.read_word(address + 1)[1], mmu.cache_miss_cycles)

        # Now, (address + 1) should not be cached again (because we read from
        # it).
        self.assertIs(mmu.is_addr_cached(address + 1), True)

        # But if we flush it again, it shouldn't.
        mmu.flush_addr(address + 1)
        self.assertIs(mmu.is_addr_cached(address + 1), False)
