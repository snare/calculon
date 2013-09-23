import sys
import curses
import string
import struct
from bpython.cli import gethw

BIN_MODE_OFF = 0
BIN_MODE_WIDE = 1
BIN_MODE_NARROW = 2

BIN_MODE_WIDTH_WIDE = 84
BIN_MODE_WIDTH_NARROW = 44

BIN_FMT = '{:0=64b}'

VALUE_FORMAT_HEX = 'h'
VALUE_FORMAT_DEC = 'd'
VALUE_FORMAT_OCT = 'o'
VALUE_FORMAT_ASC = 'a'
VALUE_FORMAT_UNI = 'u'

VALUE_FORMAT_HEX_FMT = '0x{0:X}'
VALUE_FORMAT_DEC_FMT = '{0:d}'
VALUE_FORMAT_OCT_FMT = '{0:o}'

ALIGN_LEFT = 0
ALIGN_RIGHT = 1

class CalculonDisplay (object):
    def __init__(self):
        h, w = gethw()
        self.value = 0
        self.bits = 64
        self.bin_mode = BIN_MODE_NARROW
        self.value_formats = [VALUE_FORMAT_HEX, VALUE_FORMAT_DEC, VALUE_FORMAT_OCT, VALUE_FORMAT_ASC]#, VALUE_FORMAT_UNI]
        self.vars = []
        self.align = ALIGN_LEFT
        self.padding = {
            'left': 2, 'right': 2,
            'top': 2, 'bottom': 1,
            'bintop': 1, 'binbottom': 0,
            'vartop': 1, 'varbottom': 0,
            'label': 2
        }
        self.attrs = {
            'header':   curses.A_BOLD | curses.color_pair(17),
            'binlabel': curses.A_BOLD | curses.color_pair(2),
            'vallabel': curses.A_BOLD | curses.color_pair(2),
            'binval':                   curses.color_pair(3),
            'hexval':   curses.A_BOLD | curses.color_pair(8),
            'decval':   curses.A_BOLD | curses.color_pair(6),
            'octval':   curses.A_BOLD | curses.color_pair(6),
            'ascval':   curses.A_BOLD | curses.color_pair(7),
            'unival':   curses.A_BOLD | curses.color_pair(7),
        }
        self.header = 'calculon v1.0'
        self.show_header = True

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
        n += len(self.value_formats)
        # 4 lines of binary + 1 extra padding above binary
        if self.bin_mode == BIN_MODE_NARROW:
            n += 4
        elif self.bin_mode == BIN_MODE_WIDE:
            n += 2
        n += self.padding['bintop'] + self.padding['binbottom']
        # 1 per variable, and padding above variables if we have any
        if len(self.vars) > 0:
            n += self.padding['vartop'] + self.padding['varbottom']
        return n

    def num_cols(self):
        if self.bin_mode == BIN_MODE_WIDE:
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
        for fmt in self.value_formats:
            fmtd = ''
            if fmt == VALUE_FORMAT_HEX:
                fmtd = VALUE_FORMAT_HEX_FMT.format(self.value)
                attr = self.attrs['hexval']
            elif fmt == VALUE_FORMAT_DEC:
                fmtd = VALUE_FORMAT_DEC_FMT.format(self.value)
                attr = self.attrs['decval']
            elif fmt == VALUE_FORMAT_OCT:
                fmtd = VALUE_FORMAT_OCT_FMT.format(self.value)
                attr = self.attrs['octval']
            elif fmt == VALUE_FORMAT_ASC:
                s = struct.pack('Q', self.value)
                for c in s:
                    if c not in string.printable or c == '\n':
                        fmtd += '.'
                    else:
                        fmtd += c
                attr = self.attrs['ascval']
            elif fmt == VALUE_FORMAT_UNI:
                # fmtd = struct.pack('Q', self.value).decode('utf-16')
                attr = self.attrs['unival']
            if self.align == ALIGN_RIGHT:
                self.win.addstr(y, self.num_cols() - len(fmtd) - 4, fmtd, attr)
                self.win.addstr(y, self.num_cols() - self.padding['right'], fmt, self.attrs['vallabel'])
            elif self.align == ALIGN_LEFT:
                self.win.addstr(y, self.padding['left'] + len(' ' + fmt) + self.padding['label'], fmtd, attr)
                self.win.addstr(y, self.padding['left'], ' ' + fmt, self.attrs['vallabel'])
            y += 1

    def draw_binary(self):
        s = BIN_FMT.format(self.value)
        y = len(self.value_formats) + self.padding['top'] + self.padding['bintop']
        x = self.padding['left']
        p = 0
        if self.bin_mode == BIN_MODE_NARROW:
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
                self.win.addstr(y, x*2+p, s[i], self.attrs['binval'])
        elif self.bin_mode == BIN_MODE_WIDE:
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
                self.win.addstr(y, x*2+p, s[i], self.attrs['binval'])

    def draw_vars(self):
        pass

