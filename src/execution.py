"""Execution Engine that executes instructions out-of-order."""

from dataclasses import dataclass
from typing import Callable, NewType, Optional, TypeVar, Union, cast, final

from .instructions import (
    InstrBranch,
    InstrFlush,
    InstrImm,
    InstrLoad,
    InstrReg,
    InstrStore,
    Instruction,
    InstructionType,
    RegID,
)
from .mmu import MMU, WordAndFault
from .word import Word

_T = TypeVar("_T")

# ID of a slot of the Reservation Station, also used as an index into the list of slots
_SlotID = NewType("_SlotID", int)
# Either a `Word` with a concrete value, or a `_SlotID` referencing the slot that will produce the
# value
_WordOrSlot = Union[Word, _SlotID]


@dataclass
class _FaultState:
    """Architectural state at the time a fault occurs."""

    registers: list[Word]
    pc: int


class _InstructionNotIssued(Exception):
    """
    Exception raised by `_Slot` constructors to indicate that the instruction should not be issued.

    This seems like a hacky solution, but works well with the way `_Slots` are subtyped.
    """


@dataclass
class _Slot:
    """
    An occupied slot in the Reservation Station, storing an instruction in flight.

    Every instruction goes through two phases: executing and retiring. Executing instructions are in
    the process of computing their result value. Retiring instructions have already produced their
    result, but have not yet determined if they cause a fault.
    """

    # Type of this instruction
    instr_ty: InstructionType
    # Whether we are executing or retiring
    executing: bool
    # Whether we are retired
    retired: bool

    def __init__(
        self,
        exec: ExecutionEngine,
        instr: Instruction,
        pc: int,
        source_operands: list[_WordOrSlot],
    ):
        self.instr_ty = instr.ty
        self.executing = True
        self.retired = False

    def notify_result(self, slot: _SlotID, result: Word):
        """Notify this slot that the given slot produced the given result."""

    def notify_retired(self, slot: _SlotID):
        """Notify this slot that the given slot retired without causing a fault."""

    @final
    def tick_execute(self) -> Optional[Word]:
        """Continue executing this slot, return its result if it finished executing."""
        assert self.executing and not self.retired

        r = self._tick_execute()

        if r is not None:
            self.executing = False
        return r

    @final
    def tick_retire(self) -> Optional[tuple[Optional[_FaultState]]]:
        """Continue retiring this slot, return whether it faults if it finished retiring."""
        # This return type should be `Optional[Optional[...]]`, but Python
        assert not self.executing and not self.retired

        r = self._tick_retire()

        if r is not None:
            self.retired = True
        return r

    def _tick_execute(self) -> Optional[Word]:
        raise NotImplementedError("Must be overwritten by a concrete slot type")

    def _tick_retire(self) -> Optional[tuple[Optional[_FaultState]]]:
        raise NotImplementedError("Must be overwritten by a concrete slot type")


@dataclass
class _SlotFaulting(_Slot):
    """An occupied slot in the Reservation Station, storing a potentially-faulting instruction."""

    # Slots of potentially faulting instructions that precede this instruction in program order
    faulting_preceding: list[_SlotID]
    # Architectural register state when this instruction was issued
    registers: list[_WordOrSlot]
    # Address of this instruction
    pc: int

    def __init__(
        self,
        exec: ExecutionEngine,
        instr: Instruction,
        pc: int,
        source_operands: list[_WordOrSlot],
    ):
        super().__init__(exec, instr, pc, source_operands)

        self.faulting_preceding = exec._faulting_inflight
        self.registers = exec._registers
        self.pc = pc

    def notify_result(self, slot: _SlotID, result: Word):
        super().notify_result(slot, result)

        _update_waiting_list(slot, result, self.registers)

    def notify_retired(self, slot: _SlotID):
        super().notify_retired(slot)

        self.faulting_preceding.remove(slot)

    def _tick_retire(self) -> Optional[tuple[Optional[_FaultState]]]:
        if not self.is_faulting():
            # We don't cause a fault and can retire immediately
            return (None,)

        # We want to cause a fault, but have to wait on preceding potentially faulting instructions
        # to be sure that our fault will actually be caused architecturally. We also have to wait
        # for the architectural register state to be known, so we know which register values to
        # restore when rolling back to the current architectural state.
        if self.faulting_preceding:
            return None
        for val in self.registers:
            if not isinstance(val, Word):
                return None

        # We are done waiting and allowed to cause a fault
        fault = _FaultState(cast(list[Word], self.registers), self.pc)
        return (fault,)

    def is_faulting(self) -> bool:
        """Check if this instruction causes a fault."""
        raise NotImplementedError("Must be overwritten by a concrete slot type")


