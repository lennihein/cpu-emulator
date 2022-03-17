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

### CPU (F) {#sec:CPU}
The primary purpose of the CPU module is to allow all other components to work together. That is, the CPU initializes all other components and provides interfaces to their functions, which allows the GUI to visualize the current state. In addition, the CPU provides functions which load user programs and a tick function that is called each cycle and does the following: instructions from the instruction queue are fetched from the frontend and forwarded to the execution engine, until either no more slots in the unified reservation station are available, or the instruction queue is empty. It then calls the tick function of the execution engine. In case of a rollback, the instruction queue maintained by the frontend is flushed. If the rollback was caused by a faulting load instruction, execution is resumed at the next instruction (as described in [@sec:rollback]). In case a branch was mispredicted, the frontend is notified and refills the instruction queue accordingly. If configured, corresponding microprograms are sent to the instruction queue. Lastly, a snapshot of the current state of the CPU is taken.

The second purpose of the CPU is to provide the snapshot functionality, which allows a user of the emulator to step back to previous cycles. The snapshot list is simply a list that grows at each cycles, where ech entry is a deepcopy of the CPU instance. To simply be able to deepcopy the CPU class, the snapshot list is held separately and not one of its members. Instead, the CPU class, and therefore each snapshot, maintains an index to its own entry in the snapshot list. This reference makes traversing the snapshot list one step at a time easier. Due to the low complexity of the programs we expect our users to run, at the moment, no maximum number of available snapshots is configured.

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

### Memory (F) {#sec:memory}
Memory is primarily managed by the Memory Subsystem (MS). The class contains a simple array that has $2^{Word Width}$ entries, half of which are initialized to $0$. Since our emulator does not run an operating system and therefore does not support paging, a different method is needed to model a page fault that allows attackers to enter the transient execution phase of the Meltdown-US-L1 attack (as explained in [@sec:meltdown-and-spectre]). To solve this, we have decided to make the upper half of the address space ($32768$ to $65535$, by default) inaccessible. Any reads to an address within the upper half result in a fault which causes a rollback a couple of cycles later. Naturally, the value written to the inaccessible addresses is $0x42$.

To handle memory accesses, _read\_byte_, _read\_word_, _write\_byte_, and _write\_word_ functions are available, which do what their names suggest. Each function returns a _MemResult_ object, which contains the data ($0$ for _write_ functions), the number of cycles this operation takes, whether the operation should raise a fault (i.e. memory address is inaccessible), and, if so, how many cycles this should take. These values allow users to configure the width of the transient execution window.
<!-- Braucht man bei writes diese cycle_values? -->

Other functions that allow the UI to visualize the memory contents are provided. More specifically, _is\_addr\_cached_ and _is\_illegal\_access_ return whether an address is currently cached and whether a memory access to a specific address would raise a fault, respectively. Further, the MS includes functions that handle the cache management, such as _\_load\_line_, _flush\_line_, and _flush\_all_.

#### Meltdown Mitigation (F)
As explained in [@sec:meltdown-and-spectre-mitigations], one of the mitigations implemented by Intel is believed to zero out data illegally read during transient execution. To model this, both the _read\_byte_ functions still perform the read operation, but provide $0$ as the data in the returned _MemResult_, if the mitigation is enabled. As of now, the read operation still changes the cache, but since only the contents of the inaccessible memory address are cached and not the corresponding oracle entry of the attacker, the mitigation still works. The reason for this is that we believe a consequence of the CPU still performing the read operation but zeroing out the result should have side effects on the cache. If desired, this behavior can be changed easily in the _read\_byte_ functions.

#### Cache (F)
To enable tattackers to encode transiently read data, the MS maintains a single cache. The number of sets, ways, and entries per line can be configured via the config file (see [@sec:config])

By default, there are three available cache replacement policies.

### Execution Engine {#sec:execution}

todo

## Out of Order Execution (2 pages) {#sec:Tomasulo}

