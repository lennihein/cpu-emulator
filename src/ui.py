from __future__ import annotations

import os
from math import ceil, floor

from .bpu import BPU
from .frontend import Frontend
from .memory import MemorySubsystem
from .execution import ExecutionEngine
from .word import Word
from .cpu import CPU
from .instructions import Instruction, InstrReg, InstrImm, InstrLoad, InstrStore, InstrFlush, InstrFlushAll, InstrCyclecount, InstrBranch, InstrFence

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
BOX_ARROW_PHAT = '🠊'

# get terminal size
columns: int = 120
rows: int = 30


def get_terminal_size():
    global columns, rows
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
def print_div(c=None, length=None, newline=True):
    global columns
    str = "-" * (length if length is not None else columns)
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
    print(
        hex_str(
            num,
            p_end=p_end,
            base=base,
            base_style=base_style,
            style=style),
        end="")


def hex_str(num: int, p_end=" ", base=True, fixed_width=True,
            base_style=FAINT, style=ENDC) -> str:
    if fixed_width:
        num_str = style + '{:04x}'.format(num) + ENDC
    else:
        num_str = style + '{:x}'.format(num) + ENDC
    base_str = base_style + "0x" + ENDC if base else ""
    return base_str + num_str + p_end


def print_memory(memory: MemorySubsystem, lines=8, base=0x0000):
    fits = (columns - 8) // 5
    fits = fits - (fits % 8)
    i = base
    for _ in range(lines):
        if i >= memory.mem_size:
            return
        print_hex(i, p_end=": ", base_style=BOLD + YELLOW, style=BOLD + YELLOW)
        for _ in range(fits):
            if i >= memory.mem_size:
                return
            if(memory.is_addr_cached(Word(i))):
                print_hex(memory.memory[i + 1] * 256 + memory.memory[i],
                          base_style=FAINT + RED, style=RED, base=False)
            else:
                print_hex(memory.memory[i + 1] * 256 + memory.memory[i], base=False)
            i += 2
        print()


def reg_str(val) -> str:
    if isinstance(val, Word):
        return hex_str(val.value, p_end="", base_style=ENDC + FAINT)
    elif isinstance(val, int):
        return ENDC + "RS {:03}".format(val) + ENDC
    else:
        return BOLD + RED + "ERR"
        exit(1)


def print_regs(engine: ExecutionEngine, reg_capitalisation: bool = False):
    regs = engine._registers
    fits = (columns + 3) // 14
    lines = ceil(len(regs) / fits)
    i = 0
    reg_symbol = "R" if reg_capitalisation else "r"
    for _ in range(lines):
        for j in range(fits):
            if i >= 32:
                break
            print(" " if j != 0 else "", end="")
            print(BOLD + GREEN + reg_symbol + str(i)
                  + (" : " if i < 10 else ": "), end="")
            val = regs[i]
            print(reg_str(val), end="")
            print(" │" if j != fits - 1 else "\n", end="")
            i += 1
    print()


def print_cache(mem: MemorySubsystem, show_empty_sets: bool, show_empty_ways: bool) -> None:
    # TODO: make compatible with more than 12 bits for tag or index
    # long_index = True if num_index_bits > 12 else False
    # long_tag = True if num_tag_bits > 12 else False

    data_length = 1 + 7 * mem.cache.line_size

    data_header = ('─' * floor((data_length - 4) / 2)) + "Data" + ('─' * ceil((data_length - 4) / 2))
    print(f"╭─Index─┬──Tag──┬{data_header}╮")

    for i, set in enumerate(mem.cache.sets):

        if len([entry for entry in set if entry.is_in_use()]) == 0 and show_empty_sets is False:
            print(f"├{'─' * 7}┼{'─'*7}┼{'─' * data_length}┤")
            print(f"│ {FAINT}0x{ENDC}{'{:03x}'.format(i)} │ empty │{' ' * (data_length-0)}│")
            continue

        if i != 0:
            print(f"├{'─'*7}┼{'─'*7}┼{'─' * data_length}┤")

        if show_empty_ways is False:
            set = [entry for entry in set if entry.is_in_use()]

        for j, entry in enumerate(set):

            if (j + 1) == ceil(len(set) / 2) and len(set) % 2 == 1:
                index_gap = f" {FAINT}0x{ENDC}{'{:03x}'.format(i)} "
            else:
                index_gap = f"{' '*7}"

            if entry.is_in_use():
                print(f"│{index_gap}│ {FAINT}0x{ENDC}{'{:03x}'.format(entry.tag)} │ ", end="")
                for a, val in enumerate(entry.data):
                    print(f"{hex_str(val, p_end=' ')}", end='')
                print("│")
            else:
                print(f"│{index_gap}│{' '*7}│{' '*data_length}│")

            if (j + 1) == ceil(len(set) / 2) and len(set) % 2 == 0:
                index_gap = f" {FAINT}0x{ENDC}{'{:03x}'.format(i)} "
            else:
                index_gap = f"{' '*7}"

            if j != len(set) - 1:
                print(f"│{index_gap}├{'─'*7}┼{'─' * data_length}┤")

    print(f"╰{'─'*7}┴{'─'*7}┴{'─' * data_length}╯")


