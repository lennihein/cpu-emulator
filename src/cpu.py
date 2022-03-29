from __future__ import annotations

import copy

from .bpu import BPU, SimpleBPU
from .execution import ExecutionEngine, FaultInfo
from .frontend import Frontend, InstrFrontendInfo
from .instructions import InstructionKind, InstrBranch, InstrFlush, InstrLoad, InstrStore
from .memory import MemorySubsystem
from .parser import Parser

from dataclasses import dataclass


@dataclass
class CPUStatus:
    """Current status of the CPU."""

    # Whether the CPU is currently still executing a program.
    executing_program: bool

    # FaultInfo as provided by the execution engine if the
    # last tick caused an exception.
    fault_info: FaultInfo
    # If a fault has occurred , this variable contains the
    # corresponding microprogram that will be run.
    fault_microprog: str

    # List of program counters of instructions that have
    # been issued this tick.
    issued_instructions: list[int]


_snapshots: list[CPU] = []


class CPU:

    _parser: Parser

    _frontend: Frontend

    _bpu: BPU

    _mem: MemorySubsystem

    # Execution engine.
    _exec_engine: ExecutionEngine

    # Index for snapshot list.
    _snapshot_index: int

    _config: dict

    _microprograms: dict[str, list]

    def __init__(self, config: dict):

        self._config = config

        self._parser = Parser.from_default()

        self._mem = MemorySubsystem(config)

        if config["BPU"]["advanced"]:
            self._bpu = BPU(config)
        else:
            self._bpu = SimpleBPU(config)

        # cannot initialize frontend without list of instructions
        # to execute
        self._frontend = None

        # Reservation stations
        self._exec_engine = ExecutionEngine(self._mem, self._bpu, config)

        # Microprograms
        self._microprograms = {}
        for instr_type, filename in config["Microprograms"].items():
            if filename.lower() == "none":
                continue

            with open(filename, "r") as f:
                source = f.read()

            self._microprograms[instr_type.lower()] = (filename, self._parser.parse(source))

        # Snapshots
        global _snapshots
        self._snapshot_index = 0
        _snapshots = []
        _snapshots.append(copy.deepcopy(self))

    def load_program_from_file(self, path: str):
        with open(path, "r") as f:
            source = f.read()
        self.load_program(source)

    def load_program(self, source: str):
        instructions = self._parser.parse(source)

        # Initialize frontend
        self._frontend = Frontend(self._bpu, instructions, self._config)
        # Reset reservation stations?
        self._exec_engine = ExecutionEngine(self._mem, self._bpu, self._config)

        # take snapshot
        self._take_snapshot()

    def tick(self) -> CPUStatus:

        cpu_status: CPUStatus = CPUStatus(True, None, None, [])

        # fill execution units
        while self._frontend.get_instr_queue_size() > 0:
            instr_info: InstrFrontendInfo = self._frontend.fetch_instruction_from_queue()
            if self._exec_engine.try_issue(
                instr_info.instr, instr_info.instr_index, instr_info.prediction
            ):
                self._frontend.pop_instruction_from_queue()
                cpu_status.issued_instructions.append(instr_info.instr_index)
            else:
                break

        # tick execution engine
        if (fault_info := self._exec_engine.tick()) is not None:
            cpu_status.fault_info = fault_info

            resume_at_pc = fault_info.pc

            # For faulting memory instructions, we simply skip the instruction.
            # Normally, one would have to register an exception handler. We skip this
            # step for the sake of simplicity.
            if isinstance(fault_info.instr.ty, (InstrLoad, InstrStore, InstrFlush)):
                resume_at_pc += 1

            try:
                self._frontend.pc = resume_at_pc
            except IndexError:
                print("CRITICAL ERROR, PC OUT OF BOUNDS")
                exit(0)

            self._frontend.flush_instruction_queue()

            # If configured, pick the instruction type's corresponding microprogram
            # and run it.
            filename, microprogram = self._pick_microprogram(fault_info.instr.ty)
            if microprogram is not None:
                self._frontend.add_micro_program(microprogram)
                cpu_status.fault_microprog = filename

            # If the instruction that caused the rollback is a branch
            # instruction, we notify the front end which makes sure
            # the correct path is taken next time.
            if isinstance(fault_info.instr.ty, InstrBranch):
                self._frontend.add_instructions_after_branch(
                    not fault_info.prediction, fault_info.pc
                )

        # fill up instruction queue
        self._frontend.add_instructions_to_queue()

        # create snapshot
        self._take_snapshot()

        # check if any program is being executed
        if self._frontend is None:
            return CPUStatus(False, None, None, [])

        if self._frontend.is_done() and self._exec_engine.is_done():
            return CPUStatus(False, None, None, [])

        return cpu_status

    def get_memory_subsystem(self) -> MemorySubsystem:
        """Returns an instance of the MS class."""
        return self._mem

    def get_frontend(self) -> Frontend:
        """
        Returns an instance of the Frontend class if a program is currently
        being executed.

        Otherwise, 'None' is returned.
        """
        return self._frontend

    def get_bpu(self) -> BPU:
        """Returns an instance of the BPU class."""
        return self._bpu

    def get_exec_engine(self) -> ExecutionEngine:
        '''Returns an instance of the ExecutionEngine class.'''
        return self._exec_engine

    def _take_snapshot(self) -> None:
        """
        This function creates a snapshot of the current CPU instance by deepcopying
        it and adding an entry to the global snapshot list. Note that the snapshot
        list is not part of the CPU class.
        """
        global _snapshots

        if self._snapshot_index < len(_snapshots) - 1:
            # The snapshot index is not pointing to the last snapshot in the list.
            # This means a snapshot was restored recently. After doing so, it would
            # still have been possible to go forward to newer snapshots again.
            # But, now we create a new snapshot. Rather than keeping multiple lists
            # of snapshots that allow users to switch between different execution
            # paths, we forget about the snapshots that were taken after the point
            # to which we restored.
            # It is important that we copy the cpu instance stored in the snapshot
            # list, rather than using "self.deepcopy()" here. In case this class
            # instance (self) was changed before taking this snapshot, we would
            # be altering the snapshot list at the index pointed to by snapshot_index.
            current_cpu = copy.deepcopy(_snapshots[self._snapshot_index])

            # Now we strip the snapshot list of all more recent invalid snapshots.
            _snapshots = _snapshots[: self._snapshot_index]
            _snapshots.append(current_cpu)

            # Finally, we can add the potentially modified version of this instance
            # to the snapshot list (as the most recent snapshot).

        self._snapshot_index += 1
        cpu_copy = copy.deepcopy(self)

        _snapshots.append(cpu_copy)

    def get_snapshots(self) -> list[CPU]:
        """ Returns the current snapshots. """
        global _snapshots
        return _snapshots

    @staticmethod
    def restore_snapshot(cpu: CPU, steps: int) -> CPU:
        """
        Given a CPU instance, this function returns a snapshot from 'steps' cycles
        in the future or past.

        Paremters:
            cpu (CPU) -- The CPU instance relative to which the snapshot should be chosen.
            steps (int) -- How many time steps away the desired snapshot is.

        Returns:
            CPU: A deepcopy of the corresponding CPU instance from the snapshot list.
        """
        global _snapshots
        if cpu._snapshot_index + steps < 1 or cpu._snapshot_index + steps >= len(_snapshots):
            return None

        # Returning copies is important, as otherwise a manipulation
        # of the returned cpu instance (for example, calling tick),
        # changes the class that is stored in the snapshot list.
        return copy.deepcopy(_snapshots[cpu._snapshot_index + steps])

    def _pick_microprogram(self, instr_type: InstructionKind) -> tuple(str, list):
        """
        Returns the filename and set of instructions of a microprogram given
        an instruction type.

        Parameters:
            instr_type (InstructionKind) -- The instruction for which to pick
                the corresponding microprogram.

        Returns:
            tuple[str, list]: A filename of the microprogram and its instructions.
                None if no microprogram could be found.
        """
        key = instr_type.__class__.__name__.lower()
        if key in self._microprograms:
            return self._microprograms[key]
        return None, None
