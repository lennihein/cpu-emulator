# CPU emulator/ backend {#sec:backend}
\marginpar{Melina Hoffmann}

In this chapter, we introduce the backend of our emulator program.
It contains the elements of our program that emulate actual CPU components.
Our emulator is based on information about modern real life CPUs, especially the x86 Intel Skylake architecture [@skylake].
<!--todo: gute Begründung außer "war so in SCA" dass wir eine relativ alte CPU nehmen. Einfacher zu verstehen als neuere aber trotzdem alle für die Angriffe relevanten features? oder mit Absicht etwas älter, da hier noch die für Meltdown und Spectre interessanten features vorhanden sind. -->

<!--todo: add which exact python variant and special tools and libraries, if applicable
already mentioned in the UI chapter-->
In our program, we model the distinct components of a real life CPU with a modular setup making use of the object oriented functionalities of Python3. 
Breaking up the source code into individual CPU components also makes it easier to understand and maintain. 
<!--todo: best practice anyways, maybe leave out -->
Additionally, we have made simplifications and modifications in comparison to a real life CPU, so the emulator is as clear and easy to understand as possible while still implementing an actual out-of-order execution and providing the necessary functionality for Meltdown and Spectre attacks.

In this chapter we firstly introduce the components of our CPU emulator, how they work and interact and which part of a real life CPU they emulate [@sec:components].
Then we explain how our emulator provides out of order execution and how it may differ from the general Tomasulo algorithm introduced in [@sec:background-out-of-order-execution, @sec:Tomasulo].
Subsequently, we show how we implemented rollbacks and exception handling, especially with regards to how out the implementation allows for Meltdown and Spetre attacks [@sec:rollback].
Then we give an overview over our instruction set architecture [@sec:ISA].
Lastly we show how our emulator can be adapted for different demonstrations and attacks without changing the source code via a config file [@sec:config].

## CPU Components and our equivalents/ models {#sec:components}

\marginpar{Jan-Niklas Sohn}

This section describes the individual components of our CPU emulator and various interactions between them. Each component is modelled after one or multiple components found in typical modern x86 CPUs.
The main CPU component described in [@sec:CPU] initializes all other components and interfaces between them.
The parser component described in [@sec:parser] parses users' program code into a sequence of instruction objects.
[@Sec:data] introduces the data representation used throughout the CPU, in particular with respect to memory accesses.
The CPU frontend described in [@sec:CPU_frontend] supplies the execution engine with a stream of instructions.
The memory subsystem is detailed in [@sec:memory] and manages main memory and the cache.
[@Sec:execution] describes the execution engine, which is responsible for actually performing computations.

### CPU {#sec:CPU}
\marginpar{Felix Betke}
The primary purpose of the `CPU` class is to allow all other components to work together. That is, the `CPU` initializes all other components and provides interfaces to their functions. Most importantly, it provides a `tick` function that models a single cycle and provides the snapshot functionality which allows a user of the emulator to step back to previous cycles.

The `tick` function is called each cycle and does the following: instructions from the instruction queue are fetched from the frontend and forwarded to the execution engine, until either no more slots in the unified reservation station are available, or the instruction queue is empty. It then calls the `tick` function of the execution engine. In case of a rollback, the instruction queue maintained by the frontend is flushed. If configured, a microprogram corresponding to the faulting instruction type is added to the instruction queue. That way, it will be issued before regular execution is resumed. If the rollback was caused by a faulting load instruction, execution is resumed at the next instruction. This prevents users from having to implement signal handlers, thus keeping their programs simple. In case a branch was mispredicted, the frontend is notified and refills the instruction queue accordingly. Lastly, a snapshot of the current state of the CPU is taken. To provide the UI with useful information to display to the users, the `tick` function returns an instance of a `CPUStatus` class that contains a boolean indicating if the program has terminated, whether an exception has raised a fault and, if so, whether a microprogram is to be executed, and, lastly, a list of instructions that have been issued during this tick.

The second main purpose of the `CPU` class is to provide the snapshot functionality, which allows the user of the emulator to step back to previous cycles. The snapshot list is simply a list that grows at each cycle, where ech entry is a deepcopy of the `CPU` instance. To simply be able to deepcopy the `CPU` class, the snapshot list is held separately and is not one of its members. Instead, the `CPU` class, and therefore each snapshot, maintains an index to its own entry in the snapshot list. This index makes traversing the snapshot list one step at a time easier. Due to the low complexity of the programs we expect our users to run, at the moment, no maximum number of available snapshots is configured. To restore snapshots, a static `restore_snapshot` function exists in the `CPU` class. Crucially, this function returns the deepcopy of an entry of the snapshot list relative to the value of `_snapshot_index` of the current instance. This allows users to step back and forth between snapshots. However, manipulating a restored snapshot by calling the `tick` function, for example, discards all more recent snapshots.

Other functions exist to load programs from files and initialize the frontend and execution engine accordingly. Further, references to each component are exposed by getter functions to allow the UI to visualize their current state.

### Instructions and Parser {#sec:parser}

\marginpar{Jan-Niklas Sohn}

<!-- - Users provide assembly-like source code
- Parsed and provided to the rest of the CPU
- This is in contrast to real x86 CPUs, which read and decode instructions from memory -->

Users of our CPU emulator provide programs as an assembly-like source code.
This source code is parsed by the `parser` module into a sequence of `Instruction` objects. Information about individual instructions is provided by the `instructions` module.
The parsed instruction sequence is used throughout the rest of our CPU, indexed by the current program counter.
This Harvard-style architecture is in contrast to x86 CPUs, where instructions and data share a single address space.
However, parsing the program code once and from a textual representation simplifies the design of our CPU emulator, and for instance allows us to completely omit instruction memory from our memory model.

<!-- - General instruction format: mnemonic followed by comma-separated operands, as is common in assembly languages
- Instruction mnemonic already determines the exact instruction, including the types of its operands
- Possible operand types: reg, imm, label -->

The general instruction format used by our instruction set is the instruction mnemonic followed by a comma-separated list of instruction operands, as is common in assembly languages.
In our instruction set, the instruction mnemonic already determines the exact instruction, including the number and types of its operands. This greatly simplifies parsing.
There are three different types of operands in our instruction set:

- *Register* operands specify a register the instruction should operate on. They are introduced by an `r` followed by the decimal register number.

- *Immediate* operands specify a 16-bit immediate value used by the instruction. They take on the usual decimal (without prefix) or hexadecimal (prefixed with `0x`) forms for integer literals. Immediate values can optionally be prefixed by a sign, in which case they take the value of the corresponding two's complement signed integer.

- *Label* operands specify the destination of a branch instruction. The label referenced has to be defined somewhere in the assembly file, using the label name followed by a colon.

<!-- - Concrete instructions and their semantics covered in sec:isa
- We don't support reading or writing instruction memory
  - Instructions have no defined in-memory representation -->

Our instruction set, including all concrete instructions and their semantics, are covered in detail in [@sec:ISA].
We do not support reading or writing instruction memory. Thus, instructions have no defined in-memory representation.

<!-- - Instructions distinguished based on instruction category: reg, imm, branch, load, store, flush, special: cyclecount, fence, flushall
- Instruction object knows its mnemonic, types of its operands, which category of instruction it belongs to, and some category-specific information
  - For register-register and register-immediate instructions the concrete computation performed
  - For branch instructions the branch condition
  - For load and store instructions the width of the memory access
- Execution Engine only has to handle each instruction category, not all concrete instructions
- New instructions that fit an existing category can be added easily by the user -->

