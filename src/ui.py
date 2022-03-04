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

BOX_SOUTHEAST = '╭'
BOX_SOUTHWEST = '╮'
BOX_NORTHEAST = '╰'
BOX_NORTHWEST = '╯'
BOX_HORIZOZTAL = '─'
BOX_VERTICAL = '│'
BOX_CROSS = '┼'
BOX_NES = '├'
BOX_NSW = '┤'
BOX_NEW = '┴'
BOX_ESW = '┬'
BOW_ARROW_FILLED = '►'
BOW_ARROW_OUTLINE = '▻'
BOW_TRIANGLE_MINI = '▸'
BOX_TRIANGLE_FILLED = '▶'
BOW_TRIANGLE_OUTLINE = '▷'
BOX_ARROW_BIG_OUTLINE = "⇨"

# get terminal size
try:
    columns, rows = os.get_terminal_size(0)
except OSError:
    columns, rows = 120, 30


# print colored text using ANSI escape sequences
def print_color(c, str, newline=False):
    print(fmt_color(c, str, newline=newline), end="")


def fmt_color(c, str, newline=False):
    return c + str + ENDC + ("\n" if newline else "")


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
    print(hex_str(num, p_end=p_end, base=base, base_style=base_style, style=style), end="")


def hex_str(num: int, p_end=" ", base=True, fixed_width=True, base_style=FAINT, style=ENDC) -> str:
    if fixed_width:
        num_str = style + '{:04x}'.format(num) + ENDC
    else:
        num_str = style + '{:x}'.format(num) + ENDC
    base_str = base_style + "0x" + ENDC if base else ""
    return base_str + num_str + p_end


def print_memory(mmu: MMU, lines=8, base=0x0000):
    fits = (columns - 8) // 5
    i = base
    for _ in range(lines):
        if i >= mmu.mem_size:
            return
        print_hex(i, p_end=": ", base_style=BOLD + YELLOW, style=BOLD + YELLOW)
        for _ in range(fits):
            if i >= mmu.mem_size:
                return
            if(mmu.is_addr_cached(Word(i))):
                print_hex(mmu.memory[i + 1] * 256 + mmu.memory[i], base_style=FAINT + RED, style=RED, base=False)
            else:
                print_hex(mmu.memory[i + 1] * 256 + mmu.memory[i], base=False)
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


def instruction_str(instr: Instruction) -> str:
    instr_str = YELLOW + instr.ty.name + ENDC
    instr_str += " " * (6 - len(instr.ty.name))
    op_str = ", ".join([hex_str((Word(op).value), p_end="", fixed_width=False) for op in instr.ops])
    return instr_str + op_str


def print_queue(queue: Frontend):
    for item in queue.instr_queue:
        instr = item.instr
        print(instruction_str(instr))


def print_prog(front: Frontend, engine: ExecutionEngine,
               breakpoints: dict, start=0, end=-1):
    prog = prog_str(front, engine, breakpoints, start, end)
    for line in prog:
        print(line)


def prog_str(front: Frontend, engine: ExecutionEngine, breakpoints: dict, start=0, end=-1) -> list[str]:
    start = 0 if start < 0 else start
    end = len(front.instr_list) if end == -1 else end
    end = min(end, len(front.instr_list))
    prog_str: list[str] = [""] * (end - start)

    inflights = [slot.pc for slot in engine.slots() if slot is not None]
    active_breakpoints = [pt for pt in breakpoints if breakpoints[pt]]
    disabled_breakpoints = [pt for pt in breakpoints if not breakpoints[pt]]

    for index, line in enumerate(range(start, end)):
        # print status tag
        if line in inflights and line in active_breakpoints:
            prog_str[index] += fmt_color(BOLD + RED, BOX_TRIANGLE_FILLED + " ", False)
        elif line in inflights:
            prog_str[index] += fmt_color(BOLD + GREEN, BOX_TRIANGLE_FILLED + " ", False)
        elif line in active_breakpoints:
            prog_str[index] += fmt_color(BOLD + RED, "◉ ", False)
        elif line in disabled_breakpoints:
            prog_str[index] += fmt_color(BOLD + RED, "○ ", False)
        else:
            prog_str[index] += "  "

        # print line tag
        line_str = str(line)
        line_str = " " * (2 - len(line_str)) + line_str + " "
        prog_str[index] += FAINT + line_str + ENDC

        try:
            # print instruction
            instr = front.instr_list[line]
            prog_str[index] += instruction_str(instr)
        except IndexError:
            print("\n")
            print(f"i: {line}")
            print(f"len: {len(front.instr_list)}")
            print(f"start: {start}")
            print(f"end: {end}")
    return prog_str


def print_rs(cpu: CPU):
    id = 0
    for slot in cpu.get_exec_engine().slots():
        if slot is None:
            continue
        # print(slot.pc, end=" ")
        id_str = str(id)
        id_str = " " * (2 - len(id_str)) + id_str + " "
        print(FAINT + id_str + ENDC, end="")
        instr_str = instruction_str(slot.instr)
        i_len = len(instr_str)
        print(instr_str, end="")
        print(" " * (24 - i_len), end="")
        print(f"{' ☐' if slot.executing else ' ☑'}")
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
    print_prog(front, engine, breakpoints, start=lowest_inflight - 1, end=highest_inflight + 2)
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