def instruction_str(instr: Instruction, reg_capitalisation: bool = False) -> tuple[str, int]:
    instr_str = f"{YELLOW}{instr.ty.name}{ENDC}{' ' * (6 - len(instr.ty.name))}"
    length = 6 if len(instr.ty.name) <= 6 else len(instr.ty.name)
    op_str = ""

    reg_symbol = "R" if reg_capitalisation else "r"

    if isinstance(instr.ty, (InstrReg, InstrCyclecount)):
        for index, op in enumerate(instr.ops):
            op_str += f"{reg_symbol}{op}"
            length += 1 + len(str(op))
            if index != len(instr.ops) - 1:
                op_str += ", "
                length += 2

    elif isinstance(instr.ty, (InstrStore, InstrLoad, InstrImm, InstrFlush, InstrFlushAll, InstrFence)):
        for index, op in enumerate(instr.ops):
            if index == len(instr.ops) - 1:
                op_str += hex_str(Word(op).value, p_end="", fixed_width=False)
                length += len(hex(Word(op).value))
            else:
                op_str += f"{reg_symbol}{op}, "
                length += 3 + len(str(op))

    elif isinstance(instr.ty, InstrBranch):
        for index, op in enumerate(instr.ops):
            if index == len(instr.ops) - 1:
                op_str += str(abs(op))
                length += len(str(abs(op)))
            else:
                op_str += f"{reg_symbol}{op}"
                op_str += ", "
                length += 3 + len(str(op))

    else:
        print(f"{RED + BOLD}Unknown instruction type: {instr.ty}{ENDC}")
        exit(1)

    return instr_str + op_str, length


def print_queue(queue: Frontend, reg_capitalisation: bool = False):
    q_str, _ = queue_str(queue, reg_capitalisation)
    for line in q_str:
        print(line)


def queue_str(queue: Frontend, reg_capitalisation: bool = False) -> tuple[list[str], list[int]]:
    q_str: list[str] = [""] * len(queue.instr_queue)
    q_lengths: list[int] = [0] * len(queue.instr_queue)
    for index, item in enumerate(queue.instr_queue):
        instr = item.instr
        q_str[index], q_lengths[index] = instruction_str(instr, reg_capitalisation)
    return q_str, q_lengths


def print_prog(front: Frontend, engine: ExecutionEngine,
               breakpoints: dict, start=0, end=-1, reg_capitalisation: bool = False):
    prog, _ = prog_str(front, engine, breakpoints, start, end, reg_capitalisation)
    for line in prog:
        print(line)


def prog_str(front: Frontend, engine: ExecutionEngine,
             breakpoints: dict, start=0, end=-1, reg_capitalisation: bool = False) -> tuple[list[str], list[int]]:
    start = 0 if start < 0 else start
    end = len(front.instr_list) if end == -1 else end
    end = min(end, len(front.instr_list))
    prog_str: list[str] = [""] * (end - start)
    line_lengths: list[int] = [0] * (end - start)

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
        line_str = " " * ((2 if end < 100 else 3) - len(line_str)) + line_str + " "
        prog_str[index] += FAINT + line_str + ENDC

        line_lengths[index] = 5 if end < 100 else 6

        instr = front.instr_list[line]
        instr_part, length = instruction_str(instr, reg_capitalisation)
        prog_str[index] += instr_part
        line_lengths[index] += length
    return prog_str, line_lengths