The instructions of our instruction set are further distinguished based on their *instruction category*. The possible instruction categories are *register-register* instructions, *register-immediate* instructions, *branch* instructions, *load* instructions, *store* instructions, *flush* instructions, and three special categories for the individual *rdtsc*, *fence*, and *flushall* instructions.
Our implementation uses `InstructionKind` objects to model the individual instructions of our instruction set. Each such object defines an instruction by its mnemonic, the number and types of its operands, the instruction category it belongs to, as well as some category-specific information. For register-register and register-immediate instructions, this is the concrete computation performed. For branch instructions, this is the branch condition. And for load and store instructions, this is the width of the memory access.

Grouping similar instructions into categories allows the execution engine to handle executed instructions based solely on their instruction category; the execution engine does not need to handle every concrete instruction separately.
New instructions that match an existing instruction category can be added easily by users, without having to modify the execution engine.
The mechanisms involved in the execution engine are described in detail in [@sec:execution].

<!-- - Parser consumes abstract description of instructions, only mnemonic and operand types
  - Doesn't need to know about every concrete instruction
- Strips comments, introduced by `//`
- Handles labels, label name followed by `:`
  - Labels can be referenced before they are defined without special indication
- Two passes: first to extract all labels, second to actually parse instructions -->

Our parser is based on an abstract description of the instructions of our instruction set. This description is limited to the instruction's mnemonic and the number and types of its operands. The parser handles all instructions uniformly and has no information about the semantics of any instruction.
Operation of the parser is divided into two passes over the input file. The first pass exclusively handles label definitions. The parser maintains an internal directory of labels, associating each label name with the immediately following instruction.
The second pass parses the actual program, with one instruction per line. After determining the mnemonic and looking up the corresponding instruction, it parses all operands, subject to the rules for operand types described above.
Having identified the instruction and parsed all operands, the parser builds an `Instruction` object, which models a concrete instruction in program code. Every `Instruction` object references the `InstructionKind` object of the instruction it represents, and contains the concrete values of all operands.
During both passes, the parser skips over any comments, which are lines starting with two slashes (`//`).
Performing two passes in this way allows labels to be used both before and after their definition.

### Data representation {#sec:data}

<!-- - Based on 8-bit byte, 16-bit word
- All registers store a word
- All instructions operate on whole words, except for lb and sb
- All immediate operands of instructions are words
- Words are interpreted as unsigned or twos-complement signed values
  - Distinction only relevant for comparisons of the branch instructions, see sec:isa -->

The data representation used throughout our CPU is based on 16-bit values, called *words*.
All CPU registers store a word. All instructions operate on words, and all immediate operands of instructions are words.
A minor exception to this are the *store byte* and *load byte* instructions, that truncate a word to an 8-bit byte and zero-extend an 8-bit byte to a word, respectively. See [@sec:ISA] for a detailed description of memory operations.
Words are interpreted either as unsigned or two's complement signed integer values. However, the distinction between unsigned and signed values is only relevant for the comparison operations used by branch instructions. See [@sec:ISA] for a detailed description of branch instructions.

<!-- - Bytes only relevant for the representation of words in memory
- The two individual bytes of words are stored in memory in little endian order, i.e. the least-significant byte at the lowest memory address -->

Since our memory model is based on 8-bit *bytes*, words are separated into two 8-bit values when representing them in memory.
The two individual bytes of words are stored in memory in little endian order, i.e. the least-significant byte is stored at the lowest memory address.
For a detailed description of the mechanics involved in memory operations, see [@sec:memory].

### CPU frontend {#sec:CPU_frontend}
\marginpar{Melina Hoffmann}

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
<!--todo: source needed? -->

Detailed information about the BPU of our modern base CPU is not widely available [@skylake]. 
In general, the Gshare BPU of modern CPU consists of multiple components.
It contains a branch target buffer (BTB) that holds the predicted target addresses for conditional branches [@spectre].
It also uses a pattern history table (PHT), that can be implemented as a 2-bit-saturating counter, and a global history register (GHT) to predict whether a conditional jump will be taken or not [@Evtyushkin].

In our emulator, we forgo the BTB entirely.
Real life CPUs benefit from stored target addresses since they have to expensively decode each branch instruction before they can work with the target address [@skylake].
In our emulator, the parser decodes the jump labels from the assembler code and directly provides them to the frontend, so storing them in an additional buffer is unnecessary [@sec:parser].
We further forgo the GHT because it is not strictly necessary to execute a Meltdown or Spectre attack.
Additionally, our emulator and its behavior are easier to understand and predict without it, which is important when implementing microarchitectural attacks for didactic purposes.
The BPU of our emulator only consists of a PHT, which is enough for simple Spectre-PHT variants [@sec:evaluation_spectre].

The default PHT used in our emulator holds an array called `counter` of configurable length $2^n$ to store several predictions.
The instructions are assigned to different prediction slots by the last $n$ bits of their index in the instruction list.
For each of the slots, the prediction can take the four different values from zero to three, where zero and one indicate that the branch will probably not be taken and two and three indicate that the branch is likely to be taken.
The source code for our emulator also contains a more simple BPU with only one slot for all instructions.
While the more advanced BPU is used by default, the simple BPU can be chosen in the config file [@sec:config].

When the execution engine executes a branch instruction, the BPU is updated with the actual branch outcome for the instruction and the prediction in the PHT is updated by a 2-bit-saturating counter as introduced in [@SCA].
This means that the counter has values 0 (strongly not taken), 1 (weakly not taken), 2 (weakly taken) and 3 (strongly taken).
When the branch is actually taken, the counter is increased by one, unless it is already at 3 and cannot be increased further.
Similarly the counter is decreased to as low as 0 when the branch is not actually taken.
If the counter is at values 0 or 1, it predicts the branch as not being taken, and predicts it as taken if it has a value of 2 or 3.

#### Instruction Queue {#sec:iq}

In a real life CPU, the overall purpose of the frontend is to provide the execution unit with a steady strean of instructions so the backend is busy as much as possible and therefore efficient.
In a modern x86 CPU, the frontend has to fetch x86 macro-instructions from a cache and decode, optimize and queue them repeatedly to provide the backend with a queue of µ-instructions ready for issuing in the execution engine.
[@skylake]

In our emulator, except for the BPU, the functionality of the CPU frontend is bundled in *frontend.py*.
It is significantly simplified compared to a real life x86 CPU, especially since the we use only one type of instructions instead of distinguishing between macro- and µ-instructions [@sec:ISA].
They are already provided as a list by the parser, which renders the decoding and optimization steps in the frontend unnecessary [@sec:parser].

The main task of our frontend is to act as an interface between instruction list provided by the parser and the execution engine [@sec:execution].
It provides and manages the instruction queue, which holds the instructions that the execution engine should issue next.
Conditional branches with their respective BPU predictions are taken into account when filling the queue.
This enables speculative execution which is needed for Spectre attacks [@sec:meltdown-and-spectre].

The central component of our emulated frontend ist the instruction queue.
In our version, it does not only hold the instructions themselves, but also for every instruction in the queue, the respective index in the instruction list is stored.
For branch instructions it also holds the respective branch prediction from the BPU at the time that the instruction was added to the queue.
This additional information is needed by the execution engine to handle mispredictions and other exceptions [@sec:execution].

