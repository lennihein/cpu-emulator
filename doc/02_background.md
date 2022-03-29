# Background {#sec:background}
\marginpar{Felix Betke}
This chapter briefly covers the theoretical background needed to use the presented emulator and continue its development. The reader is assumed to have an understanding of elementary CPU concepts, such as pipelining and caching.
Firstly, \ref{sec:background-cpu} introduces the three main components of a CPU and sections \ref{sec:background-out-of-order-execution} and \ref{sec:background-speculative-execution} explain the optimization techniques out-of-order and speculative execution, respectively. Lastly, \ref{sec:meltdown-and-spectre} gives a short overview of the Meltdown and Spectre vulnerabilities relevant for the emulator and presents some mitigations.

## CPU {#sec:background-cpu}
\marginpar{Felix Betke}
A CPU consists of a frontend, an execution engine, and a memory subsystem. As per Intel's Skylake architecture [@skylake], the frontend fetches the instructions, maintains a queue of instructions that are to be executed, and decodes them into simpler microinstructions, which are then communicated to the execution engine. Additionally, it is responsible for the branch prediction (see [@sec:background-speculative-execution]). [@gruss-habil]

The execution engine consists of multiple sets of execution units, each set being responsible for a specific type of microinstruction, such as loads, stores, or arithmetic. Further, the scheduler allows the execution units to work on independent instructions in parallel, while the reorder buffer makes sure that instructions retire in the correct order. A common data bus (CDB) connects the reorder buffer, scheduler, and execution units. Its purpose is further described in [@sec:background-out-of-order-execution]. [@gruss-habil]

Lastly, the memory subsystem handles all memory accesses of the execution units by maintaining caches and ensuring data is fetched from lower level caches or DRAM if needed [@gruss-habil]. Most importantly, requests to data that is present in the caches is served faster than if it were not.

A visualization of the aforementioned components can be found in [@fig:background-cpu].

![Simplified overview an Intel Skylake CPU [@gruss-habil, fig. 2.1]. For the memory subsystem, detailed knowledge of the load and store buffers, as well as the TLBs, is not required. The same applies to the allocation queue of the frontend.](fig/cpu.png){#fig:background-cpu width=450px height=675px shortcaption='Simplified overview of an Intel Skylake CPU [@gruss-habil].'}

## Out-of-order execution {#sec:background-out-of-order-execution}
\marginpar{Felix Betke}
As the name implies, out-of-order execution refers to the idea of executing instructions in a different order than the one in which they are given [@gruss-habil]. With multiple execution units that run in parallel (as described in [@sec:background-cpu]), CPUs can take advantage of mutually independent instructions and execute them at the same time.

The basic realization of this concept is provided by Tomasulo's algorithm [@tomasulo]. It introduces two components, the first of which is the reservation station, which collects the operands of instructions until they are ready to be executed by the execution units. Crucially, the corresponding execution units do not need to wait until all operands are present and can instead compute other instructions. The second component of Tomasulo's algorithm is the Common Data Bus (CDB), which connects all reservation stations and execution units. Whenever a result is computed by an execution unit, the result is broadcast onto the CDB and thus made available to all reservation stations that are waiting for it. This important step ensures that results are not needed to be written to registers first, just to be read again by other instructions that need them as operands.

Initially, according to Tomasulo, each set of execution units needed its own reservation station, however, more modern implementations by Intel use a single unified reservation station, called scheduler, that handles all types of instructions, rather than just one [@tomasulo] [@skylake] [@gruss-habil]. This can also be seen in [@fig:background-cpu].

## Speculative execution {#sec:background-speculative-execution}
\marginpar{Felix Betke}
Speculative execution allows a CPU to predict the outcome of comparisons and other branch instructions. This prevents stalls when waiting for the instruction that determines which branch is taken to finish. Similarly to out-of-order execution, rollbacks are needed in some cases. However, in addition to exceptions, they also occur if a branch was mispredicted. [@gruss-habil]

To predict the outcome of branch instructions, CPUs include a branch prediction unit (BPU) [@gruss-habil]. While available in different configurations, many modern CPUs record the most recent outcomes of a branch with a counter [@gruss-habil] that is either incremented if the branch is taken, or decremented.

## Meltdown and Spectre {#sec:meltdown-and-spectre}
\marginpar{Felix Betke}
Meltdown [@meltdown] and Spectre [@spectre] abuse out-of-order and speculative execution to leak data from memory addresses that are normally inaccessible to the attacker over the caches of the CPU.

### Meltdown
On a high level, Meltdown [@meltdown] works by forcing exceptions when reading data inaccessible to the attacker and transiently encoding this data into the cache to retrieve it once the rollback has completed. What enables Meltdown is a small time window between an invalid memory access and the raising of an exception [@meltdown].

The Meltdown-US-L1 variant of Meltdown [@meltdown] to which the presented emulator is vulnerable works by accessing a memory address for which the attacker has no permission. Firstly, the attacker allocates an oracle array and ensures none of its entries are present in the cache. Upon loading the contents of the inaccessible memory location into a register, the attacker uses the value to access the array at a specific offset. When the rollback caused by the access violation has completed, the attacker measures the access time to each of the array entries to determine which one has been accessed. It is important that the data to be stolen is currently cached. While there are numerous other variants of Meltdown that differ from the basic variant mainly by how they force an exception and from which microarchitectural buffer they leak data, these types of attacks are out of scope.

### Spectre
Spectre [@spectre], on the other hand, relies on the CPU mispredicting a branch and transiently executing instructions that are not part of the correct execution path. This misprediction in a victim process can be induced by maliciously configuring the BPU ([@sec:background-speculative-execution]). Depending on the instructions that are wrongfully executed by the victim, traces may later be found in the processor's cache. Similarly to Meltdown, different variants of Spectre exist. The presented emulator is vulnerable to variant 1 of Spectre, which takes advantage of the CPU mispredicting the outcome of comparison instructions.

### Mitigations {#sec:meltdown-and-spectre-mitigations}
The mitigations for Meltdown are available in both software and hardware, some of which are implemented in the emulator to allow users to experiment with them and determine their effectiveness. A first, rather simple, mitigation for Meltdown is to disable out-of-order execution [@meltdown], which would completely prevent an attacker from encoding the normally inaccessible data into the cache. Later revisions of Intel's architectures introduced further mitigations. Although undocumented by Intel, researchers suspect the processor still performs the illegal read, but zeros out the data that is given to dependent instructions before raising an exception [@break_kaslr]. The emulator implements this mitigation, which may be enabled by the user. Other mitigations deployed by operating systems, such as KTPI (or KAISER) [@meltdown], are highly effective, but out of scope, as there exists no operating system.

Unlike Meltdown, Spectre appears to be a design flaw. While one might argue that transiently computing on real values after it is already known an exception will occur is a bug, the behavior abused by Spectre is a direct consequence of speculative execution ([@sec:background-speculative-execution]). As a result, an effective yet questionable mitigation is to simply disable speculative execution [@spectre]. Alternatively, Intel recommends potential victim's of Spectre v1 to use an "lfence" instruction where appropriate, which ensures prior load instructions retire before continuing, thus effectively disabling speculative execution for certain parts of an application [@intel_analysis]. A fence instruction is provided as part of the emulator's instruction set.

An additional mitigation that works against both Meltdown and Spectre is to flush the entire cache after a rollback. While highly inefficient, it does prevent the retrieval of otherwise inaccessible data after the transient execution phase of the attacks. This mitigation can be realized using the emulator by a sequence of instructions (microprogram) that are executed after each rollback.
