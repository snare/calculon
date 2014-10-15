from __future__ import print_function
import socket

from .env import *

try:
    import voltron
    from voltron.core import *
    from voltron.api import *
    from voltron.plugin import *
    voltron.setup_env()
except ImportError:
    voltron = None

class VoltronProxy(object):
    _instance = None
    exception = False

    def __new__(cls, *args, **kwargs):
        if voltron:
            if not cls._instance:
                cls._instance = super(VoltronProxy, cls).__new__(cls, *args, **kwargs)
                cls._instance.connected = False
                cls._instance.connect()
        else:
            cls._instance = None
        return cls._instance

    def __getattr__(self, key):
        if self.connected:
            try:
                req = api_request('read_registers')
                res = self.client.send_request(req)
                if res.status == 'success':
                    return res.registers[key]
                else:
                    print("{} getting register: {}".format(type(res), res.message))
            except Exception as e:
                print("Exception getting register: {} {}".format(type(e), str(e)))
        else:
            raise Exception("Not connected")

    def __getitem__(self, key):
        if self.connected:
            try:
                req = api_request('read_memory')
                if isinstance(key, slice):
                    req.address = key.start
                    req.length = key.stop - key.start
                else:
                    req.address = key
                    req.length = 1

                res = self.client.send_request(req)

                if res.status == 'success':
                    return res.memory
                else:
                    print("{} reading memory: {}".format(type(res), res.message))
            except Exception as e:
                print("Exception reading memory: {} {}".format(type(e), str(e)))

            return resp['value']
        else:
            raise Exception("Not connected")

    def connect(self):
        if not self.connected:
            if not self.exception:
                try:
                    self.client = voltron.core.Client()
                    self.client.connect()
                    self.connected = True
                    print("Connected to voltron")
                except socket.error:
                    pass
                except Exception as e:
                    self.exception = True
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
