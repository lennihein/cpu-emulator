from __future__ import annotations

import unittest

from src.cpu import CPU
from src.instructions import InstrReg
from src.word import Word
from benedict import benedict as bd


class CPUTests(unittest.TestCase):

    def test_cpu(self):
        # As testing the CPU class as a whole is only possible once the project is complete, the
        # main focus of this test is the snapshot feature for now. The intended purpose of this
        # feature is to allow the user to step forward and backwards during the execution of their
        # program.

        cpu = CPU(bd.from_yaml('config.yml'))

        address = Word(Word.WIDTH // 2)

        for i in range(10):
            cpu.get_memory_subsystem().write_byte(address + Word(i), Word(i))
            cpu._take_snapshot()

        self.assertEqual(self.get_vals_at_addresses(cpu, address), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        # We will have 11 snapshots because the first one is created when the CPU instance is
        # initialized
        self.assertEqual(len(cpu.get_snapshots()), 11)
        self.assertEqual(cpu._snapshot_index, len(cpu.get_snapshots()) - 1)

        # Go 6 steps back...
        cpu = CPU.restore_snapshot(cpu, -6)
        self.assertEqual(self.get_vals_at_addresses(cpu, address), [0, 1, 2, 3, 0, 0, 0, 0, 0, 0])
        # Still should have same number of snapshots, but different index pointer
        self.assertEqual(len(cpu.get_snapshots()), 11)
        self.assertEqual(cpu._snapshot_index, len(cpu.get_snapshots()) - 1 - 6)

        # Now we step forward again. Again, we expect the number of snapshots to remain the same as
        # we are simply moving an index pointer around.
        cpu = CPU.restore_snapshot(cpu, 1)
        self.assertEqual(self.get_vals_at_addresses(cpu, address), [0, 1, 2, 3, 4, 0, 0, 0, 0, 0])
        self.assertEqual(len(cpu.get_snapshots()), 11)
        self.assertEqual(cpu._snapshot_index, len(cpu.get_snapshots()) - 1 - 6 + 1)

        # Now we write to an address. In reality, this will create a new snapshot (here, we force it
        # to happen). As a result, a new snapshot branch is entered and the snapshots at
        # `snapshots[10 - 6 + 1 + 1:]` (the ones that were created AFTER the snapshot that is
        # pointed to by cpu._snapshot_index) are no longer valid. Since we discard them, we now
        # expect the snapshot list to be smaller.
        cpu.get_memory_subsystem().write_byte(address, Word(42))
        cpu._take_snapshot()

        self.assertEqual(self.get_vals_at_addresses(cpu, address), [42, 1, 2, 3, 4, 0, 0, 0, 0, 0])
        self.assertEqual(len(cpu.get_snapshots()), 11 - 6 + 1 + 1)
        # Again, we expect the snapshot index to point to the last entry
        self.assertEqual(cpu._snapshot_index, len(cpu.get_snapshots()) - 1)

        # Lastly, our second to last snapshot should be the one we had before we wrote 42 to address
        self.assertEqual(
            self.get_vals_at_addresses(cpu.get_snapshots()[-2], address), [0, 1, 2, 3, 4, 0, 0, 0, 0, 0]
        )

        # Stepping forwards / backwards outside of the snapshot list should not be possible
        self.assertEqual(CPU.restore_snapshot(cpu, -10), None)
        self.assertEqual(CPU.restore_snapshot(cpu, 10), None)

    def get_vals_at_addresses(self, cpu: CPU, address: Word) -> list[int]:
        return [cpu.get_memory_subsystem().read_byte(address + Word(i)).value.value for i in range(10)]

    def test_program(self):
        """Test execution of a simple program."""
        code = """
            // Set r1 to 1
            addi r1, r0, 1
            // Set r2 to 2
            add r2, r1, r1
            // Set r3 to 3
            addi r3, r2, 1
            // Set r4 to 4
            mul r4, r2, r2
            // Set r5 to 5
            add r5, r2, r3
            // Store 4 to address 0
            sw r4, r0, 0
            // Store 5 to address 0
            sw r5, r2, -2
            // Overwrite to 0x0105
            sb r1, r3, -2
            // Load 0x105 into r6
            lw r6, r0, 0
            // Store 4 to address 0
            sw r4, r5, -5
            // Execute fence and query cycle counter
            fence
            rdtsc r10
            // Set r7 to 3 and count it down to 1
            addi r7, r0, 3
        loop:
            subi r7, r7, 1
            bne r7, r1, loop
            // Flush address 0
            flush r0, 0
        """

        # Create CPU
        cpu = CPU(bd.from_yaml('config.yml'))

        # Add `mul` instruction
        mul = InstrReg("mul", lambda a, b: Word(a.value * b.value), cycles=10)
        cpu._parser.add_instruction(mul)

        # Load program
        cpu.load_program(code)

        # Execute program to the end
        while True:
            info = cpu.tick()
            if not info.executing_program:
                break

        # Check that the registers have the correct values
        target = (0, 1, 2, 3, 4, 5, 0x105, 1)

        self.assertEqual(cpu._exec_engine._registers[: len(target)], [Word(x) for x in target])

    def test_immediate_snaprestore(self):
        """Test immediate snapshot/restore."""
        cpu = CPU(bd.from_yaml('config.yml'))

        # Create a program that sets r1 to 1
        code = """
            // Set r1 to 1
            addi r1, r0, 1
        """

        # Load program
        cpu.load_program(code)

        cpu = cpu.restore_snapshot(cpu, -1)

        self.assertIsNone(cpu)

    def test_fault_on_last(self):
        code = """
            // set R0 to 0
            andi r0, r0, 0
            // set R0 to 0xFF00
            addi r0, r0, 0xFF00
            // load 0xFF00 into R1
            lw r1, r0, 0
        """

        # Create CPU
        cpu = CPU(bd.from_yaml('config.yml'))

        # Load program
        cpu.load_program(code)

        # Execute program to the end
        while True:
            info = cpu.tick()
            if not info.executing_program:
                print("Program finished")
                break
