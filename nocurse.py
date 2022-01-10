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

def print_header(c, str):
    inlay = "[ " + str + " ]"
    length = (columns - len(inlay)) // 2
    print_div(c, length, False)
    print_color(c, inlay)
    print_div(c, length, True)

print_header(BOLD + RED, "nocursetest.py")
print(YELLOW + UNDERLINE + "Terminal Dimensions:" + ENDC + " " + FAINT + str(columns) + "x" + str(rows) + ENDC)
print("")
print(RED + "This" + ENDC + " uses " + GREEN + BOLD + "no library!" + ENDC + " - cool, isn't it?")
print_div(RED + BOLD)