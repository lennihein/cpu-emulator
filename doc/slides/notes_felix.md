Welcome to our LAB presentation where we would like to tell you about our TRANSIENT execution emulator that we developed as a group of 4 in the last semester.

# First: Structure
Again, we are 4 people.
- Felix: Topic, Background, further specific task, describe initial approach
  Serves as introduction
- Melina: Backend. Implementation details and design decisions
- Two Demos:
  - Lenni: Meltdown demo and Intel's mitigation (more later)
  - Jan-Niklas: Spectre demo, cache flush mitigation (more later)
- Conclusion (who?)

# Topic
- Lab builds on Side Channel Attacks (SCA) lecture
  Second part was TE attacks (Meltdown/Spectre)
- Briefly: Meltdown/Spectre 2018
  Essentially allowed user-space attackers to read arbitrary memory
- However: Patches / hardware fixes
  Difficult to experiment (educational purposes)
  Student's PC not usable (CPU not vuln., not the right OS)
- Goal: Vulnerable CPU emulator
    - runs on many systems
    - graphical UI, gdb-like interface
    - offers noise-free environment to better understand Melt/Spec
    - Better insight into what CPU is doing.
    
# Background
We assume user is attending SCA or has basic knowledge of TE attacks
Also pipelining and caching

## CPU
Consists of 3 components
- Frontend:
  - Fetches instrs, decodes to micro, maintains queue
  - queue filled with BPU

- Execution Engine
  - Schedules execution of instr
  - Sets of execution units, grouped by instr. type

- Memory Subsystem
    - memory operations
    - maintains cache
    - loads data from other caches/memory
    
## Out-of-order execution
- Now: 2 optimization techniques
- Instrs. not executed in same order as given
- Ind. Instr-streams executed in parallel
- Basis of OOE: Tomasulo algorithm. 2 important components
  Idea: Free up reservation stations while waiting for operands
  - Reservation stations
    - each set of EU get reservation station. Similar to table
    - new entry for each instruction. Operands either present or not
    - When operands present, an EU executes the instr.
    But: How are other RSs made aware of new result?
  - Common Data Bus (CDB)
    - Connects all EUs and RSs
    - Computed results broadcast on CDB
    - Prevents EUs having to write results to registers every time
  - Modern Intel implementations: Unified RS
- Rollbacks:
  - What if an instr. faults and later ones are already executed?
  Could happen: MUL takes longer than ADD
  - Restore state before faulting instr.
  - Incl. registers, etc.
  - Re-execute instr. that come after faulting instr.
  - Leave no traces, rollbacks should be invisible to programs
  
## Speculative execution
- Problem: Stall on branch predictions because path unknown
- Predict outcome based on previous outcomes. No stall
- Misprediction => Rollback
- To predict: branch prediction unit
  - One way of prediction: saturating counter, incr. if taken, decr. otherwise
- Note other ways of prediction: ret instr, for exmaple
- We focus on prediction of branch instructions

## Meltdown
- Turns out: Rollbacks leave traces (caches)
- Idea: Use faulting instrc. to obtain secret, embed in cache, await rollback, retrieve
- Original: Meltdown-US-L1
  - user/supervisor bit
  - US: no permission for page
  - L1: data to be stolen from L1 cache
  - Steps: oracle array, illegal read, embed secret-dependent oracle entry, wait, retrieve
- Bug: Small time window between illegal read and raising of an exception

## Spectre
- Abuse spec. exec.
- different variations
- here: trick victim into branch misprediction
- attacker deliberately trains BPU used by victim process
- victim leaks secret into cache
- direct consequence of sepc. exec.

## Mitigations: Meltdown
- disable OOE (slow)
- Intel's 'hotfix': microcode update
  - assumed to quietly zero out illegally read values before dependent instrs. get them
- OS mitigations
  - userspace attacker needs address from which to read to be mapped => KPTI
  - But: out of scope, we do not have an OS for our emulator
- Other: Intel should fix it.
  
## Mitigations: Spectre
- More difficult: direct consequence of spec. exec.
- Obviously: Disable spec. exec.
- Better: fence instr. Retire in program order
- For Meltdown/Spec: Flush entire cache after rollback
  - Can be achieved by microprog
  - inefficient
  
## Our task
- What exactly we plan to do
- Given difficulty to experiment with Meltdown/Spectre:
- graphical CPU emulator vulnerable to Meltdown-US-L1, Spectre v1
- Our Meltdown-US-L1
  - No US, so we model US (more later by Melina)
  - By default: Users can steal from any addr, not just data from cached addrs.
  - Can be changed in config. Makes our example programs simpler
  - we believe this does not impact the understanding.
- To achieve this: OOE and spec. exec.
- Single step for better understanding
- Implement Intel's mitigation and other mitigations via microprograms
- Target audience: SCA students / anybody with basic knowledge of TE attacks

# Our approach
Briefly show you how we started working on this task

## How we started
- List of must-haves, nice-to-haves, future work
  - must-haves: OOE, SE
  - nice-to-haves: UI cond. break
  - future work: small OS, HT, context switches with OS
- At time of M/S: Intel used Skylake, or slight variations
- Filter Skylake components; Important for M/S?
- Build simplified CPU.

## Our version:
- If you look at Skylake, we removed quite a few components.
- Kept Frontend/EE/MS structure.
- Frontend: Maintains Instr. Queue, EE has unified RS with infinitely many EUs (more in a bit)
- MS maintains memory and cache.
  - Possible because we only have a single core.
