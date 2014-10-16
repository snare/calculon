import Pyro4
import sys

from .env import *
from .voltron_integration import VoltronProxy
import repl

if 'bpython' in sys.modules.keys():
    # patch repl
    import bpython
    bpython.repl.Interpreter.runsource = repl.CalculonInterpreter().runsource

    # retrieve vended display object
    disp = Pyro4.Proxy(ENV['uri'])
    repl.disp = disp
    print("Connected to calculon")

    # connect to voltron
    v = VoltronProxy()