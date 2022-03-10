# Background {#sec:background}
This chapter briefly covers the theoretical background needed to use the presented emulator and continue its development. The reader is assumed to have an understanding of elementary CPU concepts, such as pipelining and caching.

## CPU {#sec:background-cpu}
TODO

## Out-of-order execution
As the name implies, out-of-order execution refers to the idea of executing instructions in a different order than the one in which they are given [@gruss-habil]. With multiple execution units that run in parallel (as described in [@sec:background-cpu]), CPUs can take advantage of mutually independent instructions and execute them at the same time.

The basic realization of this concept is provided by Tomasulo's algorithm [@tomasulo]. It introduces the reservation station, which collects the operands of instructions until they are executed by the execution units. Crucially, the execution units do not need to wait until all operands are present and can instead compute other instructions. The second component of Tomasulo's algorithm is the Common Data Bus (CDB), which connects all reservation stations and execution units. Whenever a result is computed by an execution unit, the result is broadcast onto the CDB and thus made available to all reservation stations that are waiting for it. This important step ensures that results are not written to registers first, just to be read again by other instructions that need them as operands.

Strictly speaking, according to Tomasulo, each set of execution units needs its own reservation station, however, more modern implementations by Intel use a single unified reservation station that handles all kinds of instructions, rather than just one [@tomasulo] [@skylake].

## Speculative execution
Speculative execution allows a CPU to predict the outcome of comparisons and other branch instructions. This prevents stalls when waiting for the instruction that determines which branch is taken to finish. Similarly to out-of-order execution, rollbacks are needed in some cases. However, in addition to exceptions, they also occur if a branch was mispredicted. [@gruss-habil]

To predict the outcome of branch instructions, CPUs include a branch prediction unit (BPU) [@gruss-habil]. While available in different configurations, many modern CPUs record the most recent outcomes of a branch with a counter [@gruss-habil] that is either incremented if the branch is taken, or decremented.

## Meltdown and Spectre
TODO 
