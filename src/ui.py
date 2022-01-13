import os

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
columns, rows = os.get_terminal_size(0)

# print colored text using ANSI escape sequences
def print_color(c, str, newline=False):
    print(c + str + ENDC, end = "\n" if newline else "")

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
    print_div(c, length + (columns - len(inlay)) %2, True)

def print_hex(num:int, p_end=" ", base=True, base_style=FAINT, style=ENDC)->None:
    num_str = style + '{:04x}'.format(num) + ENDC
    base_str = base_style + "0x" + ENDC if base else ""
    print(base_str + num_str, end=p_end)

def is_cached(addr):
    return True if addr == 0x15 else False

def print_memory(lines=8, base=0x0000):
    fits = (columns - 8) // 7
    i = base
    for _ in range(lines):
        print_hex(i, p_end=": ", base_style=BOLD+YELLOW, style=BOLD+YELLOW)
        for _ in range(fits):
            if(is_cached(i)):
                print_hex(arr[i], base_style=FAINT+RED, style=RED)
            else:
                print_hex(arr[i])
            i += 1
        print()

# print current PC position
print_header("Program", BOLD + RED + ENDC)
print("  " + FAINT + "37 " + ENDC + CYAN + "ADD " + ENDC + YELLOW + "R0, R0" + ENDC)
print(GREEN + "► " + ENDC + FAINT + "38 " + ENDC + CYAN + "MOV " + ENDC + YELLOW + "R1, R7" + ENDC)
print("  " + FAINT + "39 " + ENDC + CYAN + "LD  " + ENDC + YELLOW + "R1, R0" + ENDC)
print("  " + FAINT + "40 " + ENDC + CYAN + "DIV " + ENDC + YELLOW + "R0, R0" + ENDC)

# print reservation stations
print_header("ReservationStations", BOLD + GREEN + ENDC)
from tabulate import tabulate
print()
print(tabulate([["ADD", "R0", "R0"], ["FLUSH", "-","-"]], headers=['Instruction', 'OP1', 'OP2'], tablefmt='orgtbl'))
print()

# print memory
print_header("Memory", BOLD + YELLOW + ENDC)
print()
from random import randrange
arr = [randrange(0, 0xFFFF) for _ in range(0xFFFF)]
print_memory(lines=8, base=0x0000)
print()

# print registers
print_header("Registers", BOLD + CYAN + ENDC)
print(BOLD+GREEN + "R0:" + ENDC + " " + FAINT + "0x" + ENDC + "EB83")
print(BOLD+GREEN + "R1:" + ENDC + " " + FAINT + "0x" + ENDC + "031C")
print(BOLD+GREEN + "R2:" + ENDC + " " + FAINT + "0x" + ENDC + "0000")
print(BOLD+GREEN + "R3:" + ENDC + " " + FAINT + "0x" + ENDC + "DEAD")
