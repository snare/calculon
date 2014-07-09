from __future__ import print_function

import argparse
import Pyro4
import os
import code
from blessings import Terminal

from .display import *
from .env import *
from .voltron_integration import VoltronProxy
import repl

def display():
    with HiddenCursor():
        # setup display
        disp = CalculonDisplay()

        # setup pyro
        daemon = Pyro4.Daemon()
        uri = daemon.register(disp)

        # write uri to file
        ENV.write_file('uri', str(uri))

        # loop
        daemon.requestLoop()


def console():
    t = Terminal()

    # clear screen
    print(t.clear, end="")

    # retrieve vended display object
    try:
        disp = Pyro4.Proxy(ENV['uri'])
    except:
        print(t.bold("Failed to connect to display"))
        disp = None
    repl.disp = disp
    
    # connect to voltron
    v = VoltronProxy()

    # run repl
    code.InteractiveConsole.runsource = repl.CalculonInterpreter.runsource.im_func
    code.interact(local=locals())


def integrated():
    pass


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='sub-command help')
    sp = subparsers.add_parser('integrated', help='display with integrated console')
    sp.set_defaults(func=integrated)
    sp = subparsers.add_parser('display', help='display only')
    sp.set_defaults(func=display)
    sp = subparsers.add_parser('console', help='console only')
    sp.set_defaults(func=console)
    args = parser.parse_args()
    args.func()
