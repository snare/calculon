import sys
import curses
import locale
from locale import LC_ALL, setlocale
import signal
from types import ModuleType
import code
from collections import defaultdict
import itertools
import types

import bpython
import bpython.cli
import bpython.args
import bpython.repl

from .display import CalculonDisplay

disp = None
last_result = None
last_line = ""
repl = None


class CalculonRepl (CLIRepl):
    def __new__(cls, *args, **kwargs):
        global repl
        repl = super(CLIRepl, cls).__new__(cls, *args, **kwargs)
        return repl

    def resize(self):
        global disp
        """This method exists simply to keep it straight forward when
        initialising a window and resizing it."""
        self.size()
        self.scr.erase()
        self.scr.resize(self.h - disp.num_rows(), self.w)
        self.scr.mvwin(self.y + disp.num_rows(), self.x)
        self.statusbar.resize(refresh=False)
        self.redraw()
        disp.redraw()


def init_wins(scr, config):
    global disp

    # get background colour and dimensions
    background = bpython.cli.get_colpair(config, 'background')
    h, w = bpython.cli.gethw()

    # setup display object and calculate height
    disp = CalculonDisplay(h, w)
    dh = disp.num_rows()

    # setup REPL window
    main_win = bpython.cli.newwin(background, h - 1 - dh, w, dh, 0)
    main_win.scrollok(True)
    main_win.keypad(1)

    # set up display window
    display_win = bpython.cli.newwin(background, dh, w, 0, 0)
    display_win.keypad(1)
    disp.set_win(display_win, main_win)
    disp.update_value(0)

    # setup status bar
    statusbar = bpython.cli.Statusbar(scr, main_win, background, config,
        " <%s> Rewind  <%s> Save  <%s> Pastebin  <%s> Pager  <%s> Show Source " %
            (config.undo_key, config.save_key,
             config.pastebin_key, config.last_output_key,
             config.show_source_key),
            bpython.cli.get_colpair(config, 'main'))

    return main_win, statusbar


def runsource(self, source, filename='<input>', symbol='single', encode=True):
    global disp, last_result, last_line, repl

    # if the code starts with an operator, prepend the _ variable
    for op in ['-','+','*','/','^','|','&','<','>']:
        if source.startswith(op):
            source = '_ ' + source
            break

    # if we got an empty source line, re-evaluate the last line
    if len(source) == 0:
        source = last_line
    else:
        last_line = source

    # this is from bpython
    if encode:
        source = '# coding: %s\n%s' % (self.encoding, source.encode(self.encoding))

    # so is this
    try:
        code = self.compile(source, filename, symbol)
    except (OverflowError, SyntaxError, ValueError):
        self.showsyntaxerror(filename)
        return False
    if code is None:
        return True

    # if we got a valid code object, run it
    self.runcode(code)

    # push functions and data into locals if they're not there
    if 'watch' not in self.locals:
        self.locals['watch'] = watch
        self.locals['unwatch'] = unwatch
        self.locals['vars'] = disp.vars
        self.locals['repl'] = repl
        self.locals['disp'] = disp

    # update value from last operation
    try:
        result = self.locals['__builtins__']['_']
        if type(result) in [int, long] and result != last_result['_']:
            disp.update_value(result)
            last_result['_'] = result
    except KeyError, e:
        self.locals['__builtins__']['_'] = 0

    # update values of variables
    for varname in disp.var_names:
        try:
            result = self.locals[varname]
            if type(result) in [int, long] and result != last_result[varname]:
                disp.update_value(result, varname)
                last_result[varname] = result
        except KeyError:
            pass

    return False


def watch(varname, format='h'):
    disp.watch_var(varname, format)
    bpython.cli.do_resize(repl)
    repl.redraw()
    disp.redraw()


def unwatch(varname, format='h'):
    disp.unwatch_var(varname)
    bpython.cli.do_resize(repl)
    disp.redraw()


def constant_factory(value):
    return itertools.repeat(value).next


def main():
    global last_result

    last_result = defaultdict(constant_factory(None))

    # this is kinda hacky, but bpython doesn't play well with others
    # monkey magic!
    bpython.cli.init_wins = init_wins
    bpython.repl.Interpreter.runsource = runsource
    bpython.cli.CLIRepl = CalculonRepl

    # disable autocomplete, otherwise it appears over the main display
    # might fix this later and add a config option to enable/disable 
    bpython.repl.Repl.complete = lambda s, m: None

    # run the bpython repl
    bpython.cli.main()


if __name__ == '__main__':
    main()
