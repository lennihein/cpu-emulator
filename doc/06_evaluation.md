# Demonstration and Evaluation {#sec:evaluation}
\marginpar{Melina Hoffmann}

As specified in [chapter @sec:task], our goal is to implement a CPU emulator that offers out-of-order and speculative exection in order to demonstrate a Meltdown and a Spectre attack.
In this chapter we demonstrate that our emulator allows the user to execute both a Meltdown and a Spectre attack, with the use of basic example programs. 
Firstly, we introduce the general functionality and visualization of our emulator on a simple example program that does not yet implement microarchitectural attacks in [@sec:evaluation_example].
Then, we demonstrate both the Meltdown and the Spectre variant which are possible on our emulator in [@sec:evaluation_meltdown] and [@sec:evaluation_spectre] respectively.
Lastly, we show different mitigations against these microarchitectural attacks on our emulator, which are based on mitigations gainst real life microarchitectural attacks in [@sec:evaluation_mitigations].´

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
To this end, we `step` and `continue` through an example program and introduce the central components of our vizualisation. 
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

When we start the emulator it automatically loads the program and shows first context screen, with the registers and default memory section initialised to zero and the instruction queue and reservation station still empty.. 
<!-- pic ep_01_start.pngSS-->


Within the first two `steps` the instruction queue is filled with the first five instructions, which are subsequently issued into the reservation station as per Tomasulos algorithm for out-of-order execution [@sec:Tomasulo].
Instruction 0 is immediatly executed, since it is in the first slot of the reservation station and all operands ready as soon as it is issued.
By the checkmark in the rightmost column in the reservation station, we can see that it is ready to retire.
Since its result is broadcasted directly after the instruction finishes executing, register 1 and the first operand of intruction 1 are already set to 0x003.

As per Tomasulos algorithm, we see `SlotIDs` both in the registers and the operand lists of instructions in the reservation station as placeholders for the result of the instruction in the respective reservation station slot. For example, register 2 is waiting for the result produced by the `addi` instruction in slot 2 of the reservation station and contains the placeholder `RS 002`.
Note in particular, that for the `slli` instruction with `SlotID` 1 we see that its target register 2 already contains the `SlotID` of the next instruction. 
But in the operand list of the `addi`in slot 2 the reservation station we can see the `SlotID` of the `slli` instruction waiting to be replaced with the result value.
<!-- pic -ep_02_two_steps.png-->

In the next step, the fence instruction is issued into the reservation station.
Therefore no more instructions are issued into to the reservation station until all currently issued instructions have been executed.
<!--picture options ep_03_fence_full.png, ep_04_fence_rs.png -->

After the `slli` and the `addi` instructions in slots 1 and 2 of the reservation station, the program contains two memory operations `sw` and `lb`.
Since these are executed with latency/ take long to execute, the `addi`instruction in slot 5 of the reservation station is executed out-of-order before the memory instructions retire.
<!--Formulierung -->
<!-- pic options ep_05_addi_ooe_full.png, ep_06_addi_ooe_rs.png-->

During the execution of the `sw` instruction, the value 0x0342 is stored as a `Word`starting at memory address 4. 
In our example this is highlighted further by the the memory addresses 4-7 changing color to red.
This signifies that they are placed in the cache as a `cacheline`of length of four bytes.
Since we cannot visualze the whole memory all at once, we also offer a more detailed  visualization of the whole cache.
The result of the store instruction is placed into memory multiple cycles before the instruction retires, both to model real world latencies in memory accesses and to leave enough time when checking for faults to allow transient execution, as we see in [@sec:evaluation_meltdown].
<!--pic ep_05_addi_ooe_full.png, ep_07_cache.png -->

The `lb` instruction in slot 4 only reads one byte from memory address 5.
Since the `sw`instruction places its `Word` value into memory in little endian order, the result of reading one byte from memory address 5 is 0x03.
<!-- pc ep_08_legal_load_result.png-->

With the `lb` instruction int slot 6 of the reservation station, we attempt to load a value from the inaccessible part of the memoy [@sec:memory].
During the execution, the value from the inaccessible address is present in the target reister 3.
But before instruction can retire, the fault is detected and the target register is rolled back to its previous state.
Due to the rollback the reservation station is cleared and the subsequent instructions are put back into the instruction queue [@sec:rollback].
<!--ideally two pictures_ with 0x42 in register ep_08_legal_load_result.png and reset with fault message ep_09_mem_fault.png, ideally side by side -->

Now the `fence`instruction can be executed and the subsequent instructions are put into the instruction queue and issued to the reservation station.
Since per the default settings all jumps are first predicted as taken, we speculatively fill the instruction queue and reservation station with multiple/ infinite iterations of the loop.
<!--Formulierung -->
Since the branch condition is already violated in the first interation of the loop and the branch is not taken, we have a misprediction that results in a fault message and a rollback during which the reservation station is cleared and the `rtdsc`instruction is put into the instruction queue.
<!--pictures of iq and rs filled with multiple loop contents somewhere in the middle ep_10_loop_full.png, ep_11_loop_bottom.png, and of the fault message and  rolled back loop ep_12_loop_fault_full.png ep_13_loop_fault_bottom.png-->

Lastly the `rdtsc` instruction is executed and shows in register 0 that the program took 0x0026 cycles to execute so far. 
The end of the program is marked by the end message as well as the empty instruction queue and reservation station.
<!--pic ep_14_end.png -->


## Meltdown Demonstration {#sec:evaluation_meltdown}

todo

            show example program

            maybe compare to example program for real life architecture from SCA or literature (Gruss) if available

            explain which Meltdown variant it implements

            briefly highlight which components (we expect to) interact to make it work

            how well does it work?

## Spectre Demonstration {#sec:evaluation_spectre}

todo

            same as Meltdown

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
