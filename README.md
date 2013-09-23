calculon
========

A bpython-based programmer's calculator 
---------------------------------------

I haven't found many decent programmer's calculators for Mac and I spend a fair bit of time copying and pasting between Calculator.app and a python REPL, so I figured I'd have a go at writing a quick terminal-based calculator using curses.

Calculon is basically a curses window tacked onto `bpython`. Type python code into the `bpython` prompt, and any sane numeric values that come out will be displayed. At this stage it's barely working, let alone complete.

Dependencies
------------

Requires `bpython`.

Installation
------------

A standard `setuptools` script is included.

    # python setup.py install

