#!/usr/bin/env python3

"""
Typed Interface for Photo Detectors.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import numpy as np

from mahos.inst.daq_interface import BufferedReaderInterface


class PDInterface(BufferedReaderInterface):
    """Common interface for SinglePhotonCounter and AnalogIn-based PD."""

    # override pop_*() methods because PD has one channel per class.

    def pop_block(self) -> np.ndarray:
        """Get data from buffer. If buffer is empty, this function blocks until data is ready."""

        return self.get("data", True)

    def pop_all_block(self) -> list[np.ndarray]:
        """Get all data from buffer as list.

        If buffer is empty, this function blocks until data is ready.

        """

        return self.get("all_data", True)

    def pop_opt(self) -> np.ndarray | None:
        """Get data from buffer. If buffer is empty, returns None."""

        return self.get("data", False)

    def pop_all_opt(self) -> list[np.ndarray] | None:
        """Get all data from buffer as list. If buffer is empty, returns None."""

        return self.get("all_data", False)

    def configure_triggered(
        self,
        trigger_source: str,
        cb_samples: int,
        samples: int,
        rate: float,
        *,
        segment_samples: int | None = None,
        buffer_size: int = 0,
        bounds=(-10.0, 10.0),
        finite: bool = False,
        every: bool = False,
        drop_first: int = 0,
        oversample: int = 1,
        block_reduce_factor: int = 1,
        block_reduce_samples: int = 0,
        block_reduce_op: str = "mean",
        reduce_factor: int = 1,
        reduce_op: str = "mean",
        data_transfer: str | None = None,
        trigger_dir: bool = True,
        hardware_average: bool = True,
    ) -> bool:
        """Configure triggered fixed-length acquisition.

        ``trigger_source`` is the DAQ sample clock for conventional AnalogIn and the hardware
        trigger input for Spectrum digitizers.

        """

        params = {
            "mode": "triggered",
            "trigger_source": trigger_source,
            "trigger_dir": trigger_dir,
            "clock": trigger_source,
            "cb_samples": cb_samples,
            "samples": samples,
            "buffer_size": buffer_size,
            "rate": rate,
            "finite": finite,
            "every": every,
            "drop_first": drop_first,
            "clock_mode": True,
            "oversample": oversample,
            "block_reduce_factor": block_reduce_factor,
            "block_reduce_samples": block_reduce_samples,
            "block_reduce_op": block_reduce_op,
            "reduce_factor": reduce_factor,
            "reduce_op": reduce_op,
            "bounds": bounds,
            "hardware_average": hardware_average,
        }
        if segment_samples is not None:
            params["segment_samples"] = segment_samples
        if data_transfer:
            params["data_transfer"] = data_transfer
        return self.configure(params)

    def configure_tracer(
        self,
        clock: str,
        cb_samples: int,
        samples: int,
        rate: float,
        time_window: float,
        *,
        buffer_size: int = 0,
        bounds=(-10.0, 10.0),
        finite: bool = False,
        every: bool = False,
        stamp: bool = True,
        oversample: int = 1,
        data_transfer: str | None = None,
    ) -> bool:
        """Configure continuous tracer acquisition."""

        params = {
            "mode": "tracer",
            "cb_samples": cb_samples,
            "samples": samples,
            "buffer_size": buffer_size,
            "rate": rate,
            "finite": finite,
            "every": every,
            "stamp": stamp,
            "clock": clock,
            "time_window": time_window,
            "clock_mode": True,
            "oversample": oversample,
            "bounds": bounds,
        }
        if data_transfer:
            params["data_transfer"] = data_transfer
        return self.configure(params)


class SinglePhotonCounterInterface(PDInterface):
    """Interface for SinglePhotonCounter."""

    def correct_cps(self, raw_cps: list[float]) -> np.ndarray:
        """Correct the raw values in cps according to correction factors."""

        return self.get("correct", raw_cps)

    def get_correction_factor(self, xs_cps: list[float]) -> np.ndarray:
        """Get the correction factor for given cps values."""

        return self.get("correction_factor", xs_cps)


# Backward-compatible alias for existing code.
APDCounterInterface = SinglePhotonCounterInterface
