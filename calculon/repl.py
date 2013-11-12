import rl
import curses
import code
import os
import tokenize, token
import sys
from collections import defaultdict

from .colour import *
from .env import *
from .voltron_integration import VoltronProxy

CALCULON_HISTORY = os.path.join(CALCULON_DIR, 'history')

disp = None
last_result = defaultdict(constant_factory(None))
last_line = ""
repl = None

class CalculonInterpreter(code.InteractiveInterpreter):
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
