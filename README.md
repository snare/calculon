calculon
========

A bpython-based programmer's calculator 
---------------------------------------

I haven't found many decent programmer's calculators for Mac and I spend a fair bit of time copying and pasting between Calculator.app and a python REPL, so I figured I'd have a go at writing a quick terminal-based calculator using curses.

[![calculon example](http://i.imgur.com/SkWdnld.png)](#example)

Calculon is basically a curses window tacked onto `bpython`. Type python code into the `bpython` prompt, and any sane numeric values that come out will be displayed. At this stage it's barely working, let alone complete.

Dependencies
------------

Requires `bpython`.

Installation
------------

A standard `setuptools` script is included.

    # python setup.py install


Configuration
-------------

An example config (`example.cfg`) is included with the source. Copy it to `~/.calculon/config` and edit it if you like, otherwise the defaults in the `defaults.cfg` will be used.

Usage
-----

	$ calculon

Totally doesn't support any command line args yet.

The REPL prompt is basically just `bpython`, so any python code will work. Calculon adds some top level functions for watching variables. calling the `watch()` function with a variable name (and optional output format) will add the named variable to the variable display below the binary display.

	>>> watch("somevar")
	>>> watch("anothervar", "d")

Now when these variables are updated:

	>>> somevar = 1234
	>>> anothervar = 1234

Their values will be tracked. Variables can be removed from this display with the `unwatch()` function:

	>>> unwatch("somevar")
