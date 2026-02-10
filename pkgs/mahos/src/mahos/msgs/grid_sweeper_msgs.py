#!/usr/bin/env python3

"""
Message types for GridSweeper measurement.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import time

import numpy as np
from numpy.typing import NDArray

from mahos.msgs.data_msgs import Data, FormatTimeMixin


class GridSweeperData(Data, FormatTimeMixin):
    """Data class for 2D sweep (x, y) with repeated sweeps."""

    def __init__(self, params: dict | None = None):
        self.set_version(0)
        self.init_params(params)
        self.init_attrs()

    def init_attrs(self):
        self.running: bool = False
        self.start_time: float = time.time()
        self.finish_time: float | None = None
        self._saved: bool = False

        self.data: NDArray[np.float64] | None = None
        self.completed_sweeps: int = 0

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

    def start(self):
        self.running = True
        self.start_time = time.time()
        self.finish_time = None

    def finalize(self) -> float:
        self.running = False
        self.finish_time = time.time()
        return self.finish_time - self.start_time

    def is_finalized(self) -> bool:
        return (not self.running) and (self.finish_time is not None)

    def set_saved(self):
        self._saved = True

    def is_saved(self) -> bool:
        return self._saved

    def has_data(self) -> bool:
        return self.data is not None

    def sweeps(self) -> int:
        """Get number of completed 2D sweeps."""

        return self.completed_sweeps

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

    def get_mean_image(self, last_n: int = 0) -> NDArray[np.float64] | None:
        """Get averaged 2D image over all or last N sweeps, ignoring NaN."""

        if self.data is None:
            return None
        if last_n < 0 and self.data.shape[2] <= -last_n:
            return None

        img = self.data[:, :, -last_n:]
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