When adding instructions to the queue, the frontend selects them from the instruction list, adds the additional information for the execution engine and places them into the instruction queue until the queue's maximum capacity is reached.
The frontend maintains a program counter `pc` that points to the next instruction in the list that should be added to the queue.
When the frontend encounters a branch instruction and the branch is predicted to be taken, the frontend adjusts the pc to resume adding instructions at the branch target.
If a branch was mispredicted, the frontend provides a special function to reset the pc and refill the instruction queue with the correct instructions.

Additionally, the frontend provides a function to add a µ-program to the queue.
It consists of a list of instructions separate from the parser instruction list.
When adding the µ-program to the queue, the frontend may exceed the maximum queue capacity.
This functionality can be used to implement mitigations against microarchitectural attacks, e.g. by adding a µ-program as part of the exception handling after an illegal load [@sec:evaluation_mitigations].

The frontend provides interfaces to both read and take instructions from the queue.
It also provides a function that combines taking an instruction from the queue and refilling it.
Additionally, the frontend has an interface for flushing the whole queue at once without taking the instructions from the queue.
The latter can be used when demonstrating mitigations against microarchitectural attacks [@sec:evaluation_mitigations].

The frontend provides further basic interfaces, e.g. for reading the size the *instruction queue* and reading and setting the *pc*.
These are used by the other components during regular execution, e.g. when issuing instructions to the execution engine, but also to reset the queue to a certain point in the program after an exception has occurred [@sec:rollback].
Since our emulator only executes one program at a time, the other components can check via another interface whether the frontend has reached the end of the program.

### Memory {#sec:memory}
\marginpar{Felix Betke}
Memory is primarily managed by the Memory Subsystem (MS). As a simplification over an MS as it is assumed to be used by Intel's Skylake architecture [@skylake], our version maintains only a single cache and no load, store, or fill buffers. Further, it maintains the main memory directly. Due to the lack of an operating systems, there are no virtual addresses. These simplifications are possible, since our objective is to allow users to learn about Meltdown-US-L1 and Spectre v1, none of which rely on any of the MS components we removed in our version. Further, since our CPU consists of a single core only, the MS can directly use the main memory.

To represent the main memory, the `MemorySubsystem` class contains a simple array that has $2^{Word Width}$ entries. Since our emulator does not run an operating system and therefore does not support paging, a different method is needed to model a page fault that allows attackers to enter the transient execution phase of the Meltdown-US-L1 attack (as explained in [@sec:meltdown-and-spectre]). To solve this, we declare the upper half of the address space (`0x8000` to `0xffff`, by default) to be inaccessible. Any reads or writes to an address within the upper half result in a fault which causes a rollback a couple of cycles later. Naturally, the value written to the inaccessible addresses is `0x42`, while the ones accessible by programs are initialized to `0`.

To handle memory accesses,`read_byte`, `read_word`, `write_byte`, and `write_word` functions are available, which do as their names suggest, optionally without any cache side effects. Each function returns a `MemResult` instance, which contains the data, the number of cycles this operation takes, whether the operation should raise a fault (i.e. memory address is inaccessible), and, if so, in how many cycles this happens. For `write` operations, only the variables regarding faults are of relevance. Notice that one does not actually have to wait for the data. Instead, the caller receives the data immediately with a counter indicating in how many cycles it should be used.

Other functions that allow the UI to visualize the memory contents are provided. More specifically, `is_addr_cached` and `is_illegal_access` return whether an address is currently cached and whether a memory access to a specific address would raise a fault, respectively. Further, the `MemorySubsystem` includes functions that handle the cache management, such as `load_line`, `flush_line`, and `flush_all`.

#### Meltdown Mitigation
As explained in [@sec:meltdown-and-spectre-mitigations], researchers suggest one of Intel's mitigations to zero out any data illegaly read during the transient execution phase.
To model this, both the `read_byte` functions still perform the read operation, but provide `0` as the data in the returned `MemResult`, if the mitigation is enabled. As of now, the read operation still changes the cache, but since only the contents of the inaccessible memory address are cached and not the corresponding oracle entry of the attacker, the mitigation still works. We believe a consequence of the CPU still performing the illegal read operation but zeroing out the result is that there are cache side effects. If desired, this behavior can be changed easily in the `read_byte` function.

#### Cache {#sec:cache}
To enable attackers to encode transiently read data, the MS maintains a single cache. The number of sets, ways, and entries per line can be configured via the config file (see [@sec:config]). The base `Cache` class firstly initializes all cache sets as an array with each entry holding an array of instances of the `CacheLine` class. There are functions that allow components using the cache to `read`, `write`, and `flush` data given an address and data, if applicable. The `parse_addr` can be used to obtain the index, tag, and offset of an address. Lastly, the `Cache` class includes functions that allow the UI to visualize its state (`get_num_sets`, `get_num_lines`, `get_line_size`, and `get_cache_dump`). Note that the abstract `Cache` class cannot be used directly, as it does not implement the `_apply_replacement_policy_` function.

The `CacheLine` class holds an integer array for the data, a tag, and its own size. Further, functions to `read`, `write`, and `flush` are provided. Lastly, there are functions that set the tag (`set_tag`) and return whether or not the cache line is currently in use by checking if the tag is set. Contrary to the `Cache` class, the `CacheLine` class can be used directly.

By default, there are three available cache replacement policies that determine which cache line is evicted from a full cache set in case new data should be added. All are implemented by extending the base `Cache` and `CacheLine` classes accordingly. The first policy is the random replacement policy (RR) whose implementation can be found in the `CacheRR` class. This policy simply picks a cache line at random for eviction. Even though the policy introduces noise into the side channel, users may experiment with it for their cache attacks, if they so choose (see [@sec:config]).

The second cache replacement policy is the least-recently-used policy (LRU). By this policy, the cache line to be evicted from a full cache set should be the one whose most recent access was the longest time ago. To achieve this functionality, a new `CacheLineLRU` class updates a `lru_timestamp` variable each time the `read` or `write` functions are called. This variable is then used by the new `CacheLRU` class in its implementation of the `_apply_replacement_policy` function.

Lastly, the third cache replacement policy is the first-in-first-out (FIFO). In case of a full cache set, this policy picks the cache line that was first populated with data and flushes it. The classes `CacheFIFO` and `CacheLineFIFO` implement the required functions by using a `first_write` variable.

Even though more complex replacement policies exist, the exact way in which they work is often undocumented [@find_eviction_sets]. However, we believe our chosen policies are sufficient to understand Meltdown, Spectre, and most cache timing attacks, such as Flush+Reload. New cache replacement polices can easily be added by defining the desired behavior in new cache and cache line classes that inherit from `Cache` and `Cache_Line`, respectively. Further, the constructor of the MS needs to be adjusted to account for the existence of the new policy.

### Execution Engine {#sec:execution}

\marginpar{Jan-Niklas Sohn}

<!-- - Executes instructions out-of-order
  - Ofc data dependencies have to be honored to guarantee correctness
  - We use a modified version of Tomasulo's Algorithm described in sec:tomasulo -->

The execution engine is the central component of a CPU. It is the component responsible for actually performing computations, by executing the stream of instructions provided by the frontend.
Just like the execution engine of modern x86 processors, our execution engine executes instructions out-of-order, i.e. not necessarily in the order of the incoming instruction stream [@gruss-habil, p. 15]. In order to preserve the semantics of the program, any data dependencies have to be honored during reordering. For this we use a modified version of Tomasulo's Algorithm, that is described in detail in [@sec:Tomasulo].
<!-- although the frontend passes instructions in program order to the execution engine, the order in which these instructions are actually executed usually differs. -->

