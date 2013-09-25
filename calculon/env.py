import os
import json
import pkg_resources

CALCULON_DIR = os.path.expanduser('~/.calculon/')
CALCULON_CONFIG = os.path.join(CALCULON_DIR, 'config')
DEFAULT_CONFIG = 'config/default.cfg'

def _load_config():
    # load default config
    try:
        config = _parse_config(pkg_resources.resource_string(__name__, DEFAULT_CONFIG))
    except:
        raise IOError("No default configuration found. Your package is probably broken.")

    # load local config
    try:
        local_config = _parse_config(file(CALCULON_CONFIG).read())
        config = _merge(local_config, config)
    except:
        pass

    # parse json
    return config


def _parse_config(config):
    lines = filter(lambda x: len(x) != 0 and x.strip()[0] != '#', config.split('\n'))
    return json.loads('\n'.join(lines))


def _merge(d1, d2):
    for k1,v1 in d1.iteritems():
        if isinstance(v1, dict) and k1 in d2.keys() and isinstance(d2[k1], dict):
            _merge(v1, d2[k1])
        else:
            d2[k1] = v1
    return d2


CONFIG = _load_config()

