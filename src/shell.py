from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from os import system
from math import ceil
import sys

from src.instructions import InstrReg
from src.word import Word
from src.byte import Byte
from src import ui
from src.cpu import CPU, CPUStatus

PROMPT = ui.BOW_ARROW_FILLED + " "

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
        return cpu
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
                return cpu
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
                return cpu
        else:
            ui.print_memory(cpu.get_mmu())
    elif subcmd == 'cache':
        ui.print_cache(cpu.get_mmu())
    elif subcmd == 'regs':
        ui.print_regs(cpu.get_exec_engine())
    elif subcmd == 'queue':
        ui.print_queue(cpu.get_frontend())
    elif subcmd == 'rs':
        ui.print_rs(cpu.get_exec_engine())
    elif subcmd == 'prog':
        ui.print_prog(cpu.get_frontend(), cpu.get_exec_engine(), breakpoints)
    elif subcmd == 'bpu':
        ui.print_bpu(cpu.get_bpu())
    else:
        __not_found(input, cpu)


@func
def __edit(input: list[str], cpu: CPU) -> CPU:
    '''
    {"word": None, "byte": None, "flush": None, "load": None, "reg": None, "bpu": None}
    '''
    if len(input) < 1:
        __not_found(input, cpu)
        return cpu
    subcmd = input[0]
    if subcmd == 'word':
        if len(input) == 3:
            try:
                addr = int(input[1], base=16)
                val = int(input[2], base=16)
                cpu.get_mmu().edit_word(Word(addr), Word(val))
            except ValueError:
                print("Usage: edit word <address in hex> <value in hex>")
                return cpu
        else:
            print("Usage: edit word <address in hex> <value in hex>")
    elif subcmd == 'byte':
        if len(input) == 3:
            try:
                addr = int(input[1], base=16)
                val = int(input[2], base=16)
                cpu.get_mmu().edit_byte(Word(addr), Byte(val))
            except ValueError:
                print("Usage: edit byte <address in hex> <value in hex>")
                return cpu
        else:
            print("Usage: edit word <address in hex> <value in hex>")
    elif subcmd == 'flush':
        if len(input) == 1:
            cpu.get_mmu().flush_all()
        elif len(input) == 2:
            try:
                addr = int(input[1], base=16)
                cpu.get_mmu().flush_line(Word(addr))
            except ValueError:
                print("Usage: edit flush <address in hex>")
                return cpu
        else:
            print("Usage: edit flush <address in hex>")
    elif subcmd == 'load':
        if len(input) == 2:
            try:
                addr = int(input[1], base=16)
                cpu.get_mmu()._load_line(Word(addr))
            except ValueError:
                print("Usage: edit load <address in hex>")
                return cpu
        else:
            print("Usage: edit load <address in hex>")
    elif subcmd == 'reg':
        if len(input) == 3:
            try:
                reg = int(input[1])
                val = int(input[2], base=16)
                if reg > 31 or reg < 0:
                    print("No such register!")
                    return cpu
                cpu.get_exec_engine()._registers[reg] = Word(val)
            except ValueError:
                print("Usage: edit reg <register (0-31)> <value in hex>")
                return cpu
        else:
            print("Usage: edit reg <register in decimal> <value in hex>")
    elif subcmd == 'bpu':
        if len(input) == 3:
            try:
                pc = int(input[1])
                val = int(input[2], base=10)
                if val < 0 or val > 3:
                    print("Usage: edit bpu <pc in decimal> <value (0-3)>")
                    return cpu
                cpu.get_bpu().set_counter(pc, val)
            except ValueError:
                print("Usage: edit bpu <pc in dec> <value (0-3)>")
                return cpu
        else:
            print("Usage: edit bpu <register in decimal> <value in hex>")
    else:
        __not_found(input, cpu)
    return cpu


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
        if info.fault_info is not None:
            print(ui.BOLD + ui.RED + f"FAULT at {info.fault_info.pc}: " + str(info.fault_info.instr) + ui.ENDC + "\n", end="")
            break
    ui.all_headers(cpu, breakpoints)


@func
def __step(input: list[str], cpu: CPU):
    steps = 1
    info: CPUStatus
    if len(input) == 1:
        try:
            steps = int(input[0])
        except ValueError:
            print("Usage: step <steps>")
            return cpu
        if steps < 0:
            cpu = cpu.restore_snapshot(cpu, steps)
            if cpu is None:
                print("Can't restore snapshot")
                return cpu
            steps = 0
    for _ in range(steps):
        info = cpu.tick()
        if not info.executing_program:
            print("Program finished")
            break
        if info.fault_info is not None:
            print(ui.BOLD + ui.RED + f"FAULT at {info.fault_info.pc}: " + str(info.fault_info.instr) + ui.ENDC + "\n", end="")
            break
    ui.all_headers(cpu, breakpoints)
    return cpu


@func
def __break(input: list[str], cpu: CPU):
    '''
    {"add": None, "delete": None, "delete": None, "toggle": None, "list": None}
    '''
    if len(input) < 1:
        __not_found(input, cpu)
        return cpu
    subcmd = input[0]
    if subcmd == 'add':
        if len(input) < 2:
            print("Usage: break add <address in hex>")
            return cpu
        try:
            addr = int(input[1], base=10)
            if addr in breakpoints:
                print("Breakpoint already exists")
                return cpu
            breakpoints[addr] = True
            print("Breakpoint added")
        except ValueError:
            print("Usage: break add <address in hex>")
    elif subcmd == 'delete':
        if len(input) < 2:
            print("Usage: break delete <address in hex>")
            return cpu
        try:
            addr = int(input[1], base=10)
            if addr not in breakpoints:
                print("Breakpoint does not exist")
                return cpu
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
            print("Usage: break toggle <address in hex>")
            return cpu
        try:
            addr = int(input[1], base=10)
            if addr not in breakpoints:
                print("Breakpoint does not exist")
                return cpu
            breakpoints[addr] = not breakpoints[addr]
            print("Breakpoint toogled")
        except ValueError:
            print("Usage: break toogle <address in hex>")
    else:
        __not_found(input, cpu)


@func
def __clear(input: list[str], cpu: CPU):
    system('clear')
    return cpu


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
                PROMPT, auto_suggest=AutoSuggestFromHistory(), completer=completer, complete_while_typing=True)
        except KeyboardInterrupt:
            break
        except EOFError:
            break
        else:
            text = '__' + text
            cmd = text.split()[0]
            params = text.split()[1:]
            fn = funcs.get(cmd, __not_found)
            n_cpu = fn(params, cpu)
            if n_cpu is not None:
                cpu = n_cpu