<!-- - Contains Reservation Station with a fixed number of slots
  - Unified, i.e. each slot can contain any instruction (same as in modern CPUs)
  - Also used to model Load Buffer and Store Buffer, specifics of memory accesses are handled by the slots directly
  - Instructions' ability to execute concurrently only limited by available slots, no concept of Execution Units that instructions need to be dispatched to; instructions execute in slots directly -->

The execution engine contains the Reservation Station with a fixed number of instruction slots. Each slot is either empty or contains an instruction that is currently being executed. We call such instructions *in-flight*.
Our Reservation Station is unified, i.e. each slot can contain any kind of instruction. The same is often found in modern CPUs [@skylake].
The slots of our Reservation Station are also used to model Load Buffers and Store Buffers; the specifics of executing memory accesses are handled by the slots directly instead of separate components.
We also have no concept of Execution Units that instructions need to be dispatched to, which means that instructions' ability to execute concurrently is only limited by the number of available slots.

<!-- - Stages of execution:
  - Executing:
    - Wait for source operands to become available and compute result
    - Once result is computed: Make it available to other instructions (or the register file), transition to retiring -->

All instructions pass through two phases during execution: In the first phase the instruction is said to be *executing*. It waits for any source operands to become available and computes its result.
Once the result is computed, the instruction waits for a specific amount of CPU cycles. This delay is introduced to mimic the latency of real execution units, which may take several CPU cycles to compute a result.
After this delay expires, the instruction's result is made available to waiting instructions, and the instruction transitions to the second phase.

  <!-- - Retiring: Determine if instruction causes a fault
    - Fault means microarchitectural fault; both architecturally visible faults like memory protection violations and architecturally invisible faults like branch mispredictions are handled in the same way in the Execution Engine
    - Once the instruction finishes retiring its slot becomes available and may execute a new instruction -->

In the second phase the instruction is said to be *retiring*. The instruction determines if it causes a *fault*, which in this case means a *microarchitectural* fault. These can be architecturally visible faults like memory protection violations or architecturally invisible faults like branch mispredictions; both are handled the same way in the Execution Engine.
Once the instruction finishes retiring its slot becomes available again and may be used to execute a new instruction.

<!-- - In each clock cycle only one instruction is able to finish execution or retirement
  - Models contention of the common data bus, and improves debugging experience -->

In each clock cycle only a single instruction may finish execution or retirement. This models the contention of the Common Data Bus, which is used to provide information about computation results inside the Execution Engine and to other components and can only transmit information about a single result each clock cycle.

<!-- - Contains register file
  - Each register entry either contains a concrete value or references a slot of the Reservation Station that will produce the register's value
  - Since instructions are issued in program order, the state of the register file at a single point in time represents the architectural register state at that point in time, with yet-unknown register values present as slot references -->

Besides the Reservation Station, the Execution Engine also contains the Register File, with one entry for each register. Each register entry either contains the concrete value of the register or references a slot of the Reservation Station that will produce the register's value.
Since instructions are issued in program order, the state of the register file at a single point in time represents the architectural register state at that point in time, with yet-unknown register values present as slot references.

## Out of Order Execution {#sec:Tomasulo}
\marginpar{Melina Hoffmann}

Our emulator implements out-of-order execution.
This allows transient execution of instructions before the fault handling of previous instructions is finalized, which is essential for Meltdown type attacks [@sec:meltdown-and-spectre].
Our version of out-of-order execution is based on Tomasulos algorithm [@sec:background-out-of-order-execution].
Since the goal of our out-of-order execution is to enable and clearly illustrate microarchitectural attacks, not optimal performance, we use a simple version of Tomasulos algorithm.
In our emulator, the components necessary for Tomasulos algorithm are located in the Execution Engine [@sec:execution].
Below, we provide a detailed look at our version of out-of-order execution and the components involved in its implementation.

### Issuing instructions

Since we implement out-of-order execution according to Tomasulos algorithm, our Execution Engine does not try to execute instructions directly when it receives them from the frontend [@sec:CPU_frontend], [@sec:execution].
Instead, it issues them to the Reservation Station where multiple instructions can wait until all their operands are ready.
If all operands of an instruction are ready, the Execution Engine can execute it.
This does not generally happen in the order of instructions as provided by the program, but will always lead to the expected effect in that each instruction is executed with the right operands as determined by the program.

The instructions are provided by the frontend in program order [@sec:CPU_frontend]. 
The Execution Engine issues them into the Reservation Station, if it is not yet fully occupied.
The Reservation Station is modelled as a list of *slots* which can each hold an instruction together with additional information about the instruction.
It is unified in that each spot in the list can hold slots for all types of instructions.
This models the unified reservation stations of modern Intel CPUs [@sec:background-out-of-order-execution].

To issue an instruction, the Execution Engine creates a *slot* object that fits the type of the instruction and puts it into the Reservation Station.
Besides the instruction itself, it holds additional information, including a list of the instructions operands.
<!--todo: instruction kind, pc, executing?, retired?, operands additional information -> maybe come back later and add as needed -->
While immediate operands can be directly converted to a Word, register operands have to be resolved during the issuing process.

The registers are modelled by a list in which each entry can either be a *Word* value or the ID of the slot in the Reservation Station which holds the instruction that will produce the next register value as its result.
Since the instructions are issued in program order, this reflects the expected register state at the point of issuing the current instruction, if the program was executed in order [@sec:execution].
The only difference being, that the results of yet unexecuted instructions are being represented by the respective *slotID*.
To resolve the register operands, the current content of the respective register is added to the operand list, so the operand list can contain both *Words* and *slotIDs*.
As described below, *slotIDs* in the operand list will be replaced by the result of the instruction which produces the value when it finishes executing.

Resolving the register operands this way ensures that data dependencies between instructions that use the same registers are adhered to.
To increase performance, real life CPUs practice register renaming in order to further eliminate data dependency hazards [@gruss-habil, p. 226].
(Some) modern CPUs rename registers by assigning ISA level registers to different µ-architectural registers [@SCA].
<!--todo: add source for register renaming by assigning macro to µ (info from SCA)-->
Since we do not differentiate between the ISA and µ-architectural level [@sec:ISA], and aim to keep our emulator easy to comprehend, we do not implement register renaming.

Once the slot with the new instruction is placed into the Reservation Station, if the instruction will produce a result for a target register, the *slotID* of the instruction is put into this target register.
This ensures, that when the next instruction is issued, the register state again represents the expected register state if the instructions where executed in-order.
Note that placing the *slotID* into the target register cannot only overwrite a Word value but also a *slotID*, if the previous instruction that uses this register as its target register is not yet fully executed.
This is not a problem, since every instruction, that may need the result of the respective instruction of the previous *slotID* as an operand, already holds this *slotID* in its own operand list.
It will be notified of the result when it is ready, regardless of whether the *slotID* is still present in the register or not.


### Executing instructions

In basic Tomasulo, when all operands of an instruction in the Reservation Station are ready, it is transferred to a free execution unit and executed [@sec:background-out-of-order-execution].
In our emulator, execution of the instructions is triggered by the *tick* function of the Execution Engine, which is executed once per CPU cycle.
We do not model a finite number of execution units as separate components [@sec:execution].
Instead, the tick function goes through the occupied slots in the Reservation Station and tries to execute each instruction by calling the *tick_execute* function of its respective slot.
This follows the order of the slots in the Reservation Station, regardless of when the instruction in each slot was issued, i.e. regardless of their order in the program.

If the operands of the current instruction are not ready yet, i.e. there are still *slotIDs* in the operand list, the instruction is skipped.

