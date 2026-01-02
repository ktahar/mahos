#!/usr/bin/env python3

"""
Typed Interface for ODMR Sweeper.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np

from mahos.inst.interface import InstrumentInterface
from mahos.msgs.pulse_msgs import PulsePattern


class ODMRSweeperInterface(InstrumentInterface):
    """Interface for ODMR Sweeper."""

    def get_line(self) -> np.ndarray | None:
        """Get single sweep line."""

        return self.get("line")

    def get_point(self) -> np.ndarray | None:
        """Get single point in sweep line."""

        return self.get("point")

    def get_unit(self) -> str:
        """Get unit."""

        return self.get("unit")

    def get_bounds(self) -> dict:
        """Get SG bounds.

        Returns:
            freq (low, high): frequency bounds.
            power (low, high): power bounds.

        """

        return self.get("bounds")

    def get_pd_analog(self) -> bool:
        """Get if this sweeper uses AnalogPD or not."""

        return self.get("pd_analog")

    def get_pulse_pattern(self) -> PulsePattern | None:
        """Get current pulse pattern."""

        return self.get("pulse_pattern")
