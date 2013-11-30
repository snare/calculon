from scruffy import Environment

ENV = Environment({
    'dir':  {
        'path': '~/.calculon',
        'create': True,
        'mode': 0700
    },
    'files': {
        'config': {
            'type':     'config',
            'default':  {
                'path':     'config/default.cfg',
                'rel_to':   'pkg',
                'pkg':      'calculon'
            },
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

