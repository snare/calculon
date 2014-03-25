import sys
import string
import struct
import Pyro4
import os
import time
from blessings import Terminal

from .env import *

BIN_MODE_WIDTH_WIDE = 84
BIN_MODE_WIDTH_NARROW = 44
BIN_MODE_ROW_WIDE = 32
BIN_MODE_ROW_NARROW = 16

BASE_FMT = {
    'h': '0x{0:X}',
    'd': '{0:d}',
    'o': '{0:o}',
    'b': '{:0=%db}'
}

VALID_FORMATS = ['h','d','o','a','u','b']

# this kinda sucks, maybe do it without system
class HiddenCursor(object):
    def __enter__(self):
        os.system('tput civis')

    def __exit__(self, type, value, traceback):
        os.system('tput cnorm')


class CalculonDisplay (object):
    def __init__(self):
        self.term = Terminal()
        print(self.term.enter_fullscreen())

        # parse config
        self.config = self.init_config(CONFIG)
        self.bin_mode = self.config['bin_mode']
        self.cur_bin_mode = None
        self.bits = self.config['bits']
        self.formats = self.config['formats']
        self.align = self.config['align']
        self.padding = self.config['padding']
        self.attrs = self.config['attrs']

        self.header = 'calculon v1.0'
        self.show_header = True

        # Watched variables
        self.lastval = 0

        # Watched expressions
        self.exprs = []

        self.draw_state = {
            'header': True, 'value': True, 'vallabel': True, 'binlabel': True,
            'varlabel': True, 'varvalue': True, 'exprlabel': True, 'exprvalue': True,
            'all': True
        }

        # set initial value
        self.update_value(0)

    def init_config(self, config):
        # update text attributes
        for sec in config['attrs']:
            config['attrs'][sec] = ''.join(['{t.' + x + '}' for x in config['attrs'][sec]])

        return config

    def set_win(self, win, repl_win):
        self.win = win
        self.repl_win = repl_win
        self.update_value(0)
        self.redraw()

    def update_bin_mode(self):
        # detect bin display mode
        old_mode = self.cur_bin_mode
        if self.bin_mode == "auto":
            self.cur_bin_mode = "wide" if self.term.width >= BIN_MODE_WIDTH_WIDE else "narrow"
        if self.cur_bin_mode != old_mode:
            self.draw_state['all'] = True

        # round up bits to nearest row
        self.bin_row = BIN_MODE_ROW_NARROW if self.cur_bin_mode == "narrow" else BIN_MODE_ROW_WIDE
        if self.bits % self.bin_row > 0:
            self.bits += self.bin_row - (self.bits % self.bin_row)

    def update_value(self, value):
        self.lastval = value
        self.draw_state['value'] = True
        self.redraw()

    def set_exprs(self, values):
        self.exprs = values
        self.draw_state['exprvalue'] = True
        self.draw_state['exprlabel'] = True
        self.redraw()

    def redraw(self, all=False):
        self.update_bin_mode()
        if self.draw_state['all']:
            print(self.term.clear())
        if self.draw_state['header'] or self.draw_state['all']:
            self.draw_header()
            self.draw_state['header'] = False
        if self.draw_state['value'] or self.draw_state['all']:
            self.clear_value()
            self.draw_value()
            self.draw_binary()
            self.draw_state['value'] = False
        if self.draw_state['vallabel'] or self.draw_state['all']:
            self.draw_value_labels()
            self.draw_binary_labels()
            self.draw_state['vallabel'] = False
        if self.draw_state['exprlabel'] or self.draw_state['all']:
            self.draw_expr_labels()
            self.draw_state['exprlabel'] = False
        if self.draw_state['exprvalue'] or self.draw_state['all']:
            self.clear_exprs()
            self.draw_exprs()
            self.draw_state['exprvalue'] = False
        self.draw_state['all'] = False

    def get_value_formats(self):
        return filter(lambda x: x in VALID_FORMATS and x != 'b', self.formats)

    def num_rows(self):
        return self.offset_exprs() + self.num_rows_exprs() + self.padding['bottom']

    def num_cols(self):
        if self.cur_bin_mode == "wide":
            c = BIN_MODE_WIDTH_WIDE + self.padding['left'] + self.padding['right']
        else:
            c = BIN_MODE_WIDTH_NARROW + self.padding['left'] + self.padding['right']
        return c

    def num_rows_val(self):
        return len(self.get_value_formats())

    def num_rows_bin(self):
        return self.bits / self.bin_row + self.padding['bintop'] + self.padding['binbottom']

    def num_rows_exprs(self):
        n = len(self.exprs)
        if n > 0:
            n += self.padding['vartop'] + self.padding['varbottom']
        return n

    def offset_val(self):
        return self.padding['top']

    def offset_bin(self):
        return self.offset_val() + self.num_rows_val()

    def offset_exprs(self):
        return self.offset_bin() + self.num_rows_bin()

    def draw_str(self, str, attr='', x=0, y=0):
        print((self.term.normal + self.term.move(y, x) + attr + str).format(t=self.term))

    def draw_header(self):
        if self.show_header:
            head = self.header + ' ' * (self.term.width - len(self.header))
            self.draw_str(head, self.attrs['header'])

    def clear_value(self, varname=None):
        y = self.padding['top']
        for fmt in self.get_value_formats():
            w = self.num_cols() - self.padding['left'] - len(' ' + fmt) - self.padding['right'] - self.padding['label']*2
            x = self.padding['left'] + len(' ' + fmt)
            if varname:
                w -= len(varname)
                if self.align == 'right':
                    x += len(varname)
            self.draw_str(' '*w, '', x, y)
            y += 1

    def draw_value(self, varname=None):
        y = self.padding['top']
        for fmt in self.get_value_formats():
            self.draw_value_at_row(self.lastval, fmt, y)
            y += 1

    def draw_value_at_row(self, value, fmt, row, label=None):
        fmtd = ''
        if fmt in ['h', 'd', 'o']:
            fmtd = BASE_FMT[fmt].format(value)
            attr = self.attrs[fmt + 'val']
        elif fmt == 'a':
            s = ('{0:0=%dX}' % (self.bits/4)).format(value)
            a = [chr(int(s[i:i+2],16)) for i in range(0, len(s), 2)]
            for c in a:
                if c not in string.printable or c == '\n':
                    fmtd += '.'
                else:
                    fmtd += c
            attr = self.attrs['aval']
        elif fmt == 'u':
            # s = ('{0:0=%dX}' % (self.bits/4)).format(value)
            # a = [(chr(int(s[i:i+2],16)) + chr(int(s[i+2:i+4],16))).decode('utf-16') for i in range(0, len(s), 4)]
            attr = self.attrs['uval']
        if self.align == 'right':
            col = self.num_cols() - self.padding['right'] - self.padding['label'] - len(fmtd) - 2
            self.draw_str(fmtd, attr, col, row)
        elif self.align == 'left':
            col = self.padding['left'] + len(' ' + fmt) + self.padding['label']
            self.draw_str(fmtd, attr, col, row)

    def draw_value_labels(self):
        y = self.padding['top']
        for fmt in self.get_value_formats():
            self.draw_labels_at_row(fmt, y)
            y += 1

    def draw_labels_at_row(self, fmt, row, label=None):
        if self.align == 'right':
            col = self.num_cols() - self.padding['right'] - self.padding['label']
            self.draw_str(fmt, self.attrs['vallabel'], col, row)
            if label != None:
                self.draw_str(label, self.attrs['vallabel'], self.padding['left'], row)
        elif self.align == 'left':
            col = self.padding['left']
            self.draw_str(fmt, self.attrs['vallabel'], col, row)
            if label != None:
                self.draw_str(label, self.attrs['vallabel'], self.num_cols() - self.padding['right'] - len(label), row)

    def draw_binary(self):
        s = (BASE_FMT['b'] % self.bits).format(self.lastval)
        if len(s) > self.bits:
            s = s[len(s)-self.bits:]
        y = len(self.get_value_formats()) + self.padding['top'] + self.padding['bintop']
        x = self.padding['left']
        p = 0
        if self.lastval >= 1<<self.bits:
            attr = self.attrs['err']
        else:
            attr = self.attrs['bval']
        for i in xrange(len(s)):
            if i != 0 and i % self.bin_row == 0:
                y += 1
                x = self.padding['left']
                p = 0
            elif i != 0 and i % 8 == 0:
                p += 3
            elif i != 0 and i % 4 == 0:
                p += 1
            x += 1
            self.draw_str(s[i], attr, x*2+p, y)

    def draw_binary_labels(self):
        rows = range(self.bits / self.bin_row)
        y = self.offset_bin() + self.padding['bintop'] + len(rows) - 1
        for i in rows:
            right = str(i * self.bin_row)
            left = str((i+1) * self.bin_row - 1)
            self.draw_str(left, self.attrs['binlabel'], self.padding['left'], y)
            self.draw_str(right, self.attrs['binlabel'], self.num_cols() - self.padding['right'] - 2, y)
            y -= 1

    def clear_exprs(self):
        pass

    def draw_exprs(self):
        y = self.offset_exprs() + self.padding['vartop']
        x = self.padding['left']
        for idx, (value, fmt, label) in enumerate(self.exprs):
            # TODO Ditch hardcoded format
            self.draw_value_at_row(value, fmt, y + idx, label)

    def draw_expr_labels(self):
        y = self.offset_exprs() + self.padding['vartop']
        for idx, (value, fmt, label) in enumerate(self.exprs):
            label = "%s : %2d" % (label, idx)
            self.draw_labels_at_row(fmt, y + idx, label)
