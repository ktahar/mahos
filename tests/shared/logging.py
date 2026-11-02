"""
Shared logging helpers for tests.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import copy
import logging
import threading


class RecordingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []
        self.emit_threads = []

    def emit(self, record):
        self.records.append(copy.copy(record))
        self.emit_threads.append(threading.get_ident())
