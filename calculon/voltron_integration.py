import socket

from .env import *

try:
    import voltron
except ImportError:
    voltron = None

class VoltronProxy(object):
    config = {
            'type': 'interactive'
    }
    def __init__(self):
        try:
            self.client = voltron.comms.InteractiveClient(config=self.config)
            self.connected = True
        except Exception as e:
            self.connected = False
            raise e

    def __getattr__(self, key):
        resp = self.client.query({'msg_type': 'interactive',
                          'query': 'get_register',
                          'register': key})
        return resp['value']


def load_voltron(locals):
    if voltron is None:
        return

    print "Loading voltron"
    proxy = VoltronProxy()
    if proxy.connected:
        locals['V'] = proxy
    else:
        return None
