from __future__ import print_function
import socket
import threading

import calculon
from .env import *

try:
    import voltron
    from voltron.core import *
    from voltron.api import *
    from voltron.plugin import *
    voltron.setup_env()
    HAS_VOLTRON = True
except ImportError:
    HAS_VOLTRON = False


if HAS_VOLTRON:
    class VoltronWatcher(threading.Thread):
        def __init__(self, callback=None):
            super(VoltronWatcher, self).__init__()
            self.callback = callback

        def run(self, *args, **kwargs):
            self.done = False
            self.client = voltron.core.Client()
            self.client.connect()
            while not self.done:
                try:
                    res = self.client.send_request(api_request('wait', timeout=1))
                    if res.is_success:
                        self.callback()
                except Exception as e:
                    done = True

    class VoltronProxy(object):
        _instance = None
        exception = False
        connected = False
        watcher = None
        disp = None

        def __init__(self, callback=None):
            self.callback = callback
            if not self.connected:
                self.connect()
            self.start_watcher()
            calculon.voltron_proxy = self

        def __getattr__(self, key):
            if self.connected:
                try:
                    req = api_request('registers')
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
                    req = api_request('memory')
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

        def _connect(self):
            self.client = voltron.core.Client()
            self.client.connect()
            self.start_watcher()
            self.connected = True
            self.update_disp()

        def connect(self):
            if not self.connected:
                if not self.exception:
                    try:
                        self._connect()
                        print("Connected to voltron")
                    except socket.error:
                        pass
                    except Exception as e:
                        raise e
                        self.exception = True
                        print("Error loading voltron: " + str(e))
                        print("Make sure you have the most recent version of voltron")
            else:
                print("Already connected")

        def _disconnect(self):
            if self.watcher:
                self.watcher.done = True
                self.watcher.join()
                self.watcher = None
            self.client = None
            self.connected = False
            self.update_disp()

        def disconnect(self):
            if self.connected:
                self._disconnect()
                print("Disconnected from voltron")
            else:
                print("Not connected")

        def start_watcher(self):
            if not self.watcher and self.callback and self.connected:
                self.watcher = VoltronWatcher(self.callback)
                self.watcher.start()

        def update_disp(self):
            if self.disp:
                self.disp.set_voltron_status(self.connected)