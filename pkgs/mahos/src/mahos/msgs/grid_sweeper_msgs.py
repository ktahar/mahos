#!/usr/bin/env python3

"""
Message types for GridSweeper measurement.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from mahos.msgs.common_meas_msgs import ImageMeasData


class GridSweeperData(ImageMeasData):
    """Data class for 2D planar sweep (x, y) with repeated sweeps."""

    def __init__(self, params: dict | None = None):
        self.set_version(0)
        self.init_params(params)
        self.init_attrs()

        self.data: NDArray[np.float64] | None = None
        self.completed_sweeps: int = 0

    def init_axes(self):
        super().init_axes()
        if self.params is not None:
            x_params = self.params.get("x", {})
            y_params = self.params.get("y", {})
            meas_params = self.params.get("measure", {})
            self.xlabel: str = x_params.get("key", "X")
            self.xunit: str = x_params.get("unit", "")
            self.ylabel: str = y_params.get("key", "Y")
            self.yunit: str = y_params.get("unit", "")
            self.zlabel: str = meas_params.get("key", "Measurement")
            self.zunit: str = meas_params.get("unit", "")
        else:
            self.xlabel = "X"
            self.xunit = ""
            self.ylabel = "Y"
            self.yunit = ""
            self.zlabel = "Measurement"
            self.zunit = ""

    def has_data(self) -> bool:
        return self.data is not None

    def sweeps(self) -> int:
        """Get number of completed 2D sweeps."""

        return self.completed_sweeps

    def image_num(self) -> int:
        """Get number of available 2D sweep images.

        Returned value should be either
        - same as sweeps(): if the latest sweep image is completed (or both are 0).
        - sweeps() + 1: if the latest sweep image is incomplete (includes NaN)

        """

        if not self.has_data():
            return 0
        return self.data.shape[2]

    def has_incomplete(self) -> bool:
        """Check if the latest image is incomplete (includes NaN).

        Returns False there is no data.

        """

        if not self.has_data():
            return False
        return self.sweeps() < self.image_num()

    def get_xdata(self) -> NDArray[np.float64]:
        if self.params is None or "x" not in self.params:
            return np.array([])
        p = self.params["x"]
        if p.get("log", False):
            return np.logspace(np.log10(p["start"]), np.log10(p["stop"]), p["num"])
        else:
            return np.linspace(p["start"], p["stop"], p["num"])

    def get_ydata(self) -> NDArray[np.float64]:
        if self.params is None or "y" not in self.params:
            return np.array([])
        p = self.params["y"]
        if p.get("log", False):
            return np.logspace(np.log10(p["start"]), np.log10(p["stop"]), p["num"])
        else:
            return np.linspace(p["start"], p["stop"], p["num"])

    def get_image(self, sweep_index: int = -1) -> NDArray[np.float64] | None:
        """Get one 2D image by sweep index."""

        if self.data is None:
            return None
        try:
            return self.data[:, :, sweep_index]
        except IndexError:
            return None

    def get_latest_image(self) -> NDArray[np.float64] | None:
        """Get latest in-progress (or most recent) 2D image."""

        return self.get_image(-1)

    def get_mean_image(
        self, last_n: int = 0, include_incomplete: bool = True
    ) -> NDArray[np.float64] | None:
        """Get averaged 2D image over all or last N sweeps, ignoring NaN."""

        if self.data is None:
            return None

        stack = self.data
        if not include_incomplete and self.has_incomplete():
            stack = stack[:, :, :-1]
        if last_n < 0 and stack.shape[2] <= -last_n:
            return None

        img = stack[:, :, -last_n:]
        if img.size == 0:
            return None
        # return without nanmean() call to suppress "Mean of empty slice" warning
        if img.shape[2] == 1:
            return img[:, :, 0]

        with np.errstate(invalid="ignore"):
            return np.nanmean(img, axis=2)


def update_data(data: GridSweeperData) -> GridSweeperData:
    """Update data for schema migration."""

    return data
