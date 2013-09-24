import sys
import curses
import locale
from locale import LC_ALL, setlocale
import signal
from types import ModuleType
import code

import bpython
import bpython.cli
import bpython.args
import bpython.repl
from bpython.cli import *

from .display import CalculonDisplay

disp = None
last_result = None


def do_resize(caller):
    h, w = gethw()
    if not h:
        return

    curses.endwin()
    os.environ["LINES"] = str(h-disp.num_lines())
    os.environ["COLUMNS"] = str(w)
    curses.doupdate()
    bpython.cli.DO_RESIZE = False

    caller.resize()


def init_wins(scr, config):
    global disp

    # get background colour and dimensions
    background = get_colpair(config, 'background')
    h, w = gethw()

    # setup display window for calculon
    disp = CalculonDisplay()
    dh = disp.num_rows()
    display_win = newwin(background, dh, w, 0, 0)
    display_win.keypad(1)
    disp.set_win(display_win)
    disp.update_value(0)

    # setup REPL window
    main_win = newwin(background, h - 1 - dh, w, dh, 0)
    main_win.scrollok(True)
    main_win.keypad(1)

    # setup status bar
    statusbar = Statusbar(scr, main_win, background, config,
        " <%s> Rewind  <%s> Save  <%s> Pastebin  <%s> Pager  <%s> Show Source " %
            (config.undo_key, config.save_key,
             config.pastebin_key, config.last_output_key,
             config.show_source_key),
            get_colpair(config, 'main'))

    return main_win, statusbar


def runsource(self, source, filename='<input>', symbol='single', encode=True):
    global disp, last_result

    if encode:
        source = '# coding: %s\n%s' % (self.encoding, source.encode(self.encoding))

    try:
        code = self.compile(source, filename, symbol)
    except (OverflowError, SyntaxError, ValueError):
        self.showsyntaxerror(filename)
        return False
    if code is None:
        return True

    self.runcode(code)

    try:
        result = self.locals['__builtins__']['_']
        if type(result) in [int, long] and result != last_result:
            disp.update_value(result)
            last_result = result
    except KeyError:
        pass

    return False


# Get rid of annoying completion in the repl
bpython.repl.Repl.complete = lambda s, m: None

def main(args=None, locals_=None, banner=None):
    # this is kinda hacky, but bpython doesn't play well with others
    bpython.cli.init_wins = init_wins
    bpython.cli.do_resize = do_resize
    bpython.repl.Interpreter.runsource = runsource
    bpython.cli.main()


if __name__ == '__main__':
    main()
