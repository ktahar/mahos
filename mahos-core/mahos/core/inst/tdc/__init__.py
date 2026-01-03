#!/usr/bin/env python3

"""
Time to Digital Converter (Time Digitizer) module

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from mahos.core.inst.tdc.mcs import MCS
from mahos.core.inst.tdc.time_tagger import TimeTagger

__all__ = ["MCS", "TimeTagger"]
