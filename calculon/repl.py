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
from .display import VALID_FORMATS

CALCULON_HISTORY = os.path.join(ENV.dir, 'history')

def constant_factory(value):
    return itertools.repeat(value).next

disp = None
last_result = defaultdict(constant_factory(None))
last_line = ""
repl = None
watched_exprs = []

def warn(msg):
    sys.stderr.write("Warning: %s\n" % msg)

def safe_eval(expr):
    try:
        return expr()
    except Exception as e:
        warn(e)
        return 0


class CalculonInterpreter(code.InteractiveInterpreter):
    def runsource(self, source, filename='<input>', symbol='single', encode=True):
        global disp, last_result, last_line, repl
        eval_source = True

        # if the code starts with an operator, prepend the _ variable
        tokens = tokenize.generate_tokens(lambda: source)
        for tokenType, tokenString, (startRow, startCol), (endRow, endCol), line in tokens:
            if tokenType == token.OP:
                source = '_ ' + source
            elif tokenType == token.NAME and tokenString == 'watch':
                toks = source.split()
                if len(toks) == 1:
                    warn("syntax: watch [as <format>] <expression>")
                    return False

                # Special case `watch as d <expr>
                if toks[1] == "as":
                    if len(toks) < 4:
                        warn("syntax: watch [as <format>] <expression>")
                        return False
                    fmt = toks[2]
                    toks = toks[3:]
                else:
                    fmt = 'h'
                    toks = toks[1:]

                if fmt not in VALID_FORMATS:
                    warn("invalid format: %s" % fmt)
                    return False


                # We handle our code here, so we don't need to actually let the
                # backend poke anything
                expr = ' '.join(toks)
                try:
                    thunk = eval("lambda: %s" % expr, self.locals)
                    thunk()
                except Exception as e:
                    warn(str(e))
                    return False

                watch_expr(thunk, expr, fmt)
                eval_source = False
            elif tokenType == token.NAME and tokenString == 'unwatch':
                toks = source.split()
                if len(toks) != 2:
                    warn("syntax: unwatch <expression ID>")
                    return False
                try:
                    exprid = int(toks[1])
                except ValueError:
                    warn("syntax: unwatch <expression ID>")
                    return False
                unwatch_expr(exprid)
                eval_source = False
            break

        # if we got an empty source line, re-evaluate the last line
        if len(source) == 0:
            source = last_line
        else:
            last_line = source

        if eval_source:
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
        if '_watch' not in self.locals:
            self.locals['switch'] = switch
            self.locals['disp'] = disp
            self.locals['_watch_expr'] = watch_expr
            self.locals['_unwatch_expr'] = unwatch_expr
            proxy = VoltronProxy()
            if proxy:
                self.locals['V'] = proxy

        # update value from last operation
        try:
            result = self.locals['__builtins__']['_']
            if type(result) in [int, long] and result != last_result['_']:
                disp.update_value(result)
                last_result['_'] = result
        except KeyError as e:
            self.locals['__builtins__']['_'] = 0

        disp.set_exprs([(safe_eval(expr), fmt, label) for expr, fmt, label in watched_exprs])

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


def watch_expr(expr, label, format='h'):
    watched_exprs.append((expr, format, label))

def unwatch_expr(idx):
    del watched_exprs[idx]

def switch(value):
    h = hex(value)[2:]
    h = h.replace('L', '')
    if len(h) % 2 > 0:
        h = '0' + h
    bytes = re.findall('..', h)
    bytes.reverse()
    return int(''.join(bytes), 16)
