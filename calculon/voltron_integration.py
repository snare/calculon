from __future__ import print_function
import socket
import threading
from requests.exceptions import ConnectionError

import calculon
from .env import *

try:
    import voltron
    from voltron.repl import REPLClient
    HAS_VOLTRON = True
except ImportError:
    HAS_VOLTRON = False


if HAS_VOLTRON:
    class VoltronWatcher(threading.Thread):
        def __init__(self, callback=None):
            super(VoltronWatcher, self).__init__()
            self.callback = callback

        def run(self, *args, **kwargs):
            if self.callback:
                self.done = False
                self.client = voltron.core.Client()
                while not self.done:
                    try:
                        res = self.client.perform_request('version', block=True, timeout=1)
                        if res.is_success:
                            self.callback()
                    except Exception as e:
                        done = True

    class VoltronProxy(REPLClient):
        _instance = None
        exception = False
        watcher = None
        disp = None

        def __init__(self, callback=None):
            self.callback = callback
            self.start_watcher()
            calculon.voltron_proxy = self
            super(VoltronProxy, self).__init__()

        def start_watcher(self):
            if not self.watcher and self.callback:
                self.watcher = VoltronWatcher(self.callback)
                self.watcher.start()
