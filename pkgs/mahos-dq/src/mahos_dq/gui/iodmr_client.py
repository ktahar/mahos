#!/usr/bin/env python3

"""
Qt signal-based clients of Imaging IODMR.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from mahos.gui.Qt import QtCore

from mahos_dq.msgs.iodmr_msgs import IODMRData
from mahos.gui.client import QBasicMeasClient


class QIODMRClient(QBasicMeasClient):
    """Qt-based client for IODMR."""

    dataUpdated = QtCore.pyqtSignal(IODMRData)
    stopped = QtCore.pyqtSignal(IODMRData)
