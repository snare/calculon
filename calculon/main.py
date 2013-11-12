import argparse
import curses
import Pyro4
import os
import code

from .display import CalculonDisplay
from .env import *
from .voltron_integration import VoltronProxy
import repl

def display():
    # setup display
    disp = CalculonDisplay()

    # setup pyro
    daemon = Pyro4.Daemon()
    uri = daemon.register(disp)

    # write uri to file
    write_uri(uri)

    # loop
    daemon.requestLoop()


def console():
    # retrieve vended display object
    disp = Pyro4.Proxy(CALCULON_URI)
    repl.disp = disp

    # run repl
    code.InteractiveConsole.runsource = repl.CalculonInterpreter.runsource.im_func
    code.interact(local=locals())


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='sub-command help')
    sp = subparsers.add_parser('display', help='display help')
    sp.set_defaults(func=display)
    sp = subparsers.add_parser('console', help='display help')
    sp.set_defaults(func=console)
    args = parser.parse_args()
    args.func()
