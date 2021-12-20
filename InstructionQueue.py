class InstructionQueue:

    max_length : int #maximal number of instructions in the queue, can be ignored by µ-programs which are inserted b.c. an exception occured 
    current_length : int #current number of instructions in the queue
    pc: int #program counter ; ist there a "master pc" elsewhere? register? #dos this point to the start of the queue, the end of the queue, or the next instruction we fetch from the list?

    #initialise
    #length of queue
    #instruction pointer (where is the "master instruction pointer"? register?) -> maybe adjust during initialisation for weird edge or debugging cases
    #default maximum for length of the instruction queue was set arbitrarily to 5, open for discussion
    def __init__(self, maximum=5) -> None:
        self.max_length = maximum
        self.current_length = 0
        self.pc = 0

    #get instruction from parser
    #make sure that the length requirement is not violated
    #recognise branches, calls etc.
    #communicate with BPU and fill queue/ adjust pc accordingly
    #recognise misprediction (communicate with with RS?), flush Queue from appropriate instruction on and fill again
    #how does this work, if mispredicted instructions are already in the RS? Rollback to branch instruction and take different branch
    #"remember" branching decisions
    #update BPU after each branching instruction -> need signaling for all branching instructions, so we can also inform the BPU about succesfull predictions
    def AddInstructionToQueue () -> None:
        pass

    #hand over instruction to RS
    #read/ fetch and delete first instruction
    #will the instruction queue initialise this or the RS if it is free?
    #in the latter case, would the RS fetch instructions from the Queue out of order, would it sit empty, or do we only have one RS for all instruction types anyway?
    def FetchInstruction () -> None:
        pass

    #flush Queue
    #adjust instruction pointer?
    def FlushQueue () -> None:
        pass

    #add µ-program
    #optionally flush queue first
    def AddMicroProgram () -> None:
        pass