Once the instruction is executed and produces a result, i.e. all operands are available and the wait time is over, according to Tomasulos algorithm this result has to be broadcasted via the CDB to the other slots and the registers [@sec:background-out-of-order-execution].
In our emulator, the CDB is modelled by the *_notify_result* function.
It goes through all registers and replaces all occurrences of the *slotID* of the instruction with the result it just produced.
It also notifies all occupied slots of the result together with the *slotID* of the instruction which produced it, so they can replace the *slotID* in their operands list, if it occurs.
If a result is produced like this, the *tick* function returns without executing further slots.
This mimicks that a real life CDB can only broadcast one result each cycle.
It has the side effect that instructions do not necessarily execute in the same number of ticks, depending on where they sit in the reservation station.
The *tick* function also returns before all slots have been executed if the instruction in a slot retires, in order to properly handle potentially faulting instruction [@sec:rollback].
                    
### Memory hazards

As described above, we handle data dependencies between instructions that use the same registers by using *slotIDs* as placeholders for as yet uncomputed results.
We also need to handle data dependencies between memory accesses.
For this, each slot that contains a memory instruction also holds set of *slotIDs* of other memory instructions that potentially lead to a memory hazard together with the current instruction.
The memory instruction is only executed when all other instructions from its list of potential hazards have retired.

This list is filled when the memory address the instruction will access is computed, beforehand it is set to the placeholder value *none*.
To fill the list, the *_tick_execute* function of the slot goes through its *faulting-preceding* list that i.a. contains all in-flight memory instructions that precede the current instruction in program order, and includes them if they access the same address.
If there is a previously issued memory instructions for which the memory address is not yet available, the instruction waits until the hazard list can be completed.

By adding all instructions to the hazard list that access the same memory address, we potentially generate false positives in the case that two *load* operations read from the same memory address one after the other.
Since efficiency is not our priority, we accept this in order to keep our emulator simple.
Additionally, to simplify fault handling, *store* instructions wait until all other possibly faulting instructions have retired.

### Fence instruction

The *fence* instruction is a special instruction in that it does not produce a result or a lasting side effect in the other components of the emulator.
It creates a fixed point in the execution of the program, effectively suspending the out-of-order execution with regards to the fence instruction [@sec:ISA].
It holds a list of all instructions that were already in the Reservation Station when itself was issued.
Similar to the memory instructions, it waits for all the instructions in the list to be retired before executing itself.
Additionally, no other instructions can be issued to the Reservation Station while it contains a *fence* instruction.

## Exception- and Fault-Handling {#sec:rollback}

\marginpar{Jan-Niklas Sohn}

<!-- Exceptions: -->

<!-- - Exceptions: Distinguish between architectural and microarchitectural exceptions
- Architectural exceptions: visible to the program being executed, usually handled by that program or the underlying operating system
  - In our case there is no operating system that could handle exceptions, and requiring the program to handle exceptions would increase the complexity of both our CPU and user programs
  - For this reason architectural exceptions are handled implicitly, by skipping execution of the instruction that caused the exception. After an exception occurred, execution continues with the following instruction instead
  - In our case: Invalid memory accesses
- Microarchitectural exceptions: Not architecturally visible, handled directly by the microarchitecture
  - In our case: Mispredicted branches -->

*Exceptions* in general are certain conditions that can occur during execution and require handling before execution can be continued. We distinguish between *architectural* and *microarchitectural* exceptions.

Architectural exceptions are visible to the program being executed and are usually handled by that program or the underlying operating system.
In our CPU emulator there is no operating system that could handle architectural exceptions, and requiring the program to handle these would increase the complexity of both our CPU and user programs.
For this reason architectural exceptions are handled implicitly, by skipping execution of the instruction that caused the exception. After an exception occurred, execution continues with the following instruction instead.
The only architectural exceptions present in our CPU are caused by invalid memory accesses, when a memory operation is performed on an inaccessible address.

Microarchitectural exceptions in contrast are not visible to the program being executed and handled directly by the microarchitecture.
In our case the only cause for a microarchitectural exception are mispredicted branches.

<!-- - Both architectural exceptions and microarchitectural exceptions cause what we call microarchitectural *faults*
  - Both handled in the same way inside the Execution Engine
  - Difference in behavior only introduced in the main CPU component, as mentioned in sec:CPU -->

Both architectural exceptions and microarchitectural exceptions cause what we call microarchitectural *faults*.
All microarchitectural faults are handled in the same way inside the Execution Engine;
the difference in behavior between architectural exceptions and microarchitectural exceptions is only introduced in the main CPU component, as mentioned in [@sec:CPU].

### Rollbacks

<!-- - General concept of rollbacks:
  - Since we execute instructions out-of-order:
    - Instructions preceding the faulting instruction in program order might have not yet been executed
    - Instructions following the faulting instruction in program order might already have been executed
  - In order to preserve illusion / abstraction that instructions are executed in program order from an architectural point of view
  - We have to restore the architectural state from the time the faulting instruction was issued before we can properly handle the fault
- Instructions that follow the faulting instruction in program order, but are executed before the rollback is performed are said to occur in *transient execution*
  - They are executed as usual, but afterwards their operation is rolled back -->

As discussed in [@sec:Tomasulo], our CPU executes instructions out-of-order. Because of this, special care must be taken when handling microarchitectural faults. In particular, the following effects need to be considered:

- Instructions preceding the faulting instruction in program order might have not yet been executed.

- Instructions following the faulting instruction in program order might already have been executed.

The abstraction that, from an architectural point of view, instructions are executed in program order has to be preserved.
Thus, we have to restore the architectural state from the time the faulting instruction was issued before we can properly handle the fault.
This process of restoring the architectural state is called *rollback*.
Instructions that follow the faulting instruction in program order, but are executed before the rollback is performed, are said to occur in *transient execution*;
they are executed as usual, but afterwards their operation is rolled back.

<!-- - In our CPU, rollbacks are local to the Execution Engine
  - In case of a fault, Execution Engine performs the rollback
  - And returns information about the fault to the main CPU component, which performs the remainder of the fault handling -->

In our CPU, rollbacks are local to the Execution Engine.
In case of a fault, the Execution Engine performs the rollback,
and returns information about the fault to the main CPU component. The main CPU component then performs the remainder of the fault handling.

<!-- - Two possible approaches:
  - Track changes any executed instructions made to the architectural state, perform in reverse to recover the target state
  - Take a snapshot of the architectural state when we issue the faulting instruction, restore this snapshot on fault
  - We don't know what approach real x86 CPUs take, snapshot-based approach is easier to implement in a software simulator like ours
- Architectural state in our case includes the register state and the contents of memory
  - Not included: Cache, BPU
  - Two different techniques used for restoring the register state and the contents of memory
  - If multiple instructions might cause a fault, we also have to ensure that the fault that comes first in program order is the one that gets handled
  - To achieve that, implementation uses the category of *potentially faulting instructions*
    - In our case that includes branch instruction and memory operations -->

There are two possible approaches to performing rollbacks.
The first approach tracks any changes that executed instructions make to the architectural state. When a fault occurs, these tracked changes can be performed in reverse in order to recover the target architectural state.
The second approach records a snapshot of the architectural state when the faulting instruction is issued. When a fault occurs, this snapshot can be restored in order to recover the target architectural state.
It is not publicly documented what approach real x86 CPUs take to performing rollbacks. Our implementation follows the snapshot-based approach, since it is judged to be easier to implement in a software-based emulator.

