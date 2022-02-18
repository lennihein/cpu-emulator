import os
from src.mmu import MMU
from src.execution import ExecutionEngine
from math import ceil
from src.word import Word

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
                print_hex(mmu.memory[i], base_style=FAINT + RED, style=RED)
            else:
                print_hex(mmu.memory[i])
            i += 1
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
            print_hex(regs[i].value, p_end="", base_style=ENDC + FAINT)
            print(" |" if j != fits - 1 else "\n", end="")
            i += 1


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


def header_memory(mmu: MMU):
    print_header("Memory", BOLD + YELLOW + ENDC)
    print()
    print_memory(mmu, lines=8, base=0x0000)
    print()


def header_regs(engine: ExecutionEngine):
    print_header("Registers", BOLD + CYAN + ENDC)
    print()
    print_regs(engine)
    print("\n")


def all_headers(engine: ExecutionEngine):
    header_regs(engine)
    header_memory(engine._mmu)
