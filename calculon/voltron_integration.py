from __future__ import print_function
import socket

from .env import *

try:
    import voltron
except ImportError:
    voltron = None

class _VoltronProxy(object):
    _instance = None
    config = {
        'type': 'interactive',
        'update_on': 'stop',
    }

    def __init__(self):
        self.connected = False
        self.connect()

    def __getattr__(self, key):
        if self.connected:
            resp = self.client.query({'msg_type': 'interactive',
                              'query': 'get_register',
                              'register': key})
            return resp['value']
        else:
            raise Exception("Not connected")

    def __getitem__(self, key):
        if self.connected:
            if isinstance(key, slice):
                resp = self.client.query({'msg_type': 'interactive',
                    'query': 'get_memory',
                    'start': key.start,
                    "end": key.stop})
            else:
                resp = self.client.query({'msg_type': 'interactive',
                    'query': 'get_memory',
                    'start': key,
                    "end": key + 1})

            return resp['value']
        else:
            raise Exception("Not connected")

    def start_callback_thread(self, lock, callback):
        return self.client.start_callback_thread(lock, callback)

    def connect(self):
        if not self.connected:
            try:
                self.client = voltron.comms.InteractiveClient(config=self.config)
                self.connected = True
                print("Connected to voltron")
            except socket.error, e:
                print("Couldn't connect because %s" % str(e))
                pass
            except Exception, e:
                print("Error loading voltron: " + str(e))
                print("Make sure you have the most recent version of voltron")
        else:
            print("Already connected")
    def disconnect(self):
        if self.connected:
            self.client.close()
            self.client = None
            self.connected = False
            print("Disconnected from voltron")
        else:
            print("Not connected")

if not voltron:
    VoltronProxy = lambda *args: None
else:
    VoltronProxy = _VoltronProxy
