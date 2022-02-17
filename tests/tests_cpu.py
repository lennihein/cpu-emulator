import unittest

from src.cpu import CPU
from src.word import Word


class CPUTests(unittest.TestCase):
    def test_cpu(self):

        # As testing the CPU class as a whole is only possible once the project is complete, the
        # main focus of this test is the snapshot feature for now. The intended purpose of this
        # feature is to allow the user to step forward and backwards during the execution of their
        # program.

        cpu = CPU()

        address = Word(Word.WIDTH // 2)

        for i in range(10):
            cpu.get_mmu().write_byte(address + Word(i), Word(i))
            cpu._take_snapshot()

        self.assertEqual(self.get_vals_at_addresses(cpu, address), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        # We will have 11 snapshots because the first one is created when the CPU instance is
        # initialized
        self.assertEqual(len(cpu._snapshots), 11)
        self.assertEqual(cpu._snapshot_index, len(cpu._snapshots) - 1)

        # Go 6 steps back...
        cpu = CPU.restore_snapshot(cpu, -6)
        self.assertEqual(self.get_vals_at_addresses(cpu, address), [0, 1, 2, 3, 0, 0, 0, 0, 0, 0])
        # Still should have same number of snapshots, but different index pointer
        self.assertEqual(len(cpu._snapshots), 11)
        self.assertEqual(cpu._snapshot_index, len(cpu._snapshots) - 1 - 6)

        # Now we step forward again. Again, we expect the number of snapshots to remain the same as
        # we are simply moving an index pointer around.
        cpu = CPU.restore_snapshot(cpu, 1)
        self.assertEqual(self.get_vals_at_addresses(cpu, address), [0, 1, 2, 3, 4, 0, 0, 0, 0, 0])
        self.assertEqual(len(cpu._snapshots), 11)
        self.assertEqual(cpu._snapshot_index, len(cpu._snapshots) - 1 - 6 + 1)

        # Now we write to an address. In reality, this will create a new snapshot (here, we force it
        # to happen). As a result, a new snapshot branch is entered and the snapshots at
        # `snapshots[10 - 6 + 1 + 1:]` (the ones that were created AFTER the snapshot that is
        # pointed to by cpu._snapshot_index) are no longer valid. Since we discard them, we now
        # expect the snapshot list to be smaller.
        cpu.get_mmu().write_byte(address, Word(42))
        cpu._take_snapshot()

        self.assertEqual(self.get_vals_at_addresses(cpu, address), [42, 1, 2, 3, 4, 0, 0, 0, 0, 0])
        self.assertEqual(len(cpu._snapshots), 11 - 6 + 1 + 1)
        # Again, we expect the snapshot index to point to the last entry
        self.assertEqual(cpu._snapshot_index, len(cpu._snapshots) - 1)

        # Lastly, our second to last snapshot should be the one we had before we wrote 42 to address
        self.assertEqual(
            self.get_vals_at_addresses(cpu._snapshots[-2], address), [0, 1, 2, 3, 4, 0, 0, 0, 0, 0]
        )

        # Stepping forwards / backwards outside of the snapshot list should not be possible
        self.assertEqual(CPU.restore_snapshot(cpu, -10), False)
        self.assertEqual(CPU.restore_snapshot(cpu, 10), False)

    def get_vals_at_addresses(self, cpu: CPU, address: Word) -> list[int]:
        return [cpu.get_mmu().read_byte(address + Word(i)).value.value for i in range(10)]