In our case, the architectural state that needs to be restored includes the register state and the contents of memory.
The state of the cache and the BPU are not considered part of the architectural state and are not restored when performing a rollback.
If multiple instructions might cause a fault, the fault that comes first in program order must be the one that is handled.
We employ different techniques for ensuring that the register state and the contents of memory have the proper state after the rollback, and for making sure the first fault in program order is handled. These are described in the following sections.
Our implementation uses the category of *potentially faulting instructions*, which includes branch instructions and memory operations.

#### Restoring the Register State

<!-- - When a potentially faulting instruction is issued, a copy of the current register state is stored in the reservation station slot
  - As described in sec:execution, the register state might contain references to other slots of the reservation station
- When the instruction actually faults, we continue execution normally until all of the slots referenced by the captured register state have finished executing
- Then we can restore the captured register state -->

<!-- To restore the correct architectural register state during rollback, a copy of the current register state is made whenever a potentially faulting instruction is issued -->
When a potentially faulting instruction is issued, a copy of the current register state is stored in the reservation station slot.
As described in [@sec:execution], the register state might contain references to other slots of the reservation station.
When the instruction actually faults, execution continues normally until all of the slots referenced by the captured register state have finished executing.
Then the captured register state contains no more slot references, and can be restored.

#### Restoring the Contents of Memory

<!-- - Storing a snapshot of the contents of memory every time a potentially faulting instruction is issued would require lot of space and prevent the rollback from being local to the Execution Engine
  - Thus, we instead serialize the execution of store instructions with respect to other potentially faulting instructions
- When a store instruction is issued, we record all slots of the reservation station that contain potentially faulting instructions
- Before performing the store operation, we wait until all of the recorded slots have retired
- This ensures that store operations are only performed when we know that no preceding instructions cause a fault -->

Storing a snapshot of the contents of memory every time a store instruction is issued would require a lot of space and prevent the rollback from being local to the Execution Engine.
Thus, we instead serialize the execution of store instructions with respect to other potentially faulting instructions.
When a store instruction is issued, all slots of the reservation station that contain potentially faulting instructions are recorded.
Before performing the store operation, execution halts until all of the recorded slots have retired.
This ensures that store operations are only performed when it is known that no preceding instructions cause a fault.

#### Handling Faults in Program Order

<!-- - Same technique as used to avoid having to restore contents of memory
- When a potentially faulting instruction is issued, we record all slots of the reservation station that contain potentially faulting instructions
- When the instruction actually faults, we continue execution normally until all of the recorded slots have retired
- This ensures that potentially faulting instructions retire strictly in program order -->

To make sure that faults are handled strictly in program order, we use the same technique as used to avoid having to snapshot and restore the contents of memory, described above.
When a potentially faulting instruction is issued, all slots of the reservation station that contain potentially faulting instructions are recorded.
When the instruction actually faults, execution continues normally until all of the recorded slots have retired.
This ensures that potentially faulting instructions retire strictly in program order.

<!-- - All three of these techniques require waiting on the execution or retirement of preceding instructions
- Except for store instructions waiting for preceding potentially faulting instructions, this is only required in the case when a fault actually occurs
- Thus, in the expected case of no faults the out-of-order execution is not unnecessarily restricted -->

The techniques described above require waiting on the execution or retirement of preceding instructions.
However, except for store instructions waiting for preceding potentially faulting instructions, this is only required in the case when a fault actually occurs.
Thus, in the expected case of no faults the out-of-order execution is not unnecessarily restricted.

### Transient Execution Attacks

<!-- - State of the cache is not restored
  - Allows using the cache as a transmission channel from transient execution
  - As usually used in Meltdown- and Spectre-type attacks
- State of the BPU is not restored
  - Could be used as a transmission channel just like the cache -->

As mentioned above, the state of the cache is not restored during a rollback.
Thus, transiently executed instructions can influence the cache in a way that persists beyond the rollback. During normal execution, the state of the cache can then be observed using a timing-based side channel.
This allows using the cache as a transmission channel from the transient execution domain to the usual architectural domain.
Such a transmission channel is typically used in Meltdown- and Spectre-type attacks, and integral to their success.

The state of the BPU is similarly not restored during a rollback. Transiently executed instructions can influence the BPU by performing branches, and during normal execution the state of the BPU can be observed using the differences in execution time caused by mispredicted branches.
Because of this, the BPU could be used as a transmission channel just like the cache.

<!-- - Why meltdown is possible
  - The result of a faulting load operation is made available to following instructions before the fault is handled
  - During transient execution, the result can be encoded in the cache -->

The result of a faulting load operation is made available to following instructions before the fault is handled.
During transient execution, this result can be transmitted to the architectural domain via a cache-based channel.
Thus, Meltdown-type attacks are possible in our CPU emulator.
This is demonstrated and described in detail in [@sec:evaluation_meltdown].
<!-- [Section @sec:evaluation_meltdown] describes and demonstrates such a Meltdown-type attack. -->

<!-- - Why spectre is possible
  - During transient execution after a mispredicted branch, memory loads can be performed and their result encoded in the cache -->

During the transient execution after a mispredicted branch, memory loads can be performed.
In the same transient execution, their result can be transmitted to the architectural domain via a cache-based channel.
Thus, Spectre-type attacks are possible in our CPU emulator.
This is demonstrated and described in detail in [@sec:evaluation_spectre].

## ISA {#sec:ISA}
\marginpar{Melina Hoffmann}

Real life Intel x86 CPUs differentiate between two types of instructions or operations. 
Macro-operations refer to the relatively easily human readable and convenient but complex instructions that are described by the x86 ISA.
Their length differs between the instructions.
Internally, in the execution units, the CPU works on µ-operations, which are small operations of a fixed length.
One macro-operation contains one or multiple µ-operations.
The CPU frontend has to decode the macro-operations into µ-operations in an expensive multi step process.
[@skylake], [@macro_op], [@micro_op]
<!--todo: get a better source. Intel directly? Gruss habille? -->
<!--
    erstmal weg lassen und auf x86 konzentrieren, weil die das aus der VL kennen
RISC V: pseudo- and base instructions
pseudo instructions: can encapsulate more than one base instruction or can be a convenient ... for a base instruction where one or more operand is fixed (e.g. nop -> addi x0, x0, 0, mv rd, rs -> addi rd, rs, 0) (source: RISC V ISA Doc)
    in RISC V also directly use base instructions? not really the same?
-->

Our CPU emulator only uses one type of instructions.
They are directly read from our assembler code by the parser and passed to the execution engine without further decoding, splitting or replacing [@sec:parser], [@sec:CPU_frontend].
To show basic Meltdown and Spectre variants, we do not need overly complex instructions, e.g. instructions that contain multiple memory accesses in one or that are used to perform encryption in hardware [@sec:evaluation_meltdown], [@sec:evaluation_spectre].
Basic arithmetic operations, memory accesses, branches and a few special operations are sufficient for the demonstrated attacks and are both easy to implement as single instructions and to use in assembler code that should be well understood by the author. 
Using the same operations throughout the emulator also makes the visualization more clear and easier to follow, e.g. when the same operations appear, one after the other, in the visualization of the assembler code, the instruction queue and the reservation stations [@sec:UI].

### Default Instruction Set {#sec:default_instr} 

In order that our CPU emulator can recognize and work with an instruction, it has to be registered with the parser [@sec:parser].
In our default setting, we register a basic set of instructions with the parser so students can start writing assembler code and using the emulator right away.
This basic instruction set is also used in our example programs in [@sec:UI].

