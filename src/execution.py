"""Execution Engine that executes instructions out-of-order."""

from dataclasses import dataclass
from typing import NewType, Optional, TypeVar, Union, cast, final

from .byte import Byte
from .instructions import (
    InstrBranch,
    InstrCyclecount,
    InstrFence,
    InstrFlush,
    InstrImm,
    InstrLoad,
    InstrReg,
    InstrStore,
    Instruction,
    InstructionKind,
)
from .mmu import MMU, MemResult
from .word import Word

_T = TypeVar("_T")

# ID of a slot of the Reservation Station, also used as an index into the list of slots
_SlotID = NewType("_SlotID", int)
# Either a `Word` with a concrete value, or a `_SlotID` referencing the slot that will produce the
# value
_WordOrSlot = Union[Word, _SlotID]


@dataclass
class FaultInfo:
    """Information about a fault that occurred, passed back to the CPU class."""

    # PC of the faulting instruction
    pc: int
    # Kind of the faulting instruction
    kind: InstructionKind
    # Predicted branch condition if the instruction is a branch
    prediction: Optional[bool] = None
    # Faulting address if applicable to the instruction kind
    address: Optional[Word] = None


@dataclass
class _FaultState:
    """Architectural state at the time a fault occurs, and additional information about it."""

    registers: list[Word]
    info: FaultInfo


@dataclass
class _ArgsSlot:
    """Arguments to the `Slot` constructor, just to avoid having to repeat them on each subclass."""

    exe: "ExecutionEngine"
    instr: Instruction
    pc: int
    source_operands: list[_WordOrSlot]
    prediction: Optional[bool]


def _update_waiting_list(slot: _SlotID, result: Word, values: list[_WordOrSlot]):
    """Update waiting values using the result from the given slot."""
    for i, val in enumerate(values):
        if val == slot:
            values[i] = result


class _Slot:
    """
    An occupied slot in the Reservation Station, storing an instruction in flight.

    Every instruction goes through two phases: executing and retiring. Executing instructions are in
    the process of computing their result value. Retiring instructions have already produced their
    result, but have not yet determined if they cause a fault.
    """

    # Kind of this instruction
    instr_ty: InstructionKind
    # Whether we are executing or retiring
    executing: bool
    # Whether we are retired
    retired: bool
    # Source operands
    operands: list[_WordOrSlot]

    def __init__(self, args: _ArgsSlot):
        self.instr_ty = args.instr.ty
        self.executing = True
        self.retired = False
        self.operands = args.source_operands

    def notify_result(self, slot: _SlotID, result: Word):
        """Notify this slot that the given slot produced the given result."""
        _update_waiting_list(slot, result, self.operands)

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


class _SlotFaulting(_Slot):
    """An occupied slot in the Reservation Station, storing a potentially-faulting instruction."""

    # Slots of potentially faulting instructions that precede this instruction in program order
    faulting_preceding: set[_SlotID]
    # Architectural register state when this instruction was issued
    registers: list[_WordOrSlot]
    # Address of this instruction
    pc: int

    def __init__(self, args: _ArgsSlot):
        super().__init__(args)

        self.faulting_preceding = args.exe._faulting_inflight.copy()
        self.registers = args.exe._registers.copy()
        self.pc = args.pc

    def notify_result(self, slot: _SlotID, result: Word):
        super().notify_result(slot, result)

        _update_waiting_list(slot, result, self.registers)

    def notify_retired(self, slot: _SlotID):
        super().notify_retired(slot)

        if slot in self.faulting_preceding:
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
        info = FaultInfo(self.pc, self.instr_ty)
        self.populate_fault_info(info)
        fault = _FaultState(cast(list[Word], self.registers), info)
        return (fault,)

    def is_faulting(self) -> bool:
        """Check if this instruction causes a fault."""
        raise NotImplementedError("Must be overwritten by a concrete slot type")

    def populate_fault_info(self, info: FaultInfo):
        """Populate information about the fault."""


