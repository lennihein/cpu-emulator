# Demonstration and Evaluation {#sec:evaluation}
\marginpar{Melina Hoffmann}

As specified in [chapter @sec:task], our goal is to implement a CPU emulator that offers out-of-order and speculative exection in order to demonstrate a Meltdown and a Spectre attack.
In this chapter we demonstrate that our emulator allows the user to execute both a Meltdown and a Spectre attack, with the use of basic example programs. 
Firstly, we introduce the general functionality and visualization of our emulator on a simple example program that does not yet implement microarchitectural attacks in [@sec:evaluation_example].
Then, we demonstrate both the Meltdown and the Spectre variant which are possible on our emulator in [@sec:evaluation_meltdown] and [@sec:evaluation_spectre] respectively.
Lastly, we show different mitigations against these microarchitectural attacks on our emulator, which are based on mitigations gainst real life microarchitectural attacks in [@sec:evaluation_mitigations].

## Example Program {#sec:evaluation_example}
\marginpar{Melina Hoffmann}

<!--
brief example program showing all the features in a "normal" execution, e.g. adding stuff
at least one instruction from each category
at least one faulting (memory) instruction
faulting branch
main goals: 
    shown what the vizualization looks like
        default view
        different components
        especially cache
        instructions in RS waiting for operands
        memory instructions execution vs. retiring
    show that the emulator works in general
why are the files called .tea again? transient emulator assembly?

einfach mal Programm aufschreiben und morgen ausführen und schauen, ob es so passt
    sieht man irgendwas nicht? wäre eine andere Reihenfolge schöner?
    
Bilder erstmal reinwerfen wie sie kommen, evtl. am Donnerstag oder heute Abend wenn noch Zeit ist Bilder klein nebeneinander stellen oder so

Demoprogramm ausführen und schauen ob es sich verhält wie erwartet
ggf. Demoprogramm anpassen
Plan machen, was genau man an jeder Stelle des Programms gezeigt bekommen soll
anschauen, was für ein Bild lenni für das UI gemacht hat und wie er es eingefügt hat
gleichzeitig Demoprogramm Schritt für Schritt ausführen und Text schreiben 
    ggf. mit Windowssnippigtool Bilder machen und später einfügen
auch nur das beschreiben und bebildern
nicht in Details verlieren!

go through everything I want to show of the code with pictures
    maybe later look up how I can make the pictures small and group them
    also: show commands as part of pictures: not main focus, but maybe mention with which commands the output was generated, if it fits
    
breakpoint weg lassen, kennen die ja aus gdb oder UI Kapitel


