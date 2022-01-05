import bpu
import parser
from collections import deque



class Frontend:

    max_length : int #maximal number of instructions in the queue, can be ignored by µ-programs which are inserted b.c. an exception occured 
    pc: int #program counter ; points to the next instruction to fetch from the Instruction List into the Instruction Queue
    bpu : BPU #branch prediction unit; should be set as a shallow copy by the CPU class
    instr_list #List of instructions provided by the parser, should be set as a shallow copy by the CPU class; explicit type hint?
    instr_queue #queue of the next max_length or less instructions that should be placed into the RS (more instr. possible if a µ-programm is executed)


    #initialise
    #length of queue
    #instruction pointer (where is the "master instruction pointer"? register?) -> maybe adjust during initialisation for weird edge or debugging cases
    #default maximum for length of the instruction queue was set arbitrarily to 5, open for discussion
    #cpu_bpu and cpu_instr_list expect shallow copies of the bpu initialised by the cpu and the instruction list returned to the cpu by the parser respectively
    def __init__(self, cpu_bpu, cpu_instr_list, maximum=5) -> None:
        self.max_length = maximum
        self.current_length = 0
        self.pc = 0
        self.bpu = cpu_bpu
        self.instr_list = cpu_instr_list
        self.instr_queue = deque()

    def add_instruction_to_queue (self) -> None:

        #check if next, instr is valid, i.e. pc < len(instr_list)
        if self.pc > len(self.instr_list):
            #do we have a functionality to properly raise errors?
            #do we have something like an exit funtion/ operation or is this the only way a program ends?
            print("end of program reached\n **goodbye**\n")
            return

        #make sure that the length requirement is not violated
        if len(self.instr_queue) >= self.max_length:
            return
            
        current_instr : Instruction = self.instr_list[self.pc]

        #append instr to queue
        self.instr_queue.append(current_instr)

        #this needs to be modified if further jump instruction types are implemented
        #does comparing for a class work like this?
        if current_instr.ty == InstrBranch:
        
            #get branch prediction from bpu
            #true if branch was/ should be taken (?)
            prediction : bool = self.bpu.predict(self.pc)

            if prediction == True:
                self.pc = current_instr.ops[0]

            else:
                self.pc = self.pc + 1

            #no further handling of the bpu in this step
            #here: direct contact with bpu, b.c. interface clear
            #might need adjustment if we have a branch order buffer

        else:            
            #use setter function instead?
            self.pc = self.pc + 1


    #hand over instruction to RS
    #read/ fetch and delete first instruction from the queue
    def fetch_instruction_from_queue (self) -> Instruction:

        if len(self.instr_queue>0):
            return self.instr_queue.popleft()

        else:
            print("no instruction in queue")
            #TODO: proper handling/ interface design if the queue is empty
            return None

    #flush Queue
    #adjust instruction pointer so the flushed instructuions are "back in the queue"? 
    # might not be feasible without further buffering for branches 
    # -> maybe leave for those who initiate the flushing
    def flush_instruction_queue (self) -> None:
        self.instr_queue.clear()

    #add µ-program
    #optionally flush queue first -> leave as mitigation
    def add_micro_program (self, micro_prog : list[Instruction]) -> None:
        
        for current_instr in micro_prog:

            self.instr_queue.append(current_instr)


    #setter function for the program counter, e.g. for external rollback handling
    #e.g. with property decorator?
    #is this really necessary?