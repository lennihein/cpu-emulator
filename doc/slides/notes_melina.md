# Implementation of Our Emulator
    thank you felix
    so, after felix has already introduced our goal and has talked in general terms about the theoretical background and our plan for the emulator
    I will talk about how we actually implemented our emulator
        this will be a very selective overview over the implementation and design decisions
        I will have a strong focus on the aspects and components needed for the Meltdown and Spectre attacks which we will see during the practical demonstrations
            i.e. how we implemented out-of-order and speculative execution and how we handle microarchitectural faults

    but firstly I will give a brief overview over how we implemented our emulator as a whole
        in general divided into the actual emulator and the frontend that provides the visualization and controls the emulator
        b.c. of time constraints, I will only talk about the emulator
        it has a modular structure based on the different components of a real life CPUS
            but, to keep the emulator easier to understand and to use, we have made some changes and simplifications
        functionality for the UI, that a real life CPU lacks
            snapshots of the CPU to allow UI to step backwards
            visualization functions

## CPU class     
     CPU
        overarching CPU class that initializes, coordinates and controls the other components
        it provides a tick function that mimicks a cycle in a real life CPU by triggering the other components and partially acting as an interface between them
        in general, our emulated CPU works on data chunks that are either one byte in length or on data words that per default have a length of two bytes

## Parser        
    parser
        firstly the CPU uses our parser to load the program the user wants to execute
        users can provide their programs to our emulator in a assembler style source code format
        per default we offer a range of arithmetic, branch and basic memory instructions and fence and rtdsc
        the parser that reads this code and provides it in an instruction list to the other components, where branch labels have already been resolved to point at the target instructions
        this is of course different from the von Neuman architecture that many modern computers use, where the program resides in general memory, but is much easier to use in case of our emulator
        
        other than modern intel x86 CPUs introduced in the SCA lecture, we also use only use one type of instructions throughout the emulator and in the assembler program, i.e. we make no distinction between macro- and microinstructions
            this again makes our emulator clearer to understand since we do not need further decoding steps and the user can clearly see the instructions from their assembler program throughout the visualization of the execution
			
## CPU components
	besides the parser, implementation of models of actual CPU components
		simplified and, in some cases, aggregated
     
    CPU frontend and BPU
        further handles the parser instruction list
            provides an interface between parser instruction list and execution engine
            will be discussed in more detail later on, when we talk about speculative execution
     
    execution engine 
        main function is to take the instructions from the frontend and to execute them out-of-order with a version of Tomasulos algorithm
        other than a real life CPU, it contains no execution units to dispatch the instructions to, instead instructions are executed by the ee in the slots of the reservation station
		execution engine also contains register file
        I will talk about our implementation of the execution engine and ooe in more detail soon
    
    memory and cache
        simplified version of memory subsystem of skylake
        single cache, no further buffers
            size and replacement strategy can be configured by the user
        also directly maintains and handles the main memory
            possible since only one core
        only physical addresses, since there is no OS
        enough for our chosen meltdown and spectre variants
        
		top half of the address space of our main memory is marked as inaccessible
			attempts to access this part of the memory causes faults
			essential for our version of a Meltdown attack, so we will see this used in the following demonstrations
            will discuss how we implemented the handling of these faults in more detail when talking about exceptions and fault handling

## Out-of-order Execution

	out-of-order execution necessary for meltdown type attacks, and also in a way necessary for Spectre, as we have seen/ will see in the demos
		as Felix already mentioned, we implement out-of-order execution based on Tomasulos algorithm
        necessary components located in execution engine
        does not execute instructions directly in-order as they are provided by the frontend
        issues them into the reservation station where instructions wait until all of their operands are ready
            reservation station
                modelled as a list of slots, which can hold one instruction with additional information each
                unified: in our version this means that we have only one list and each list element can be a slot for any type of instruction
		mean in termins of out-of-order execution:
        in rs instructions wait for operands, and if a instruction has its operands ready before a previous instruction in program order, it can be executed while the previous instruction is still waiting
            
    sounds nice, but if we have more than one instruction waiting for operands and getting executed out of order, how do we keep track of and handle the operands and results of these intructions?
        closer look at Tomasulos algorithm

