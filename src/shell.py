from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from logging import raiseExceptions
from os import system

from src import ui
# from src.cpu import CPU
from src.execution import ExecutionEngine
# from src.bpu import BPU
from src.mmu import MMU
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
def __show(input):
    '''
    {"mem": None, "cache": None, "regs": None, "queue": None, "rs": None, "prog": None}
    '''
    raiseExceptions(NotImplementedError)


@func
def __continue(input):
    raiseExceptions(NotImplementedError)


@func
def __step(input):
    raiseExceptions(NotImplementedError)


@func
def __break(input):
    '''
    {"add": None, "delete": None, "delete": None, "toogle": None, "list": None}
    '''
    raiseExceptions(NotImplementedError)


@func
def __clear(input):
    system('clear')
    return


@func
def __exit(input):
    exit()


@func
def __(input):
    ui.all_headers(engine)


def __not_found(input):
    print('Your input did not match any known command')


completer = NestedCompleter.from_nested_dict(completions)

engine = ExecutionEngine(MMU())

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
        funcs.get(text.split()[0], __not_found)(text.split()[1:])
