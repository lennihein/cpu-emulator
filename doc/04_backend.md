# CPU emulator/ backend {#sec:backend}

In this chapte, we introduce the backend of our emulator program.
It contains the elements of our program that emulate actual CPU components.
Our emulator is based on information about modern real life CPUs, especially the x86 Intel Skylake architecture [@skylake].
<!--todo: gute Begründung außer "war so in SCA" dass wir eine relativ alte CPU nehmen. Einfacher zu verstehen als neuere aber trotzdem alle für die Angriffe relevanten features? oder mit Absicht etwas älter, da hier noch die für Meltdown und Spectre interessanten features vorhanden sind. -->

<!--todo: add which exact python variant and special tools and libraries, if applicable -->
In our program, we model the distinct components of a real life CPU with a modular setup making use of the object oriented functionalities of Python3. 
Breaking up the source code into individual CPU components also makes it easier to understand and maintain. <!--todo: best practice anyways, maybe leave out -->
Additionally, we have made simplifications and modifications in comparison to a real life CPU, so the emulator is as clear and easy to understand as possible while still implementing an actual out of order execution and providing the necessary functionality for Meltdown and Spectre attacks.

In this chapter we firstly introduce the components of our CPU emulator, how they work (together) and which part of a real life CPU they emulate [@sec:components].
Then we explain how our emulator provides out of order execution and how it may differ from the general Tomasulo algorithm introduced in [@sec:background-out-of-order-execution, @sec:Tomasulo].
Subsequently, we show how we implemented rollbacks and exception handling, especially with regards to how out the implementation allows for Meltdown and Spetre attacks [@sec:rollback].
Then we give an overview over our instruction set architecture [@sec:ISA].
Lastly we show how our emulator can be adapted for different demonstrations and attacks without changing the source code via a config file [@sec:config].

## CPU Components and our equivalents/ models (10-11 pages) {#sec:components}

todo

### CPU {#sec:CPU}
The primary purpose of the CPU module is to allow all other components to work together. That is, the CPU initializes all other components and provides interfaces to their functions, which allows the GUI to visualize the current state. In addition, the CPU provides functions which load user programs and a tick function that is called each cycle and does the following: instructions from the instruction queue are fetched from the frontend and forwarded to the execution engine, until either no more slots in the unified reservation station are available, or the instruction queue is empty. It then calls the tick function of the execution engine. In case of a rollback, the instruction queue maintained by the frontend is flushed. If the rollback was caused by a faulting load instruction, execution is resumed at the next instruction (as described in [@sec:rollback]). In case a branch was mispredicted, the frontend is notified and refills the instruction queue accordingly. If configured, corresponding microprograms are sent to the instruction queue. Lastly, a snapshot of the current state of the CPU is taken.

The second purpose of the CPU is to provide the snapshot functionality which allows a user of the emulator to step back to previous cycles. The snapshot list is simply a list which grows at each cycle, where each entry is a deep copy of the CPU instance. However, this would imply that each snapshot maintains a full list of snapshots, where each entry contains a list of snapshots, and so on. To combat this, there is only a single global list of snapshots, and each snapshot entry maintains a reference and an index to its own entry. As a result, the default deep copy function is adjusted accordingly. Due to the low complexity of the programs we expect users to run, at the moment, no maximum number of available snapshots is configured.

### Instructions and Parser {#sec:parser}

todo

### Data representation {#sec:data}

todo

### CPU frontend {#sec:CPU_frontend}

In modern CPUs, the CPU frontend provides an interface between code and execution engine.
It contains components to fetch and decode the instructions from a cache and supply them to the CPU in a queue.
It is also involved in speculative execution by predicting the result of conditional jumps and supplying instructions to the execution engine accordingly.
[@skylake]

In our emulator we simplify the components and procedures.
We also separate the branch prediction unit (BPU), that manages and predicts the results of conditional jumps, from the rest of the frontend.
This makes our code easier to understand and makes potential future changes or additions to the BPU more convenient.

#### Branch Prediction Unit (BPU) {#sec:BPU}

The BPU of modern CPUs plays a vital role in enabling speculative execution.
It stores information about previously executed conditional branch instructions and predicts the outcome of future branch instructions accordingly.
The rest of the CPU can then speculatively execute further instructions at an address based on the predicted outcome of the branch instead of stalling until the branch instruction is processed by the execution engine.
If the prediction was false, a rollback is performed on the speculatively executed instruction [@sec:rollback].
If the prediction was true, the execution is overall faster than without speculative execution.
<!--todo: source? -->

Detailed information about the BPU of our modern base CPU is not widely available [@skylake]. 
In general, the Gshare BPU of modern CPU consists of multiple components.
It contains a branch target buffer (BTB) that holds the predicted target addresses for conditional branches.
It also uses a pattern history table (PTH), that can be implemented as a 2-bit-saturating counter, and a global history register (GHT) to predict whether a conditional jump will be taken or not.
[@SCA]
<!-- todo: ordentliche Quelle finden
        vllt. BPU, Gshare BPU, die einzelnen Komponenten etc. oder direkt Skylake nochmal googlen-->
<!--  wikichip skylake: The intimate improvements done in the branch predictor were not further disclosed by Intel. -->

In our emulator, we forgo the BTB entirely.
Real life CPUs benefit from stored target addresses since they have to expensively decode each branch instruction before they can work with the target address [@skylake].
In our emulator, the parser decodes the jump labels from the assembler code and directly provides them to the frontend, so storing them in an additional buffer is unnecessary [@sec:parser].
We further forgo the GHT because it is not strictly necessary to execute a Meltdown or Spectre attack.
Additionally, our emulator and its behaviour are easier to understand and predict without it, which is important when implementing microarchitectural attacks for didactic purposes.
The BPU of our emulator only consists of a PHT, which is enough for simple Spectre-PHT variants [@reference-eval-spectre].
<!--todo: add correct reference for last sentence -->

