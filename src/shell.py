from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from logging import raiseExceptions
from os import system

from src import ui
from src.cpu import CPU
# from src.execution import ExecutionEngine
# from src.bpu import BPU
# from src.mmu import MMU
# from src.frontend import Frontend
# from src.cache import Cache
# from src.parser import Parser
# from src.byte import Byte
# from src.word import Word

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
        # TODO: pass optionally a range of memory to show
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
