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
        self.lastvars = {}
        self.vars = {}
        self.vars['_'] = 0
        self.var_fmt = {}
        self.var_names = []
        self.draw_state = {
            'header': True, 'value': True, 'vallabel': True, 'binlabel': True,
            'varlabel': True, 'varvalue': True, 'all': True
        }
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
            self.lastvars['_'] = self.vars['_']
            self.vars['_'] = value
            self.draw_state['value'] = True
        else:
            self.lastvars[name] = self.vars[name]
            self.vars[name] = value
            self.draw_state['varvalue'] = True
        self.redraw()

    def watch_var(self, varname, format):
        if varname not in self.vars:
            self.var_fmt[varname] = format
            self.vars[varname] = 0
            self.var_names.append(varname)
            self.draw_state['all'] = True
        else:
            print("Variable '%s' is already being watched" % varname)

    def unwatch_var(self, varname):
        if varname in self.vars:
            del self.var_fmt[varname]
            del self.vars[varname]
            self.var_names.remove(varname)
            self.draw_state['all'] = True
        else:
            print("Variable '%s' is not being watched" % varname)

    def redraw(self, all=False):
        self.resize()
        if self.draw_state['all']:
            self.win.clear()
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
            self.draw_state['vallabel'] = False
        if self.draw_state['varlabel'] or self.draw_state['all']:
            self.draw_var_labels()
            self.draw_state['varlabel'] = False
        if self.draw_state['varvalue'] or self.draw_state['all']:
            self.draw_vars()
            self.draw_state['varvalue'] = False
        self.draw_state['all'] = False
        self.win.refresh()
        self.repl_win.refresh()

    def resize(self):
        self.win.resize(self.num_rows(), self.num_cols())
        self.win.refresh()
        self.repl_win.refresh()

    def get_value_formats(self):
        return filter(lambda x: x in VALID_FORMATS and x != 'b', self.formats)

    def num_rows(self):
        return self.offset_vars() + self.num_rows_vars() + self.padding['bottom']

    def num_cols(self):
        if self.bin_mode == "wide":
            c = BIN_MODE_WIDTH_WIDE + self.padding['left'] + self.padding['right']
        else:
            c = BIN_MODE_WIDTH_NARROW + self.padding['left'] + self.padding['right']
        return c

    def num_rows_val(self):
        return len(self.get_value_formats())

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

    def clear_value(self, varname=None):
        y = self.padding['top']
        for fmt in self.get_value_formats():
            w = self.num_cols() - self.padding['left'] - len(' ' + fmt) - self.padding['right'] - self.padding['label']*2
            x = self.padding['left'] + len(' ' + fmt)
            if varname:
                w -= len(varname)
                if self.align == 'right':
                    x += len(varname)
            self.win.addstr(y, x, ' '*w)
            y += 1

    def draw_value(self, varname=None):
        y = self.padding['top']
        for fmt in self.get_value_formats():
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
            self.win.addstr(row, self.num_cols() - self.padding['right'] - self.padding['label'] - len(fmtd) - 2, fmtd, attr)
        elif self.align == 'left':
            self.win.addstr(row, self.padding['left'] + len(' ' + fmt) + self.padding['label'], fmtd, attr)

    def draw_value_labels(self):
        y = self.padding['top']
        for fmt in self.get_value_formats():
            self.draw_labels_at_row(fmt, y)
            y += 1

    def draw_labels_at_row(self, fmt, row, label=None):
        if self.align == 'right':
            self.win.addstr(row, self.num_cols() - self.padding['right'] - self.padding['label'], fmt, self.attrs['vallabel'])
            if label != None:
                self.win.addstr(row, self.padding['left'], label, self.attrs['vallabel'])
        elif self.align == 'left':
            self.win.addstr(row, self.padding['left'], ' ' + fmt, self.attrs['vallabel'])
            if label != None:
                self.win.addstr(row, self.num_cols() - self.padding['right'] - len(label), label, self.attrs['vallabel'])

    def draw_binary(self):
        s = BASE_FMT['b'].format(self.vars['_'])
        y = len(self.get_value_formats()) + self.padding['top'] + self.padding['bintop']
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

    def draw_var_labels(self):
        y = self.offset_vars() + self.padding['vartop']
        for var in self.var_names:
            self.draw_labels_at_row(self.var_fmt[var], y, var)
            y += 1