class _SlotMem(_SlotFaulting):
    """An occupied slot in the Reservation Station, storing a memory instruction."""

    instr_ty: Union[InstrLoad, InstrStore, InstrFlush]

    # Reference to MMU so we can perform memory operations
    mmu: MMU
    # Reference to Execution Engine so we can check for hazards
    exe: "ExecutionEngine"
    # Effective address of the memory access, or `None` if it is not yet available
    address: Optional[Word]
    # Memory instructions that have to be retired before this one executes due to hazards, or `None`
    # if the effective address is not yet available
    hazards: Optional[set[_SlotID]]
    # Result of the memory operation, or `None` if we have not yet performed it
    result: Optional[MemResult]

    def __init__(self, args: _ArgsSlot):
        super().__init__(args)

        self.mmu = args.exe._mmu
        self.exe = args.exe
        self.address = None
        self.hazards = None
        self.result = None

    def notify_retired(self, slot: _SlotID):
        super().notify_retired(slot)

        if self.hazards is not None and slot in self.hazards:
            self.hazards.remove(slot)

    def _tick_execute(self) -> Optional[Word]:
        base = self.operands[0]
        offset = self.operands[1]
        assert isinstance(offset, Word)

        # Wait for base register to be available
        if not isinstance(base, Word):
            return None

        # Compute effective address
        if self.address is None:
            self.address = base + offset

        # Determine hazards
        if self.hazards is None:
            hazards = set()
            # Hazards can only be caused by preceding potentially-faulting instructions (because all
            # memory instructions are potentially-faulting), so we only check these
            for slot_id in self.faulting_preceding:
                slot = self.exe._slots[slot_id]
                # We only care about memory instructions
                if not isinstance(slot, _SlotMem):
                    continue
                # We have to wait until the effective address is available
                if slot.address is None:
                    return None
                # Check if accesses overlap
                if self._accesses_overlap(slot):
                    hazards.add(slot_id)
            self.hazards = hazards

        # Wait for hazards
        if self.hazards:
            return None

        # Perform memory operation
        if self.result is None:
            result = self._perform_access()
            if result is None:
                return None
            # Zero-extend a byte result to a word
            if isinstance(result.value, Byte):
                result.value = result.value.zero_extend()
            self.result = result

        # Wait until we want to return the value
        self.result.cycles_value -= 1
        if self.result.cycles_value > 0:
            return None

        # Return the value
        assert not isinstance(self.result.value, Byte)
        return self.result.value

    def _accesses_overlap(self, other: "_SlotMem") -> bool:
        """Check if two memory accesses overlap."""

        def access(slot):
            addr = slot.address
            width = slot.instr_ty.width
            return {addr + Word(i) for i in range(width)}

        return bool(access(self) & access(other))

    def _perform_access(self) -> Optional[MemResult]:
        """Perform the memory operation and return its result if it is done."""
        raise NotImplementedError("Must be overwritten by a concrete slot type")

    def _tick_retire(self) -> Optional[tuple[Optional[_FaultState]]]:
        assert self.result is not None

        # Wait until we want to signal whether we fault
        self.result.cycles_fault -= 1
        if self.result.cycles_fault > 0:
            return None

        # Delegate to base class
        return super()._tick_retire()

    def is_faulting(self) -> bool:
        assert self.result is not None
        return self.result.fault

    def populate_fault_info(self, info: FaultInfo):
        assert self.address is not None
        info.address = self.address


class _SlotALU(_Slot):
    """An occupied slot in the Reservation Station, storing an ALU instruction."""

    instr_ty: Union[InstrReg, InstrImm]

    cycles_remaining: int

    def __init__(self, args: _ArgsSlot):
        super().__init__(args)

        self.cycles_remaining = self.instr_ty.cycles

    def _tick_execute(self) -> Optional[Word]:
        # Wait for operands to be available
        for op in self.operands:
            if not isinstance(op, Word):
                return None

        # Wait the specified amount of cycles
        self.cycles_remaining -= 1
        if self.cycles_remaining > 0:
            return None

        # `operands` contains no more `_SlotID`s
        operands = cast(list[Word], self.operands)
        # Compute the result and return it
        assert self.instr_ty.compute_result is not None
        return self.instr_ty.compute_result(*operands)

    def _tick_retire(self) -> Optional[tuple[Optional[_FaultState]]]:
        # Retire immediately without a fault
        return (None,)