## Issuing instructions 
	ee gets intructions out of the iq and has to issue them into the rs
    when issueing an instruction into the reservation station, its register operands and its target register have to be resolved, i.e. the register name has to be replaced with the register value and in the instructions operand list
        as per Tomasulos algorithm, registers in our emulator can have two kinds of values
            Word data value: 
                easy, just put this value as the operand value into the reservation station slot with the instruction
            SlotID in the reservation station of the instruction that is currently producing this register value, i.e. the SlotID of an instruction that has not yet finished execution but whose result will become the next register value
                put the SlotID from the register into the operand list of the new instruction to show, that the new instruction is also waiting for this result
            lastly if our instruction itself produces a result that should be put in a target register
                put the new SlotID of our instruction into this register to show that it is now waiting for the result of our newly issued instruction
				
## Example reservation Station				
	can see this in the example picture
		visualization of the reservation station from the execution of our demo program
		example program can be found in our Gitlab repo and is discussed in more detail in our documentation
		different columns: 
			instr index in program, 
			instruction as it appears in program with first target register and then register and immediate operands, 
			3rd and 4th coum resolved operands that are either data words or reservation stations
		e.g. addi instruction in slot 2 operates on the result of ssli in reg2
			shift instruction has not finished execution
			-> waits for the result of slot 1 as its operand

## Common Data Bus (CDB)
     when all operands of an instruction are ready, we can execute it
        in basic Tomasulo/ real life it gets transferred to an execution unit
        in our emulator, we execute instructions as soon as all their operands are ready, while they stay in the reservation station
            but caveat to "as soon as they are ready" not more than one instruction can finish per cycle/ tick, for reasons we'll see shortly
            built in latency by waiting (at least) a specific number of cycles for each kind of instruction after its operands are ready, to mimick real life execution times
       
	   when an instructuion has finished execution and produced a result, in classic Tomasulo this gets broadcasted over the common data bus to the other slots in the reservation station and to the registers
        in our emulator, when we finish executing an instruction, i.e. all its operands are ready, the wait time is over and we have a result, we call a notification function that models the common data bus
            goes through all registers and, if the register contains the SlotID of the instruction that just produced the result, we replace it with the result
            the notification function also gives the result to all other reservation station slots so they can replace the SlotID too, if they have it in their operands list
            we allow this only once per cycle to mimick the limitations of a hardware data bus
     
     our version of Tomasulos algorithm that I just described ensures that data dependencies between instructions based on the fact that they use the same registers are resolved/ adhered to
     also have to take care of memory hazards, 
		out of scope of this presentation, 
		details in our documentation

## Speculative execution
	other important principle that we need for our microarchitectural attacks

    without speculative execution, whenever we would encounter a conditional branch instruction we would have to wait until its operands are ready, compute the result of the condition, and then choose the next instruction based on whether we take the branch or not
    we have just seen the effort we go to with Tomasulos algorithm to stall as little as possible because of our "normal" arithmetic and memory instruction etc.
        also want a mechanism to prevent stalls b.c. of branch instructions as much as possible
    
    speculative execution basic principle
        when we encounter a branch instruction, make a prediction on whether we will take this branch or not
        start executing subsequent instructions based on this prediction
            if the prediction was right, we did not stall and saved time
            if it was false, we have to rollback the falsely executed instructions after the branch instruction is actually resolved, but did not loose more time than without speculative execution
                I'll talk about rollbacks later
                
    need two centralc components for our speculative execution
        branch prediction unit, that offers a prediction for each branch instruction
        component that ensures that we resume execution according to the prediction, in our emulator the CPU frontend with its instruction queue

 ## Branch Prediction Uni (BPU)       
    branch prediction unit
        as seen in SCA lecture quite sophisticated in modern CPUs with different components to make the predictions and to assign predictions to instructions
        in our version simplified
            still enough for Spectre
            actually advantage for the user if the branch prediction is rather simple and easy to follow and predict by the user, b.c. as we will see in the practical demonstration, we have to manipulate the branch predictiopn quite precisely for Spectre type attacks
        in our version, we have an array of predictions of configurable length 2^n and simply assign each instruction to a prediction by the last n bits of its index in the program
        predictions are each handled by a simpe two-bit-saturating counter as introduced in the SCA lecture

