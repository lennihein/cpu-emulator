"""
Execution Engine that executes instructions out-of-order.

The main component here is the Reservation Station; we don't model individual Execution Units and
just pretend there is an infinite number of them.
"""

from dataclasses import dataclass
from typing import NewType, Optional, Union, cast

from .instructions import (
    InstrImm,
    InstrLoad,
    InstrReg,
    InstrStore,
    Instruction,
    InstructionType,
    OperandKind,
    RegID,
)
from .mmu import MMU
from .word import Word

# ID of a slot of the Reservation Station or the Load Buffer, also used as an index
SlotID = NewType("SlotID", int)


@dataclass
class SlotALU:
    """An occupied slot in the Reservation Station, storing an ALU instruction in flight."""

    instr_ty: InstructionType
    # Either a `Word` with the operand's value, or a `SlotID` referencing the slot that will produce
    # the operand value
    operands: list[Union[Word, SlotID]]
    cycles_remaining: int


@dataclass
class SlotLoad:
    """An occupied slot in the Load Buffer, storing a load instruction in flight."""

    instr_ty: InstructionType
    address: Word
    value: Optional[Word]
    cycles_remaining: int


@dataclass
class SlotStore:
    """An occupied slot in the Store Buffer, storing a store instruction in flight."""

    instr_ty: InstructionType
    address: Word
    value: Union[Word, SlotID]
    cycles_remaining: int


class ExecutionEngine:
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

    # Register file, either a `Word` with a value or a `SlotID` referencing the slot that will
    # produce the register value
    _registers: list[Union[Word, SlotID]]
    _alus: list[Optional[SlotALU]]
    _loads: list[Optional[SlotLoad]]
    _stores: list[Optional[SlotStore]]

    def __init__(self, mmu, regs=32, alus=8, loads=4, stores=4):
        """Create a new Reservation Station, with empty slots and zeroed registers."""
        self._mmu = mmu

        # Initialize registers to zero
        self._registers = [Word(0) for _ in range(regs)]

        # Initialize slots to empty
        self._alus = [None for _ in range(alus)]
        self._loads = [None for _ in range(loads)]
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

    def _put_into_free_slot(self, slots, new_slot) -> Optional[int]:
        """Try to put the given new slot into a free slot of the given slots."""
        for i, slot in enumerate(slots):
            if slot is not None:
                continue

            # Found a free slot, populate it
            slots[i] = new_slot

            return i
        return None

    def _try_issue_alu(self, instr: Instruction) -> bool:
        """Try to issue the given ALU instruction."""
        operands = [
            self._initial_operand(ty, op)
            for ty, op in zip(instr.ty.operand_types[1:], instr.ops[1:])
        ]
        alu = SlotALU(
            instr_ty=instr.ty,
            operands=operands,
            cycles_remaining=instr.ty.cycles,
        )

        idx = self._put_into_free_slot(self._alus, alu)
        if idx is None:
            return False

        # Mark destination register as waiting on new slot
        assert instr.ty.operand_types[0] == "reg"
        self._registers[instr.ops[0]] = SlotID(idx)

        return True

    def _try_issue_mem(self, instr: Instruction) -> bool:
        """Try to issue the given load or store instruction."""
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
            load = SlotLoad(
                instr_ty=instr.ty,
                address=address,
                value=None,
                cycles_remaining=0,
            )
            idx = self._put_into_free_slot(self._loads, load)
            if idx is None:
                return False

            # Mark destination register as waiting on this slot
            self._registers[instr.ops[0]] = SlotID(len(self._alus) + idx)

            return True

        else:
            # Check for WAR hazard
            for load in self._loads:
                # TODO: Check for overlap in address
                if load is not None and load.address == address:
                    return False

            store = SlotStore(
                instr_ty=instr.ty,
                address=address,
                value=self._registers[instr.ops[0]],
                cycles_remaining=0,
            )

            idx = self._put_into_free_slot(self._stores, store)
            return idx is not None

    def try_issue(self, instr: Instruction) -> bool:
        """Try to issue the given instruction by putting it in a free slot.

        ALU instructions will be put in the Reservation Station, load instructions in the Load
        Buffer and store instructions in the Store Buffer. Additionally, load and store instructions
        are only issued once the effective address of their memory access can be computed.

        Return whether the instruction was issued.
        """
        if isinstance(instr.ty, (InstrReg, InstrImm)):
            return self._try_issue_alu(instr)
        if isinstance(instr.ty, (InstrLoad, InstrStore)):
            return self._try_issue_mem(instr)

        raise ValueError(f"Unsupported instruction type {instr.ty!r}")

    def _update_waiting(self, slot_id: SlotID, result: Word):
        """Update all registers and slots that wait on the given slot.

        This models broadcasting the given result on the CDB.
        """
        # Update all waiting registers
        for i, reg in enumerate(self._registers):
            if reg == slot_id:
                self._registers[i] = result

        # Update all waiting alus
        for alu in self._alus:
            if alu is None:
                continue
            for i, op in enumerate(alu.operands):
                if op == slot_id:
                    alu.operands[i] = result

        # Update all waiting stores
        for store in self._stores:
            if store is None:
                continue
            if store.value == slot_id:
                store.value = result

    def tick(self):
        """Execute instructions that are ready."""
        # We only retire up to one instruction each cycle
        retired = False

        for i, slot in enumerate(self._alus):
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
            res = slot.instr_ty.compute_result(*slot.operands)
            self._update_waiting(SlotID(i), res)

            # Free retired slot
            self._alus[i] = None

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

            # Broadcast result
            self._update_waiting(SlotID(len(self._alus) + i), load.value)

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
