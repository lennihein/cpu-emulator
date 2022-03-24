# User Interface and Usage

This chapter focuses on the usage of the application. The user interface and the design choices are described. An instruction on how to prepare the system and how to run the program is given. Furthermore, the application and it's features are explained in detail. Finally, we showcase the application in action.

## Purpose and Inspiration

In order to demonstrate Meltdown and Spectre attacks, this program is designed to visualise the execution of a modern CPU on a microarchitectural level. We impement a simplified model of a CPU to keep focus on the essential parts to understand the demonstrated attacks. At the same time, the CPU needs to show all information required to follow the attack, and offer convenient features to the user.

It was chosen to follow the rough structure of the GNU Debugger GNU [@GDB] and more specifically the extension Pwndbg [@pwndbg]. The assumption is that many of the target audience are already well familiar with the GNU Debugger and the Pwndbg extension. GDB and Pwndbg can be interacted with via the command line. Different to other similar solutions, GDB can only be interacted with using commands. Most notable is the 'context' screen, which is issued after execution is paused. The context screen prints out the current state of the CPU, including the registers, the stack, a backtrace, and the disassembly.

As with GDB, the emulator can only be interacted with using commands. We further implemented auto-completion and auto-suggestion using the \texttt{python-prompt-toolkit} [@prompt]. This should lower the difficulty of getting started with a new tool. The emulator also implements a Pwndbg-style context-visualisation, albeit with different elements show to adapt to the different goal compared to GDB. This ensures most of the relevant information is on the screen at all times.

## System Requirements and installation

The following things need to be installed to run the program:

- Python
- Python-Benedict
- Python-Prompt-Toolkit

To install the required packages, one may use the following command:\footnote{The requirements file is located in the root directory of the project. In some distributions pip may be called pip3.}

    pip install -r requirements.txt

Optionally, the following things can be installed:

- Git

It is recommended to use the program on a Linux system, although Windows functionality is mostly implemented. Further, it's recommended to have a terminal with a width of at least 120 characters.

The following system was used to test the program:

- Debian GNU/Linux 11 (bullseye) 
- Python 3.9.10
- Python-Prompt-Toolkit 3.0.28
- Python-Benedict 0.25.0
- Git Commit 419678d33a41eefb0bcd775966dae0418ba51245

## Running the program

The syntax for running the emulator from the root folder of the repository is:

    python -m src.shell <path_to_target_program>

