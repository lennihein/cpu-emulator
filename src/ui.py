import os
from src.bpu import BPU
from src.frontend import Frontend
from src.mmu import MMU
from src.execution import ExecutionEngine
from math import ceil
from src.word import Word
from src.cpu import CPU
from src.instructions import Instruction

HEADER = '\033[95m'
BLUE = '\033[94m'
CYAN = '\033[96m'
GREEN = '\033[92m'
RED = '\33[31m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
FAINT = '\33[2m'
YELLOW = '\33[33m'


# get terminal size
try:
    columns, rows = os.get_terminal_size(0)
except OSError:
    columns, rows = 120, 30


# print colored text using ANSI escape sequences
def print_color(c, str, newline=False):
    print(c + str + ENDC, end="\n" if newline else "")


# print a simple divider
def print_div(c=None, length=columns, newline=True):
    str = "-" * length
    if c is None:
        print(str)
    else:
        print_color(c, str, newline)


# print a divider with a header
def print_header(str, c=ENDC):
    inlay = "[ " + str + " ]"
    length = (columns - len(inlay)) // 2
    print_div(c, length, False)
    print_color(c, inlay)
    print_div(c, length + (columns - len(inlay)) % 2, True)


def print_hex(num: int, p_end=" ", base=True,
              base_style=FAINT, style=ENDC) -> None:
    num_str = style + '{:04x}'.format(num) + ENDC
    base_str = base_style + "0x" + ENDC if base else ""
    print(base_str + num_str, end=p_end)


def print_memory(mmu: MMU, lines=8, base=0x0000):
    fits = (columns - 8) // 7
    i = base
    for _ in range(lines):
        if i >= mmu.mem_size:
            return
        print_hex(i, p_end=": ", base_style=BOLD + YELLOW, style=BOLD + YELLOW)
        for _ in range(fits):
            if i >= mmu.mem_size:
                return
            if(mmu.is_addr_cached(Word(i))):
                print_hex(mmu.memory[i + 1] * 256 + mmu.memory[i], base_style=FAINT + RED, style=RED)
            else:
                print_hex(mmu.memory[i + 1] * 256 + mmu.memory[i])
            i += 2
        print()


def print_regs(engine: ExecutionEngine):
    regs = engine._registers
    fits = (columns + 3) // 14
    lines = ceil(len(regs) / fits)
    i = 0
    for _ in range(lines):
        for j in range(fits):
            if i >= 32:
                break
            print(" " if j != 0 else "", end="")
            print(BOLD + GREEN + "R" + str(i)
                  + (" : " if i < 10 else ": "), end="")
            try:
                print_hex(regs[i].value, p_end="", base_style=ENDC + FAINT)
            except AttributeError:
                print(ENDC + FAINT + "RS {:03}".format(regs[i]), end="")
            print(" |" if j != fits - 1 else "\n", end="")
            i += 1
    print()


def print_cache(mmu: MMU) -> None:
    """Prints the cache. Only to be used during development."""
    for i in range(len(mmu.cache.sets)):
        print(i, end=' ')
        for j in range(len(mmu.cache.sets[i])):
            if mmu.cache.sets[i][j].is_in_use():
                print("*", end='')
            for a in range(len(mmu.cache.sets[i][j].data)):
                val = mmu.cache.sets[i][j].data[a]
                print(
                    '{:04x}'.format(val) if val is not None else "none",
                    end='|')
            # print(mmu.cache.sets[i][j].data)
            print(' ', end='')
        print('')


def print_instruction(instr: Instruction) -> int:
    instr_str = YELLOW + instr.ty.name + ENDC
    instr_str += " " * (6 - len(instr.ty.name))
    op_str = ", ".join([str(op) for op in instr.ops])
    print(instr_str + op_str, end="")
    return len(instr_str) + len(op_str)


def print_queue(queue: Frontend):
    for item in queue.instr_queue:
        instr = item.instr
        print_instruction(instr)
        print()


def print_prog(front: Frontend, engine: ExecutionEngine,
               breakpoints: dict, start=0, end=-1):

    start = 0 if start < 0 else start
    end = len(front.instr_list) if end == -1 else end
    end = min(end, len(front.instr_list))

    inflights = [slot.pc for slot in engine.slots() if slot is not None]
    active_breakpoints = [pt for pt in breakpoints if breakpoints[pt]]
    disabled_breakpoints = [pt for pt in breakpoints if not breakpoints[pt]]

    for i in range(start, end):

        # print status tag
        if i in inflights and i in active_breakpoints:
            print_color(BOLD + RED, "► ", False)
        elif i in inflights:
            print_color(BOLD + GREEN, "► ", False)
        elif i in active_breakpoints:
            print_color(BOLD + RED, "◉ ", False)
        elif i in disabled_breakpoints:
            print_color(BOLD + RED, "○ ", False)
        else:
            print("  ", end="")

        # print line tag
        line_str = str(i)
        line_str = " " * (2 - len(line_str)) + line_str + " "
        print(FAINT + line_str + ENDC, end="")

        try:
            # print instruction
            instr = front.instr_list[i]
            print_instruction(instr)
        except IndexError:
            print("\n")
            print(f"i: {i}")
            print(f"len: {len(front.instr_list)}")
            print(f"start: {start}")
            print(f"end: {end}")

        # newline
        print()


def print_rs(cpu: CPU):
    id = 0
    for slot in cpu.get_exec_engine().slots():
        if slot is None:
            continue
        # print(slot.pc, end=" ")
        id_str = str(id)
        id_str = " " * (2 - len(id_str)) + id_str + " "
        print(FAINT + id_str + ENDC, end="")
        i_len = print_instruction(slot.instr)
        print(" " * (24 - i_len), end="")
        print(f"{' RUNNING' if slot.executing else 'RETIRING'}")
        id += 1


def print_bpu(bpu: BPU) -> None:
    print(bpu, end="")


def print_info(cpu: CPU) -> None:
    print("PC: ", cpu.get_frontend().get_pc(), end="")


def header_memory(mmu: MMU):
    print_header("Memory", BOLD + YELLOW + ENDC)
    print()
    print_memory(mmu, lines=8, base=0x0000)
    print()


def header_regs(engine: ExecutionEngine):
    print_header("Registers", BOLD + CYAN + ENDC)
    print()
    print_regs(engine)
    print()


def header_prog(front: Frontend, engine: ExecutionEngine, breakpoints: dict):
    print_header("Programme", BOLD + CYAN + ENDC)
    print()
    lowest_inflight = min([slot.pc for slot in engine.slots() if slot is not None], default=0)
    highest_inflight = max([slot.pc for slot in engine.slots() if slot is not None], default=len(front.instr_list))
    print_prog(front, engine, breakpoints, start=lowest_inflight - 2, end=highest_inflight + 2)
    print()


def header_info(cpu: CPU):
    print_header("Info", BOLD + CYAN + ENDC)
    print()
    print_info(cpu)
    print()


def header_rs(engine: ExecutionEngine):
    print_header("Reservation Stations", BOLD + CYAN + ENDC)
    print()
    print_rs(engine)
    print()


def all_headers(cpu: CPU, breakpoints: dict):
    # header_info(cpu)
    header_regs(cpu.get_exec_engine())
    header_memory(cpu.get_mmu())
    header_prog(cpu.get_frontend(), cpu.get_exec_engine(), breakpoints)