Our relatively small instruction set is based on a subset of the RISC-V ISA [@riscv].
It offers a selection of instructions that is sufficient to implement Meltdown and Spectre attacks as well as other small assembler programs, while still being of a manageable size so students can start to write assembler code quickly without spending much time to get to  know our ISA.
<!--todo: add this?  (still turing complete, vgl. vllt. TI-Folien wegen konkreter min. Instruktionssets...) -->
The syntax of the assembler representation is also based on RISC-V as introduced in the "RISC-V Assembly Programmer’s Handbook" chapter of the RISC-V ISA [@riscv]. 
Also as in the RISC-V ISA, with our default configuration we have 32 registers available, see [@sec:config].
If needed, students can add further instructions by registering them with the parser [@sec:parser].

In the following subchapters we introduce the instructions of our default ISA.
They are grouped according to their respective instruction type in the emulator except for the special instructions which are grouped together [@sec:parser].
All default instructions are summarized in the appendix into a quick reference sheet [ref_appendix]. 
<!--
todo: cheat sheet in Anhang
vllt. referenz in Fussnote verschieben
ggf. auf Cheat Sheet im Anhang verweisen
    maybe put information like address calculation in table description so everyone has all the information
adjust cheat sheet and table snippets so the wording is nice and the table is as non-redundant as possible
-->
<!--
try inline LAtex and the option to place tables "here" \h! , needs some additional LaTex package
if that does not work, maybe table descritions? but that would be a bad formatting choice
-->

#### Arithmetic and Logical Instructions without Immediate {#sec:instr_alu}

These are basic arithmetic and logical instructions that operate solely on register values, i.e. both source operands and the destination operand reference registers.
For simplicity, we write, for example, Reg1 when referring to the value read from or stored in the register referenced by the first register operand.

Each of these default instructions uses the respective python standard operator on our *Word* class to compute the result, except for the right shifts.
For the logical and the arithmetic right shift, the python standard right shift operator is used on the unsigned and the signed version of the register value respectively.
When returning the result as a *Word*, it is truncated to the maximal word length by a modulo operation, if necessary. 
This means, that any potential carry bits or overflows are effectively ignored.
<!--
    weg lassen, eh schon wieder sehr lang:
    no explicit NOP, but in RISC V: NOP is encoded as ADDI x0, x0, 0
        if needed, can do something similar manually
-->
<!--
(arithmetic) flags:
same as RISC V: branch and comparison function in one -> can be easily implemented, is easier for the students than splitting this into a comparison and a branch instruction, no real influence on Meltdown and SPectre
no need for flags (RISC V: does not seem to use flags for normal arithmetic instr (carry, zero etc.), only for exceptions, memory accesses -> leave out)
-> do I even mention this?
-->

\begin{tabular}{ |p{2cm}|p{3cm}|p{9cm}|  }
\hline
\multicolumn{3}{|c|}{Arithmetic and Logical Instructions without Immediate} \\
\hline
Instr. Name&Operators&Description\\
\hline
add &Reg1, Reg2, Reg3&   Reg1 $:=$ Reg2 $+$ Reg3\\
sub& Reg1, Reg2, Reg3   & Reg1 $:=$ Reg2 $-$ Reg3\\
sll& Reg1, Reg2, Reg3&  Reg1 $:=$ Reg2 $<<$ Reg3\\
srl& Reg1, Reg2, Reg3&  Reg1 $:=$ Reg2 $>>$ Reg3 logical\\
sra  & Reg1, Reg2, Reg3& Reg1 $:=$ Reg2 $>>$ Reg3 arithmetical\\
xor& Reg1, Reg2, Reg3 &  Reg1 $:=$ Reg2 xor Reg3\\
or& Reg1, Reg2, Reg3&  Reg1 $:=$ Reg2 or Reg3\\
and& Reg1, Reg2, Reg3&  Reg1 $:=$ Reg2 and Reg3\\
\hline
\end{tabular} 


#### Arithmetic and Logical Instructions with Immediate {#sec:instr_alui}

These are basically the same instructions as in [@sec:instr_alu].
The main difference is, that the second source register is replaced by an immediate operand which is set directly in the assembler code.
This immediate is used as the value of a *Word*, so it is truncated by a modulo operation to be in the appropriate range.

\begin{tabular}{ |p{2cm}|p{3cm}|p{9cm}|  }
\hline
\multicolumn{3}{|c|}{Arithmetic and Logical Instructions with Immediate} \\
\hline
Instr. Name&Operators&Description\\
\hline
 addi &Reg1, Reg2, Imm&  Reg1 $:=$ Reg2 $+$ Imm\\
subi& Reg1, Reg2, Imm   & Reg1 $:=$ Reg2 $-$ Imm\\
slli& Reg1, Reg2, Imm&  Reg1 $:=$ Reg2 $<<$ Imm\\
srli& Reg1, Reg2, Imm&  Reg1 $:=$ Reg2 $>>$ Imm logical\\
srai  & Reg1, Reg2, Imm&Reg1 $:=$ Reg2 $>>$ Imm arithmetical\\
xori& Reg1, Reg2, Imm&Reg1 $:=$ Reg2 xor Imm\\
ori& Reg1, Reg2, Imm&Reg1 $:=$ Reg2 or Imm\\
andi& Reg1, Reg2, Imm&Reg1 $:=$ Reg2 and Imm\\
\hline
\end{tabular} 
    
#### Memory Instructions {#sec:instr_mem}

These instructions provide basic interactions with the emulated memory [@sec:memory].
Load and store instructions exist in two versions, one that operates on *Word* length data chunks, for convenience, and one that operates on *Byte* length data chunks, for the fine granular access needed in micro architectural attacks.
The flush instruction flushes the cache line for the given address [@sec:memory].
The flushall instruction flushes the whole cache.
<!--todo: maybe be more precise about what the flush instruction does -->
The address is calculated in the same way for all memory instructions: addr:=Reg2+Imm, and addr:=Reg+Imm for the flush instruction respectively.
<!--with Reg2 acting as the base and Imm acting as an offset -->

\begin{tabular}{ |p{2cm}|p{3cm}|p{9cm}|  }
\hline
\multicolumn{3}{|c|}{Memory Instructions} \\
\hline
Instr. Name&Operators&Description\\
\hline
lw &Reg1, Reg2, Imm&Reg1$:=$Mem\_word[addr]\\
lb& Reg1, Reg2, Imm   &Reg1$:=$Mem\_byte[addr]\\
sw& Reg1, Reg2, Imm  &Mem\_word[addr]$:=$Reg1\\
sb& Reg1, Reg2, Imm  &Mem\_byte[addr]$:=$Reg1\\
flush  & Reg, Imm&flush cache line of addr\\
flushall  &  - &flush whole cache\\
\hline
\end{tabular} 

#### Branch Instructions {#sec:instr_branch}

All branch instructions compare the values of two source registers. If the comparison evaluates to true, the execution of the program is resumed at the given label in the assembler code.
If it evaluates to false, the next instruction in the program is executed.
Depending on the instruction, the register values are interpreted as signed (s) or unsigned (u) integers.
Labels in the assembler code are automatically resolved by the parser [@sec:parser], [@sec:evaluation_example].
<!-- There are different options for the branch condition so the students can choose which one suits their program best. -->


