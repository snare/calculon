import rl
import curses
import code
import os
import tokenize, token
import sys
import Pyro4
import itertools
import re
from collections import defaultdict

from .colour import *
from .env import *
from .voltron_integration import VoltronProxy

CALCULON_HISTORY = os.path.join(ENV.dir, 'history')

def constant_factory(value):
    return itertools.repeat(value).next

disp = None
last_result = defaultdict(constant_factory(None))
last_line = ""
repl = None

class CalculonInterpreter(code.InteractiveInterpreter):
    def runsource(self, source, filename='<input>', symbol='single', encode=True):
        global disp, last_result, last_line, repl

        # if the code starts with an operator, prepend the _ variable
        tokens = tokenize.generate_tokens(lambda: source)
        for tokenType, tokenString, (startRow, startCol), (endRow, endCol), line in tokens:
            if tokenType == token.OP:
                source = '_ ' + source
            break

        # if we got an empty source line, re-evaluate the last line
        if len(source) == 0:
            source = last_line
        else:
            last_line = source

        # compile code
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
            self.locals['switch'] = switch
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
        for varname in disp.get_var_names():
            try:
                result = self.locals[varname]
                if type(result) in [int, long] and result != last_result[varname]:
                    disp.update_value(result, varname)
                    last_result[varname] = result
            except KeyError:
                pass

        return False


class Repl(object):
    def __init__(self, scr, offset=0):
        # set up windows
        self.scr = scr
        h,w = self.scr.getmaxyx()
        self.win = curses.newwin(h - 1 - offset, w, offset, 0)
        self.win.scrollok(True)
        self.win.keypad(1)

        # set up line editor
        # rl.history.read_file(CONSOLE_HISTORY)
        self.lastbuf = None

        # create interpreter object
        self.interp = code.InteractiveInterpreter()

        # set prompt
        self.update_prompt()


    def run(self):
        while 1:
            # read the next line
            try:
                line = raw_input(self.prompt.encode(sys.stdout.encoding))
            except EOFError:
                break
            self.interp.runsource(line)
            rl.readline.write_history_file(CALCULON_HISTORY)

    def update_prompt(self):
        self.prompt = self.process_prompt(CONFIG['prompt'])

    def process_prompt(self, prompt):
        return self.escape_prompt(prompt['format'].format(**FMT_ESCAPES))

    def escape_prompt(self, prompt, start = "\x01", end = "\x02"):
        escaped = False
        result = ""
        for c in prompt:
            if c == "\x1b" and not escaped:
                result += start + c
                escaped = True
            elif c.isalpha() and escaped:
                result += c + end
                escaped = False
            else:
                result += c
        return result


def watch(varname, format='h'):
    if type(varname) is str:
        if varname not in disp.get_var_names():
            disp.watch_var(varname, format)
            disp.redraw()
        else:
            print("Variable '%s' is already being watched" % varname)
    else:
        print("Specify variable name as a string")


def unwatch(varname, format='h'):
    if type(varname) is str:
        if varname not in disp.get_var_names():
            disp.unwatch_var(varname)
            disp.redraw()
        else:
            print("Variable '%s' is already being watched" % varname)
    else:
        print("Specify variable name as a string")


def switch(value):
    h = hex(value)[2:]
    if len(h) % 2 > 0:
        h = '0' + h
    bytes = re.findall('..', h)
    bytes.reverse()
    return int(''.join(bytes), 16)
