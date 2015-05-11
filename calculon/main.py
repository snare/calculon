from __future__ import print_function

import argparse
import Pyro4
import os
import code
import signal
from blessings import Terminal

import calculon
from .display import *
from .env import *
from .voltron_integration import *
from . import repl

def display():
    with HiddenCursor():
        # register resize handler
        signal.signal(signal.SIGWINCH, sigwinch_handler)

        # setup display
        disp = CalculonDisplay()

        # setup pyro
        daemon = Pyro4.Daemon()
        uri = daemon.register(disp)

        # write uri to file
        ENV.main_dir.uri.write(str(uri))

        # loop
        daemon.requestLoop()


def console():
    t = Terminal()

    # clear screen
    print(t.clear, end="")

    # retrieve vended display object
    try:
        calculon.disp = Pyro4.Proxy(ENV.main_dir.uri.content)
    except:
        print(t.bold("Failed to connect to display"))
        calculon.disp = None
    repl.disp = calculon.disp

    # connect to voltron
    try:
        calculon.V = VoltronProxy()
        calculon.V.disp = calculon.disp
        calculon.V.update_disp()
    except NameError:
        pass

    # run repl
    code.InteractiveConsole.runsource = repl.CalculonInterpreter().runsource
    code.interact(local=locals())

    # clean up
    if calculon.V:
        calculon.V._disconnect()
    if calculon.disp:
        calculon.disp._pyroRelease()


def integrated():
    pass


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='sub-command help')
    # sp = subparsers.add_parser('integrated', help='display with integrated console')
    # sp.set_defaults(func=integrated)
    sp = subparsers.add_parser('display', help='display only')
    sp.set_defaults(func=display)
    sp = subparsers.add_parser('console', help='console only')
    sp.set_defaults(func=console)
    args = parser.parse_args()
    args.func()