## CPU frontend with instruction queue 
	other central component of ooe
    frontend with instruction queue
        in real life CPUs frontend multiple tasks, including taking instructions from memory and decoding them for the execution engine
            not necessary in our case, b.c. we get the instructions from the parser as a list that do not need further decoding
        main job in our emulator is to act as an interface between the instruction list and the execution unit
            take part in providing speculativ execution
            
        holds queue of limited number of instructions to pass on to the execution engine
            fills it with instructions from the instruction list, joint with some information about them
            maintains a pc that points to the next instruction that should be put into the queue
            when it encounters a branch instruction
                gets the respective prediction from the BPU
                fills the queue accordingly by either "jumping" to the branch target, i.e. setting the pc to the branch target, and resuming to fill the instruction queue from this target on, or just increments the pc as usual if the branch is predicted not to be taken
			
	** screenshot of iq with instructions, event though we never actually take the jump (would be easy to see, if we had he time)
		again an example from the execution our our demo program
		can see a part of the assembler program, the instruction queue and the reservation station
		very small loop consisting of one subi and the branch equal instruction
		BPU per default initially predicts every branch as taken when we start a program
			until branches are not taken and the BPU is updated
		iq and rs full of as many iterations of the loop as possible
			even though we can see in the RS that operands of most of the beq instructions are not ready yet, so the actual branch condition cannot be resolved yet

## Faults and Rollbacks
    already mentioned in the part about speculative execution that we sometimes mispredict branches and have to roll back the falsely executed instructions
        
    more generally speaking, when this happens we have a microarchitectural fault or an exception, i.e. we have a situation or condition in our execution that has to be handled bevore we can resume our execution
        in our emulator, two different kinds of micorarchitectural fault can occur
            when we have a misprediction
            when we try to access the inaccessbile part of our memory
        in our emulator we handle exceptions mostly in the execution engine and also the CPU, which notifies other components if they also have make changes b.c. of the exception
	
    why do we even need fault handling?
        as described before, we implement ooe and speculative execution
        when a fault occurs, it can happen that instructions that come after the faulting instruction in program order are already present in the reservation station or even already executed
            we call this transient execution
        also, generally speaking, instructions that come before the faulting instruction in program order might not have finished executing yet
        cannot simply immediatly clear the iq and rs and reset the pc 
			but have to make sure that we both execute all instructions that precede the faulting instruction in program order and that we take back the effect on the architectural state of the transient execution of following instructions before we do that

## Rollback	 
    in our emulator we actually only roll back the register state and the memory contents
        cache and BPU are not considered part of the architectural state that should be rolled back
        also, as we will see, the register state cannot be rolled back immediatly when a fault is detected, in part b.c. we have to handle instructions that precede the faulting instruction in program order but have not yet been executed
        this is critcal for Meltdown and Spectre attacks, as we will see during the practical demonstrations
        
    to be able to restore the register state
        we store a snapshot of the current register state whenever a potentially faulting instruction, i.e. a branch or a memory instruction, is issued
        when the instruction faults, we wait until all SlotIDs in the stored register state are resolved
            thus we ensure, that all instructions that precede the faulting instruction in program order and change the registers have been executed
        than we can restore the register state
        
    storing a snapshot of our memory would require too much space and would also involve the memory subsystem into the fault handling
        prevent that we have to actually rollback memory by executing store instructions in-order wrt the other store instructions
        check for fault right before we actually change our memory 
        
    if a fault occurs, we also wait for all other potentially faulting instructions that precede the actually faulting instruction in program order to retire
        -> handle faults in program order
        -> but this waiting only necessary when a fault actually occurs -> does not usually hinder the ooe
 
## Rollback after mispredicted branch

	here we can the same loop as before in instructions 8 and 9
	have seen previously the the rs and iq were completely full with iterations of our loop
    but eventually the branch condition was not fulfilled and the prediction that the branch would be taken was false
		rollback, i.e. restore register and memory state
		clear reservation station and iq 
		refill iq based on whether the branch was actually taken, rtdsc in this case
	the instructions that are issued into the reservation station will operate on the correct/ expected register state 

## Thank you for your attention

thank your for your attention for my part of our group presentation
a lot of inmformation, but necessary for the following practical demonstrations
before we start those, are there any questions so far?

hand over (Wort übergeben?) to Lenni (Lennart Hein) who will show a more practical example/ start to give a more practival demonstration of what our emulator can do
