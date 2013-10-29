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
import os

import tokenize, token

import bpython
import bpython.cli
import bpython.args
import bpython.repl
from bpython.config import Struct
from bpython.cli import *

py3 = (sys.version_info[0] == 3)

from .display import CalculonDisplay
from .env import CONFIG
from .voltron_integration import VoltronProxy

disp = None
last_result = None
last_line = ""
repl = None


class CalculonRepl (bpython.cli.CLIRepl):
    def __new__(cls, *args, **kwargs):
        global repl
        repl = super(bpython.cli.CLIRepl, cls).__new__(cls, *args, **kwargs)
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

    # Sux to have to copy this method in here, but it's the easiest way to fix the list window position
    def show_list(self, items, topline=None, current_item=None):
        shared = Struct()
        shared.cols = 0
        shared.rows = 0
        shared.wl = 0
        y, x = self.scr.getyx()
        # offset y by the height of the calculon display. this is the only thing added to this function.
        y += disp.num_rows()
        h, w = self.scr.getmaxyx()
        down = (y < h // 2)
        if down:
            max_h = h - y
        else:
            max_h = y + 1
        max_w = int(w * self.config.cli_suggestion_width)
        self.list_win.erase()
        if items:
            sep = '.'
            if os.path.sep in items[0]:
                # Filename completion
                sep = os.path.sep
            if sep in items[0]:
                items = [x.rstrip(sep).rsplit(sep)[-1] for x in items]
                if current_item:
                    current_item = current_item.rstrip(sep).rsplit(sep)[-1]

        if topline:
            height_offset = self.mkargspec(topline, down) + 1
        else:
            height_offset = 0

        def lsize():
            wl = max(len(i) for i in v_items) + 1
            if not wl:
                wl = 1
            cols = ((max_w - 2) // wl) or 1
            rows = len(v_items) // cols

            if cols * rows < len(v_items):
                rows += 1

            if rows + 2 >= max_h:
                rows = max_h - 2
                return False

            shared.rows = rows
            shared.cols = cols
            shared.wl = wl
            return True

        if items:
            # visible items (we'll append until we can't fit any more in)
            v_items = [items[0][:max_w - 3]]
            lsize()
        else:
            v_items = []

        for i in items[1:]:
            v_items.append(i[:max_w - 3])
            if not lsize():
                del v_items[-1]
                v_items[-1] = '...'
                break

        rows = shared.rows
        if rows + height_offset < max_h:
            rows += height_offset
            display_rows = rows
        else:
            display_rows = rows + height_offset

        cols = shared.cols
        wl = shared.wl

        if topline and not v_items:
            w = max_w
        elif wl + 3 > max_w:
            w = max_w
        else:
            t = (cols + 1) * wl + 3
            if t > max_w:
                t = max_w
            w = t

        if height_offset and display_rows + 5 >= max_h:
            del v_items[-(cols * (height_offset)):]

        if self.docstring is None:
            self.list_win.resize(rows + 2, w)
        else:
            docstring = self.format_docstring(self.docstring, max_w - 2,
                max_h - height_offset)
            docstring_string = ''.join(docstring)
            rows += len(docstring)
            self.list_win.resize(rows, max_w)

        if down:
            self.list_win.mvwin(y + 1, 0)
        else:
            self.list_win.mvwin(y - rows - 2, 0)

        if v_items:
            self.list_win.addstr('\n ')

        if not py3:
            encoding = getpreferredencoding()
        for ix, i in enumerate(v_items):
            padding = (wl - len(i)) * ' '
            if i == current_item:
                color = get_colpair(self.config, 'operator')
            else:
                color = get_colpair(self.config, 'main')
            if not py3:
                i = i.encode(encoding)
            self.list_win.addstr(i + padding, color)
            if ((cols == 1 or (ix and not (ix + 1) % cols))
                    and ix + 1 < len(v_items)):
                self.list_win.addstr('\n ')

        if self.docstring is not None:
            if not py3 and isinstance(docstring_string, unicode):
                docstring_string = docstring_string.encode(encoding, 'ignore')
            self.list_win.addstr('\n' + docstring_string,
                                 get_colpair(self.config, 'comment'))
            # XXX: After all the trouble I had with sizing the list box (I'm not very good
            # at that type of thing) I decided to do this bit of tidying up here just to
            # make sure there's no unnececessary blank lines, it makes things look nicer.

        y = self.list_win.getyx()[0]
        self.list_win.resize(y + 2, w)

        self.statusbar.win.touchwin()
        self.statusbar.win.noutrefresh()
        self.list_win.attron(get_colpair(self.config, 'main'))
        self.list_win.border()
        self.scr.touchwin()
        self.scr.cursyncup()
        self.scr.noutrefresh()

        # This looks a little odd, but I can't figure a better way to stick the cursor
        # back where it belongs (refreshing the window hides the list_win)

        self.scr.move(*self.scr.getyx())
        self.list_win.refresh()


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
    for tokenType, tokenString, (startRow, startCol), (endRow, endCol), line in tokens:
        if tokenType == token.OP:
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
        proxy = VoltronProxy()
        if proxy:
            self.locals['V'] = proxy

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
    if type(varname) is str:
        disp.watch_var(varname, format)
        bpython.cli.do_resize(repl)
        repl.redraw()
        disp.redraw()
    else:
        print("Specify variable name as a string")


def unwatch(varname, format='h'):
    if type(varname) is str:
        disp.unwatch_var(varname)
        bpython.cli.do_resize(repl)
        disp.redraw()
    else:
        print("Specify variable name as a string")


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

    if 'autocomplete' in CONFIG and not CONFIG['autocomplete']:
        bpython.repl.Repl.complete = lambda s, m: None

    # run the bpython repl
    bpython.cli.main()


if __name__ == '__main__':
    main()
