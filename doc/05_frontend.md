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