class _SlotLoad(_SlotMem):
    """An occupied slot in the Reservation Station, storing a load instruction."""

    instr_ty: InstrLoad

    def _perform_access(self) -> Optional[MemResult]:
        assert self.address is not None

        # Perform the load operation
        if self.instr_ty.width_byte:
            return self.mmu.read_byte(self.address)
        else:
            return self.mmu.read_word(self.address)


class _SlotStore(_SlotMem):
    """An occupied slot in the Reservation Station, storing a store instruction."""

    instr_ty: InstrStore

    def _perform_access(self) -> Optional[MemResult]:
        assert self.address is not None
        value = self.operands[2]

        # Wait until the stored value is available
        if not isinstance(value, Word):
            return None

        # Before actually performing the store operation, we have to wait until all preceding
        # potentially faulting instructions are retired, because we don't roll back store operations
        if self.faulting_preceding:
            return None

        # Perform the store operation
        if self.instr_ty.width_byte:
            return self.mmu.write_byte(self.address, Byte(value.value))
        else:
            return self.mmu.write_word(self.address, value)


class _SlotFlush(_SlotMem):
    """An occupied slot in the Reservation Station, storing a flush instruction."""

    instr_ty: InstrFlush

    def _perform_access(self) -> Optional[MemResult]:
        assert self.address is not None

        # Perform the flush operation
        return self.mmu.flush_line(self.address)


class _SlotBranch(_SlotFaulting):
    """An occupied slot in the Reservation Station, storing a branch instruction."""

    instr_ty: InstrBranch

    prediction: bool
    cycles_remaining: int
    condition: Optional[bool]

    def __init__(self, args: _ArgsSlot):
        super().__init__(args)

        assert args.prediction is not None
        self.prediction = args.prediction

        self.cycles_remaining = self.instr_ty.cycles
        self.condition = None

    def _tick_execute(self) -> Optional[Word]:
        # Wait for operands to be available
        for op in self.operands:
            if not isinstance(op, Word):
                return None

        # Wait the specified amount of cycles
        self.cycles_remaining -= 1
        if self.cycles_remaining > 0:
            return None

        # `operands` contains no more `_SlotID`s
        operands = cast(list[Word], self.operands)
        # Compute the branch condition
        assert self.instr_ty.condition is not None
        self.condition = self.instr_ty.condition(*operands)

        # Return dummy value
        return Word(0)

    def is_faulting(self) -> bool:
        return self.condition != self.prediction

    def populate_fault_info(self, info: FaultInfo):
        info.prediction = self.prediction


class _SlotCyclecount(_Slot):
    """An occupied slot in the Reservation Station, storing a cyclecount instruction."""

    instr_ty: InstrCyclecount

    # Reference to execution engine, so we can query the cycle counter
    exe: "ExecutionEngine"

    def __init__(self, args: _ArgsSlot):
        super().__init__(args)

        self.exe = args.exe

    def _tick_execute(self) -> Optional[Word]:
        # Return the current value of the cycle counter immediately
        return Word(self.exe._cyclecount)

    def _tick_retire(self) -> Optional[tuple[Optional[_FaultState]]]:
        # Retire immediately without a fault
        return (None,)


class _SlotFence(_Slot):
    """An occupied slot in the Reservation Station, storing a fence instruction."""

    instr_ty: InstrFence

    # Slots of instructions that precede this instruction in program order
    preceding: set[_SlotID]

    def __init__(self, args: _ArgsSlot):
        super().__init__(args)

        # IDs of all slots that are not empty
        self.preceding = {_SlotID(i) for i, slot in enumerate(args.exe._slots) if slot is not None}

    def notify_retired(self, slot: _SlotID):
        super().notify_retired(slot)

        if slot in self.preceding:
            self.preceding.remove(slot)

    def _tick_execute(self) -> Optional[Word]:
        # Wait for preceding instructions to retire
        if self.preceding:
            return None

        # Return dummy value
        return Word(0)

    def _tick_retire(self) -> Optional[tuple[Optional[_FaultState]]]:
        # Retire immediately without a fault
        return (None,)


