#!/usr/bin/env python3

"""
Message Types for Piezo Instruments.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations
import enum

from mahos.msgs.common_msgs import Message


class Axis(Message, enum.Enum):
    """Piezo axis identifier used in move and status messages."""

    X = 0
    Y = 1
    Z = 2
