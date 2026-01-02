#!/usr/bin/env python3

"""
Spectrometer module

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from mahos.inst.spectrometer.princeton import Princeton_LightField
from mahos.inst.spectrometer.andor import Andor_Spectrometer

__all__ = ["Princeton_LightField", "Andor_Spectrometer"]
