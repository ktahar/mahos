#!/usr/bin/env python3

"""
File I/O for Sweeper measurement.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

from os import path

import matplotlib.pyplot as plt
import numpy as np

from ..msgs.sweeper_msgs import SweeperData, update_data
from ..node.log import DummyLogger
from ..util.io import load_pickle_or_h5, save_pickle_or_h5


class SweeperIO(object):
    """File I/O handler for Sweeper measurement."""

    def __init__(self, logger=None):
        if logger is None:
            self.logger = DummyLogger(self.__class__.__name__)
        else:
            self.logger = logger

    def save_data(self, file_name: str, data: SweeperData, note: str = "") -> bool:
        """Save data to file. Returns True on success."""

        data.set_saved()
        return save_pickle_or_h5(file_name, data, SweeperData, self.logger, note=note)

    def load_data(self, file_name: str) -> SweeperData | None:
        """Load data from file. Returns None on failure."""

        d = load_pickle_or_h5(file_name, SweeperData, self.logger)
        if d is not None:
            return update_data(d)
        return None

    def export_data(self, file_name: str, data: SweeperData, params: dict | None = None) -> bool:
        if params is None:
            params = {}

        if not isinstance(data, SweeperData):
            self.logger.error(f"Given object is not SweeperData: {type(data)}")
            return False

        if not data.has_data():
            self.logger.error("Data is empty, cannot export.")
            return False

        ext = path.splitext(file_name)[1]
        if ext in (".txt", ".csv"):
            return self._export_data_csv(file_name, data)
        elif ext in (".png", ".pdf", ".eps"):
            return self._export_data_image(file_name, data, params)
        else:
            self.logger.error(f"Unknown extension to export data: {file_name}")
            return False

    def _export_data_csv(self, file_name: str, data: SweeperData) -> bool:
        """Export data to CSV format."""

        xdata = data.get_xdata()
        ydata = data.get_ydata()

        xlabel = data.xlabel
        xunit = f" ({data.xunit})" if data.xunit else ""
        ylabel = data.ylabel
        yunit = f" ({data.yunit})" if data.yunit else ""

        with open(file_name, "w", encoding="utf-8", newline="\n") as fo:
            fo.write("# Sweeper data\n")
            fo.write(f"# {xlabel}{xunit}, {ylabel}{yunit}\n")

        with open(file_name, "ab") as fo:
            np.savetxt(fo, np.column_stack((xdata, ydata)), delimiter=",")

        self.logger.info(f"Exported data to {file_name}.")
        return True

    def _export_data_image(self, file_name: str, data: SweeperData, params: dict) -> bool:
        """Export data to image format (PNG, PDF, EPS)."""

        plt.rcParams["font.size"] = params.get("fontsize", 28)

        fig = plt.figure(
            figsize=params.get("figsize", (12, 12)),
            dpi=params.get("dpi", 100),
        )
        ax = fig.subplots()

        xdata = data.get_xdata()
        ydata = data.get_ydata()

        ax.plot(xdata, ydata)

        xlabel = data.xlabel
        xunit = f" ({data.xunit})" if data.xunit else ""
        ylabel = data.ylabel
        yunit = f" ({data.yunit})" if data.yunit else ""

        ax.set_xlabel(f"{xlabel}{xunit}")
        ax.set_ylabel(f"{ylabel}{yunit}")

        if data.params.get("log", False):
            ax.set_xscale("log")

        plt.tight_layout()
        plt.savefig(file_name)
        plt.close()

        self.logger.info(f"Exported data to {file_name}.")
        return True
