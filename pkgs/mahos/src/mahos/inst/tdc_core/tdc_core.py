#!/usr/bin/env python3

"""
Core shared components for Time to Digital Converter (Time Digitizer) module

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import numpy as np

from mahos.inst.instrument import Instrument


class TDCBase(Instrument):
    """Base class for TDC instruments, providing get_data_roi()."""

    def get_data_roi(self, ch: int, roi: list[tuple[int, int]]) -> list[np.ndarray] | None:
        """Get histogram-mode data with ROI specification.

        :param ch: TDC channel to get data.
        :param roi: ROI definitions. List of (start, stop) index pairs.

        :returns: List of histogram segments for each ROI.
            Each segment should have length of (stop - start).

        """

        data = self.get_data(ch)
        if data is None:
            return None
        data_roi = []
        for start, stop in roi:
            if start > stop:
                self.logger.error(f"Invalid ROI ({start}, {stop}): start must be <= stop.")
                return None
            if (start < 0 and stop < 0) or (start > len(data) and stop > len(data)):
                data_roi.append(np.zeros(stop - start, dtype=data.dtype))
                continue

            # fill up out-of-bounds in ROI with zeros
            if start < 0:
                d = np.concatenate((np.zeros(abs(start), dtype=data.dtype), data[:stop]))
            else:
                d = data[start:stop]
            if stop > len(data):
                d = np.concatenate((d, np.zeros(stop - len(data), dtype=data.dtype)))
            data_roi.append(d)
        return data_roi
