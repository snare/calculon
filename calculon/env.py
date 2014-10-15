from scruffy import Environment

ENV = None
CONFIG = None

def load_env():
    ENV = Environment({
        'dir':  {
            'path': '~/.calculon',
            'create': True,
            'mode': 0o700
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
    return ENV

ENV = load_env()

CONFIG = ENV['config']
