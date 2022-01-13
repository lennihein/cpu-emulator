"""
Frontend for the CPU instruction management.

Holds and manages a queue of instructions.
Instructions are taken from a list provided by the parser and added to the queue with respect to branch management (bpu).
Instructions can be fetched from the queue, e.g. by reservation stations.
Supports flushing the queue and adding a micro program directly to the queue.

TODO:discuss other points as indicated in the code.
TODO:make the test prettier/ maybe split it up between functions.

# Example

>>> import bpu
>>> import parser
>>> cpu_bpu = bpu.BPU()
>>> addi = parser.InstructionType("addi", ["reg", "reg", "imm"])
>>> j = parser.InstrBranch("j", ["label"], "condition needed")
>>> p = parser.Parser()
>>> p.add_instruction(addi)
>>> p.add_instruction(j)
>>> instrs = p.parse('''
...     a:
...     addi r1, r0, 100
...     addi r1, r0, 99
...     j a    
...     addi r1, r0, 98
...     addi r1, r0, 97
... ''')
>>> assert instrs == [
...     parser.Instruction(addi, [1, 0, 100]),
...     parser.Instruction(addi, [1, 0, 99]),
...     parser.Instruction(j, [0]),
...     parser.Instruction(addi, [1, 0, 98]),
...     parser.Instruction(addi, [1, 0, 97]),
... ]
>>> front = Frontend(cpu_bpu, instrs, 3)
>>> cpu_bpu.update(2, True)
>>> next_instr = front.fetch_instruction_from_queue()
no instruction in queue
>>> front.add_instructions_to_queue()
>>> print(front.instr_queue)
deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 100]), Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 99]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[0])])
>>> front.add_instructions_to_queue()
>>> print(front.instr_queue)
deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 100]), Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 99]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[0])])
>>> print(front.get_pc())
0
>>> next_instr = front.fetch_instruction_from_queue()
>>> print(next_instr)
Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 100])
>>> print(front.instr_queue)
deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 99]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[0])])
>>> print(cpu_bpu.counter)
[2, 2, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
>>> print(front.get_pc())
0
>>> front.add_instructions_to_queue()
>>> print(front.instr_queue)
deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 99]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[0]), Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 100])])
>>> front.flush_instruction_queue()
>>> print(front.instr_queue)
deque([])
>>> cpu_bpu.update(2, False)
>>> cpu_bpu.update(2, False)
>>> print(cpu_bpu.counter)
[2, 2, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
>>> front.add_instructions_to_queue()
>>> print(front.instr_queue)
deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 99]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[0]), Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 98])])
>>> micro_program=list([parser.Instruction(addi, [1, 1, 2]), parser.Instruction(j, [1])])
>>> front.add_micro_program(micro_program)
>>> print(front.instr_queue)
deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 99]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[0]), Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 98]), Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 1, 2]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[1])])
>>> next_instr = front.fetch_instruction_from_queue()
>>> next_instr = front.fetch_instruction_from_queue()
>>> next_instr = front.fetch_instruction_from_queue()
>>> front.add_instructions_to_queue()
>>> print(front.instr_queue)
deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 1, 2]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[1]), Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 99])])
>>> next_instr = front.fetch_instruction_from_queue()
>>> next_instr = front.fetch_instruction_from_queue()
>>> front.set_pc(-1)
new pc out of range
>>> front.set_pc(6)
new pc out of range
>>> front.set_pc(4)
>>> front.add_instructions_to_queue()
end of program reached by instruction queue
**goodbye**
>>> print(front.instr_queue)
deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 99]), Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 97])])
"""


from . import parser
from . import bpu
from collections import deque