![Example output of the context screen](fig/context.png){#fig:context width=470px height=317px shortcaption='Example output of the context screen'}
.png Bilder in den Ordner fig/ legen
-->

In this section, we introduce different components of the vizualisation of our emulator and showcase our emulators out-of-order and speculative execution.
To this end, we `step` through an example program and introduce the central components of our vizualisation. 
Introducing all the commands and vizualisations our emulator implements with an example program would be out of scope of this section, but a complete list of commands is given in [chapter @sec:UI].

This is our example program.
<!--
It consists of some basic arithmetic operations that prepare addresses and content for the following memory accesses.
Then we introduce and show the effects of the fence and the flush operation.
Lastly the program includes a small loop to show the effects of our speculative execution.
-->
To produce the examples for this section, the program is run on the default config settings as discussed in [@sec:config].

    addi r1, r0, 3
    slli r2, r1, 8
    addi r2, r2, 66
    sw r2, r0, 4
    lb r4, r0, 5
    addi r3, r0, 33768
    lb r3, r3, 1
    fence
    loop_label:
        subi r4, r4, 1
        beq r4, r0, loop_label
    rdtsc r0

When we start the emulator, it automatically loads the program and shows the first context screen, as described in [@sec:context_screen].
As we see in [@fig:ep_01_start], the registers and default memory section are initialised to zero and the instruction queue and reservation station are still empty.
<!-- pic ep_01_start.png-->

![Context screen at the start of the program](fig/ep_01_start.png){#fig:ep_01_start width=470px height=317px shortcaption='Context screen at the start of the program'}


As we can see in [@fig:ep_02_two_steps], within the first two `steps` the instruction queue is filled with the first five instructions, which are subsequently issued into the reservation station as per Tomasulos algorithm for out-of-order execution [@sec:Tomasulo].
Instruction 0 is immediatly executed, since it is in the first slot of the reservation station and all are operands ready as soon as it is issued.
By the checkmark in the rightmost column in the reservation station, we can see that it is ready to retire.
Since its result is broadcasted directly after the instruction finishes executing, register 1 and the first operand of intruction 1 are already set to 0x003.

As per Tomasulos algorithm, in [@fig:ep_02_two_steps] we see `SlotIDs` as placeholders for the result of the instruction in the respective reservation station slot, both in the registers and the operand lists of instructions in the reservation station. 
For example, register 2 is waiting for the result produced by the `addi` instruction in slot 2 of the reservation station and contains the placeholder `RS 002`.
Note in particular, that for the `slli` instruction with `SlotID` 1 we see that its target register 2 already contains the `SlotID` of the next instruction. 
But in the operand list of the `addi` in slot 2 the reservation station we can see the `SlotID` of the `slli` instruction waiting to be replaced with the result value.
<!-- pic -ep_02_two_steps.png-->

![Context screen after two `steps`](fig/ep_02_two_steps.png){#fig:ep_02_two_steps width=470px height=317px shortcaption='Context screen after two `steps`'}

In the next step, the fence instruction is issued into the reservation station.
Therefore no more instructions are issued into the reservation station until all currently issued instructions have been executed.
This can be observed in [@fig:ep_05_addi_ooe_full] and [@fig:ep_08_legal_load_result], in which the empty slots in the reservation station are not refilled with the instructions waiting in the instruction queue.
<!--picture options ep_03_fence_full.png, ep_04_fence_rs.png -->

<!-- ![Program, instruction queue and reservation station visualization after the `fence` instruction is issued](fig/ep_04_fence_rs.png){#fig:ep_04_fence_rs width=470px height=317px shortcaption='Program, instruction queue and reservation station visualization after the `fence` instruction is issued'} -->

After the `slli` and the `addi` instructions in slots 1 and 2 of the reservation station, the program contains two memory operations `sw` and `lb`.
Since memory instructions take longer to execute, the `addi` instruction in slot 5 of the reservation station is executed out-of-order before the memory instructions retire.
[@fig:ep_05_addi_ooe_full] shows the reservation station that still contains the `sw` and `lb` instructions but from which the `addi` instruction has already retired.
<!--Formulierung -->
<!-- pic options ep_05_addi_ooe_full.png, ep_06_addi_ooe_rs.png-->

![Context screen after out-of-order execution of `addi` instruction](fig/ep_05_addi_ooe_full.png){#fig:ep_05_addi_ooe_full width=470px height=317px shortcaption='Context screen after out-of-order execution of `addi` instruction'}

During the execution of the `sw` instruction, the value 0x0342 is stored as a `Word` starting at memory address 4. 
In our example this is highlighted further by the the memory addresses 4-7 changing their color to red.
This signifies that they are placed in the cache as a `cacheline` of length four bytes.
Since we cannot visualize the whole memory all at once, we also offer a more detailed  visualization of the whole cache, as depicted in [@fig:ep_07_cache].
The result of the store instruction is placed into memory multiple cycles before the instruction retires, both to model real world latencies in memory accesses and to leave enough time to check for faults during which transient execution happens, as we see in [@sec:evaluation_meltdown].
Therefore, we can already observe the aforementioned changes in the memory visualization in [@fig:ep_05_addi_ooe_full], while the `sw` instruction is still being executed and present in the reservation station.
<!--pic ep_05_addi_ooe_full.png, ep_07_cache.png -->

<!--
![Cache effect of the `sw` instruction](fig/ep_07_cache.png){#fig:ep_07_cache width=470px height=317px shortcaption='Cache effect of the `sw` instruction'}
-->

![Cached target address of the `sw` instruction](fig/ep_07_cache.png){#fig:ep_07_cache shortcaption='Cached target address of the `sw` instruction'}

The `lb` instruction in slot 4 only reads one byte from memory address 5.
Since the `sw` instruction places its `Word` value into memory in little endian order, the result of reading one byte from memory address 5 is 0x03.
This can be observed as the new value of register 4 in [@fig:ep_08_legal_load_result], where the `lb` instruction has finished executing and is ready to retire, as shown by the tickmark.
<!-- pc ep_08_legal_load_result.png-->

![Context screen the `lb` instruction in slot 4 ready to retire](fig/ep_08_legal_load_result.png){#fig:ep_08_legal_load_result width=470px height=317px shortcaption='Context screen the `lb` instruction in slot 4 ready to retire'}

With the `lb` instruction in slot 6 of the reservation station, we attempt to load a value from the inaccessible part of the memoy, as described in [@sec:memory].
During the execution, the value 0x42 from the inaccessible address is present in the target register 3, as we can observe in [@fig:ep_08_legal_load_result].
But before the instruction can retire, the fault is detected and the target register is rolled back to its previous state.
Due to the rollback the reservation station is cleared and the subsequent instructions are put back into the instruction queue [@sec:rollback].
In [@fig:ep_09_mem_fault] we can see the previous value of 0x83e8 from the address calculation in register 3, and the rolled back instruction queue and reservation station as well as the fault message.
<!--ideally two pictures_ with 0x42 in register ep_08_legal_load_result.png and reset with fault message ep_09_mem_fault.png, ideally side by side -->

![Rolled back memory fault](fig/ep_09_mem_fault.png){#fig:ep_09_mem_fault width=470px height=317px shortcaption='Rolled back memory fault'}

Now the `fence` instruction can be executed and the subsequent instructions are put into the instruction queue and issued to the reservation station.
Since per the default settings all jumps are first predicted as taken, we speculatively fill the instruction queue and reservation station with as many iterations of the loop as fit into them, as seen in [@fig:ep_10_loop_full].
Since the branch condition is already violated in the first interation of the loop and the branch is not taken, we have a misprediction that results in a fault message and a rollback. 
During the rollback the reservation station is cleared of the excess instructions from the loop interations that are not executed after all. 
Instead the `rtdsc` instruction, which follows the loop in the program, is put into the instruction queue, as we can see in [@fig:ep_12_loop_fault_full].
<!--pictures of iq and rs filled with multiple loop contents somewhere in the middle ep_10_loop_full.png, ep_11_loop_bottom.png, and of the fault message and  rolled back loop ep_12_loop_fault_full.png ep_13_loop_fault_bottom.png-->

![Loop instructions are speculatively put into the instruction queue and issued into the reservation station](fig/ep_10_loop_full.png){#fig:ep_10_loop_full width=470px height=317px shortcaption='Loop instructions are speculatively put into the instruction queue and issued into the reservation station'}

![Rolled back loop fault](fig/ep_12_loop_fault_full.png){#fig:ep_12_loop_fault_full width=470px height=317px shortcaption='Rolled back loop fault'}

Lastly the `rdtsc` instruction is executed and shows in register 0 that the program took 0x0026 cycles to execute so far. 
The end of the program is marked by the end message as well as the empty instruction queue and reservation station, as we can see in [@fig:ep_14_end].
<!--pic ep_14_end.png -->

![Context screen at the end of the execution of the example program](fig/ep_14_end.png){#fig:ep_14_end width=470px height=317px shortcaption='Context screen at the end of the execution of the example program'}


## Demonstration of a Meltdown-Type Attack {#sec:evaluation_meltdown}

- demonstrate that a meltdown-type attack can be performed inside our emulator
- this is shown through an example program that performs such an attack
- afterwards the attack is categorized according to the naming scheme established by transient-fail
- and compared to the attack described in the original meltdown paper

### A Meltdown-Type Attack

- high-level explanation
  - Load byte from inaccessible memory. That triggers a fault
  - During the following transient execution, use loaded value to index into a "probe array"
  - That causes this entry of the probe array to be cached, encodes the value in the cache
  - After the transient execution, check which entry of the probe array is cached
    - By loading each entry and measuring the access time
  - That way we leak the value that is supposed to be inaccessible

- code: meltdown part
    lb r1, r0, 0xc000
    slli r1, r1, 4
    lb r2, r1, 0x1000
- explanation meltdown part
  - Load byte from the inaccessible address 0xc000
  - Shift by 4, multiplying the value by 0x10, because the entries of our probe array are 0x10 bytes apart
  - Use resulting value to index into the probe array starting at address 0x1000
- when we step through the program, we see that the faulting load indeed provides the secret value 0x42 to the following instructions (screenshot)
- after the transient execution is ended by the rollback, we can investigate the state of the cache to see that entry 0x42 of the probe array is cached (screenshot)

- code: cache decoding
    // Loop over the probe array, record the shortest access time:

    // Index of shortest access, in bytes
    addi r1, r0, 0
    // Time of shortest access
    addi r2, r0, -1
    // Current index, in bytes
    addi r3, r0, 0
    // Probe array length, in bytes
    addi r4, r0, 0x1000
    probe:

    // Perform timed access into probe array
    fence
    rdtsc r5
    lb r7, r3, 0x1000
    fence
    rdtsc r6
    sub r5, r6, r5

    // Update shortest access
    bgeu r5, r2, skip
    addi r1, r3, 0
    addi r2, r5, 0
    skip:

    // Increment index and loop
    addi r3, r3, 0x10
    bne r3, r4, probe
- explanation cache decoding
  - Loops over the probe array and records the shortest access time
  - During the loop, register r1 stores the index of the shortest seen access, and register r2 stores its access time. Register r3 stores the current index into the probe array, and register r4 stores the length of the probe array. To simplify the code, the indices and lengths are stored in units of bytes and not in units of probe array entries.
  - These registers are initialized in the block starting in line X
  - The loop body starting in line X performs an access into the probe array, and records the access time
  - This is done by surrounding the `lb` instruction that performs the access with `fence; rdtsc` sequences that record the cycle counter before and after the access
  - The fence in front of the lb ensures that the recorded cycle count closely matches the time the lb is issued, by waiting for preceding instructions occupying the reservation station to complete
  - The fence following the lb ensures that the load completes before the cycle count is recorded
  - The second part of the loop body, starting at line X, updates the shortest access index and time in the case that the load was the shortest yet
  - The loop tail starts at line X and increments the index into the probe array. It checks if the end of the probe array was reached, looping back up to line X if that is not the case.
- when executing the whole program, we can see that index 0x42 had the shortest access time; the secret was transmitted from the transient execution successfully

- which components interact to make it work
  - out of order execution that leads to a transient execution window after the faulting load
  - memory subsystem that provides the value stored in memory as the result of the load, even when it faults
  - cache that is used as a transmission channel from the transient execution domain to the architectural domain

### Comparison With Meltdown-Type Attacks on Real CPUs

- explain which Meltdown variant it implements: Meltdown-US-L1 and Meltdown-US-Mem
  - according to transient-fail naming scheme
    - first component describes how the leaking fault is triggered
    - second component describes where the leaked data comes from
  - our scheme for checking memory accesses models the way the user/supervisor-bit is usually set up in x86 operating systems, in that the top half of memory is reserved for the kernel and accesses to it cause a fault
  - if the value accessed by the meltdown snippet already resides in the cache, the value is leaked from the cache. this results in meltdown-us-l1. if the value is not cached, it is leaked from main memory. this results in meltdown-us-mem

- compare to example program from meltdown paper
  - code: the small meltdown snippet
        ; rcx = kernel address, rbx = probe array
        xor rax, rax
        retry:
        mov al, byte [rcx]
        shl rax, 0xc
        jz retry
        mov rbx, qword [rbx + rax]
  - explain how it works
    - loads a byte from a kernel address
    - shifts the value by 12, multiplying it by 0x1000
    - retries the load until it produces a non-zero value
    - uses the value to index into the probe array
  - point out differences
    - very similar to our code snippet
    - beside the differing size of the probe array entries, the only difference is the retry loop
    - on real x86 CPUs the faulting load only leaks data sporadically
    - our emulator is completely deterministic -> attack works every time

## Demonstration of a Spectre-Type Attack {#sec:evaluation_spectre}

- intro
  - very similar
  - demonstrate the mechanism behind spectre-type attacks
- example attack
  - not really an attack, since we only have a single privilege mode and cannot attack anyone
  - spectre part
  - cache decoding: same as meltdown
- involved components
  - branch prediction
  - cache as transmission channel
- comparison with real attacks
  - classification with transient-fail: Spectre-PHT-SA-IP
    - first component is the component that is trained to perform a misprediction
      - our BPU only has a single prediction mechanism, that matched the PHT from modern x86 CPUs
    - second and third component is if the training is performed in the same address space or a different one, and if the training uses a branch at the same or a branch at a different address
      - we only have a single address space
      - and in this case we perform the training in-place
      - out-of-place would also be possible, since our BPU uses a limited number of address bits to index its internal counter table
- comparison with spectre paper
  - original spectre paper describes a very similar attack, where an array is repeatedly indexed in-bounds to train the branch predictor, and then a single time out-of-bounds to force a misprediction and access a secret value during the following transient execution

## Mitigations Demonstration {#sec:evaluation_mitigations}

todo

            it is known which mitigations exist, here is what we have in our emulator:

            what is possible in our program as is
                planned:    cache flush: microcode -> config file
                            mfence im assembler (normally in compiler)
                            aslr directly in program -> config (es gibt ja auch mitigations, die keine echte mitigation sind; nice to have -> könnte demonstrieren dass es nicht der Fall ist; war eh schon einige Jahre vor Meltdown vorhanden/ in Gebrauch; KSLR brachen kann man auch als Angriff verkaufen)
                            flush IQ -> passiert eh schon, ist das überhaupt eine echte mitigation?
                            disable speculation (nice to have, lassen wir weg)-> config
                            out of order -> in config RS mit nur einem Slot
                            zero mem load result

            is our meltdown/ spectre variant still possible?
            ggf. how does this affect the performance?
            vorsichtig sein, dass man dann auch die richtige Frage für die Antwort stellt
                in real life (already in background)
                in our program

            what would be the necessary steps/ changes to the program for further mitigations
                compare to changes in hardware by the manufacturers
