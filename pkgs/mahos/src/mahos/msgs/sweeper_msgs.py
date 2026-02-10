#!/usr/bin/env python3

"""
Message types for Sweeper measurement.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from mahos.msgs.common_meas_msgs import BasicMeasData


class SweeperData(BasicMeasData):
    """Data class for Sweeper measurement."""

    def __init__(self, params: dict | None = None):
        self.set_version(0)
        self.init_params(params)
        self.init_attrs()
        self.data: NDArray[np.float64] | None = None
        self.init_axes()

    def init_axes(self):
        """Initialize axis labels and units from params."""

        if self.params is not None:
            self.xlabel: str = self.params.get("x_key", "X")
            self.xunit: str = self.params.get("x_unit", "")
            self.ylabel: str = self.params.get("meas_key", "Measurement")
            self.yunit: str = self.params.get("meas_unit", "")
        else:
            self.xlabel = "X"
            self.xunit = ""
            self.ylabel = "Measurement"
            self.yunit = ""
        self.xscale: str = "linear"
        self.yscale: str = "linear"

    def has_data(self) -> bool:
        return self.data is not None

    def sweeps(self) -> int:
        """Get number of sweeps done."""

        if self.data is None:
            return 0
        return self.data.shape[1]

    def get_xdata(self) -> NDArray[np.float64]:
        if self.params is None:
            return np.array([])
        if self.params.get("log", False):
            return np.logspace(
                np.log10(self.params["start"]),
                np.log10(self.params["stop"]),
                self.params["num"],
            )
        else:
            return np.linspace(
                self.params["start"],
                self.params["stop"],
                self.params["num"],
            )

    def get_ydata(self, last_n: int = 0) -> NDArray[np.float64] | None:
        if not self.has_data():
            return None
        if last_n < 0 and self.data.shape[1] <= -last_n:
            return None
        return np.mean(self.data[:, -last_n:], axis=1)

    def get_image(self, last_n: int = 0) -> NDArray:
        return self.data[:, -last_n:]


def update_data(data: SweeperData) -> SweeperData:
    """Update data for schema migration."""

    return data
