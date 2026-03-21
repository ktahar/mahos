#!/usr/bin/env python3

"""
File I/O for Analog-PD Pulse ODMR.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import numpy as np

from mahos.node.log import DummyLogger
from mahos.util.io import save_pickle_or_h5, load_pickle_or_h5
from mahos_dq.msgs.apodmr_msgs import APODMRData, update_data
from mahos_dq.meas.apodmr_worker import APODMRDataOperator
from mahos_dq.meas.podmr_fitter import PODMRFitter
from mahos_dq.meas.podmr_io import PODMRIO


class APODMRIO(PODMRIO):
    """File I/O helper for :class:`mahos_dq.msgs.apodmr_msgs.APODMRData`."""

    def __init__(self, logger=None):
        if logger is None:
            self.logger = DummyLogger(self.__class__.__name__)
        else:
            self.logger = logger

    def save_data(
        self, file_name: str, data: APODMRData, params: dict | None = None, note: str = ""
    ) -> bool:
        data.set_saved()
        return save_pickle_or_h5(file_name, data, APODMRData, self.logger, note=note)

    def load_data(self, file_name: str) -> APODMRData | None:
        d = load_pickle_or_h5(file_name, APODMRData, self.logger)
        if d is not None:
            return update_data(d)

    def reanalyze_data(self, plot_params: dict, data: APODMRData):
        op = APODMRDataOperator()
        pparams = data.params["plot"].copy()
        pparams.update(plot_params)
        op.update_plot_params(data, pparams)
        op.get_marker_indices(data)
        op.analyze(data)

    def refit_data(self, params: dict, data: APODMRData) -> bool:
        fitter = PODMRFitter(self.logger)
        success = bool(fitter.fitd(data, params["fit"], params["fit_label"]))
        if not success:
            self.logger.error("Failed to fit.")
        return success

    def _export_data_csv(self, fn, data: APODMRData) -> bool:
        header = "# Analog-PD Pulse ODMR data taken by mahos_dq.meas.apodmr.\n"
        header += f"# {data.xlabel} {data.ylabel}\n"
        header += f"# {data.xunit} {data.yunit}\n"

        x = data.get_xdata()
        y0, y1 = data.get_ydata()

        with open(fn, "w", encoding="utf-8", newline="\n") as f:
            f.write(header)
        with open(fn, "ab") as f:
            if y1 is not None:
                np.savetxt(f, np.column_stack((x, y0, y1)))
            else:
                np.savetxt(f, np.column_stack((x, y0)))

        self.logger.info(f"Exported Data to {fn}.")
        return True