class Frontend:
    '''
    Holds and manages a queue of at most max_length instructions.
    An exception to this max length is made when adding micro programs.
    Expects a already initialised bpu (e.g. shallow copy of the bpu from a surrounding cpu class) and a list of instructions (e.g. as provided by the Parser in paser.py) upon initilisation.
    Max_length can be initialised, too, otherwise a default of 5 is used.
    Uses a program counter pc to keep track of the next instruction from the provided instruction list that should be added to the queue.
    '''

    max_length : int
    pc: int 
    bpu : bpu.BPU


    #TODO: discuss whether 5 is a reasonable default value for the max_length
    def __init__(self, cpu_bpu : bpu.BPU, cpu_instr_list, maximum=5) -> None:

        self.max_length = maximum
        self.current_length = 0
        self.pc = 0
        self.bpu = cpu_bpu
        self.instr_list = cpu_instr_list
        self.instr_queue = deque()

    def add_instructions_to_queue(self) -> None:
        '''
        Adds the next instructions from the instruction list, as indicated by the pc, to the queue, until the queue is full.

        Only adds an instruction, if max_langth is not yet reached.
        If the queue is full, the function returns withput further effect.
        Notifies the user if the end of the program is reached, i.e. the pc exceeds the number of instructions in the instr_list.

        If the intruction currently added to the list is of the type InstrBranch, the pc for the next instruction is set 
        according to the label/ number provided by the instruction and the bpu prediction for the branch instruction.
        Important: jump and branching instructions need to be explicitly registered as InstrBranch, not the more generic InstructionType, in the instruction list from the parser.
        For all other instructions, the pc is set to the next instruction in the list.

        Currently, this functions interacts directly with the bpu to get predictions.
        This has to be modified if a branch order buffer should be used.
        '''

        while (len(self.instr_queue) < self.max_length):

            if self.pc >= len(self.instr_list):
                #TODO: discuss if we have/ want a functionality to properly raise errors
                #TODO: discuss if we have/ want something like an exit funtion/ operation or is this the only way a program ends and therefore not actually an error?
                print("end of program reached by instruction queue\n**goodbye**")
                return

            #sanity check, should never happen since the set_pc function checks for this too and jump goals are set by the parser from labels within the code
            if self.pc < 0:
                #TODO: exception interface
                print("pc out of bounds")
                return
            
            current_instr : parser.Instruction = self.instr_list[self.pc]
            self.instr_queue.append(current_instr)

            #this needs to be modified if further jump instruction types are implemented
            if type(current_instr.ty) == parser.InstrBranch:
            
                #true if branch was/ should be taken
                prediction : bool = self.bpu.predict(self.pc)

                if prediction == True:
                    self.pc = current_instr.ops[0]

                else:
                    self.pc = self.pc + 1

            else:            
                
                self.pc = self.pc + 1
        return

    def fetch_instruction_from_queue(self) -> parser.Instruction:
        '''
        Takes the first (current first in) instruction from the instruction queue and returns it.
        '''

        if len(self.instr_queue)>0:
            return self.instr_queue.popleft()

        else:
            print("no instruction in queue")
            #TODO: proper handling/ interface design if the queue is empty
            return None


    def flush_instruction_queue(self) -> None:
        '''
        Empties the queue.
        Does not adjust the pc. This has to be done separately, otherwise the instructions that were flushed from the queue will be silently skipped.
        '''
        self.instr_queue.clear()
        return


    def add_micro_program(self, micro_prog : list[parser.Instruction]) -> None:
        '''
        Adds a list of instructions as a µ-program to the queue.
        The queue is not automatically flushed.
        This can be done separately as a "mitigation" against Meltdown.
        The max_length of the queue is disregarded when adding the µ-program, so µ-programs can be arbitrarily long and added to full queues.
        '''
        
        for current_instr in micro_prog:

            self.instr_queue.append(current_instr)

            #do we want to allow this functionality?
            if type(current_instr.ty) == parser.InstrBranch:
        
                self.pc = current_instr.ops[0]
        return

    def set_pc(self, new_pc : int) -> None:
        '''
        Provides an interface to change the program counter to an arbitrary position within the instruction list.
        Does not consider or change the instructions which are already in the instruction queue.
        '''
        if (new_pc >= 0 and new_pc < len(self.instr_list)):

            self.pc = new_pc

        #TODO: actual exception/ error interface
        else: 
            print("new pc out of range")

        return

    def get_pc(self) -> int:
        '''
        Interface to retrieve the current value of the program counter.
        '''
        return self.pc


if __name__ == "__main__":
    import doctest
    doctest.testmod()