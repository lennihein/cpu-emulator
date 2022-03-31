general Aufbau ca. 5 Minuten -> ca. 60 Zeilen (wenn dann Redezeit von der speculative Execution weg nehmen)

## Implementation of Our Emulator
    thank you felix
    so, after felix has already introduced our goal/ task and has talked in general terms about the theoretical background and our version of these principles
    I will take about how we actually implemented our emulator
        this will be a very selective overview over the implementation and design decisions, since I do not want to show anyone hundreds or thousands of lines of code before lunch
        I will have a strong focus on the aspects and components needed for the Meltdown and Spectre attacks we will see during the practical demonstrations
            i.e. how we implemented out-of-order and speculative execution

    but firstly I will give a brief overview over how we implemented our emulator as a whole
        divided into the actual emulator and the frontend that provides the visualization and controls the emulator
        b.c. of time constraints, I will only talk about the emulator
        it has a modular structure based on the different components of a real life CPUS
            but, to keep the emulator easier to understand and to use, we have made some changes and simplifications
        functionality for the UI, that a real life CPU lacks
            snapshots of the CPU to allow UI to step backwards
            visualization functions

## CPU class     
     CPU
        overarching (?) CPU class that initializes, coordinates and controls the other component
        it provides a tick function that mimicks a cycle in a real life CPU by triggering the (functionality of) the other components and partially acting as an interface between them
        in general, our emulated CPU works on data chunks that are either one byte in length or on data words that per default have a length of two bytes

## Parser        
    parser
        firstly the CPU uses our parser to load the program the user wants to execute
        users can provide their programs to our emulator in a assembler style source code format
        per default we offer a range of arithmetic, branch and basic memory instructions and fence and rtdsc
        our emulator contains a parser that reads this code and provides it in an instruction list, where branch labels have already been resolved to point at the target instructions
        this is of course different from the von Neuman architecture that many modern computers use, where the program resides in general memory, but is much easier to use in case of our emulator
        
        other than modern intel x86 CPUs introduced in the SCA lecture, we also use only use one type of instructions throughout the emulator, i.e. we make no distinction between macro- and microinstructions
            this again makes our emulator clearer to understand since we do not need further decoding steps and the user can clearly see the instructions from their assembler program throughout the visualization of the execution
			
## CPU components
	implementation of models of actual CPU components
		simplified and, in some cases, aggregated
     
    bpu and frontend
        these instructions are then further handled by the CPU frontend
            provides an interface between parser instruction list and execution engine
            will be discussed in more detail later on, when we talk about speculative execution
     
    execution engine 
        main function is to take the executions from the frontend and to execute them out-of-order with a version of Tomasulos algorithm with a unified reservation station
        no execution units to dispatch the instructions to, instructions are executed by the ee in the slots of the reservation station
            two phases
                executing, when the instr waits for operands, produces a result and waits to mimick latency
                retiring when it checks for faults
            but only one instruction can produce a result or retire each cycle/ tick
                model common data busy
        I will talk about our implementation of ooe in more detail soon
    
    memory and cache
        simplified version of memory subsystem of skylake
        single cache, no further buffers
            size and replacement strategy can be configured by the user
        also directly maintains and handles the main memory
            possible since only one core
        only physical addresses, since there is no OS
        enough for our chosen meltdown and spectre variants
        
        possibility for illegal memory access attampts: top half of the address space is marked as inaccessible
            attempts to access this part of the memory causes faults
            will discuss this in more detail when talking about exceptions and fault handling
            will also see this used in the following demonstrations, since it is essential for our version of a Meltdown attack


out-of-order-execution ca. 5 Minuten -> ca. 60 Zeilen

## Out-of-order Execution
    as Felix already mentioned, we implement out-of-order execution based on Tomasulos algorithm
        out-of-order execution necessary for meltdown type attacks, and also in a way necessary for Spectre, as we have seen/ will see in the demos
        necessary components located in execution engine
        does not execute instructions directly in-order as they are provided by the frontend
        issues them into the reservation station where instructions wait until all of their operands are ready
            reservation station
                modelled as a list of slots, which can hold one instruction with additional information each
                unified: in our version this means that we have only one list and each list element can be a slot for any type of instruction
        if a subsequent operation in program order has its operands ready before a previous one, it can be executed while the previous instruction is still waiting
        execution engine also contains register file
            
    sounds nice, but if we have more than one instruction waiting for operands and getting executed out of order, how do we keep track of and handle the operands and results of these intructions?
        closer look at Tomasulos algorithm

