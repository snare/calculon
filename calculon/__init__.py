import sys

from .main import *
from .display import *
from .env import *

import repl

if __name__ == "calculon":
    if 'bpython' in sys.modules.keys():
        # patch repl
        import bpython
        bpython.repl.Interpreter.runsource = repl.CalculonInterpreter.runsource.im_func

        # retrieve vended display object
        disp = Pyro4.Proxy(CALCULON_URI)
        repl.disp = disp
