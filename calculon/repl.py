from __future__ import print_function

import code
import tokenize
import token
import sys
import Pyro4
import itertools
import functools
import threading
import re
import six
from collections import defaultdict
from blessed import Terminal

import calculon
from .colour import *
from .env import *
from .voltron_integration import *
from .display import VALID_FORMATS

if sys.version_info[0] > 2:
    long = int

def constant_factory(value):
    return functools.partial(next, itertools.repeat(value))

last_result = defaultdict(constant_factory(None))
last_line = ""
repl = None
watched_exprs = []
exprs = []

t = Terminal()

lock = threading.Lock()


def warn(msg):
    sys.stderr.write("Warning: %s\n" % msg)


def safe_eval(expr):
    try:
        return expr()
    except Exception as e:
        warn(e)
        return 0


def formatter(v):
    """
    Default REPL formatter.
    """
    if config.repl_format:
        return config.repl_format.format(v=v, t=t)
    else:
        return v


def displayhook(v):
    try:
        print(formatter(v))
    except:
        print(v)

    if isinstance(v, int):
        calculon.disp.update_value(v)


class CalculonInterpreter(code.InteractiveInterpreter):
    def runsource(self, source, filename='<input>', symbol='single', encode=True):
        global last_result, last_line, repl, env

        def update_display_exprs():
            global exprs
            exprs = [(safe_eval(expr), fmt, label) for expr, fmt, label in watched_exprs]
            calculon.disp.set_exprs(exprs)

        lock.acquire()

        eval_source = True

        try:
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

            temp_stdout = None
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
                stdout = sys.stdout
                temp_stdout = six.StringIO()
                sys.stdout = temp_stdout
                self.runcode(code)
                sys.stdout = stdout

            # push functions and data into locals if they're not there
            if 'disp' not in self.locals:
                self.locals['disp'] = disp
                self.locals['swap'] = swap
                self.locals['switch'] = swap
                self.locals['_watch_expr'] = watch_expr
                self.locals['_unwatch_expr'] = unwatch_expr
                if calculon.V:
                    calculon.V.callback = update_display_exprs
                    calculon.V.start_watcher()
                    self.locals['V'] = calculon.V

            # make sure there's a valid connection to the display
            try:
                calculon.disp.are_you_there()
            except:
                # reload the environment just in case the display has been started/restarted
                env = load_env()
                calculon.disp = Pyro4.Proxy(env.main_dir.uri.content)
                try:
                    calculon.disp.are_you_there()
                except:
                    calculon.disp = None
            if calculon.V:
                calculon.V.disp = calculon.disp

            # update value from last operation
            if calculon.formatter and temp_stdout:
                try:
                    # only print with the formatter if the output is an int and nothing else
                    output = temp_stdout.getvalue().strip()
                    if output.endswith('L'):
                        output = output[:-1]
                    int(output)
                    print(calculon.formatter(self.locals['__builtins__']['_']))
                except Exception as e:
                    # otherwise just print whatever came out of `exec`
                    print(temp_stdout.getvalue(), end='')
            else:
                if temp_stdout:
                    print(temp_stdout.getvalue(), end='')
            if calculon.disp:
                try:
                    result = self.locals['__builtins__']['_']
                    if type(result) in [int, long] and result != last_result['_']:
                        calculon.disp.update_value(result)
                        last_result['_'] = result
                except KeyError as e:
                    self.locals['__builtins__']['_'] = 0

                update_display_exprs()
        finally:
            lock.release()

        return False


def watch_expr(expr, label, format='h'):
    watched_exprs.append((expr, format, label))


def unwatch_expr(idx):
    global exprs
    del watched_exprs[idx]
    del exprs[idx]
    calculon.disp.set_exprs(exprs)
    calculon.disp.redraw(True)


def swap(value):
    h = hex(value)[2:]
    h = h.replace('L', '')
    if len(h) % 2 > 0:
        h = '0' + h
    bytes = re.findall('..', h)
    bytes.reverse()
    return int(''.join(bytes), 16)
