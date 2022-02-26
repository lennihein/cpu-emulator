from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from logging import raiseExceptions
from os import system
from math import ceil

from src.instructions import InstrReg
from src.word import Word
from src import ui
from src.cpu import CPU

session = PromptSession()


funcs = {}
completions = {}


def func(f):
    if len(f.__name__[2:]) > 0:
        completions[f.__name__[2:]] = None
        if f.__doc__ is not None:
            completions[f.__name__[2:]] = eval(f.__doc__.strip())
    funcs[f.__name__] = f


@func
def __show(input: list[str], cpu: CPU):
    '''
    {"mem": None, "cache": None, "regs": None, "queue": None, "rs": None, "prog": None, "bpu": None}
    '''
    if len(input) < 1:
        __not_found(input, cpu)
        return
    subcmd = input[0]
    if subcmd == 'mem':
        if len(input) == 2:
            # check if the input is an int
            try:
                start = int(input[1], base=16)
                start = max(start, 0)
                ui.print_memory(cpu.get_mmu(), base=start)
            except ValueError:
                print("Usage: show mem <start in hex> <words in hex>")
                return
        elif len(input) == 3:
            # check if both inputs are ints
            try:
                start = int(input[1], base=16)
                start = max(start, 0)
                words = int(input[2], base=16)
                fits_per_line = (ui.columns - 8) // 7
                lines = ceil(words / fits_per_line)
                ui.print_memory(cpu.get_mmu(), base=start, lines=lines)
            except ValueError:
                print("Usage: show mem <start in hex> <words in hex>")
                return
        else:
            ui.print_memory(cpu.get_mmu())
    elif subcmd == 'cache':
        ui.print_cache(cpu.get_mmu())
    elif subcmd == 'regs':
        ui.print_regs(cpu.get_exec_engine())
    elif subcmd == 'queue':
        ui.print_queue(cpu.get_frontend())
    elif subcmd == 'rs':
        ui.print_rs(cpu.get_frontend())
    elif subcmd == 'prog':
        ui.print_prog(cpu.get_frontend())
    elif subcmd == 'bpu':
        ui.print_bpu(cpu.get_bpu())
    else:
        __not_found(input, cpu)


@func
def __continue(input: list[str], cpu: CPU):
    raiseExceptions(NotImplementedError)


@func
def __step(input: list[str], cpu: CPU):
    raiseExceptions(NotImplementedError)


@func
def __break(input: list[str], cpu: CPU):
    '''
    {"add": None, "delete": None, "delete": None, "toogle": None, "list": None}
    '''
    raiseExceptions(NotImplementedError)


@func
def __clear(input: list[str], cpu: CPU):
    system('clear')
    return


@func
def __quit(input: list[str], cpu: CPU):
    exit()


# 'q' is a substitute for 'quit'
funcs['__q'] = funcs['__quit']


@func
def __(input: list[str], cpu: CPU):
    ui.all_headers(cpu)


def __not_found(input: list[str], cpu: CPU):
    print('Your input did not match any known command')


completer = NestedCompleter.from_nested_dict(completions)

cpu = CPU()

code = """
    // Set r1 to 1
    addi r1, r0, 1
    // Set r2 to 2
    add r2, r1, r1
    // Set r3 to 3
    addi r3, r2, 1
    // Set r4 to 4
    mul r4, r2, r2
    // Set r5 to 5
    add r5, r2, r3
    // Store 4 to address 0
    sw r4, r0, 0
    // Store 5 to address 0
    sw r5, r2, -2
    // Overwrite to 0x0105
    sb r1, r3, -2
    // Load 0x105 into r6
    lw r6, r0, 0
    // Store 4 to address 0
    sw r4, r5, -5
    // Execute fence and query cycle counter
    fence
    cyclecount r10
    // Set r7 to 3 and count it down to 1
    addi r7, r0, 3
loop:
    subi r7, r7, 1
    bne r7, r1, loop
    // Flush address 0
    flush r0, 0
"""

# Create CPU
cpu = CPU()

# Add `mul` instruction
mul = InstrReg("mul", lambda a, b: Word(a.value * b.value), cycles=10)
cpu._parser.add_instruction(mul)

# Load program
cpu.load_program(code)

while True:
    try:
        text = session.prompt(
            '-> ', auto_suggest=AutoSuggestFromHistory(), completer=completer, complete_while_typing=True)
    except KeyboardInterrupt:
        break
    except EOFError:
        break
    else:
        text = '__' + text
        cmd = text.split()[0]
        params = text.split()[1:]
        fn = funcs.get(cmd, __not_found)
        fn(params, cpu)
