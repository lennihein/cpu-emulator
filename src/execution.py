"""Execution Engine that executes instructions out-of-order."""

from dataclasses import dataclass
from typing import NewType, Optional, TypeVar, Union, cast

from .instructions import InstrImm, InstrLoad, InstrReg, InstrStore, Instruction, RegID
from .mmu import MMU
from .word import Word

_T = TypeVar("_T")

# ID of a slot of the Reservation Station or the Load Buffer, also used as
# an index
_SlotID = NewType("_SlotID", int)


@dataclass
class _SlotALU:
    """An occupied slot in the Reservation Station, storing an ALU instruction in flight."""

    instr_ty: Union[InstrReg, InstrImm]
    # Either a `Word` with the operand's value, or a `_SlotID` referencing the slot that will
    # produce the operand value
    operands: list[Union[Word, _SlotID]]
    cycles_remaining: int


@dataclass
class _SlotLoad:
    """An occupied slot in the Load Buffer, storing a load instruction in flight."""

    instr_ty: InstrLoad
    # Effective address of the memory access
    address: Word
    # Value loaded from memory, or `None` if the load instruction was issued
    # this cycle
    value: Optional[Word]
    cycles_remaining: int


@dataclass
class _SlotStore:
    """An occupied slot in the Store Buffer, storing a store instruction in flight."""

    instr_ty: InstrStore
    # Effective address of the memory access
    address: Word
    # Value stored to memory, or a `_SlotID` if the value is yet to be
    # produced by another slot
    value: Union[Word, _SlotID]
    cycles_remaining: int
    # Tracks if we already performed the store operation
    completed: bool