The default PHT used in our emulator holds an array called counter of configurable length to store several predictions.
The instructions are assigned to different prediction slots by the last bits of their index in the instruction list.
For each of the slots, the prediction can take the four different values from zero to three, where zero and one indicate that the branch will probably not be taken and two and three indicate that the branch is likely to be taken.

<!--todo: maybe remove the Simple BPU and this paragraph with it. -->
The source code for our emulator also contains a more simple BPU with only one slot for all instructions.
Since the number of slots in the default BPU is freely configurable by the user, this simple BPU is now obsolete.

<!-- Todo: Hier noch ergänzen, wo die BPU wann geupdated wird.-->
<!-- Todo: Ggf. Begründung überlegen, wieso 2-bit statt 2-bit-sat.-->
<!-- Todo: Nochmal überarbeiten, wenn bimodal_update klarer ist.-->
When the BPU is updated with an actual branch outcome from the execution engine, the prediction in the PHT is updated by a 2-bit counter.
This means, that if the prediction was right, the counter remains at or updates to zero (strongly not taken) or three (strongly taken) respectively.
If the prediction counter is at zero but the branch is actually taken, the counter is updated to one (weakly not taken).
If it is at a one when the branch is taken, it is directly updated to three.
The counter behaves similarly when it has tha value two or three and the branch is not actually taken.
        
#### Instruction Queue {#sec:iq}

In a real life CPU, the overall purpose of the frontend is to provide the execution unit with a steady strean of instructions so the backend is busy as much as possible and therefore efficient.
In a modern x86 CPu, the frontend has to fetch x86 macro-instructions from a cache and decode, optimize and queue them repeatedly to provide the backend with a queue of µ-instructions ready for issuing in the execution engine.
[@skylake]
<!---
workflow decoding and queue filling in CPU:
     fetch complex x86 macro instructions from cache
     pre-decoded instructions are delivered to the Instruction Queue
     fusing of macro ops
     decoding in multiple decoders: input macro op, emit regular, fixed length µOPs
        even more complicated for more complex macro ops (microcode sequencer)
    µ-op cache b.c. all of this is resource intensive
    Allocation Queue acts as the interface between the front-end (in-order) and the back-end (out-of-order)
    additional optimizations
-->

In our emulator, except for the BPU, the functionality of the CPU frontend is bundled in frontend.py.
It is significantly simplified compared to a real life x86 CPU, especially since the we use only one type of instructions instead of distinguishing between macro- and µ-instructions [@sec:ISA].
They are already provided as a list by the parser, which renders the decoding and optimization steps in the frontend unnecessary [@sec:parser].

The main task of our frontend is to acts as interface between instruction list provided by the parser and the execution engine [@sec:execution].
It provides and manages the instruction queue, which holds the instructions that the execution engine should issue next.
Conditional branches with their respective BPU predictions are taken into account when filling the queue.
This enables speculative execution which is needed for Spectre attacks [@sec:meltdown-and-spectre].

The central component of our emulated frontend ist the instruction queue.
In our version, it does not only hold the instructions themselves, but also for every instruction in the queue, the respective index in the instruction list is stored.
For branch instructions it also holds the respective branch prediction from the BPU at the time that the instruction was added to the queue.
This additional information is needed by the execution engine to handle mispredictions and other exceptions [@sec:execution].

When adding instructions to the queue, the frontend selects them from the instruction list, adds the additional information for the execution engine and places them into the instruction queue until the queue's maximum capacity is reached.
The frontend maintains a program counter (pc) that points to the next instruction in the list that should be added to the queue.
When the frontend encounters a branch instruction and the branch is predicted to be taken, the frontend adjusts the pc to resume adding instructions at the branch target.
If a branch was mispredicted, the frontend provides a special function to reset the pc and refill the instruction queue with the correct instructions.

Additionally, the frontend provides a function to add a µ-program to the queue.
It consists of a list of instructions separate from the parser instruction list.
When adding the µ-program to the queue, the frontend may exceed the maximum queue capacity.
This functionality can be used to implement mitigations against microarchitectural attacks, e.g. by adding a µ-program as part of the exception handling after an illegal load [@reference-eval-mitigations].
<!--todo: add correct reference for last sentence -->

<!--todo: add correct reference for second sentence -->
The frontend provides interfaces to both read and take instructions from the queue.
It also provides a function that combines taking an instruction from the queue and refilling it, .
Additionally, the frontend has an interface for flushing the whole queue at once without taking the instructions from the queue.
This can be used when demonstrating mitigations against microarchitectural attacks [@reference-eval-mitigations].

The frontend provides further basic interfaces, e.g. for reading the size the instruction queue and reading and setting the pc.
These are used by the other components during regular execution, e.g. when issuing instructions to the execution engine, but also to reset the queue to a certain point in the program after an exception has occured [@sec:rollback].
Since our emulator only executes one program at a time, the other components can check via another interface whether the frontend has reached the end of the program.

### Memory {#sec:memory}

todo

### Execution Engine {#sec:execution}

todo

## Out of Order Execution (2 pages) {#sec:Tomasulo}

todo

## Exceptions and Rollbacks (2-3 pages) {#sec:rollback}

todo

## ISA (2 pages) {#sec:ISA}

todo

## Config Files (1 page) {#sec:config}

todo
