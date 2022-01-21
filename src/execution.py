"""
Execution Engine that executes instructions out-of-order.

The main component here is the Reservation Station; we don't model individual Execution Units and
just pretend there is an infinite number of them.
"""

from dataclasses import dataclass
from typing import NewType, Optional, Union

from .instructions import Instruction, InstructionType, OperandKind
from .word import Word

# ID of a register, used as index into the register file
RegID = NewType("RegID", int)
# ID of a slot of the Reservation Station, also used as an index
SlotID = NewType("SlotID", int)


@dataclass
class Slot:
    """An occupied slot in the Reservation Station, storing an instruction in flight."""

    instr: InstructionType
    # Either a `Word` with the operand's value, or a `SlotID` referencing the slot that will produce
    # the operand value
    operands: list[Union[Word, SlotID]]
    cycles_remaining: int


class ReservationStation:
    """
    Reseration Station, containing of a number of slots and the register file.

    Each slot is either free or contains an `Instruction` in flight. An instruction in flight is
    either still waiting for some of its operands to be produced by preceding instructions, or being
    executed.

    Each register in the register file either contains a value or references a slot that will
    produce the register's value. Since instructions are executed out-of-order, the state of the
    register file at a single point in time might not represent the architectural register state at
    that or any other point in time.
    """

    _slots: list[Optional[Slot]]
    _registers: list[Union[Word, SlotID]]

    def __init__(self, slots=8, regs=32):
        """Create a new Reservation Station, with empty slots and zeroed registers."""
        # Initialize slots to empty
        self._slots = [None for _ in range(slots)]
        # Initialize registers to zero
        self._registers = [Word(0) for _ in range(regs)]

    def _initial_operand(self, ty: OperandKind, op: int) -> Union[Word, SlotID]:
        """Return the initial operand to be stored in a newly populated slot."""
        if ty == "reg":
            return self._registers[op]

        if ty == "imm":
            return Word(op)

        if ty == "label":
            return Word(op)

        raise ValueError(f"Unknown operand type {ty!r}")

    def issue(self, instr: Instruction) -> bool:
        """Put the given instruction in a free slot."""
        for i, slot in enumerate(self._slots):
            if slot is not None:
                continue

            # Found a free slot, populate it
            operands = [
                self._initial_operand(ty, op)
                for ty, op in zip(instr.ty.operand_types[1:], instr.ops[1:])
            ]
            self._slots[i] = Slot(instr.ty, operands, instr.ty.cycles)

            # Mark destination register as waiting on this slot
            assert instr.ty.operand_types[0] == "reg"
            self._registers[instr.ops[0]] = SlotID(i)

            return True
        return False

    def tick(self):
        """Execute instructions that are ready."""
        for i, slot in enumerate(self._slots):
            # Skip free slots
            if slot is None:
                continue
            # Skip waiting slots
            if not all(isinstance(op, Word) for op in slot.operands):
                continue

            # Found ready slot, execute it
            slot.cycles_remaining -= 1
            # Check if slot is done
            if slot.cycles_remaining > 0:
                continue

            # Compute result
            res = slot.instr.compute_result(*slot.operands)

            # Update all waiting registers
            for j, reg in enumerate(self._registers):
                if reg == SlotID(i):
                    self._registers[j] = res

            # Update all waiting slots
            for waiting in self._slots:
                if waiting is None:
                    continue
                for j, op in enumerate(waiting.operands):
                    if op == SlotID(i):
                        waiting.operands[j] = res

            # Free executed slot
            self._slots[i] = None