def _get_slot_type(kind: InstructionKind) -> type:
    if isinstance(kind, (InstrReg, InstrImm)):
        return _SlotALU
    if isinstance(kind, InstrLoad):
        return _SlotLoad
    if isinstance(kind, InstrStore):
        return _SlotStore
    if isinstance(kind, InstrFlush):
        return _SlotFlush
    if isinstance(kind, InstrBranch):
        return _SlotBranch
    if isinstance(kind, InstrCyclecount):
        return _SlotCyclecount
    if isinstance(kind, InstrFence):
        return _SlotFence

    raise ValueError(f"Unsupported instruction kind {kind!r}")


class ExecutionEngine:
    """
    Execution Engine that executes instructions out-of-order.

    The Execution Engine contains the register file and the Reservation Station. The Reservation
    Station is completely unified, i.e. each slot can contain any kind of instruction. We don't
    explicitly model Load Buffers or Store Buffers; the specifics of memory operations are handled
    by the Slots themselves.

    Each slot is either free or contains an `Instruction` in flight. The number of instructions that
    can execute concurrently is only limited by the amount of slots; we don't model individual
    Execution Units and just pretend there is an infinite number of them.

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
    _faulting_inflight: set[_SlotID]
    # Cycle counter, incremented on each tick
    _cyclecount: int

    def __init__(self, mmu, regs=32, slots=8):
        """Create a new Reservation Station, with empty slots and zeroed registers."""
        self._mmu = mmu

        # Initialize registers to zero
        self._registers = [Word(0) for _ in range(regs)]

        # Initialize slots to empty
        self._slots = [None for _ in range(slots)]

        # No instructions in flight
        self._faulting_inflight = set()

        # Initialize cycle counter
        self._cyclecount = 0

    def try_issue(self, instr: Instruction, pc: int, prediction: Optional[bool] = None) -> bool:
        """Try to issue the instruction by putting it in a free slot, return `True` on success."""
        # Don't issue any instructions while a fence instruction is in flight
        if any(isinstance(slot, _SlotFence) for slot in self._slots):
            return False

        # Get source operands
        source_operands = self._source_operands(instr)

        # Create new slot object
        args = _ArgsSlot(self, instr, pc, source_operands, prediction)
        new_slot = _get_slot_type(instr.ty)(args)

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

            # Update list of potentially faulting slots
            if isinstance(new_slot, _SlotFaulting):
                self._faulting_inflight.add(_SlotID(i))

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

    def tick(self) -> Optional[FaultInfo]:
        """
        Execute instructions that are ready.

        If a fault occurs, return information about the fault.
        """
        # Increment cycle counter
        self._cyclecount += 1

        # Iterate over all slots
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
                    state = retired[0]
                    if state is None:
                        # No fault, notify other slots
                        self._notify_retired(_SlotID(i))
                        # Free retired slot
                        self._slots[i] = None
                    else:
                        # Fault occurred, roll back to given architectural state and notify frontend
                        self._rollback(state)
                        return state.info

        # No fault occurred
        return None

    def _notify_result(self, slot_id: _SlotID, result: Word):
        """
        Notify all slots that the given slot produced the given result.

        This models broadcasting the given result on the CDB.
        """
        # Update register file
        for i, reg in enumerate(self._registers):
            if reg == slot_id:
                self._registers[i] = result

        # Notify slots
        for slot in self._slots:
            if slot is not None:
                slot.notify_result(slot_id, result)

    def _notify_retired(self, slot_id: _SlotID):
        """Notify all slots that the given slot retired without causing a fault."""
        # Remove retired slot from list of potentially faulting slots
        if slot_id in self._faulting_inflight:
            self._faulting_inflight.remove(slot_id)

        # Notify slots
        for slot in self._slots:
            if slot is None:
                continue

            slot.notify_retired(slot_id)

    def _rollback(self, state: _FaultState):
        """Roll back to the given state."""
        self._registers = cast(list[_WordOrSlot], state.registers)
        self._slots = [None for _ in range(len(self._slots))]
        self._faulting_inflight = set()
