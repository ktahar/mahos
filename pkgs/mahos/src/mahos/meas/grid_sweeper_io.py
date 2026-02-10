#!/usr/bin/env python3

"""
File I/O for GridSweeper measurement.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

from os import path

import matplotlib.pyplot as plt
import numpy as np

from ..msgs.grid_sweeper_msgs import GridSweeperData, update_data
from ..node.log import DummyLogger
from ..util.io import load_pickle_or_h5, save_pickle_or_h5


class GridSweeperIO(object):
    """File I/O handler for GridSweeper measurement."""

    def __init__(self, logger=None):
        if logger is None:
            self.logger = DummyLogger(self.__class__.__name__)
        else:
            self.logger = logger

    def save_data(self, filename: str, data: GridSweeperData, note: str = "") -> bool:
        """Save data to file. Returns True on success."""

        data.set_saved()
        return save_pickle_or_h5(filename, data, GridSweeperData, self.logger, note=note)

    def load_data(self, filename: str) -> GridSweeperData | None:
        """Load data from file. Returns None on failure."""

        d = load_pickle_or_h5(filename, GridSweeperData, self.logger)
        if d is not None:
            return update_data(d)
        return None

    def export_data(
        self, filename: str, data: GridSweeperData, params: dict | None = None
    ) -> bool:
        if params is None:
            params = {}

        if not isinstance(data, GridSweeperData):
            self.logger.error(f"Given object is not GridSweeperData: {type(data)}")
            return False

        if not data.has_data():
            self.logger.error("Data is empty, cannot export.")
            return False

        ext = path.splitext(filename)[1]
        if ext in (".txt", ".csv"):
            return self._export_data_csv(filename, data, params)
        elif ext in (".png", ".pdf", ".eps"):
            return self._export_data_image(filename, data, params)
        else:
            self.logger.error(f"Unknown extension to export data: {filename}")
            return False

    def _select_image(self, data: GridSweeperData, params: dict) -> np.ndarray | None:
        if params.get("mean", True):
            return data.get_mean_image(
                last_n=params.get("last_n", 0),
                include_incomplete=params.get("include_incomplete", True),
            )

        if "sweep_index" in params:
            return data.get_image(params["sweep_index"])

        return data.get_latest_image()

    def _export_data_csv(self, filename: str, data: GridSweeperData, params: dict) -> bool:
        """Export selected 2D image to CSV with x, y, z columns."""

        xdata = data.get_xdata()
        ydata = data.get_ydata()
        zdata = self._select_image(data, params)
        if zdata is None:
            self.logger.error("Selected image is unavailable.")
            return False

        xx, yy = np.meshgrid(xdata, ydata, indexing="ij")

        with open(filename, "w", encoding="utf-8", newline="\n") as fo:
            fo.write("# GridSweeper data\n")
            fo.write(f"# x: {data.xlabel} ({data.xunit}), y: {data.ylabel} ({data.yunit})\n")
            fo.write(f"# z: {data.zlabel} ({data.zunit})\n")
            fo.write("# x,y,z\n")

        with open(filename, "ab") as fo:
            arr = np.column_stack((xx.ravel(), yy.ravel(), zdata.ravel()))
            np.savetxt(fo, arr, delimiter=",")

        self.logger.info(f"Exported data to {filename}.")
        return True

    def _export_data_image(self, filename: str, data: GridSweeperData, params: dict) -> bool:
        """Export selected 2D image to image format (PNG, PDF, EPS)."""

        zdata = self._select_image(data, params)
        if zdata is None:
            self.logger.error("Selected image is unavailable.")
            return False

        xdata = data.get_xdata()
        ydata = data.get_ydata()
        if xdata.size == 0 or ydata.size == 0:
            self.logger.error("Axis values are unavailable.")
            return False

        plt.rcParams["font.size"] = params.get("fontsize", 28)
        fig = plt.figure(
            figsize=params.get("figsize", (12, 12)),
            dpi=params.get("dpi", 100),
        )
        ax = fig.subplots()

        extent = (xdata[0], xdata[-1], ydata[0], ydata[-1])
        im = ax.imshow(zdata.T, origin="lower", aspect="auto", extent=extent)
        cbar = fig.colorbar(im, ax=ax)

        xunit = f" ({data.xunit})" if data.xunit else ""
        yunit = f" ({data.yunit})" if data.yunit else ""
        zunit = f" ({data.zunit})" if data.zunit else ""

        ax.set_xlabel(f"{data.xlabel}{xunit}")
        ax.set_ylabel(f"{data.ylabel}{yunit}")
        cbar.set_label(f"{data.zlabel}{zunit}")

        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

        self.logger.info(f"Exported data to {filename}.")
        return True
