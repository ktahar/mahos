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

    def validate(self, params: dict, label: str) -> bool:
        """Validate parameters using sweeper-specific constraints."""

        return bool(self.get("validate", params, label))

    def get_line(self) -> np.ndarray | None:
        """Get single sweep line."""

        return self.get("line")

    def get_point(self) -> np.ndarray | tuple[np.ndarray, np.ndarray] | None:
        """Get a point, paired with its raw traces when trace acquisition is enabled."""

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

    def get_pd_trace(self) -> bool:
        """Get if this sweeper uses laser-resolved AnalogPD traces or not."""

        return self.get("pd_trace")

    def get_pulse_pattern(self) -> PulsePattern | None:
        """Get current pulse pattern."""

        return self.get("pulse_pattern")
