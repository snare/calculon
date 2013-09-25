import sys
import curses
import string
import struct
from bpython.cli import gethw

from .env import CONFIG

BIN_MODE_WIDTH_WIDE = 84
BIN_MODE_WIDTH_NARROW = 44

BASE_FMT = {
    'h': '0x{0:X}',
    'd': '{0:d}',
    'o': '{0:o}',
    'b': '{:0=64b}'
}

CURSES_ATTRS = {
    "altcharset": curses.A_ALTCHARSET,
    "blink": curses.A_BLINK,
    "bold": curses.A_BOLD,
    "dim": curses.A_DIM,
    "normal": curses.A_NORMAL,
    "reverse": curses.A_REVERSE,
    "standout": curses.A_STANDOUT,
    "underline": curses.A_UNDERLINE,
}

VALID_FORMATS = ['h','d','o','a','u','b']

class CalculonDisplay (object):
    def __init__(self):
        self.config = self.init_config(CONFIG)
        h, w = gethw()
        self.value = 0
        self.bits = self.config['bits']
        self.bin_mode = self.config['bin_mode']
        self.formats = self.config['formats']
        self.vars = self.config['variables']
        self.align = self.config['align']
        self.padding = self.config['padding']
        self.attrs = self.config['attrs']
        self.header = 'calculon v1.0'
        self.show_header = True

    def init_config(self, config):
        # update curses text attributes
        for sec in config['attrs']:
            attrs = 0
            for attr in config['attrs'][sec]['attrs']:
                attrs |= CURSES_ATTRS[attr]
            attrs |= curses.color_pair(config['attrs'][sec]['colour_pair'])
            config['attrs'][sec] = attrs
        return config

    def set_win(self, win):
        self.win = win
        self.redraw()

    def update_value(self, value, name=None):
        if name == None:
            self.value = value
        else:
            self.vars[name] = value
        self.redraw()

    def redraw(self):
        self.resize()
        self.win.clear()
        self.draw_header()
        self.draw_value()
        self.draw_binary()
        self.draw_vars()
        self.win.refresh()

    def resize(self):
        self.win.resize(self.num_rows(), self.num_cols())

    def num_rows(self):
        # top and bottom padding
        n = self.padding['top'] + self.padding['bottom']
        # 1 per value format
        n += len(self.formats)
        # 4 lines of binary + 1 extra padding above binary
        if self.bin_mode == "narrow":
            n += 4
        elif self.bin_mode == "wide":
            n += 2
        n += self.padding['bintop'] + self.padding['binbottom']
        # 1 per variable, and padding above variables if we have any
        if len(self.vars) > 0:
            n += self.padding['vartop'] + self.padding['varbottom']
        return n

    def num_cols(self):
        if self.bin_mode == "wide":
            c = BIN_MODE_WIDTH_WIDE + self.padding['left'] + self.padding['right']
        else:
            c = BIN_MODE_WIDTH_NARROW + self.padding['left'] + self.padding['right']
        return c

    def draw_header(self):
        if self.show_header:
            head = self.header + ' ' * (self.num_cols() - len(self.header))
            self.win.addstr(0, 0, head, self.attrs['header'])

    def draw_value(self):
        y = self.padding['top']
        for fmt in filter(lambda x: x in VALID_FORMATS and x != 'b', self.formats):
            fmtd = ''
            if fmt in ['h', 'd', 'o']:
                fmtd = BASE_FMT[fmt].format(self.value)
                attr = self.attrs[fmt + 'val']
            elif fmt == 'a':
                s = struct.pack('Q', self.value)
                for c in s:
                    if c not in string.printable or c == '\n':
                        fmtd += '.'
                    else:
                        fmtd += c
                attr = self.attrs['aval']
            elif fmt == 'u':
                # fmtd = struct.pack('Q', self.value).decode('utf-16')
                attr = self.attrs['uval']
            if self.align == 'right':
                self.win.addstr(y, self.num_cols() - len(fmtd) - 4, fmtd, attr)
                self.win.addstr(y, self.num_cols() - self.padding['right'], fmt, self.attrs['vallabel'])
            elif self.align == 'left':
                self.win.addstr(y, self.padding['left'] + len(' ' + fmt) + self.padding['label'], fmtd, attr)
                self.win.addstr(y, self.padding['left'], ' ' + fmt, self.attrs['vallabel'])
            y += 1

    def draw_binary(self):
        s = BASE_FMT['b'].format(self.value)
        y = len(self.formats) + self.padding['top'] + self.padding['bintop']
        x = self.padding['left']
        p = 0
        if self.bin_mode == 'narrow':
            left = ['63', '47', '31', '15']
            right = ['48', '32', '16', '0']
            for i in range(4):
                self.win.addstr(y + i, self.padding['left'], left[i], self.attrs['binlabel'])
                self.win.addstr(y + i, self.num_cols() - self.padding['right'] - 2, right[i], self.attrs['binlabel'])
            for i in xrange(len(s)):
                if i != 0 and i % 16 == 0:
                    y += 1
                    x = self.padding['left']
                    p = 0
                elif i != 0 and i % 8 == 0:
                    p += 3
                elif i != 0 and i % 4 == 0:
                    p += 1
                x += 1
                self.win.addstr(y, x*2+p, s[i], self.attrs['bval'])
        elif self.bin_mode == 'wide':
            left = ['63', '31']
            right = ['32', '0']
            for i in range(2):
                self.win.addstr(y + i, self.padding['left'], left[i], self.attrs['binlabel'])
                self.win.addstr(y + i, self.num_cols() - self.padding['right'] - 2, right[i], self.attrs['binlabel'])
            for i in xrange(len(s)):
                if i != 0 and i % 32 == 0:
                    y += 1
                    x = self.padding['left']
                    p = 0
                elif i != 0 and i % 8 == 0:
                    p += 3
                elif i != 0 and i % 4 == 0:
                    p += 1
                x += 1
                self.win.addstr(y, x*2+p, s[i], self.attrs['bval'])

    def draw_vars(self):
        pass

