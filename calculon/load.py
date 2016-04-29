import Pyro4
import sys

import calculon
from .env import *
from .voltron_integration import *
import repl

if 'bpython' in sys.modules.keys():
    # patch repl
    import bpython
    bpython.repl.Interpreter.runsource = repl.CalculonInterpreter().runsource

    # retrieve vended display object
    calculon.disp = Pyro4.Proxy(env.main_dir.uri.content)
    repl.disp = calculon.disp
    print("Connected to calculon")

    # connect to voltron
    try:
        calculon.V = VoltronProxy()
        calculon.V.disp = calculon.disp
        calculon.formatter = None
    except NameError:
        pass
