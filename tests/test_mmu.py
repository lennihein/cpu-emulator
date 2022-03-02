import unittest

from src.mmu import MMU
from src.word import Word
from src.byte import Byte


class MMUTests(unittest.TestCase):
    def test_mmu(self):
        mmu = MMU()
        import random

        # Make sure we do not pick the highest address and try to write a Word (> 1 byte) to this
        # address.
        address = max(0, random.randint(0, 2**Word.WIDTH) - Word.WIDTH_BYTES)
        address = Word(address)

        # Reading / Writing bytes
        random_value = random.randint(0, 255)
        random_byte = Byte(random_value)
        mmu.write_byte(address, random_byte)
        returned_byte = mmu.read_byte(address)

        self.assertEqual(returned_byte.value.value, random_value)
        self.assertEqual(returned_byte.cycles_value, mmu.cache_hit_cycles)
        self.assertEqual(returned_byte.cycles_fault, mmu.num_fault_cycles)

        # Reading / Writing words
        random_value = random.randint((-1) * 2 ** (Word.WIDTH - 1), 2 ** (Word.WIDTH - 1))
        random_word = Word(random_value)
        mmu.write_word(address, random_word)
        returned_word = mmu.read_word(address)

        self.assertEqual(returned_word.value.signed_value, random_value)
        self.assertEqual(returned_word.cycles_value, mmu.cache_hit_cycles)
        self.assertEqual(returned_word.cycles_fault, mmu.num_fault_cycles)

        # Flushing the line at address (address + 1) should prevent the MMU from fetching all data
        # from the cache
        mmu.flush_line(address + Word(1))
        self.assertEqual(mmu.read_word(address + Word(1)).cycles_value, mmu.cache_miss_cycles)

        # Now, (address + 1) should be cached again (because we read from it)
        self.assertIs(mmu.is_addr_cached(address + Word(1)), True)

        # But if we flush it again, it shouldn't
        mmu.flush_line(address + Word(1))
        self.assertIs(mmu.is_addr_cached(address + Word(1)), False)

        # Accessing protected memory should induce a fault.
        mem_result = mmu.read_byte(Word(2 ** (Word.WIDTH - 1)))
        self.assertIs(mem_result.fault, True)
        mem_result = mmu.write_byte(Word(2 ** (Word.WIDTH - 1)), Word(1))
        self.assertEqual(mem_result.fault, True)
