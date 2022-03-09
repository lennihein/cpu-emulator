# Catchy Lab title

## Abstract

## Introduction (1 page)

    general task/ goal
        CPU emulator with actual out of order execution, maybe speculative execution and comprehensible implementation and documentation
        implement different µ-architectural features like out-of-order exe., speculative exe. b.c. we want to observe and teach µ-arch. attacks
    brief context of the task/ goal (e.g. a sentence on Meltdown and why it is important to understand it)
    structure of the report

## Brief Theoretical Background (2-3 pages)

    premise according to Felix: reader knows SCA lecture -> brief recaps/ reminders to reference back to from the other chapters
    
    ### really brief introduction to CPU
    
        multiple components
            maybe mostly via picture
        
        how they work together
        
        maybe data-flow from instruction to result
        
        a lot of hypothticals due to trade secrets
        
        suggested literature:
            maybe Gruss Diss. and other works on cbsca
            maybe textbooks
            maybe CPU wiki for pictures

    ### out-of-order execution
    
        a bit more in depth b.c. this is not content of the sca lecture
    
        maybe why do we need it/ advantages
            
        brief explanation of Tomasulo and how it works
        
        suggested literature:
            original Tomasulo paper from 1965
            maybe a more recent/ didactically edited explanation (is this in texbooks?)
        
        also something about speculative execution
        
    ### Meltdown and Spectre
    
        brief introduction to Meltdown (and Spectre) in general
        
        slightly more in-depth introduction to the Meltdown attack we picked and want to run in our emulator
        
        highlight the relevant parts of the CPU, maybe mention how they interact in Meltdown (and Spectre)
        
        mitigations and maybe how successfull they are
        
        suggested literature: 
            ggf. Dissertation Gruss if we mention basic cbsca
            Gruss et al. papers on Meltdown and Spectre e.g. https://gruss.cc/files/meltdown.pdf or https://gruss.cc/files/meltdown_cacm.pdf
            Canella, Gruss et al. on mititgations https://gruss.cc/files/transient-attacks.pdf

## maybe Specification of the task (1 page)

    emulator to execute and teach Meltdown
        who is the target audience
        which Meltdown attacks specifically
        etc. further concretisations
        
    are there existing solutions/ related works?
        Felix' old emulator? citable?
        suggested literature:
            todo
            
## Our Emulator Program/ backend (17-18 pages)

    maybe general info e.g. that we wrote it in python, if we used special tools/ libraries
    for everything we implemented:
            which part of a real life cpu does this model/ how is this done in real life cpus
            briefly how does it work
            why did we choose to model it like we do
                nice code structure/ code easy to understand by students
                some features more or less relevant for meltdown
                etc.
            maybe what did we leave out
            challenges?

    ### CPU Components and our equivalents/ models (10-11 pages)
            
        modular setup based on real life CPUs and nice coding conventions
            
        #### CPU
        
            contains/ controls the rest
            
            preparation (loading the program, init the rest)
            
            ticks
            
            coordinate rollbacks?
            
        #### program handling
        
            instructions
            
            parser
            
        #### data handling
        
            how we model and handle data
            
            byte, word
            
        #### scheduling
        
            BPU
            
            frontend
        
        #### memory
        
            mmu
            
                how do we store data
                
                how do we model data access (i.p. wrt Meltdown)
        
            cache
            
                what kinds of caches can we represent
                
                how do we model if something is cached and the access times (i.p. wrt Meltdown)
            
        #### execution
        
            Reservation Station/ Slots
            
            unlimited execution units
    
    ### Tomasulo (2 pages)
        
        our version of out-of-order execution
    
        where in our program do we implement which components
        
        what did we leave out/ do differently
        
    ### Rollbacks/ Exception handling (2-3 pages)
        
            in particular wrt making Meltdown possible
            
            general goal/ concept of rolling back after a misprediction or an exception
            
            snapshots and interaction of the CPU components

    ### ISA (2 pages)
    
        overview of ISA
        
        µ-instr. vs. ISA
            mixture of both in one: only µ-code, but more abstract than in real life
            do not need to think about page faults etc. anyways, do not need overly complex instructions
        
        reasoning behind the choice of instructions (manageable size and instructions (e.g. no divide by zero) balanced with functionality particularly wrt Meltdown)

        
    ### config files (1 page)
    
        what can be configured without changing the source code
            why these variables? relevant for Meltdown?

## Our Visualisation and Usage/ Frontend (10 pages)

    ggf. gemäß Anmerkung von Lenni umsortieren: die idee das UI nicht mit in die 'unsere designetnscheidungen' zu nehmen, sondern im prinzip so als Manual abzukapseln finde ich eigentlich ganz gut. Müssen wir aber dann mal in der Praxis schauen. Soll ja keine didaktischen begründungen das manual zu sehr aufblähen, vllt wird das sinnvoll, dann einen teil des UI im "backend" kapitel einzubauen, und dann wirklich ein cleanes manual kapitel zu haben

    ### general concept
    
        goal: UI for the emulator with visualisation of CPU/ memory components and their contents
        
        in terminal
            maybe comparison to existing analysis tool/ debugger gdb
        
        triggers/ controls the actual emulator
            overview features, e.g. breakpoints, step-by-step and stepback
    
        maybe which tools/ libraries were used?
        
    ### features in more detail and their didactic purpose
    
        breakpoints, step-by-step, stepback and more
        
        challenges/ design choices during the implementation

## Demonstration/ evaluation (7 pages)

    what kind of system do we need/ did we use to run this?
        which python Version?

    ## general demonstration
    
        brief example program showing all the features in a "normal" execution, e.g. adding stuff

    ### Meltdown und Spectre demonstration

        #### Example Program Meltdown
        
            show example program
        
            maybe compare to example program for real life architecture from SCA or literature (Gruss) if available
            
            explain which Meltdown variant it implements
            
            briefly highlight which components (we expect to) interact to make it work
            
            how well does it work?
        
        #### maybe example program spectre
        
            same as Meltdown
        
        #### mitigations
        
            what is possible in our program as is
                planned:    cache flush: microcode -> config file
                            mfence im assembler (normally in compiler)
                            aslr directly in program -> config
                            flush IQ -> 
                            disable speculation und out of order (nice to have)-> config
            
            how effective are these
                in real life
                in our program
            
            what would be the necessary steps/ changes to the program for further mitigations
                compare to changes in hardware by the manufacturers

## Conclusion (1 Page)

    recap goals

    did we reach the goal of implementing a CPU emulator where a user can perform a Meltdown attack
    
    how many Meltdown attacks are possible?
    
    is Spectre possible?
    
    mitigations
        which mitigations did we implement
        is this a good amount/ sample of real world mitigations or do we miss important ones?
        how well do they perform (also in comparison to how they perform in the real world)
        
    value to students:
        how easy to use and convenient do we think our program is? 
        do we think this will be a good tool for teaching?
        how accessible is it wrt different host architectures?
    
    further work
        more (detailed/ realistic) functionality for more Meltdown and Spectre variants
        more mitigations
        maybe nice to haves wrt to the visualisation/ general UI functionality/ ISA?
