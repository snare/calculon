import os
import json
import pkg_resources
import itertools
import errno

MAX_BASENAME = 16


class Environment(object):
    def __init__(self, spec):
        self.spec = spec
        self.basename = spec['basename']
        self.files = {}

        # set up environment directory
        self.dir = os.path.expanduser(self.spec['dir']['path'])
        if self.spec['dir']['create']:
            try:
                os.mkdir(self.dir, self.spec['dir']['mode'])
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise

        # init files
        for name in self.spec['files']:
            fspec = self.spec['files'][name]

            # add filename if one isn't provided
            if 'name' not in fspec:
                fspec['name'] = name
            if 'var' in fspec and fspec['var'] in os.environ:
                fspec['name'] = os.environ[fspec['var']]

            # if environment var exists, override path
            if 'var' in fspec and fspec['var'] in os.environ:
                fspec['path'] = os.environ[fspec['var']]
            else:
                fspec['path'] = os.path.join(self.dir, fspec['name'])

            # substitute basename
            if self.basename:
                fspec['name'] = fspec['name'].format(basename=self.basename)

            # store updated spec
            self.spec['files'][name] = fspec

            # create file
            if 'create' in fspec and fspec['create']:
                if not os.path.isfile(fspec['path']):
                    f = open(fspec['path'], 'w+')
                    f.close()

            # load file
            if 'read' in fspec and fspec['read']:
                if fspec['type'] == 'config':
                    self.files[name] = self.load_config(fspec)
                    if 'basename_variable' in self.files[name] and self.files[name]['basename_variable'] in os.environ:
                        self.basename = os.environ[self.files[name]['basename_variable']].replace("/", '')
                        if len(self.basename) > MAX_BASENAME:
                            self.basename = self.basename[-MAX_BASENAME:]
                elif fspec['type'] == 'json':
                    self.files[name] = self.load_json(fspec)
                elif fspec['type'] == 'raw':
                    self.files[name] = self.load_raw(fspec)

    def __getitem__(self, key):
        if key == 'dir':
            return self.dir
        else:
            return self.files[key]

    def load_config(self, spec):
        # load default config
        config = {}
        if 'default' in spec:
            try:
                config = self.parse_json(pkg_resources.resource_string(__name__, spec['default']))
            except:
                raise IOError("Failed to parse default configuration. Your package is probably broken.")

        # load local config
        try:
            local_config = self.parse_json(file(spec['path']).read())
            config = self.merge_dicts(local_config, config)
        except ValueError, e:
            raise ValueError("Error parsing local configuration file: " + e.message)
        except IOError:
            pass

        return config

    def load_json(self, spec):
        return self.parse_json(file(spec['path']).read())

    def load_raw(self, spec):
        return file(spec['path']).read()

    def parse_json(self, config):
        lines = filter(lambda x: len(x) != 0 and x.strip()[0] != '#', config.split('\n'))
        return json.loads('\n'.join(lines))

    def merge_dicts(self, d1, d2):
        # recursive merge where items in d2 override those in d1
        for k1,v1 in d1.iteritems():
            if isinstance(v1, dict) and k1 in d2.keys() and isinstance(d2[k1], dict):
                self.merge_dicts(v1, d2[k1])
            else:
                d2[k1] = v1
        return d2

    def read_file(self, name):
        # build path to file
        path = os.path.join(self.dir, name)

        # read file
        return file(path).read()

    def write_file(self, name, data):
        # find or build a spec for this file
        if name in self.spec['files']:
            spec = self.spec['files'][name]
        else:
            spec = {'name': name, 'type': 'raw', 'path': os.path.join(self.dir, name)}

        # open file
        f = open(spec['path'], 'w+')

        # truncate the file if we're not appending
        if not 'append' in spec or 'append' in spec and not spec['append']:
            f.truncate()

        # write file
        f.write(data)
        f.close()


ENV = Environment({
    'dir':  {
        'path': '~/.calculon',
        'create': True,
        'mode': 0700
    },
    'files': {
        'config': {
            'type':     'config',
            'default':  'config/default.cfg',
            'read':     True
        },
        'uri': {
            'type':     'raw',
            'read':     True,
            'create':   True,
            'var':      'CALCULON_URI'
        }
    },
    'basename': 'calculon'
})

CONFIG = ENV['config']