## Issuing instructions        
    when issueing an instruction into the reservation station, its register operands and its target register have to be resolved, i.e. the register name has to be replaced with the register value and put into the slot in the reservation station of the instruction
        as per Tomasulos algorithm, registers in our emulator can have two kinds of values
            Word data value: 
                easy, just put this value as the operand value into the reservation station slot with the instruction
            SlotID in the reservation station of the instruction that is currently producing this register value, i.e. the SlotID of the instruction that has not yet finished execution but whose result will become the next register value:
                put the SlotID into the reservation station slot to show, that the new instruction is also waiting for this result/ register value
            lastly we, if our instruction itself produces a result that should be put in a target register
                put the new SlotID of our instruction into this register to show that it is now waiting for the result of our newly issued instruction
## Example reservation Station				
	can see this in the example picture
		visualization of the reservation station from the execution of our demo program
		example program can be found in our Gitlab repo and is discussed in more detail in our documentation
		different columns: 
			instr index in program, 
			instruction as it is in program with register and immediate operands, 
			resolved operands that are either data words or reservation stations
		e.g. addi instruction in slot 2 operates on the result of the addi instruction of ssli in reg2
			-> waits for the result of slot 1 as its operand

## Issuing instructions				
    by putting the SlotIDs of newly issued intructions in their respective target register whenever we issue a instruction, we make sure that the registers always reflect the expected register state at the point of issuing the current instruction, if the program was executed in order
        only difference that instead of some of the values we have SlotIDs as placeholders instead
        but since we pass these placeholder SlotIDs on to the operands lists of the instructions, this is not a problem 
            even if placeholders get overwritten with other placeholders before they are ever replaced with the actual value, as we will see shortly
 
## Common Data Bus (CDB)
     when all operands of an instruction are ready, we can execute it
        in basic Tomasulo/ real life it gets transferred to an execution unit
        in our emulator, we execute instructions as soon as all their operands are ready, while they stay in the reservation station
            but not more than one instruction can finish per cycle/ tick, for reasons we'll see shortly
            built in latency by waiting (at least) a specific number of cycles for each kind of instruction after its operands are ready, to mimick real life execution times
        when an instructuion has finished execution and produced a result, in classic Tomasulo this gets broadcasted over the common data bus to the other slots in the reservation station and to the registers
        when we finish executing an instruction, i.e. all its operands are ready, the wait time is over and we have a result, we call a notification function that models the common data bus
            goes through all registers and, if the register contains the SlotID of the instruction that just produced the result, we replace it with the result
            gives the result to all other reservation station slots so they can replace the SlotID too, if they have it in their operands list
            we allow this only once per cycle to mimick the limitations of a hardware data bus
            also, to briefly cycle back to thinking about issuing instruction into the reservation station, since we not only notify the registers but also the reservation station slots, we ensure that all instructions receive their correct operands even if the register that should provide their operand has been modified since the instruction was issued
                since the instructions operand lists contain not the current register contents but either the value or the SlotID that was in the register when we issued the instruction
     
     our version of Tomasulos algorithm that I just described ensures that data dependencies between instructions based on the fact that they use the same registers are resolved/ adhered to
     also have to take care of memory hazards, out of scope of this presentation, details in our documentation

    at this point, almost ready to look at Meltdown, but before the practical demonstrations start, we also take a look at speculative execution, which we need for Spectre type attacks

speculative execution ca. 5 Minuten -> ca. 60 Zeilen 

## Speculative execution
    without speculative execution, whenever we would encounter a branch instruction that branches based on a condition like e.g. a comparison between two register values, we would have to wait until these values are ready, compute the result of the condition, and then choose the next instruction based on whether we take the jump or not
    we have just seen the effort we go to with Tomasulos algorithm to stall as little as possible because of our "normal" arithmetic and memory instruction etc.
        also want a mechanism to prevent stalls b.c. of branch instructions as much as possible
    
    speculative execution basic principle
        when we encounter a branch instruction, make a prediction on whether we will take this branch or not
        start executing subsequent instructions based on this prediction
            if the prediction was right, we saved time
            if it was false, we have to rollback the falsely executed instructions after the branch instruction but did not loose (much) more time than without speculative execution
                I'll talk about rollbacks later
                
    need two centralc components for our speculative execution
        branch prediction unit, that offers a prediction for each branch instruction
        component that ensures that we resume execution according to the prediction, in our emulator the frontend with its instruction queue

 ## Branch Prediction Uni (BPU)       
    branch prediction unit
        quite sophisticated in modern CPUs with different components to make the predictions and to assign predictions to instructions
            in general not as many predictions as instructions
        in our version simplified
            enough for Spectre
            actually advantage for the user if the branch prediction is rather simple and easy to follow/ predict, b.c. as we will see in the practical demonstration, we have to manipulate the branch predictiopn quite precisely for Spectre type attacks
        in our version, we have an array of predictions of configurable length 2*n and simple assign each instruction to a prediction by the last n bits of its index in the program
        predictions are handled by a simpe two-bit-saturating counter
            **hier wäre tatsächlich ein Bild nett
            ** oder die genaue Beschreibung einfach weglassen
            four states, strongly not taken, weakly not taken, weakly taken, strongly taken
            updated after each execution of a branch instruction
            +1 of branch was taken, up to 3, -1 if branch was not taken at most down to 0
            predict not taken for 0 or 1, taken for 2 or 3

