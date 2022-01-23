"""
Execution Engine that executes instructions out-of-order.

The main component here is the Reservation Station; we don't model individual Execution Units and
just pretend there is an infinite number of them.
"""

from dataclasses import dataclass
from typing import NewType, Optional, Union, cast

from .instructions import InstrLoad, InstrStore, Instruction, InstructionType, OperandKind, RegID
from .mmu import MMU
from .word import Word

# ID of a slot of the Reservation Station or the Load Buffer, also used as an index
SlotID = NewType("SlotID", int)


@dataclass
class Slot:
    """An occupied slot in the Reservation Station, storing an instruction in flight."""

    instr: InstructionType
    # Either a `Word` with the operand's value, or a `SlotID` referencing the slot that will produce
    # the operand value
    operands: list[Union[Word, SlotID]]
    cycles_remaining: int


@dataclass
class Load:
    instr: InstructionType
    address: Word
    value: Optional[Word]
    cycles_remaining: int


@dataclass
class Store:
    instr: InstructionType
    address: Word
    value: Union[Word, SlotID]
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

    _mmu: MMU

    _slots: list[Optional[Slot]]
    _registers: list[Union[Word, SlotID]]
    _loads: list[Optional[Load]]
    _stores: list[Optional[Store]]

    def __init__(self, mmu, slots=8, regs=32, loads=4, stores=4):
        """Create a new Reservation Station, with empty slots and zeroed registers."""
        self._mmu = mmu
        # Initialize slots to empty
        self._slots = [None for _ in range(slots)]
        # Initialize registers to zero
        self._registers = [Word(0) for _ in range(regs)]
        # Initialize loads to empty
        self._loads = [None for _ in range(loads)]
        # Initialize stores to empty
        self._stores = [None for _ in range(stores)]

    def _initial_operand(self, ty: OperandKind, op: int) -> Union[Word, SlotID]:
        """Return the initial operand to be stored in a newly populated slot."""
        if ty == "reg":
            return self._registers[op]

        if ty == "imm":
            return Word(op)

        if ty == "label":
            return Word(op)

        raise ValueError(f"Unknown operand type {ty!r}")

    def try_issue(self, instr: Instruction) -> bool:
        """Put the given instruction in a free slot."""
        if isinstance(instr.ty, (InstrLoad, InstrStore)):
            base = RegID(instr.ops[1])
            offset = Word(instr.ops[2])

            # Only issue memory instructions when the effective address is available
            if not isinstance(self._registers[base], Word):
                return False

            # Compute effective address
            address = cast(Word, self._registers[base]) + offset

            # Check for RAW / WAW hazards
            for store in self._stores:
                # TODO: Check for overlap in address
                if store is not None and store.address == address:
                    return False

            if isinstance(instr.ty, InstrLoad):
                # Put load instruction into the load buffer
                for i, load in enumerate(self._loads):
                    if load is not None:
                        continue

                    # Found a free slot, populate it
                    self._loads[i] = Load(
                        instr=instr.ty,
                        address=address,
                        value=None,
                        cycles_remaining=0,
                    )

                    # Mark destination register as waiting on this slot
                    self._registers[instr.ops[0]] = SlotID(len(self._slots) + i)

                    return True

            else:
                # Check for WAR hazard
                for load in self._loads:
                    # TODO: Check for overlap in address
                    if load is not None and load.address == address:
                        return False

                # Put store instruction into the store buffer
                for i, store in enumerate(self._stores):
                    if store is not None:
                        continue

                    # Found a free slot, populate it
                    self._stores[i] = Store(
                        instr=instr.ty,
                        address=address,
                        value=self._registers[instr.ops[0]],
                        cycles_remaining=0,
                    )

                    return True

        else:
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
        # We only retire up to one instruction each cycle
        retired = False

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
            # Only retire up to one instruction
            if retired:
                continue
            retired = True

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

            # Update all waiting stores
            for waiting in self._stores:
                if waiting is None:
                    continue
                if waiting.value == SlotID(i):
                    waiting.value = res

            # Free retired slot
            self._slots[i] = None

        for i, load in enumerate(self._loads):
            # Skip free slots
            if load is None:
                continue

            # Inform the memory subsystem of loads that just got issued
            if load.value is None:
                val, cycles = self._mmu.read_word(load.address.value)
                load.value = val
                load.cycles_remaining = cycles

            # Execute load
            load.cycles_remaining -= 1
            # Check if load is done
            if load.cycles_remaining > 0:
                continue
            # Only retire up to one instruction
            if retired:
                continue
            retired = True

            # Update all waiting registers
            for j, reg in enumerate(self._registers):
                if reg == SlotID(len(self._slots) + i):
                    self._registers[j] = load.value

            # Update all waiting slots
            for waiting in self._slots:
                if waiting is None:
                    continue
                for j, op in enumerate(waiting.operands):
                    if op == SlotID(len(self._slots) + i):
                        waiting.operands[j] = load.value

            # Update all waiting stores
            for waiting in self._stores:
                if waiting is None:
                    continue
                if waiting.value == SlotID(len(self._slots) + i):
                    waiting.value = load.value

            # Free retired slot
            self._loads[i] = None

        for i, store in enumerate(self._stores):
            # Skip free slots
            if store is None:
                continue
            # Skip waiting slots
            if not isinstance(store.value, Word):
                continue

            # Execute store
            store.cycles_remaining -= 1
            # Check if store is done
            if store.cycles_remaining > 0:
                continue
            # Only retire up to one instruction
            if retired:
                continue
            retired = True

            # Actually perform the store
            self._mmu.write_word(store.address.value, store.value)

            # Free retired slot
            self._stores[i] = None