\begin{tabular}{ |p{2cm}|p{3cm}|p{9cm}|  }
\hline
\multicolumn{3}{|c|}{Branch Instructions} \\
\hline
Instr. Name&Operators&Description\\
\hline
beq &Reg1, Reg2, Label& jump to Label if Reg1$==$Reg2\\
bne& Reg1, Reg2, Label&jump to Label if Reg1$!=$Reg2\\
bltu& Reg1, Reg2, Label&  jump to Label if u(Reg1)$<$u(Reg2)\\
bleu& Reg1, Reg2, Label&  jump to Label if u(Reg1)$<=$u(Reg2)\\
bgtu& Reg1, Reg2, Label&jump to Label if u(Reg1)$>$u(Reg2)\\
bgeu& Reg1, Reg2, Label&jump to Label if u(Reg1)$>=$u(Reg2)\\
blts& Reg1, Reg2, Label&jump to Label if s(Reg1)$<$s(Reg2)\\
bles& Reg1, Reg2, Label&jump to Label if s(Reg1)$<=$s(Reg2)\\
bgts& Reg1, Reg2, Label&jump to Label if s(Reg1)$>$s(Reg2)\\
bges& Reg1, Reg2, Label&jump to Label if s(Reg1)$>=$s(Reg2)\\
\hline
\end{tabular} 

#### Special Instructions {#sec:instr_special}

Rdtsc acts like a basic timing instruction.
It returns the number of *ticks* the execution unit has executed so far into the given register.
<!-- not reset when called-->
<!--todo: This kind of information is used in real life micro architectural attacks [@source]. -->

The fence instruction acts as a fixed point in the out of order execution.
All instructions that are already issued in the execution unit at the point of issuing the fence instruction are executed before the fence is executed.
No new instructions are issued before the execution of the fence instruction is complete.
This can be used to model mitigations against µ-architectural attacks [@sec:evaluation_mitigations].

\begin{tabular}{ |p{2cm}|p{3cm}|p{9cm}|  }
\hline
\multicolumn{3}{|c|}{Special Instructions} \\
\hline
Instr. Name&Operators&Description\\
\hline
rdtsc &Reg& Reg$:=$cyclecount\\
fence& - & add execution fixpoint at this code position\\
\hline
\end{tabular} 


## Config File {#sec:config}
\marginpar{Felix Betke}
To allow users to change certain parameters of the presented emulator or to toggle certain mitigations on or off, a YAML configuration file is available. It can be found in the root folder of the project. Internally, a dictionary containing the entire configuration is passed to each individual component. This section briefly mentions which parts of the demonstrated emulator can be configured, and why which default values have been chosen.

### Memory {#sec:config-memory}
In the "Memory" section, users may configure how many cycles write operations should take (`num_write_cycles`), and how many cycles should be between a faulting memory operation and the corresponding instruction raising a fault (`num_fault_cycles`). By default, the former is set to `5` cycles, the latter to `8`. While the specific values are not as important, the difference between the number of cycles it takes to perform a faulting memory operation (`num_write_cycles`, `cache_hit_cycles`, and `cache_miss_cycles`, see [@sec:config-cache]) and the number of cycles it takes to raise the fault (`num_fault_cycles`) should be at least `1`. Otherwise, the rollback is initiated before the faulting instruction makes the data available to subsequent instructions, thus removing the transient execution time window on which Meltdown and Spectre rely. Note that `num_write_cycles` only affects write operations. To configure the number of cycles it takes to read data, see [@sec:config-cache].

### Cache {#sec:config-cache}
In the "Cache" section, users may configure the size of the cache by setting the number of sets, ways, and entries per cache line. For readability when printing, the default value we chose for all values is `4`. However, it is important to note that if one were to perform the full Meltdown/Spectre attacks by measuring access times to each oracle entry, a sufficient cache size that ensures accessing an oracle entry does not evict another is required.

Further, the cache replacement policy can be set to either "RR", for random replacement, "LRU", for least-recently-used, and "FIFO", for first-in-first-out. Each policy is explained in [@sec:cache]. As RR introduces noise, we have decided against using it as the default. Although widely undocumented, Intel's Skylake architecture is believed to use some kind of specialized version of LRU [@find_eviction_sets]. For that reason, and since our choice is largely irrelevant as long as users clearly understand how the policy works, LRU is set as the default.

The other two values that can be configured are the number of cycles cache hits and misses take (`cache_hit_cycles` and `cache_miss_cycles`). As already mentioned in [@sec:config-memory], the specific values are not as important as their differences. As explained in [@sec:config-memory], Meltdown is not possible if it takes longer to read than to raise an exception. Due to our decision to allow users to perform the Meltdown-US-L1 attack even if the data to be stolen is not currently cached (see [@sec:task]), the number of cycles needed for retrieve data from memory after a cache miss (`cache_miss_cycles`) is lower than the number of cycles it takes for a faulting memory operation to raise a fault (`num_fault_cycles`, see [@sec:config-memory]). To model the Meltdown-US-L1 attack more accurately, a cache miss would have to take more cycles to retrieve the data than the CPU takes to initiate the rollback. In the more realistic scenario, attackers would have to perform two illegal reads, one to cache the secret, and one to steal it. By default, the first read is not necessary.

### Instruction Queue
The config allows users to configure the size of the instruction queue maintained by the frontend. It determines the maximum number of instructions that can be issued per tick. As the transient execution window is largely determined by memory access times and the number of available entries in the unified reservation station, this choice is not as important. Our testing shows the desired attacks are possible with an instruction queue size of `5`. As pointed out in [@sec:CPU_frontend], this limit is ignored in case microprograms are to be executed.

### BPU
Here, the user may configure whether to use the simple BPU, or the advanced one. The difference is that the simple BPU maintains only a single counter, while the advanced one maintains a counter for each index. Additionally, the number of bits used for the counter as well as its initial value can be chosen. By default, we use the advanced BPU with `4` index bits and an initial counter of `2`, which represents "weakly taken".

### Execution Engine
The execution engine allows the configuration of the number of available slots in the reservation station. In part, this value determines the width of the transient execution window. We find that with `8` slots, Meltdown and Spectre attacks are possible. Additionally, the number of registers can be configured. Since our instruction set is based on the RISC-V ISA, we offer the same number of registers by default, which is `32` [@riscv, p. 9].

### UX
The UX can be configured to omit display of certain elements. When selecting to use a large cache, it may be desirable to hide empty cache ways and sets to prevent clutter. By default, we choose to show the empty cache ways so the user can easily can see whether or not a cache set is full. We also choose to show the empty cache sets so there is a visual representation of which addresses correspond to certain sets. Another option is to hide the unused reservation station slots. In this case every entry in the reservation station will be numbered. Showing the unused slots may help the user to keep track of bottlenecks in the execution, and is therefore chosen per default. Finally, the user may choose between capitalized or lowercase letters for the registers. By default, we choose to use lowercase letters.

### Microprograms {#sec:config-microprograms}
This section allows users to configure microprograms that are run once a rollback has been completed and before regular program execution is resumed. For each instruction type, the user can provide the path to a file containing the microprogram. If no microprogram should be run after a specific instruction type faults, the user can either set the file path to `None`, or simply not include it in the config. The instruction types must be their corresponding class names as they are given in the `execution.py` file. We expect users to mostly use microprograms for faulting `InstrLoad` and `InstrBranch` instructions. By default, no microprograms are configured, but one that flushes the entire cache can be found in `demo/flushall.tea`.

### Mitigations
This section allows users to toggle Intel's Meltdown mitigation that overwrites the illegally read value with `0` (see [@sec:meltdown-and-spectre-mitigations]) on or off. By default, it is disabled.

Further, mitigations that are implemented in microcode, such as flushing the entire cache after a rollback (see [@sec:meltdown-and-spectre-mitigations]), can be enabled by users using microprograms in the Microprograms section of the config file (see [@sec:config-microprograms]).