def print_rs(engine: ExecutionEngine, show_rs_empty: bool, reg_capitalisation: bool = False) -> None:
    strings, _ = rs_str(engine, show_empty=show_rs_empty, reg_capitalisation=reg_capitalisation)
    for line in strings:
        if line != "":
            print(line)


def rs_str(engine: ExecutionEngine, show_empty=True, reg_capitalisation: bool = False) -> tuple[list[str], int]:

    rs_length: int

    instructions = []
    pcs = []
    indices = []
    status = []

    instr_lengths: list[int] = []

    for i, slot in enumerate(engine.slots()):
        if slot is None:
            pcs += [""]
            instructions += [""]
            indices += [""]
            status += [""]
            instr_lengths += [0]
            continue

        instr_str, instr_length = instruction_str(slot.instr, reg_capitalisation)
        instructions.append(instr_str)

        pcs.append(str(slot.pc if slot.pc != -1 else "μ"))
        indices.append(str(i))
        status.append(f"{'☐' if slot.executing else '☑'}")

        instr_lengths.append(instr_length)

    max_instr_length = max(instr_lengths) if instr_lengths else 0
    max_pc_length = max([len(pc) for pc in pcs]) if pcs else 0
    max_index_length = max([len(index) for index in indices]) if indices else 0

    max_instr_length = max(max_instr_length, 10)
    max_pc_length = max(max_pc_length, 1)
    max_index_length = max(max_index_length, 1)

    rs_length = max_instr_length + max_pc_length + 1 + 3 + 3 + 14 + 4

    if not show_empty:
        rs_length += max_index_length + 3

    rs_str: list[str] = []

    line_top = '╭'
    if not show_empty:
        line_top += '─' * (max_index_length + 2) + '┬'
    line_top += '─' * (max_pc_length + 2) + '┬' + '─' * (max_instr_length + 2) + '┬────────┬────────┬' + '─' * 3 + '╮'
    rs_str.append(line_top)

    for i, slot in enumerate(engine.slots()):
        if slot is None:
            if show_empty:
                rs_str.append('│' + ' ' * (max_pc_length + 2) + '│' + ' ' * (max_instr_length + 2) + '│        │        │' + ' ' * 3 + '│')
            continue
        else:
            line = '│ '
            if not show_empty:
                line += ' ' * (max_index_length - len(indices[i])) + indices[i] + ' │ '
            line += ' ' * (max_pc_length - len(pcs[i])) + pcs[i] + ' │ '
            line += instructions[i] + ' ' * (max_instr_length - instr_lengths[i]) + ' │'
            line += f" {reg_str(slot.source_operands[0]) if len(slot.source_operands) >= 1 else ' ' * 6} │"
            line += f" {reg_str(slot.source_operands[1]) if len(slot.source_operands) >= 2 else ' ' * 6} │"
            line += f" {status[i]} │"
            rs_str.append(line)

    line_bot = '╰'
    if not show_empty:
        line_bot += '─' * (max_index_length + 2) + '┴'
    line_bot += '─' * (max_pc_length + 2) + '┴' + '─' * (max_instr_length + 2) + '┴────────┴────────┴' + '─' * 3 + '╯'
    rs_str.append(line_bot)

    return rs_str, rs_length


def print_bpu(bpu: BPU) -> None:
    print(bpu, end="")


def print_info(cpu: CPU) -> None:
    print("PC: ", cpu.get_frontend().get_pc(), end="")


def header_memory(memory: MemorySubsystem):
    print_header("Memory", BOLD + YELLOW + ENDC)
    print()
    print_memory(memory, lines=8, base=0x0000)
    print()


def header_regs(engine: ExecutionEngine, reg_capitalisation: bool = False):
    print_header("Registers", BOLD + CYAN + ENDC)
    print()
    print_regs(engine, reg_capitalisation)
    print()