@dataclass
class _SlotALU(_Slot):
    """An occupied slot in the Reservation Station, storing an ALU instruction."""

    instr_ty: Union[InstrReg, InstrImm]

    operands: list[_WordOrSlot]
    cycles_remaining: int

    def __init__(
        self,
        exec: ExecutionEngine,
        instr: Instruction,
        pc: int,
        source_operands: list[_WordOrSlot],
    ):
        super().__init__(exec, instr, pc, source_operands)

        # Instruction is either of type `InstrReg` or `InstrImm`
        ty = cast(Union[InstrReg, InstrImm], instr.ty)

        self.operands = source_operands
        self.cycles_remaining = ty.cycles

    def notify_result(self, slot: _SlotID, result: Word):
        super().notify_result(slot, result)

        _update_waiting_list(slot, result, self.operands)

    def _tick_execute(self) -> Optional[Word]:
        # Wait for operands to be available
        for op in self.operands:
            if not isinstance(op, Word):
                return None

        # Wait the specified amount of cycles
        self.cycles_remaining -= 1
        if self.cycles_remaining > 0:
            return None

        # `operands` contains no more `_SlotID`s, we checked that above
        operands = cast(list[Word], self.operands)
        # Compute the result and return it
        assert self.instr_ty.compute_result is not None
        return self.instr_ty.compute_result(*operands)

    def _tick_retire(self) -> Optional[tuple[Optional[_FaultState]]]:
        # Retire immediately without fault
        return (None,)


@dataclass
class _SlotLoad(_SlotFaulting):
    """An occupied slot in the Reservation Station, storing a load instruction."""

    instr_ty: InstrLoad

    # Memory instructions that have to be retired before this one executes due to hazards
    hazards: list[_SlotID]
    # Value loaded from memory
    value: WordAndFault
    # Cycles remaining for loading the value
    cycles_load: int
    # Cycles remaining for checking if the load faults
    cycles_fault: int

    def __init__(
        self,
        exec: ExecutionEngine,
        instr: Instruction,
        pc: int,
        source_operands: list[_WordOrSlot],
    ):
        super().__init__(exec, instr, pc, source_operands)

        # Instruction is of type `InstrLoad`
        ty = cast(InstrLoad, instr.ty)

        base = source_operands[0]
        offset = cast(Word, source_operands[1])

        # Only issue memory instructions when the effective address is available
        if not isinstance(base, Word):
            raise _InstructionNotIssued()

        # Compute effective address
        address = cast(Word, base) + offset

        # Check for hazards
        hazards = []
        for i, slot in enumerate(exec._slots):
            if isinstance(slot, _SlotLoad) and self._accesses_overlap(slot, address, ty):
                hazards.append(_SlotID(i))
        self.hazards = hazards

        # Perform load operation
        result = exec._mmu.read_word(address)
        self.value = result.value
        self.cycles_load = result.cycles_load
        self.cycles_fault = result.cycles_fault

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

    def notify_retired(self, slot: _SlotID):
        super().notify_retired(slot)

        self.hazards.remove(slot)

    def _tick_execute(self) -> Optional[Word]:
        # Wait until hazards are resolved
        if self.hazards:
            return None

        # Wait the specified amount of cycles
        self.cycles_load -= 1
        if self.cycles_load > 0:
            return None

        # Return loaded value
        return self.value[0]

    def _tick_retire(self) -> Optional[tuple[Optional[_FaultState]]]:
        # Wait the specified amount of cycles
        self.cycles_fault -= 1
        if self.cycles_fault > 0:
            return None

        # Delegate to base class
        return super()._tick_retire()

    def is_faulting(self) -> bool:
        return self.value[1]


@dataclass
class _SlotStore(_SlotFaulting):
    """An occupied slot in the Reservation Station, storing a store instruction."""

    instr_ty: InstrStore

    # Reference to MMU so we can perform store operations
    mmu: MMU
    # Memory instructions that have to be retired before this one executes due to hazards
    hazards: list[_SlotID]
    # Effective address of the memory access
    address: Word
    # Value stored to memory
    value: _WordOrSlot
    # Cycles remaining for checking if the store faults
    cycles_fault: int
    # Whether the store faults, or `None` if we have not yet performed the store
    faulting: Optional[bool]

    def notify_result(self, slot: _SlotID, result: Word):
        super().notify_result(slot, result)

        if self.value == slot:
            self.value = result

    def notify_retired(self, slot: _SlotID):
        super().notify_retired(slot)

        self.hazards.remove(slot)

    def _tick_execute(self) -> Optional[Word]:
        # Return dummy value, store operations have no output
        return Word(0)

    def _tick_retire(self) -> Optional[tuple[Optional[_FaultState]]]:
        # Wait until hazards are resolved
        if self.hazards:
            return None

        # Wait until the stored value is available
        if not isinstance(self.value, Word):
            return None

        # Before actually performing the store operation, we have to wait until all preceding
        # potentially faulting instructions are retired, because we don't roll back store operations
        if self.faulting_preceding:
            return None

        # Perform the store operation
        if self.faulting is None:
            faulting, cycles = self.mmu.write_word(self.address, self.value)
            self.faulting = faulting
            self.cycles_fault = cycles

        # Wait the specified amount of cycles
        self.cycles_fault -= 1
        if self.cycles_fault > 0:
            return None

        # Delegate to base class
        return super()._tick_retire()

    def is_faulting(self) -> bool:
        assert self.faulting is not None
        return self.faulting


