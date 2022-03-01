from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from os import system
from math import ceil
import sys

from src.instructions import InstrReg
from src.word import Word
from src import ui
from src.cpu import CPU, CPUStatus

session = PromptSession()


funcs = {}
completions = {}
breakpoints = {}


def func(f):
    if len(f.__name__[2:]) > 0:
        completions[f.__name__[2:]] = None
        if f.__doc__ is not None:
            completions[f.__name__[2:]] = eval(f.__doc__.strip())
    funcs[f.__name__] = f


def __not_found(input: list[str], cpu: CPU):
    print('Your input did not match any known command')


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
        ui.print_rs(cpu)
    elif subcmd == 'prog':
        ui.print_prog(cpu.get_frontend(), cpu.get_exec_engine(), breakpoints)
    elif subcmd == 'bpu':
        ui.print_bpu(cpu.get_bpu())
    else:
        __not_found(input, cpu)


@func
def __continue(input: list[str], cpu: CPU):
    while True:
        info: CPUStatus = cpu.tick()
        active_breakpoints = [i for i in breakpoints if breakpoints[i] is True]
        if set(active_breakpoints) & set(info.issued_instructions):
            ui.print_color(ui.RED, 'BREAKPOINT', newline=True)
            break
        if not info.executing_program:
            print("Program finished")
            break
    ui.all_headers(cpu, breakpoints)


@func
def __step(input: list[str], cpu: CPU):
    steps = 1
    if len(input) == 1:
        try:
            steps = int(input[0])
        except ValueError:
            print("Usage: step <steps>")
            return
    for _ in range(steps):
        info: CPUStatus = cpu.tick()
        if not info.executing_program:
            print("Program finished")
            break
    ui.all_headers(cpu, breakpoints)


@func
def __break(input: list[str], cpu: CPU):
    '''
    {"add": None, "delete": None, "delete": None, "toggle": None, "list": None}
    '''
    if len(input) < 1:
        __not_found(input, cpu)
        return
    subcmd = input[0]
    if subcmd == 'add':
        if len(input) < 2:
            print("Usage: break add <address in hex>")
            return
        try:
            addr = int(input[1], base=10)
            if addr in breakpoints:
                print("Breakpoint already exists")
                return
            breakpoints[addr] = True
            print("Breakpoint added")
        except ValueError:
            print("Usage: break add <address in hex>")
    elif subcmd == 'delete':
        if len(input) < 2:
            print("Usage: break delete <address in hex>")
            return
        try:
            addr = int(input[1], base=10)
            if addr not in breakpoints:
                print("Breakpoint does not exist")
                return
            breakpoints.pop(addr)
            print("Breakpoint deleted")
        except ValueError:
            print("Usage: break delete <address in hex>")
    elif subcmd == 'list':
        print("Breakpoints:")
        for addr in breakpoints:
            print(
                "\t0x{:04x} {}".format(
                    addr,
                    "(disabled)" if not breakpoints[addr] else ""))
    elif subcmd == 'toggle':
        if len(input) < 2:
            print("Usage: break toogle <address in hex>")
            return
        try:
            addr = int(input[1], base=10)
            if addr not in breakpoints:
                print("Breakpoint does not exist")
                return
            breakpoints[addr] = not breakpoints[addr]
            print("Breakpoint toogled")
        except ValueError:
            print("Usage: break toogle <address in hex>")
    else:
        __not_found(input, cpu)


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
    ui.all_headers(cpu, breakpoints)


completer = NestedCompleter.from_nested_dict(completions)

if __name__ == "__main__":
    # grab arguments
    args = sys.argv[1:]
    # Create CPU
    cpu = CPU()

    # Add `mul` instruction for test programme
    mul = InstrReg("mul", lambda a, b: Word(a.value * b.value), cycles=10)
    cpu._parser.add_instruction(mul)

    # Load program
    try:
        # Load program
        cpu.load_program_from_file(args[0])
    except IndexError:
        print("Provide the path to your programm!")
        exit()

    # enter main loop for shell
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
