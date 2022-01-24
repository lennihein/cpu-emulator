from bpu import SimpleBPU
from mmu import MMU
from word import Word
from frontend import Frontend
from parser import Parser, InstructionType
from execution import ReservationStation
import copy

class CPU:

    _parser: Parser

    _frontend: Frontend

    _bpu: SimpleBPU

    _mmu: MMU

    # Reservation stations.
    # Should we put this functionality in its own class (e.g. ExecutionEngine)?
    _num_reservation_stations: int = 4
    _reservation_stations: list[ReservationStation]

    # Snapshots. Intended for usage by the UI to allow users to
    # step forward/backwards freely.
    _snapshots: list[CPU]
    _snapshot_index: int

    def __init__(self):
        self._mmu = MMU(Word.WIDTH)

        # cannot initialize frontend without list of instructions
        # to execute
        self._frontend = None

        self._parser = Parser()
        # set of valid instructions
        self._parser.add_instruction(
            InstructionType("addi", ["reg", "reg", "imm"])
        )

        # Reservation stations
        self._reservation_stations = [ReservationStation() for _ in range(self._num_reservation_stations)]

        # Snapshots
        self._snapshots = [copy.deepcopy(self)]
        self._snapshot_index = 0

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

        # take snapshot
        self.take_snapshot()

        return True

    def tick(self) -> None:

        # check if any program is being executed
        if self._frontend is None:
            return

        # fill up instruction queue / reorder buffer
        self._frontend.add_instructions_to_queue()

        # For now we only take one instruction from the instruction qeueu per tick
        for _ in range(1):
            instr = self._frontend.fetch_instruction_from_queue()
            if instr is not None:
                for i, rs in enumerate(self._reservation_stations):
                    if rs.issue(instr):
                        self._frontend.pop_instruction_from_queue()
                        break

        # tick reservation stations
        for i, rs in enumerate(self._reservation_stations):
            rs.tick()

        # create snapshot
        self.take_snapshot()

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

    def take_snapshot(self) -> None:

        if self._snapshot_index < len(self._snapshots) - 1:
            # The snapshot index is not pointing to the last snapshot in the list.
            # This means a snapshot was restored recently. After doing so, it would
            # still have been possible to go forward to newer snapshots again.
            # But, now we create a new snapshot. Rather than keeping multiple lists
            # of snapshots that allow users to switch between different execution
            # paths, we forget about the snapshots that were taken after the point
            # to which we restored.
            self._snapshots = self._snapshots[:self._snapshot_index]

        cpu_copy = copy.deepcopy(self)
        # With our approach from above, there is no need to have each snapshot
        # maintain a full list of snapshots individually.
        cpu_copy._snapshots = self._snapshots

        self._snapshots.append(cpu_copy)

        self._snapshot_index += 1

    def get_snapshots(self) -> list[CPU]:
        return self._snapshots

    @staticmethod
    def restore_snapshot(cpu: CPU, steps: int) -> CPU:
        if cpu._snapshot_index + steps < 0 or cpu._snapshot_index + steps >= len(cpu._snapshots):
            return None

        return cpu._snapshots[cpu._snapshot_index + steps]