@dataclass
class _SlotFlush(_SlotFaulting):
    """An occupied slot in the Reservation Station, storing a flush instruction."""

    instr_ty: InstrFlush

    # Effective address of the flush
    address: Word


@dataclass
class _SlotBranch(_SlotFaulting):
    """An occupied slot in the Reservation Station, storing a branch instruction."""

    instr_ty: InstrBranch

    destination: int
    prediction: bool
    operands: list[_WordOrSlot]


def _update_waiting_list(slot: _SlotID, result: Word, values: list[_WordOrSlot]):
    """Update waiting values using the result from the given slot."""
    for i, val in enumerate(values):
        if val == slot:
            values[i] = result


_slot_types = {
    InstrReg: _SlotALU,
    InstrImm: _SlotALU,
    InstrLoad: _SlotLoad,
    InstrStore: _SlotStore,
    InstrFlush: _SlotFlush,
    InstrBranch: _SlotBranch,
}


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

    # Register file, containing the architectural register state if all in-flight instructions were
    # completed
    _registers: list[_WordOrSlot]
    # Slots of the Reservation Station
    _slots: list[Optional[_Slot]]
    # Potentially faulting instructions in flight
    _faulting_inflight: list[_SlotID]

    def __init__(self, mmu, regs=32, slots=8):
        """Create a new Reservation Station, with empty slots and zeroed registers."""
        self._mmu = mmu

        # Initialize registers to zero
        self._registers = [Word(0) for _ in range(regs)]

        # Initialize slots to empty
        self._slots = [None for _ in range(slots)]

        # No instructions in flight
        self._faulting_inflight = []

    def try_issue(self, instr: Instruction, pc: int) -> bool:
        """Try to issue the instruction by putting it in a free slot, return `True` on success."""
        # Get source operands
        source_operands = self._source_operands(instr)

        # Create new slot object
        if instr.ty not in _slot_types:
            raise ValueError(f"Unsupported instruction type {instr.ty!r}")
        try:
            new_slot = _slot_types[instr.ty](self, instr, pc, source_operands)
        except _InstructionNotIssued:
            # Instruction should not be issued at the moment
            return False

        # Try to put new slot in a free slot
        for i, slot in enumerate(self._slots):
            if slot is not None:
                continue

            # Found a free slot, populate it
            self._slots[i] = new_slot

            # Mark destination register as waiting on new slot
            dst = instr.destination()
            if dst is not None:
                self._registers[dst] = _SlotID(i)

            return True
        return False

    def _source_operands(self, instr: Instruction) -> list[_WordOrSlot]:
        """Return the source operands of the given instruction."""
        sources = []
        for op, ty in instr.sources():
            if ty == "reg":
                val = self._registers[op]
            elif ty == "imm":
                val = Word(op)
            elif ty == "label":
                val = Word(op)
            else:
                raise ValueError(f"Unknown operand type {ty!r}")
            sources.append(val)
        return sources

    def tick(self) -> Optional[int]:
        """
        Execute instructions that are ready.

        If a fault occurs, return the address of the faulting instruction.
        """
        for i, slot in enumerate(self._slots):
            # Skip free slots
            if slot is None:
                continue

            if slot.executing:
                # Continue execution
                result = slot.tick_execute()
                if result is not None:
                    # Execution completed, notify other slots
                    self._notify_result(_SlotID(i), result)

            else:
                # Continue retirement
                retired = slot.tick_retire()
                if retired is not None:
                    # Retirement completed, check for fault
                    if retired[0] is None:
                        # No fault, notify other slots
                        self._notify_retired(_SlotID(i))
                        # Free retired slot
                        self._slots[i] = None
                    else:
                        # Fault occurred, roll back to given architectural state and notify frontend
                        state = retired[0]
                        self._rollback(state)
                        return state.pc

        # No fault occurred
        return None

    def _notify_result(self, slot_id: _SlotID, result: Word):
        """
        Notify all slots that the given slot produced the given result.

        This models broadcasting the given result on the CDB.
        """
        for slot in self._slots:
            if slot is None:
                continue

            slot.notify_result(slot_id, result)

    def _notify_retired(self, slot_id: _SlotID):
        """Notify all slots that the given slot retired without causing a fault."""
        for slot in self._slots:
            if slot is None:
                continue

            slot.notify_retired(slot_id)

    def _rollback(self, state: _FaultState):
        """Roll back to the given state."""
        self._registers = cast(list[_WordOrSlot], state.registers)
        self._slots = [None for _ in range(len(self._slots))]
        self._faulting_inflight = []
