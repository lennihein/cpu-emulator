"""
Frontend for the CPU instruction management.

Holds and manages a queue of instructions.
Instructions are taken from a list provided by the parser
and added to the queue with respect to branch management (bpu).
Instructions can be fetched from the queue, e.g. by reservation stations.
Supports flushing the queue and adding a micro program directly to the queue.
"""


from . import bpu
from . import instructions
from collections import deque
from dataclasses import dataclass


@dataclass
class InstrFrontendInfo:
    '''
    Holds an instruction, e.g. from the instruction list provided by the parser,
    with the additional information needed by the CPU and execution engine.
    Keeps track of the index from the instruction list for each instruction.
    Keeps track of the BPU prediction for branch instructions
    at the time the instruction is added to the queue.
    '''

    instr: instructions.Instruction
    instr_index: int
    prediction: bool


class Frontend:
    '''
    Holds and manages a queue of at most max_length InstrFrontendInfo objects.
    These contain an instruction from the parser instruction list,
    their respective instruction index from the parser list
    and their bpu prediction at the time they are added to the queue
    if they are a branch instruction.
    An exception to this max length is made when adding micro programs.
    Expects an already initialised bpu (e.g. shallow copy of the bpu from a surrounding cpu class)
    and a list of instructions (e.g. as provided by the Parser in paser.py) upon initilisation.
    Max_length can be initialised, too, otherwise a default of 5 is used.
    Uses a program counter pc to keep track of
    the next instruction from the provided instruction list that should be added to the queue.
    '''

    max_length: int
    pc: int
    bpu: bpu.BPU

    def __init__(self, cpu_bpu: bpu.BPU, cpu_instr_list, maximum=5) -> None:

        self.max_length = maximum
        self.current_length = 0
        self.pc = 0
        self.bpu = cpu_bpu
        self.instr_list = cpu_instr_list
        self.instr_queue = deque()

    def add_instructions_to_queue(self) -> None:
        '''
        Fills the queue with the InstrFrontendInfo objects
        for th next instructions from the instruction list, as indicated by the pc.

        Only adds an instruction, if max_langth is not yet reached
        and the pc does not exceed the number of instructions in the instr_list.
        If the queue is full, the function returns without further effect.

        If the instruction currently added to the list is of the type InstrBranch,
        the pc for the next instruction is set according to the label/ number
        provided by the instruction and the bpu prediction for the branch instruction.
        Important: jump and branching instructions need to be explicitly registered as InstrBranch,
        not the more generic InstructionType, in the instruction list from the parser.
        For all other instructions, the pc is set to the next instruction in the list.

        Currently, this functions interacts directly with the bpu to get predictions.
        This has to be modified if a branch order buffer should be used.
        '''

        while ((len(self.instr_queue) < self.max_length)
               and (self.pc < len(self.instr_list))):

            # sanity check, should never happen since the set_pc function
            # checks for this too and jump goals are set by the parser from
            # labels within the code
            if self.pc < 0:
                raise IndexError("pc negative")

            current_instr: instructions.Instruction = self.instr_list[self.pc]
            current_prediction: bool = None
            current_pc: int = self.pc

            # this needs to be modified if further jump instruction types are
            # implemented
            if isinstance(current_instr.ty, instructions.InstrBranch):

                # true if branch was/ should be taken
                current_prediction = self.bpu.predict(self.pc)

                if current_prediction:
                    self.pc = current_instr.ops[-1]

                else:
                    self.pc = self.pc + 1

            else:

                self.pc = self.pc + 1

            current_instr_info = InstrFrontendInfo(
                current_instr, current_pc, current_prediction)
            self.instr_queue.append(current_instr_info)

        return

    def add_micro_program(
            self, micro_prog: list[instructions.Instruction]) -> None:
        '''
        Adds a list of instructions with their info as a µ-program to the queue.
        The queue is not automatically flushed.
        This can be done separately as a "mitigation" against Meltdown.
        The max_length of the queue is disregarded when adding the µ-program,
        so µ-programs can be arbitrarily long and added to full queues.
        If the µ-code contains jump instructions,
        the pc will be set according to the last of these jump instructions.
        The BPU does not affect the µ-program and the jump is always taken.
        The respective instruction index is -1 for alle instructions in the µ-program.
        '''

        for current_instr in micro_prog:

            current_instr_info = InstrFrontendInfo(current_instr, -1, None)
            self.instr_queue.append(current_instr_info)

            if isinstance(current_instr.ty, instructions.InstrBranch):

                self.pc = current_instr.ops[0]

        return

    def add_instructions_after_branch(
            self, taken: bool, instr_index: int) -> None:
        '''
        Takes the index of a branch instruction in the instruction list
        and a boolen whether or not this branch should be taken as arguments.
        Adds the given branch instruction to the queue with the correct boolean
        instead of the respective BPU prediction.
        Fills the rest of the instruction queue accordingly.
        Does not automatically flush the queue beforehand.
        '''

        # sanity check, should always be the case
        if (instr_index >= 0 and instr_index < len(self.instr_list)):

            current_instr: instructions.Instruction = self.instr_list[instr_index]

            # sanity check, should always be the case
            # this needs to be modified if further jump instruction types are
            # implemented
            if isinstance(current_instr.ty, instructions.InstrBranch):

                if taken:
                    self.pc = current_instr.ops[0]

                else:
                    self.pc = instr_index + 1

            else:

                raise TypeError(
                    f"index {instr_index!r} does not point to a branch instruction")

            current_instr_info = InstrFrontendInfo(
                current_instr, instr_index, taken)
            self.instr_queue.append(current_instr_info)

            self.add_instructions_to_queue()

        else:
            raise IndexError("instruction index out of range")

        return

    def pop_instruction_from_queue(self) -> InstrFrontendInfo:
        '''
        Deletes the first (current first in) instruction with it's info
        from the instruction queue and returns it.
        '''

        if len(self.instr_queue) > 0:
            return self.instr_queue.popleft()

        else:
            raise LookupError("instruction queue is empty")

    def fetch_instruction_from_queue(self) -> InstrFrontendInfo:
        '''
        Returns the first (current first in) instruction with it's info
        from the instruction queue.
        It is are not deleted from the queue.
        '''

        if len(self.instr_queue) > 0:
            return self.instr_queue[0]

        else:
            raise LookupError("instruction queue is empty")

    def pop_refill(self) -> InstrFrontendInfo:
        '''
        Pop the first instruction from the queue
        and automatically refill the queue with
        the next instruction(s).
        Does not handle any raised exceptions.
        '''

        current_instr = self.pop_instruction_from_queue()
        self.add_instructions_to_queue()
        return current_instr

    def get_instr_queue_size(self):
        '''
        Returns the number of instructions currently scheduled in the instruction queue.
        '''

        size = len(self.instr_queue)
        return size

    def flush_instruction_queue(self) -> None:
        '''
        Empties the instruction queue.
        Does not adjust the pc.
        This has to be done separately,
        otherwise the instructions that were flushed from the queue will be silently skipped.
        '''

        self.instr_queue.clear()
        return

    def set_pc(self, new_pc: int) -> None:
        '''
        Provides an interface to change the program counter
        to an arbitrary position within the instruction list.
        Does not consider or change the instructions which are already in the instruction queue.
        '''

        if (new_pc >= 0 and new_pc < len(self.instr_list)):

            self.pc = new_pc

        else:
            raise IndexError("new pc out of range")

        return

    def get_pc(self) -> int:
        '''
        Interface to retrieve the current value of the program counter.
        '''

        return self.pc

    def is_done(self) -> bool:
        '''
        Returns true if the frontend has fully handled the program,
        i.e. has reached the end of the instr_list
        and all instructions and their info have been removed from the queue.
        This status can reverse from True to False, e.g. if
        µ-programs are added, instructions are added after a branch
        or the pc is adjusted via set_pc.
        '''

        if (self.pc >= len(self.instr_list)) and (len(self.instr_queue) == 0):

            return True

        else:

            return False