## CPU frontend with instruction queue            
    frontend with instruction queue
        in real life CPUs frontend multiple tasks, including taking instructions from memory and decoding them for the execution engine
            not necessary in our case, b.c. we get the instructions from the parser as a list that do not need further decoding
        main job in our emulator is to act as an interface between the parser instruction list and the execution unit
            especially wrt speculativ execution
            
        holds queue of limited number of instructions
            fills it with instructions from the instruction list, joint with some information about them, e.g. predictions for branch instructions
            maintains a pc that points to the next instruction that shuld be put into the queue
            when it encounters a branch instruction
                gets the respective prediction from the BPU
                fills the queue accordingly by either "jumping" to the branch target, i.e. setting the pc to the branch target, and resuming to fill the instruction queue from this target on, or just increments the pc as usual if the branch is predicted not to be taken
            if there was a misprediction we also have a special instruction that refills the queue according to whether the branch is actually taken or not
			
	** screenshot of iq with instructions, event though we never actually take the jump (would be easy to see, if we had he time)
		again an example from the execution our our demo program
		can see a part of the assembler program, the instruction queue and the reservation station
		very small loop consisting of one subi and the branch equal instruction
		BPU per default predicts every branch as taken when we start a program
		iq and rs full of as many iterations of the loop as possible
			even though we can see in the RS that operands of most of the beq instructions are not ready yet, so the actual branch condition cannot be resolved yet

rollbacks ca. 5 Minuten -> ca. 60 Zeilen

## Faults and Rollbacks
    already mentioned in the part about speculative execution that we sometimes mispredict branches and have to roll back the falsely executed instructions
        
    more generally speaking, we have a microarchitectural fault or an exception, i.e. we have a situation/ concition in our execution that has to be handled bevore we can resume our execution
        in our emulator, two different kinds of micorarchitectural fault can occur
            when we have a misprediction
            when we try to access the inaccessbile part of our memory
        in our emulator we handle exceptions in the execution engine and the CPU, which notifies/ handles other components if they also have make changes b.c. of the exception
	
    why do we even need fault handling?
        as described before, we implement ooe and speculative execution
        when a fault occurs, instructions that come after the faulting instruction in program order can already be present in the reservation station or even already executed
            we call this transient execution
        also, generally speaking, instructions that come before the faulting instruction in program order might not have finished executing yet
        cannot simply reset the pc but have to make sure that we both execute all instructions that precede the faulting instruction in program order and that we take back the effect on the architectural state of the transient execution of following instructions

## Rollback	 
    in our emulator we actually only roll back the register state and the memory contents
        cache and BPU are not considered part of the architectural state and not rolled back
        also, as we will see, the register state cannot be rolled back immediatly when a fault is detected, in part b.c. we have to handle instructions that precede the faulting instruction in program order but have not yet been handled
        this is critcal for Meltdown and Spectre attacks, as we will see during the practical demonstrations
        
    to be able to restore the register state
        we store a snapshot of the current register state whenever a potentially faulting instruction, i.e. a branch or a memory instruction, is issued
        when the instruction faults, we wait until all SlotIDs in the stored register state are resolved
            thus we ensure, that all instructions that precede the faulting instruction in program order and change the registers have been executed
        than we can restore the register state
        
    storing a snapshot of our memory would require too much space and would also involve the memory subsystem into the fault handling
        prevent that we have to actually rollback memory by executing store instructions in-order wrt the other store instructions
        check for fault right before we actually change our memory 
        
    if a fault occurs, we also wait for all other potentially faulting instructions that precede the faulting instruction in program order to retire
        -> handle faults in program order
        -> only necessary when a fault actually occurs -> does not usually hinder the ooe
 
## Rollback after mispredicted branch
    when register and memory state have been restored, reset pc either to the next instruction after the faulting one in program order (?) and refill the iq for memory instructions, or refill the iq based on whether the branch was actually taken
        the instructions that are issued into the reservation station will operate on the correct/ expected register state (except of course that results of illegal loads are not present) 
		
	here we can the same loop as before in instructions 8 and 9
    but eventually the branch condition was not fulfilled and the prediction tha the branch would be taken was false
	rollback, clear reservation station and iq and instruction after branch instruction, rtdsc in this case, put into instruction queue

## Thank you for your attention

thank your for your attention for my part of our group presentation
any questions so far?
hand over (Wort übergeben?) to Lenni (Lennart Hein) who will show a more practical example/ start to give a more practival demonstration of what our emulator can do
