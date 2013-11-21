import sys
import curses
import string
import struct
import atexit

from .env import CONFIG

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

CURSES_COLOURS = {
    "black" : curses.COLOR_BLACK,
    "blue" : curses.COLOR_BLUE,
    "cyan" : curses.COLOR_CYAN,
    "green" : curses.COLOR_GREEN,
    "magenta" : curses.COLOR_MAGENTA,
    "red" : curses.COLOR_RED,
    "white" : curses.COLOR_WHITE,
    "yellow" : curses.COLOR_YELLOW,
    "none" : 0
}

VALID_FORMATS = ['h','d','o','a','u','b']

class CalculonDisplay (object):
    def __init__(self):
        self.scr = curses.initscr()
        atexit.register(curses.endwin)
        curses.start_color()

        self.config = self.init_config(CONFIG)
        self.bin_mode = self.config['bin_mode']
        self.bin_row = self.config['bin_row']
        self.bits = self.config['bits']
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

        h, w = self.scr.getmaxyx()
        win = curses.newwin(self.num_rows(), w, 0, 0)
        win.keypad(1)
        self.set_win(win, win)
        curses.curs_set(0)

        self.update_value(0)

    def init_config(self, config):
        # update curses text attributes
        colour_pairs = {}
        cp = 1
        for sec in config['attrs']:
            attrs = 0
            for attr in config['attrs'][sec]['attrs']:
                attrs |= CURSES_ATTRS[attr]
            colours = tuple(config['attrs'][sec].get('colours'))
            if colours and len(colours) >= 2:
                if colours not in colour_pairs:
                    curses.init_pair(cp, CURSES_COLOURS[colours[0].lower()], CURSES_COLOURS[colours[1].lower()])
                    colour_pairs[colours] = cp
                    cp += 1
                attrs |= curses.color_pair(colour_pairs[colours])
            config['attrs'][sec] = attrs

        # round up bits to nearest row
        config['bin_row'] = BIN_MODE_ROW_NARROW if config['bin_mode'] == "narrow" else BIN_MODE_ROW_WIDE
        if config['bits'] % config['bin_row'] > 0:
            config['bits'] += config['bin_row'] - (config['bits'] % config['bin_row'])

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

    def unwatch_var(self, varname):
        if varname in self.vars:
            del self.var_fmt[varname]
            del self.vars[varname]
            self.var_names.remove(varname)
            self.draw_state['all'] = True

    def get_var_names(self):
        return self.var_names

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
            self.draw_binary_labels()
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
        return self.bits / self.bin_row + self.padding['bintop'] + self.padding['binbottom']

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
        s = (BASE_FMT['b'] % self.bits).format(self.vars['_'])
        if len(s) > self.bits:
            s = s[len(s)-self.bits:]
        y = len(self.get_value_formats()) + self.padding['top'] + self.padding['bintop']
        x = self.padding['left']
        p = 0
        if self.vars['_'] >= 1<<self.bits:
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
            self.win.addstr(y, x*2+p, s[i], attr)

    def draw_binary_labels(self):
        rows = range(self.bits / self.bin_row)
        y = self.offset_bin() + self.padding['bintop'] + len(rows) - 1
        for i in rows:
            right = str(i * self.bin_row)
            left = str((i+1) * self.bin_row - 1)
            self.win.addstr(y, self.padding['left'], left, self.attrs['binlabel'])
            self.win.addstr(y, self.num_cols() - self.padding['right'] - 2, right, self.attrs['binlabel'])
            y -= 1

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