class ExecutionEngine:
    """
    Execution Engine that executes instructions out-of-order.

    The Execution Engine contains the register file and the Reservation Station, Load Buffer, and
    Store Buffer. The latter contain a number of slots for ALU, load, and store instructions,
    respectively.

    Each slot is either free or contains an `Instruction` in flight. An instruction in flight is
    either still waiting for some of its operands to be produced by preceding instructions, or being
    executed. The number of instructions that can execute concurrently is only limited by the amount
    of slots; we don't model individual Execution Units and just pretend there is an infinite number
    of them.

    Each register in the register file either contains a value or references a slot that will
    produce the register's value. Since instructions are issued in-order, the state of the register
    file at a single point in time represents the architectural register state at that point in
    time, with yet-unknown register values present as slot references.
    """

    _mmu: MMU

    # Register file, either a `Word` with a value or a `_SlotID` referencing the slot that will
    # produce the register value
    _registers: list[Union[Word, _SlotID]]
    # Reservation Station with slots for ALU instructions
    _alus: list[Optional[_SlotALU]]
    # Load Buffer with slots for load instructions
    _loads: list[Optional[_SlotLoad]]
    # Store Buffer with slots for store instructions
    _stores: list[Optional[_SlotStore]]

    def __init__(self, mmu, regs=32, alus=8, loads=4, stores=4):
        """Create a new Reservation Station, with empty slots and zeroed registers."""
        self._mmu = mmu

        # Initialize registers to zero
        self._registers = [Word(0) for _ in range(regs)]

        # Initialize slots to empty
        self._alus = [None for _ in range(alus)]
        self._loads = [None for _ in range(loads)]
        self._stores = [None for _ in range(stores)]

    @staticmethod
    def _put_into_free_slot(
            slots: list[Optional[_T]], new_slot: _T) -> Optional[int]:
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
        # Get the source operands depending on the instruction type
        if isinstance(instr.ty, InstrReg):
            # This is an `InstrReg` instruction, with source operands `reg`,
            # `reg`
            operands = [self._registers[instr.ops[1]],
                        self._registers[instr.ops[2]]]
        else:
            # This is an `InstrImm` instruction, with source operands `reg`,
            # `imm`
            operands = [self._registers[instr.ops[1]], Word(instr.ops[2])]

        # Create slot entry and put it into a free slot
        ty = cast(Union[InstrReg, InstrImm], instr.ty)
        alu = _SlotALU(
            instr_ty=ty,
            operands=operands,
            cycles_remaining=ty.cycles,
        )
        idx = self._put_into_free_slot(self._alus, alu)
        if idx is None:
            return False

        # Mark destination register as waiting on new slot
        self._registers[instr.ops[0]] = _SlotID(idx)

        return True

    @staticmethod
    def _accesses_overlap(
        slot: Union[_SlotLoad, _SlotStore],
        addr: Word,
        ty: Union[InstrLoad, InstrStore],
    ) -> bool:
        """Check if two memory accesses overlap."""

        def access(addr, ty):
            if ty.width_byte:
                return {addr.value}
            else:
                return {addr.value, addr.value + 1}

        return bool(access(slot.address, slot.instr_ty) & access(addr, ty))

    def _try_issue_mem(self, instr: Instruction) -> bool:
        """Try to issue the given load or store instruction."""
        base = RegID(instr.ops[1])
        offset = Word(instr.ops[2])

        # Only issue memory instructions when the effective address is
        # available
        if not isinstance(self._registers[base], Word):
            return False

        # Compute effective address
        address = cast(Word, self._registers[base]) + offset

        # Check for RAW / WAW hazards
        for haz_store in self._stores:
            ty = cast(Union[InstrLoad, InstrStore], instr.ty)
            if haz_store is not None and self._accesses_overlap(
                    haz_store, address, ty):
                return False

        if isinstance(instr.ty, InstrLoad):
            # Create slot entry and put it into a free slot
            load = _SlotLoad(
                instr_ty=cast(InstrLoad, instr.ty),
                address=address,
                value=None,
                cycles_remaining=0,
            )
            idx = self._put_into_free_slot(self._loads, load)
            if idx is None:
                return False

            # Mark destination register as waiting on this slot
            self._registers[instr.ops[0]] = _SlotID(len(self._alus) + idx)

            return True

        else:
            # Check for WAR hazard
            for haz_load in self._loads:
                ty = cast(Union[InstrLoad, InstrStore], instr.ty)
                if haz_load is not None and self._accesses_overlap(
                        haz_load, address, ty):
                    return False

            # Create slot entry and put it into a free slot
            store = _SlotStore(
                instr_ty=cast(InstrStore, instr.ty),
                address=address,
                value=self._registers[instr.ops[0]],
                cycles_remaining=0,
                completed=False,
            )
            idx = self._put_into_free_slot(self._stores, store)
            return idx is not None

    def try_issue(self, instr: Instruction) -> bool:
        """
        Try to issue the given instruction by putting it in a free slot.

        ALU instructions will be put in the Reservation Station, load instructions in the Load
        Buffer and store instructions in the Store Buffer. Additionally, load and store instructions
        are only issued once the effective address of their memory access can be computed and there
        are no hazards with load or store instructions in-flight.

        Return whether the instruction was issued.
        """
        if isinstance(instr.ty, (InstrReg, InstrImm)):
            return self._try_issue_alu(instr)
        if isinstance(instr.ty, (InstrLoad, InstrStore)):
            return self._try_issue_mem(instr)

        raise ValueError(f"Unsupported instruction type {instr.ty!r}")

    def _update_waiting(self, slot_id: _SlotID, result: Word):
        """
        Update all registers and slots that wait on the given slot.

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
            self._update_waiting(_SlotID(i), res)

            # Free retired slot
            self._alus[i] = None

        for i, load in enumerate(self._loads):
            # Skip free slots
            if load is None:
                continue

            # Inform the memory subsystem of loads that just got issued
            if load.value is None:
                if load.instr_ty.width_byte:
                    val, cycles = self._mmu.read_byte(load.address.value)
                else:
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
            self._update_waiting(_SlotID(len(self._alus) + i), load.value)

            # Free retired slot
            self._loads[i] = None

        for i, store in enumerate(self._stores):
            # Skip free slots
            if store is None:
                continue
            # Skip waiting slots
            if not isinstance(store.value, Word):
                continue

            if not store.completed:
                # Actually perform the store
                if store.instr_ty.width_byte:
                    cycles = self._mmu.write_byte(
                        store.address.value, store.value)
                else:
                    cycles = self._mmu.write_word(
                        store.address.value, store.value)

                store.cycles_remaining = cycles
                store.completed = True

            # Execute store
            store.cycles_remaining -= 1
            # Check if store is done
            if store.cycles_remaining > 0:
                continue
            # Only retire up to one instruction
            if retired:
                continue
            retired = True

            # Free retired slot
            self._stores[i] = None