If no target program is supplied, the emulator will print system information, along with a help message. The target program may contain instructions as specified in [@sec:ISA](#sec:ISA), seperated by linebreaks. Comments can be added to the target program by preceding them with \texttt{//}. Furthermore, the \texttt{config.yml} file in the root folder can be modified to configure the emulator, see [@sec:config].

## Commands

Following, we describe the commands available in the emulator. The commands are grouped into the following categories: displaying information, modifying the CPU, commands that revolve around pausing and resuming the execution, breakpoint management, as well as some miscellaneous commands.

### Display Information

When displaying specific information, the following command serves as a base:

    show

The following subcommands are available:

#### show mem

Show the memory of the CPU, visualised as words in hexadecimal.

    show mem <start in hex> <words in hex>

The parametres are optional, the emulator defaults to showing memory starting at address \texttt{0x0000} until 8 lines of the terminal are printed. Displaying contents from the memory does neither load the memory into the cache if not already present, nor does it change the order of future eviction from the cache. The subcommand is thus side effect free.

#### show cache

Show the cache. The visualisation is configurable in the \texttt{config.yml} file, see [@sec:config].

    show cache

#### show regs

Show the CPU registers. For each register, either the value of the word is shown in hexadecimal, or, in case the register is waiting for the result of a reservation station, a reference to that reservation station is shown. The nomenclature is configurable in the \texttt{config.yml} file, see [@sec:config]. 

    show regs

#### show queue

Display all instructions currently in the instruction queue.

    show queue

#### show rs

Displays the reservation stations. Whether or not empty slots are shown is configurable in the \texttt{config.yml} file, see [@sec:config]. The information supplied include the index of the instruction in the source code, the instruction itself, as well as current values for the source operands, either as a word in hexadecimal, or as a reference to another reservation station. This allows the user to quickly determine, which reservation stations are currently waiting for the result of other reservation stations, and are stalled as a result. Furthermore, retiring instructions are marked with a ticked checkbow. 

    show rs

#### show prog

Displays a visualisation of the source program. Further, there are icons indicating which instructions are currently in-flight, as well as which instruction is marked as a breakpoint. 

    show prog

![Icon legend for show prog command](fig/ui_01.png){width=137px height=78px}\

#### show bpu

Displays the value of the 2bit counter for every index in the BPU.

    show bpu

### Modifying the CPU

When modifying the CPU, the following command serves as a base:

    edit

The following subcommands are available:

#### edit word

Takes an address and value in hexadecimal, and overwrites the word at that address with the new value.

    edit word <address in hex> <value in hex>

Editing the memory through this command does not affect which lines are stored in the cache. It does update the contents of the cache, however, if the address is in the cache, to keep the state of the cache and memory consistent. The user should be aware that the memory is addressed bytewise, but the subcommand is writing a word in little-endian order. 

#### edit byte

Takes and address and a value in hexadecimal, and overwrites the byte at that address with the new value.

    edit byte <address in hex> <value in hex>

This command is analoguous to the \texttt{edit word} command, but operates on a byte instead of a word.

#### edit flush 

Allows to flush the cache, selectively or fully.

    edit flush <address in hex>

If no address is supplied, the entire cache is flushed. If an address is supplied, the cacheline containing that address is flushed, if present in the cache.

#### edit reg

Changes the value of a register.

    edit reg <register (0-31)> <value in hex>

Any of the 32 registers (\texttt{0-31}) can be modified.

#### edit bpu

Overwrites the 2bit counter for a specific index in the BPU.

    edit bpu <pc in dec> <value (0-3)>

The values correspond to the following:

- \texttt{0}: Strongly not taken
- \texttt{1}: Weakly not taken
- \texttt{2}: Weakly taken
- \texttt{3}: Strongly taken

See further in chapter \ref{sec:bpu} for more information.

### Pause and Resume Execution

Since the emulator is thought to be used similar to a debugger, to provide a more convenient way to pause and resume execution, the following commands are available:

#### continue

Continues execution of the program.

    continue

The execution will be resumed until the next breakpoint is reached, a fault is encountered, or the program terminates.

#### step

Allows to step through the program one cycle at a time.

    step <steps>

If steps is not supplied, the emulator will execute a single cycle. If steps is supplied, the emulator will execute the specified number of cycles. The execution is also paused when encountering a breakpoint, a fault, or the program terminates.

If a negative number is supplied, the emulator will execute the specified number of cycles in reverse order. This allows the user to conveniently review the events that occur during the execution without having to restart the program. Furthermore, this can be combined with other commands such as \texttt{continue}, to see the status during the last cycle before a notable event such as a fault caused the execution to be paused.

#### retire 

Continues execution of the program until the next instruction is retired.

    retire

As with \texttt{step} and \texttt{continue}, the execution is also paused when encountering a breakpoint, a fault, or the program terminates.

#### Restart

Resets the program to the state it was in after launching the emulator.

    restart

### Breakpoint Management

The emulator allows to set, clear, toggle and list breakpoints. The base command is:

    break

#### break add

Sets a breakpoint.

    break add <address in hex>

#### break delete

Deletes a breakpoint.

    break delete <address in hex>

#### break toggle

Disables an active breakpoints, and likewise enables a disabled breakpoint.

    break toggle <address in hex>

#### break list

Outputs a list of all breakpoints, and whether they are enabled or disabled.

    break list

Note that the breakpoints also can be seen when calling \texttt{show prog}. See [@sec:showprog] for more information.

### Miscellaneous Commands

Further, the following commands are available:


#### quit

Quits the program.

    quit

Also can be called using:

    q

#### help

Displays help.
    
        help

#### clear

Clears the screen

    clear