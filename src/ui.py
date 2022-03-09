import os
from src.bpu import BPU
from src.frontend import Frontend
from src.mmu import MMU
from src.execution import ExecutionEngine
from math import ceil, floor
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
BOX_ARROW_PHAT = '🠊'

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
                print_hex(mmu.memory[i + 1] * 256 + mmu.memory[i],
                          base_style=FAINT + RED, style=RED, base=False)
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
            val = regs[i]
            if isinstance(val, Word):
                print_hex(val.value, p_end="", base_style=ENDC + FAINT)
            elif isinstance(val, int):
                print(ENDC + FAINT + "RS {:03}".format(regs[i]) + ENDC, end="")
            else:
                print(BOLD + RED + "ERR", end="")
                exit(1)
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


def instruction_str(instr: Instruction) -> tuple[str, int]:
    instr_str = YELLOW + instr.ty.name + ENDC
    instr_str += " " * (6 - len(instr.ty.name))
    op_str = ", ".join(
        [hex_str((Word(op).value), p_end="", fixed_width=False) for op in instr.ops])
    length = 6 + sum([len(hex(Word(op).value)) for op in instr.ops]) + \
        len(instr.ops) * 2 - 2 if len(instr.ops) > 0 else 6
    return instr_str + op_str, length


def print_queue(queue: Frontend):
    q_str, _ = queue_str(queue)
    for line in q_str:
        print(line)


def queue_str(queue: Frontend) -> tuple[list[str], list[int]]:
    q_str: list[str] = [""] * len(queue.instr_queue)
    q_lengths: list[int] = [0] * len(queue.instr_queue)
    for index, item in enumerate(queue.instr_queue):
        instr = item.instr
        q_str[index], q_lengths[index] = instruction_str(instr)
    return q_str, q_lengths


def print_prog(front: Frontend, engine: ExecutionEngine,
               breakpoints: dict, start=0, end=-1):
    prog, _ = prog_str(front, engine, breakpoints, start, end)
    for line in prog:
        print(line)


def prog_str(front: Frontend, engine: ExecutionEngine,
             breakpoints: dict, start=0, end=-1) -> tuple[list[str], list[int]]:
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
        instr_part, length = instruction_str(instr)
        prog_str[index] += instr_part
        line_lengths[index] += length
    return prog_str, line_lengths


def print_rs(engine: ExecutionEngine) -> None:
    strings, _ = rs_str(engine)
    for line in strings:
        if line != "":
            print(line)


def rs_str(engine: ExecutionEngine, show_empty=True) -> tuple[list[str], int]:

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

        instr_str, instr_length = instruction_str(slot.instr)
        instructions.append(instr_str)

        pcs.append(str(slot.pc))
        indices.append(str(i))
        status.append(f"{'☐' if slot.executing else '☑'}")

        instr_lengths.append(instr_length)

    max_instr_length = max(instr_lengths) if instr_lengths else 0
    max_pc_length = max([len(pc) for pc in pcs]) if pcs else 0
    max_index_length = max([len(index) for index in indices]) if indices else 0

    if max_index_length == 0 and max_pc_length == 0 and max_instr_length == 0:
        return [""], 0

    rs_length = max_instr_length + max_pc_length + 1 + 3 + 3 + 4
    if not show_empty:
        rs_length += max_index_length + 3

    rs_str: list[str] = []

    line_top = '╭'
    if not show_empty:
        line_top += '─' * (max_index_length + 2) + '┬'
    line_top += '─' * (max_pc_length + 2) + '┬' + '─' * (max_instr_length + 2) + '┬' + '─' * 3 + '╮'
    rs_str.append(line_top)

    for i, slot in enumerate(engine.slots()):
        if slot is None:
            if show_empty:
                rs_str.append('│' + ' ' * (max_pc_length + 2) + '│' + ' ' * (max_instr_length + 2) + '│' + ' ' * 3 + '│')
            continue
        else:
            line = '| '
            if not show_empty:
                line += ' ' * (max_index_length - len(indices[i])) + indices[i] + ' | '
            line += ' ' * (max_pc_length - len(pcs[i])) + pcs[i] + ' | '
            line += instructions[i] + ' ' * (max_instr_length - instr_lengths[i]) + ' |'
            line += f" {status[i]} |"
            rs_str.append(line)

    line_bot = '╰'
    if not show_empty:
        line_bot += '─' * (max_index_length + 2) + '┴'
    line_bot += '─' * (max_pc_length + 2) + '┴' + '─' * (max_instr_length + 2) + '┴' + '─' * 3 + '╯'
    rs_str.append(line_bot)

    return rs_str, rs_length


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


def header_pipeline(front: Frontend, engine: ExecutionEngine, breakpoints: dict):
    # calculate prog start and end
    lowest_inflight = min([slot.pc for slot in engine.slots() if slot is not None], default=0)
    highest_inflight = max([slot.pc for slot in engine.slots() if slot is not None], default=len(front.instr_list))

    prog, prog_lengths = prog_str(front, engine, breakpoints, start=lowest_inflight - 1, end=highest_inflight + 2)
    arrow = ["  ╭─► "] + ["  │   "] * (len(prog) - 2) + [" ─╯   "]
    q, q_lengths = queue_str(front)
    rs, rs_length = rs_str(engine)

    lines = max(len(prog), len(q), len(rs) - 1)

    max_prog = max(prog_lengths) if prog_lengths else 25
    max_arrow = 6
    max_q = max(q_lengths) if q_lengths else 25

    prog = [prog[i] + " " * (max_prog - prog_lengths[i])
            for i in range(len(prog))] + [" " * max_prog] * (lines - len(prog))
    arrow = arrow + [" " * max_arrow] * (lines - len(arrow))
    q = [q[i] + " " * (max_q - q_lengths[i])
         for i in range(len(q))] + [" " * max_q] * (lines - len(q))

    # TODO: check if line fits
    header_str = "-" * ceil((max_prog - len("[ Program ]")) / 2) + "[ Program ]" + "-" * floor((max_prog - len("[ Program ]")) / 2)
    header_str += "-" * max_arrow
    header_str += "-" * ceil((max_q - len("[ Queue ]")) / 2) + "[ Queue ]" + "-" * floor((max_q - len("[ Queue ]")) / 2)
    header_str += "-" * 4
    header_str += "-" * ceil((rs_length - len("[ Reservation Stations ]")) / 2) + "[ Reservation Stations ]" + "-" * floor((rs_length - len("[ Reservation Stations ]")) / 2)
    print(header_str + "-" * (columns - len(header_str)))

    print(" " * (max_prog + max_arrow + max_q + 4), end="")
    print(rs[0])

    for i in range(max(len(prog), len(q), len(rs))):
        if i < len(prog):
            print(prog[i], end="")
            print(arrow[i], end="") if len(front.instr_queue) else print(" " * max_arrow, end="")
        if i < len(q):
            print(q[i], end="")
        print("    ", end="") if i != lines // 2 or rs_length == 0 else print(" " + "─►" + " ", end="")
        if i < len(rs) - 1:
            print(rs[i + 1], end="")
        print("")
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
    header_pipeline(cpu.get_frontend(), cpu.get_exec_engine(), breakpoints)
