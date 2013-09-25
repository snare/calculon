import sys
import curses
import string
import struct

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

    def __init__(self, h, w):
        self.config = self.init_config(CONFIG)
        self.bits = self.config['bits']
        self.bin_mode = self.config['bin_mode']
        self.formats = self.config['formats']
        self.align = self.config['align']
        self.padding = self.config['padding']
        self.attrs = self.config['attrs']

        self.header = 'calculon v1.0'
        self.show_header = True
        self.vars = {}
        self.vars['_'] = 0
        self.var_fmt = {}
        self.var_names = []
        for var in self.config['variables']:
            self.watch_var(var, self.config['variables'][var]['format'])

    def init_config(self, config):
        # update curses text attributes
        for sec in config['attrs']:
            attrs = 0
            for attr in config['attrs'][sec]['attrs']:
                attrs |= CURSES_ATTRS[attr]
            attrs |= curses.color_pair(config['attrs'][sec]['colour_pair'])
            config['attrs'][sec] = attrs
        return config

    def set_win(self, win, repl_win):
        self.win = win
        self.repl_win = repl_win
        self.update_value(0)
        self.redraw()

    def update_value(self, value, name=None):
        if name == None:
            self.vars['_'] = value
        else:
            self.vars[name] = value
        self.redraw()

    def watch_var(self, varname, format):
        self.var_fmt[varname] = format
        self.vars[varname] = 0
        self.var_names.append(varname)

    def unwatch_var(self, varname):
        del self.var_fmt[varname]
        del self.vars[varname]
        self.var_names.remove(varname)

    def redraw(self):
        self.resize()
        self.win.clear()
        self.draw_header()
        self.draw_value()
        self.draw_binary()
        self.draw_vars()
        self.win.refresh()
        self.repl_win.refresh()

    def resize(self):
        self.win.resize(self.num_rows(), self.num_cols())

    def num_rows(self):
        return self.offset_vars() + self.num_rows_vars() + self.padding['bottom']

    def num_cols(self):
        if self.bin_mode == "wide":
            c = BIN_MODE_WIDTH_WIDE + self.padding['left'] + self.padding['right']
        else:
            c = BIN_MODE_WIDTH_NARROW + self.padding['left'] + self.padding['right']
        return c

    def num_rows_val(self):
        return len(filter(lambda x: x in VALID_FORMATS and x != 'b', self.formats))

    def num_rows_bin(self):
        if self.bin_mode == "narrow":
            n = 4
        elif self.bin_mode == "wide":
            n = 2
        return n + self.padding['bintop'] + self.padding['binbottom']

    def num_rows_vars(self):
        n = len(self.var_fmt)
        if n > 0:
            n += self.padding['vartop'] + self.padding['varbottom']
        return n

    def offset_val(self):
        return self.padding['top']

    def offset_bin(self):
        return self.offset_val() + self.num_rows_val()

    def offset_vars(self):
        return self.offset_bin() + self.num_rows_bin()

    def draw_header(self):
        if self.show_header:
            head = self.header + ' ' * (self.num_cols() - len(self.header))
            self.win.addstr(0, 0, head, self.attrs['header'])

    def draw_value(self, varname=None):
        y = self.padding['top']
        for fmt in filter(lambda x: x in VALID_FORMATS and x != 'b', self.formats):
            self.draw_value_at_row(self.vars['_'], fmt, y)
            y += 1

    def draw_value_at_row(self, value, fmt, row, label=None):
        fmtd = ''
        if fmt in ['h', 'd', 'o']:
            fmtd = BASE_FMT[fmt].format(value)
            attr = self.attrs[fmt + 'val']
        elif fmt == 'a':
            s = struct.pack('Q', value)
            for c in s:
                if c not in string.printable or c == '\n':
                    fmtd += '.'
                else:
                    fmtd += c
            attr = self.attrs['aval']
        elif fmt == 'u':
            # fmtd = struct.pack('Q', value).decode('utf-16')
            attr = self.attrs['uval']
        if self.align == 'right':
            self.win.addstr(row, self.num_cols() - len(fmtd) - 4, fmtd, attr)
            self.win.addstr(row, self.num_cols() - self.padding['right'], fmt, self.attrs['vallabel'])
        elif self.align == 'left':
            self.win.addstr(row, self.padding['left'] + len(' ' + fmt) + self.padding['label'], fmtd, attr)
            self.win.addstr(row, self.padding['left'], ' ' + fmt, self.attrs['vallabel'])
            if label != None:
                self.win.addstr(row, self.num_cols() - self.padding['right'] - len(label), label, self.attrs['vallabel'])

    def draw_binary(self):
        s = BASE_FMT['b'].format(self.vars['_'])
        y = len(filter(lambda x: x in VALID_FORMATS and x != 'b', self.formats)) + self.padding['top'] + self.padding['bintop']
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
        y = self.offset_vars() + self.padding['vartop']
        x = self.padding['left']
        for var in self.var_names:
            self.draw_value_at_row(self.vars[var], self.var_fmt[var], y, var)
            y += 1

