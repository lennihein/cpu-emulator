from __future__ import annotations

import copy

from .bpu import BPU, SimpleBPU
from .execution import ExecutionEngine, FaultInfo
from .frontend import Frontend, InstrFrontendInfo
from .instructions import InstrBranch, InstrFlush, InstrLoad, InstrStore
from .mmu import MMU
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

    # List of program counters of instructions that have
    # been issued this tick.
    issued_instructions: list[int]


_snapshots: list[CPU] = []


class CPU:

    _parser: Parser

    _frontend: Frontend

    _bpu: BPU

    _mmu: MMU

    # Execution engine.
    _exec_engine: ExecutionEngine

    # Snapshots. Intended for usage by the UI to allow users to
    # step forward/backwards freely.
    _snapshots: list[CPU] = []
    _snapshot_index: int

    _config: dict

    def __init__(self, config):

        self._config = config

        self._parser = Parser.from_default()

        self._mmu = MMU(config)

        if config["BPU"]["advanced"]:
            self._bpu = BPU(config)
        else:
            self._bpu = SimpleBPU(config)

        # cannot initialize frontend without list of instructions
        # to execute
        self._frontend = None

        # Reservation stations
        self._exec_engine = ExecutionEngine(self._mmu, self._bpu, config)

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
        self._exec_engine = ExecutionEngine(self._mmu, self._bpu, self._config)

        # take snapshot
        self._take_snapshot()

    def tick(self) -> CPUStatus:

        # check if any program is being executed
        if self._frontend is None:
            return CPUStatus(False, None, [])

        if self._frontend.is_done() and self._exec_engine.is_done():
            return CPUStatus(False, None, [])

        cpu_status: CPUStatus = CPUStatus(True, None, [])

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
                self._frontend.set_pc(resume_at_pc)
            except IndexError:
                # program has ended
                return CPUStatus(False, None, [])
            self._frontend.flush_instruction_queue()

            # If the instruction that caused the rollback is a branch
            # instruction, we notify the front end which makes sure
            # the correct path is taken next time.
            if isinstance(fault_info.instr.ty, InstrBranch):
                self._frontend.add_instructions_after_branch(
                    not fault_info.prediction, fault_info.pc
                )

        # fill up instruction queue / reorder buffer
        self._frontend.add_instructions_to_queue()

        # create snapshot
        self._take_snapshot()

        return cpu_status

    def get_mmu(self) -> MMU:
        """Returns an instance of the MMU class."""
        return self._mmu

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
        global _snapshots
        return _snapshots

    @staticmethod
    def restore_snapshot(cpu: CPU, steps: int) -> CPU:
        global _snapshots
        if cpu._snapshot_index + steps < 1 or cpu._snapshot_index + steps >= len(_snapshots):
            return None

        # Returning copies are is important, as otherwise a manipulation
        # of the returned cpu instance (for example, calling tick),
        # changes the class that is stored in the snapshot list.
        return copy.deepcopy(_snapshots[cpu._snapshot_index + steps])
