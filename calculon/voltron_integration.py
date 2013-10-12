from __future__ import print_function
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

    def __new__(cls, *args, **kwargs):
        if voltron:
            obj = super(VoltronProxy, cls).__new__(cls, *args, **kwargs)
        else:
            obj = None
        return obj

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

    def connect(self):
        if not self.connected:
            try:
                self.client = voltron.comms.InteractiveClient(config=self.config)
                self.connected = True
                print("Connected to voltron")
            except socket.error, e:
                print("Failed to connect to voltron")
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
