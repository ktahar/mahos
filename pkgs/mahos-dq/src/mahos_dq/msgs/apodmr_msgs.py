#!/usr/bin/env python3

"""
Message Types for Analog-PD Pulse ODMR.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import numpy as np

from mahos.msgs.common_msgs import BinaryState, Status

# just for re-export: ValidateReq, DiscardReq, and UpdatePlotParamsReq
from mahos_dq.msgs.podmr_msgs import (  # noqa: F401
    PODMRData,
    ValidateReq,
    DiscardReq,
    UpdatePlotParamsReq,
)


class APODMRStatus(Status):
    """Status message for APODMR measurements.

    :ivar state: Measurement state (IDLE/ACTIVE).
    :ivar pg_freq: Pulse generator frequency used by the current sequence.

    """

    def __init__(self, state: BinaryState, pg_freq: float):
        self.state = state
        self.pg_freq = pg_freq

    def __repr__(self):
        return f"APODMRStatus({self.state}, {self.pg_freq*1e-9:.2f} GHz)"

    def __str__(self):
        return f"APODMR({self.state.name}, {self.pg_freq*1e-9:.2f} GHz)"


class APODMRData(PODMRData):
    """Analog-PD pulse ODMR data container.

    :ivar raw_data: Aggregated raw traces with shape
        ``(record, trace, sample)``.
    :ivar raw_xdata: Trace-local time axis for a single aggregated trace.
    :ivar trace_laser_timing: Laser-start timing in trace-local time, measured from trigger.
    :ivar marker_indices: Marker indices with shape ``(4,)`` as
        ``(sig_head, sig_tail, ref_head, ref_tail)`` shared by all traces.
    :ivar trigger_timing: Trigger timings for each trace in sequence time.
    :ivar laser_timing: Laser-start timings in sequence time (same semantics as
        :class:`mahos_dq.msgs.podmr_msgs.PODMRData`), kept for compatibility;
        APODMR analysis uses ``trace_laser_timing`` instead. When
        ``shots_per_point > 1``, each entry marks only the first shot of a repeated point.

    ``data0`` .. ``data3`` and ``data0ref`` .. ``data3ref`` retain the same
    analyzed-data semantics as :class:`mahos_dq.msgs.podmr_msgs.PODMRData`.

    """

    def __init__(self, params: dict | None = None, label: str = ""):
        super().__init__(params, label)
        self.set_version(0)

        self.tdc_status = None
        self.trace_laser_timing = None
        self.trigger_timing = None

    def _h5_attr_writers(self) -> dict:
        d = super()._h5_attr_writers()
        d.pop("tdc_status", None)
        return d

    def _h5_readers(self) -> dict:
        d = super()._h5_readers()
        d.pop("tdc_status", None)
        return d

    def get_raw_xdata(self) -> np.ndarray | None:
        """Get trace-local x-axis of raw data."""

        if self.raw_xdata is not None:
            return self.raw_xdata

        sample_period = self.get_bin()
        samples_per_trace = self.get_samples_per_trace()
        if sample_period is None or samples_per_trace is None:
            return None

        self.raw_xdata = np.arange(samples_per_trace) * sample_period
        return self.raw_xdata

    def records(self) -> int:
        if self.raw_data is None:
            return 0
        return int(self.raw_data.shape[0])

    def get_samples_per_trace(self) -> int | None:
        if self.raw_data is not None and np.size(self.raw_data) > 0:
            return int(self.raw_data.shape[-1])
        try:
            samples = int(self.params["instrument"]["samples_per_trace"])
            if samples > 0:
                return samples
        except (KeyError, TypeError, ValueError):
            pass
        try:
            trange = float(self.params["instrument"]["trange"])
            tbin = float(self.params["instrument"]["tbin"])
            if tbin > 0.0 and trange >= 0.0:
                return max(1, int(round(trange / tbin)))
        except (KeyError, TypeError, ValueError):
            pass
        return None

    def get_sweeps_per_record(self) -> int:
        if not self.has_params():
            return 1
        try:
            return max(1, int(self.params.get("sweeps_per_record", 1)))
        except (TypeError, ValueError):
            return 1

    def sweeps(self) -> int:
        return self.records() * self.get_sweeps_per_record()

    def measurement_time(self) -> float:
        if not self.has_params():
            return 0.0
        try:
            freq = float(self.params["instrument"]["pg_freq"])
            length = float(self.params["instrument"]["length"])
        except (KeyError, TypeError, ValueError):
            return 0.0
        if freq <= 0.0:
            return 0.0
        return self.sweeps() * length / freq

    def has_raw_data(self) -> bool:
        return self.raw_data is not None and np.size(self.raw_data) > 0

    def _get_xdata_head(self, xdata):
        raise ValueError("taumode 'head' is unsupported for APODMR")


def update_data(data: APODMRData):
    """Update APODMR data to the latest schema."""

    return data