def header_pipeline(front: Frontend, engine: ExecutionEngine, breakpoints: dict, show_rs_empty: bool = True, reg_capitalisation: bool = False):
    # calculate prog start and end
    lowest_inflight = min([slot.pc for slot in engine.slots() if slot is not None and slot.pc >= 0], default=0)
    highest_inflight = max([slot.pc for slot in engine.slots() if slot is not None and slot.pc >= 0], default=len(front.instr_list))

    prog, prog_lengths = prog_str(front, engine, breakpoints, start=lowest_inflight - 1, end=highest_inflight + 2, reg_capitalisation=reg_capitalisation)
    arrow = ["  ╭─► "] + ["  │   "] * (len(prog) - 2) + [" ─╯   "]
    q, q_lengths = queue_str(front, reg_capitalisation=reg_capitalisation)
    rs, rs_length = rs_str(engine, show_empty=show_rs_empty, reg_capitalisation=reg_capitalisation)

    lines = max(len(prog), len(q), len(rs) - 1)

    max_prog = max(prog_lengths) if prog_lengths else 25
    max_arrow = 6
    max_q = max(q_lengths) if q_lengths else 25

    prog = [prog[i] + " " * (max_prog - prog_lengths[i])
            for i in range(len(prog))] + [" " * max_prog] * (lines - len(prog))
    arrow = arrow + [" " * max_arrow] * (lines - len(arrow))
    q = [q[i] + " " * (max_q - q_lengths[i])
         for i in range(len(q))] + [" " * max_q] * (lines - len(q))

    header_str = "-" * ceil((max_prog - len("[ Program ]")) / 2) + "[ Program ]" + "-" * floor((max_prog - len("[ Program ]")) / 2)
    header_str += "-" * max_arrow
    header_str += "-" * ceil((max_q - len("[ Queue ]")) / 2) + "[ Queue ]" + "-" * floor((max_q - len("[ Queue ]")) / 2)
    header_str += "-" * 4
    header_str += "-" * ceil((rs_length - len("[ Reservation Stations ]")) / 2) + "[ Reservation Stations ]" + "-" * floor((rs_length - len("[ Reservation Stations ]")) / 2)

    if columns < len(header_str):
        print(BOLD + RED + UNDERLINE + "Please increase the terminal width to at least " + str(len(header_str)) + " characters" + ENDC + "\n")
        print_prog(front, engine, breakpoints, start=lowest_inflight - 1, end=highest_inflight + 1)
        print_div(length=columns)
        print_queue(front)
        print_div(length=columns)
        print_rs(engine, show_rs_empty=show_rs_empty)
        return
    print(header_str + "-" * (columns - len(header_str)))

    print(" " * (max_prog + max_arrow + max_q + 4), end="")
    print(rs[0])

    for i in range(max(len(prog), len(q), len(rs))):
        if i < len(prog):
            print(prog[i], end="")
            print(arrow[i], end="") if len(front.instr_queue) else print(" " * max_arrow, end="")
        if i < len(q):
            print(q[i], end="")
        print("    ", end="") if i != 0 or len(front.instr_queue) == 0 else print(" " + "─►" + " ", end="")
        if i < len(rs) - 1:
            print(rs[i + 1], end="")
        print("")
    print()


def header_info(cpu: CPU):
    print_header("Info", BOLD + CYAN + ENDC)
    print()
    print_info(cpu)
    print()


def header_rs(engine: ExecutionEngine, reg_capitalisation: bool = False):
    print_header("Reservation Stations", BOLD + CYAN + ENDC)
    print()
    print_rs(engine)
    print()


def all_headers(cpu: CPU, breakpoints: dict):
    header_regs(cpu.get_exec_engine(), cpu._config["UX"]["reg_capitalisation"])
    header_memory(cpu.get_memory_subsystem())
    header_pipeline(cpu.get_frontend(), cpu.get_exec_engine(), breakpoints, cpu._config["UX"]["show_empty_slots"], cpu._config["UX"]["reg_capitalisation"])
