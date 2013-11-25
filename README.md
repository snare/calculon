calculon
========

A terminal-based programmer's calculator
----------------------------------------

I haven't found many decent programmer's calculators for Mac and I spend a fair bit of time copying and pasting between Calculator.app and a Python REPL, so I figured I'd have a go at writing a quick terminal-based calculator in Python.

[![calculon example](http://i.imgur.com/SkWdnld.png)](#example)

[![calculon example2](http://ho.ax/posts/2013/10/calculon_wide.png)](#example2)

Calculon supports two modes of operation - 'integrated' and 'decoupled'. When run in integrated mode (the default), the display and an embedded REPL are displayed in a single terminal session. The embedded REPL is a standard Python console provided by the `code` module. Decoupled mode allows you to run the display and REPL in different terminal sessions. The advantage of this mode is that you can also use `bpython` (or possibly other REPLs with some hacking) as the REPL to talk to the `calculon` display.

Dependencies
------------

Calculon requires the `Pyro4`, `blessings` and `rl` modules. They will be automatically installed by the `setup.py` script.

To use `bpython` as the REPL you will obviously have to have `bpython` installed.

Installation
------------

A standard `setuptools` script is included.

    # python setup.py install


Configuration
-------------

An example config (`example.cfg`) is included with the source. Copy it to `~/.calculon/config` and edit it if you like, otherwise the defaults in the `defaults.cfg` will be used.

Usage
-----

To run `calculon` in integrated mode:

	$ calculon

To run the display in decoupled mode:

	$ calculon display

To run the embedded REPL in decoupled mode:

	$ calculon console

To connect to the display from within a `bpython` instance:

	$ bpython
	>>> import calculon.load

From here, any Python code entered into the REPL that results in a numeric value will be rendered in the display. For example:

	>>> 1234 + 1234
	2468

2468 will be rendered in the display.

Calculon adds some top level functions to the REPL for watching variables. Calling the `watch()` function with a variable name (and optional output format) will add the named variable to the variable display below the binary display.

	>>> watch("somevar")
	>>> watch("anothervar", "d")

Now when these variables are updated:

	>>> somevar = 1234
	>>> anothervar = 1234

Their values will be tracked. Variables can be removed from this display with the `unwatch()` function:

	>>> unwatch("somevar")

Calculon now has support to connect to [voltron](https://github.com/snarez/voltron) and inspect register state. If you have the most recent version of calculon and voltron, and voltron is running, calculon will connect to it at startup. Calculon can manually connect and disconnect from voltron as follows:

	>>> V.connect()
	Connected to voltron
	>>> V.disconnect()
	Disconnected from voltron

When connected to voltron, calculon can inspect registers:

	>>> V.rip
	4294971201

Or memory:

    >>> V[V.rbp]
    'x'
    >>> V[V.rbp:V.rbp + 32]
    'x\xee\xbf_\xff\x7f\x00\x00\xfd\xf5\xad\x85\xff\x7f\x00\x00'


Credits
-------
[richo](https://github.com/richo) deserves many beers for his efforts