<!--no implicit register renaming by assigning macro- to µ-registers` -->

todo

## Exceptions and Rollbacks (2-3 pages) {#sec:rollback}

todo

## ISA (2 pages) {#sec:ISA}
<!--
todo: decideshould we move this subchapter to the frontend?
    general concept fits nicely into the backend
    ISA itself is more of a manual
-->

<!--todo: nochmal drübergehen, ob ich instructions und operations noch besser auseinanderhalten muss -->

Real life Intel x86 CPUs differenciate between two types of instructions or operations. 
Macro-operations refer to the relatively easily human readable and convenient but complex instructions that are described by the x86 ISA.
Their length differs between the instructions.
Internally, in the execution units, the CPU works on µ-operations, which are small operations of a fixed length.
One macro-operation contains one or multiple µ-operations.
The CPU frontend has to decode the macro-operations into µ-operations in an expensive multi step process.
sources: [@skylake], https://en.wikichip.org/wiki/macro-operation, https://en.wikichip.org/wiki/micro-operation
<!--todo: get a better source. Intel directly? Gruss habille? -->
<!--
    erstmal weg lassen und auf x86 konzentrieren, weil die das aus der VL kennen
RISC V: pseudo- and base instructions
pseudo instructions: can encapsulate more than one base instruction or can be a convenient ... for a base instruction where one or more operand is fixed (e.g. nop -> addi x0, x0, 0, mv rd, rs -> addi rd, rs, 0) (source: RISC V ISA Doc)
    in RISC V also directly use base instructions? not really the same?
-->

Our CPU emulator only uses one type of instructions.
They are directly read from our assembler code by the parser and passed to the execution engine without further decoding, splitting or replacing [@sec:parser], [@sec:CPU_frontend].
To show basic Meltdown and Spectre variants, we do not need overly complex instructions, e.g. instructions that contain multiple memory accesses in one or that are used to perform encryption in hardware [ref_evaluation_meltdown], [ref_evaluation_spectre].
Basic arithmetic operations, memory accesses, branches and a few special operations are sufficient for the demonstrated attacks and are both easy to implement as single instructions and to use in assembler code that should be well understood by the author. 
Using the same operations throughout the emulator also makes the visualization more clear and easier to follow, e.g. when the same operations appear, one after the other, in the visualization of the assembler code, the instruction queue and the reservation stations [ref_ui].
<!--todo: am Endeeinzelne UI Komponenten referenzieren -->
<!--todo: Formulierungen überarbeiten -->

### Default Instruction Set {#sec:default_instr} 

In order that our CPU emulator can recognize and work with an instruction, it has to be registered with the parser [@sec:parser].
<!--todo: maybe adjust time they need to execute/ in MMU -> maybe sufficiently summarized by "register with the parser" -->
In our default setting default, we register a basic set of instructions with the parser so students can start writing assembler code and using the emulator right away.
This basic instruction set is also used in our example programs in [ref_UI].

Our relatively small instruction set is based on a subset of the RISC-V ISA.
It offers a selection of instructions that is sufficient to implement Meltdown and Spectre attacks as well as other small assembler programs while still being of a manageable size so students can start to write assembler code quickly without spending much time to get to  know our ISA.
<!--todo: add this? (still turing complete, vgl. vllt. TI-Folien wegen konkreter min. Instruktionssets...) -->
The syntax of the assembler representation is also based on RISC-V (as introduced in the "RISC-V Assembly Programmer’s Handbook" chapter of the RISC-V ISA) [ref_RISC-V]. 
If needed, students can add further instructions by registering them with the parser [@sec:parser].

In the following subchapters we introduce the instructions of our default ISA.
They are grouped according to their respective instruction type in the emulator except for the special instructions which are grouped together [@sec:parser].
All default instructions are summarized in the appendix into a quick reference sheet [@ref_appendix]. 
<!--
todo: cheat sheet in Anhang
vllt. referenz in Fussnote verschieben
ggf. auf Cheat Sheet im Anhang verweisen
    maybe put information like address calculation in table description so everyone has all the information
adjust cheat sheet and table snippets so the wording is nice and the table is as non-redundant as possible
-->

<!--todo: hier der Vollständigkeit halber einfügen, dass unser Parser Kommentare kann? -->

<!--
try inline LAtex and the option to place tables "here" \h! , needs some additional LaTex package
if that does not work, maybe table descritions? but that would be a bad formatting choice
-->

#### Arithmetic and Logical Instructions without Immediate {#sec:instr_alu}

These are basic arithmetic and logical instructions that operate solely on register values, i.e. both source operands and the destination operand reference registers.
For simplicity, we write, for example, Reg1 when referring to the value read from or stored in the register referenced by the first register operand.

Each of these default operations uses the respective python standard operator on our Word class to compute the result, except for the right shifts.
For the logical and the arithmetic right shift, the python standard right shift operator is used on the unsigned and the signed version of the register value respectively.
When returning the result as a Word, it is truncated to the maximal word length by a modulo operation, if necessary [@sec:data]. 
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
The main difference is, that the second source register is replaced by an immediate operand which is set directly in the Assembler code.
This immediate is used as the value of a Word in the execution engine, so it is truncated by a modulo operation to be in the appropriate range [@sec:data], [@sec:execution].

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
Load and store instructions exist in two versions, one that operates on Word length data chunks, for convenience, and one that operates on Byte length data chunks, for the fine granular access needed in micro architectural attacks.
The flush instruction flushes the cache line for the given address [@sec:memory].
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
\hline
\end{tabular} 

#### Branch Instructions {#sec:instr_branch}

All branch instructions compare the values of two source registers. If the comparison evaluates to true, the execution of the program is resumed at the given label in the assembler code.
If it evaluates to false, the next instruction in the program is executed.
Depending on the instruction, the register values are interpreted as signed or unsigned integers.
Labels in the assembler code are automatically resolved by the parser [@sec:parser], [rev_eval_and_example_code].
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
It returns the number of ticks the execution unit has executed so far in the given register.
<!-- not reset when called-->
<!--todo: This kind of information is used in real life micro architectural attacks [@source]. -->

The fence instruction acts as a fixed point in the out of order execution.
All instructions that are already issued in the execution unit at the point of issueing the fence instruction are executed before the fence is executed.
No new instructions are issued before the execution of the fence instruction is complete.

\begin{tabular}{ |p{2cm}|p{3cm}|p{9cm}|  }
\hline
\multicolumn{3}{|c|}{Special Instructions} \\
\hline
Instr. Name&Operators&Description\\
\hline
rdtsc &Reg& Reg$:=$cyclecount\\
fence&none& add execution fixpoint at this code position\\
\hline
\end{tabular} 


## Config Files (1 page) {#sec:config}
<!--todo: should we move this to the frontend? more like a manual? -->


todo
