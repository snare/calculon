import os
import json
import pkg_resources

CALCULON_DIR = os.path.expanduser('~/.calculon/')
CALCULON_CONFIG = os.path.join(CALCULON_DIR, 'config')
DEFAULT_CONFIG = 'config/default.cfg'

def _load_config():
    # load config
    try:
        # load local config if it exists
        config_data = file(CALCULON_CONFIG).read()
    except:
        # otherwise load default config or bail out
        try:
            config_data = pkg_resources.resource_string(__name__, DEFAULT_CONFIG)
        except:
            raise IOError("No local or default configuration found. Your package is probably broken.")

    # parse json
    lines = filter(lambda x: len(x) != 0 and x.strip()[0] != '#', config_data.split('\n'))
    return json.loads('\n'.join(lines))

CONFIG = _load_config()

