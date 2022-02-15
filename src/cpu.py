from __future__ import annotations
from .bpu import SimpleBPU
from .mmu import MMU
from .frontend import Frontend
from .parser import Parser
from .execution import ExecutionEngine
import copy


class CPU:

    _parser: Parser

    _frontend: Frontend

    _bpu: SimpleBPU

    _mmu: MMU

    # Execution engine.
    _exec_engine: ExecutionEngine

    # Snapshots. Intended for usage by the UI to allow users to
    # step forward/backwards freely.
    _snapshots: list[CPU]
    _snapshot_index: int

    def __init__(self):

        self._parser = Parser()

        self._mmu = MMU()

        self._bpu = SimpleBPU()

        # cannot initialize frontend without list of instructions
        # to execute
        self._frontend = None

        # Reservation stations
        self._exec_engine = ExecutionEngine(self._mmu)

        # Snapshots
        self._snapshot_index = 0
        self._snapshots = [copy.deepcopy(self)]

    def load_program(self, file_path: str) -> bool:

        file_contents = None
        try:

            with open(file_path, 'r') as file:
                file_contents = file.readlines()

        except IOError:
            return False

        instructions = self._parser.parse((file_contents))

        self._frontend = Frontend(self._bpu, instructions)

        # reset reservation stations?
        # self._exec_engine = ExecutionEngine(self.mmu)

        # take snapshot
        self._take_snapshot()

        return True

    def tick(self) -> None:

        # check if any program is being executed
        if self._frontend is None:
            return

        # fill up instruction queue / reorder buffer
        self._frontend.add_instructions_to_queue()

        # fill execution units
        while self._frontend.get_instr_queue_size() > 0:
            instr, instr_index = self._frontend.fetch_instruction_from_queue()
            if self._exec_engine.try_issue(instr, instr_index):
                self._frontend.pop_instruction_from_queue()
            else:
                break

        # tick execution engine
        if (rollback_pc := self._exec_engine.tick()) is not None:
            # TODO
            self._frontend.set_pc(rollback_pc)

        # create snapshot
        self._take_snapshot()

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

    def deepcopy(self):
        """
        This function returns a deepcopy of a CPU instance, with the
        exception of the snapshot list, which is shallow copied.

        The intended use of this function is when creating
        and restoring snapshots, as each snapshot having a list
        of snapshots is inefficent.
        """
        # Deepcopy already is insanely slow, this way we prevent
        # the snapshot list from being copied as well.
        cpu_copy = CPU()

        cpu_copy._parser = copy.deepcopy(self._parser)
        cpu_copy._frontend = copy.deepcopy(self._frontend)
        cpu_copy._bpu = copy.deepcopy(self._bpu)
        cpu_copy._mmu = copy.deepcopy(self._mmu)
        cpu_copy._exec_engine = copy.deepcopy(self._exec_engine)

        cpu_copy._snapshots = self._snapshots
        cpu_copy._snapshot_index = copy.deepcopy(self._snapshot_index)

        return cpu_copy

    def _take_snapshot(self) -> None:

        if self._snapshot_index < len(self._snapshots) - 1:
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
            current_cpu = self._snapshots[self._snapshot_index].deepcopy()

            # Now we strip the snapshot list of all more recent invalid snapshots.
            self._snapshots = self._snapshots[:self._snapshot_index]
            self._snapshots.append(current_cpu)

            # Finally, we can add the potentially modified version of this instance
            # to the snapshot list (as the most recent snapshot).

        self._snapshot_index += 1
        cpu_copy = self.deepcopy()

        self._snapshots.append(cpu_copy)

    def get_snapshots(self) -> list[CPU]:
        return self._snapshots

    @staticmethod
    def restore_snapshot(cpu: CPU, steps: int) -> CPU:
        if cpu._snapshot_index + steps < 0 or cpu._snapshot_index + \
                steps >= len(cpu._snapshots):
            return False

        # Returning copies are is important, as otherwise a manipulation
        # of the returned cpu instance (for example, calling tick),
        # changes the class that is stored in the snapshot list.
        return cpu._snapshots[cpu._snapshot_index + steps].deepcopy()
