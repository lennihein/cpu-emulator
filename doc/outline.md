# Catchy Lab title

## Abstract

## Introduction

    general task/ goal
        CPU emulator with actual out of order execution, maybe speculative execution and comprehensible implementation and documentation
    brief context of the task/ goal (e.g. a sentence on Meltdown and why it is important to understand it)
    structure of the report

## Brief Theoretical Background

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
        
    ### Meltdown and Spectre
    
        brief introduction to Meltdown (and Spectre) in general
        
        slightly more in-depth introduction to the Meltdown attack we picked and want to run in our emulator
        
        highlight the relevant parts of the CPU, maybe mention how they interact in Meltdown (and Spectre)
        
        maybe briefly mitigations and how successfull they are
        
        suggested literature: 
            ggf. Dissertation Gruss if we mention basic cbsca
            Gruss et al. papers on Meltdown and Spectre e.g. https://gruss.cc/files/meltdown.pdf or https://gruss.cc/files/meltdown_cacm.pdf
            Canella, Gruss et al. on mititgations https://gruss.cc/files/transient-attacks.pdf

## maybe Specification of the task

    emulator to execute and teach Meltdown
        who is the target audience
        which Meltdown attacks specifically
        etc. further concretisations
        
    are there existing solutions/ related works?
        Felix' old emulator? citable?
        suggested literature:
            todo
            
## Our Emulator Program/ backend

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

    ### CPU Components and our equivalents/ models
            
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
        
    ### Rollbacks/ Exception handling
        
            in particular wrt making Meltdown possible
            
            general goal/ concept of rolling back after a misprediction or an exception
            
            snapshots and interaction of the CPU components

    ### ISA
    
        overview of ISA
        
        maybe µ-instr. vs. ISA
        
        reasoning behind the choice of instructions (manageable size and instructions (e.g. no divide by zero) balanced with functionality particularly wrt Meltdown)

    ### Tomasulo
        
        our version of out-of-order execution
    
        where in our program do we implement which components
        
        what did we leave out/ do differently
        
    ### config files
    
        what can be configured without changing the source code
            why these variables? relevant for Meltdown?

## Our Visualisation and Usage/ Frontend

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

## Demonstration/ evaluation

    what kind of system do we need/ did we use to run this?

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
            
            how effective are these
                in real life
                in our program
            
            what would be the necessary steps/ changes to the program for further mitigations
                compare to changes in hardware by the manufacturers

## Conclusion

    recap goals

    did we reach the goal of implementing a CPU emulator where a user can perform a Meltdown attack
    
    how many Meltdown attacks are possible?
    
    is Spectre possible?
    
    value to students:
        how easy to use and convenient do we think our program is? 
        do we think this will be a good tool for teaching?
        how accessible is it wrt different host architectures?
    
    further work
        more (detailed/ realistic) functionality for more Meltdown and Spectre variants
        more mitigations
        maybe nice to haves wrt to the visualisation/ general UI functionality/ ISA?
