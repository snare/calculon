import os
import json
import pkg_resources
import itertools


CALCULON_DIR = os.path.expanduser('~/.calculon/')
CALCULON_CONFIG = os.path.join(CALCULON_DIR, 'config')
DEFAULT_CONFIG = 'config/default.cfg'
CALCULON_URI_FILE = os.path.join(CALCULON_DIR, 'uri')

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
    except ValueError, e:
        raise ValueError("Error parsing local configuration file: " + e.message)
    except IOError:
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

def _calculon_basename():
    SOCKET_LENGTH = 16
    default = "calculon"
    try:
        name = os.getenv(CONFIG['main']['basename_variable'])
        name = name.replace("/", '')
        if len(name) > SOCKET_LENGTH:
            return name[-SOCKET_LENGTH:]
        else:
            return name
    except:
        return default

CALCULON_BASENAME = _calculon_basename()

def _calculon_socket():
    if "CALCULON_SOCKET" in os.environ:
        return os.getenv("CALCULON_SOCKET")
    else:
        d = CALCULON_DIR
        if not os.path.exists(d):
            os.mkdir(d, 0700)
        return os.path.join(d, "%s.sock" % CALCULON_BASENAME)

CALCULON_SOCKET = _calculon_socket()

def write_uri(uri):
    try:
        os.remove(CALCULON_URI_FILE)
    except:
        pass
    f = open(CALCULON_URI_FILE, 'w')
    f.write(str(uri))
    f.close()

def read_uri():
    try:
        f = open(CALCULON_URI_FILE, 'r')
        uri = f.read()
        f.close()
    except:
        uri = None
    return uri

CALCULON_URI = read_uri()

def constant_factory(value):
    return itertools.repeat(value).next
