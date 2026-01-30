#!/usr/bin/env python3

"""
Typed Interface for Camera.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

from mahos.inst.interface import InstrumentInterface
from mahos.msgs.inst.camera_msgs import FrameResult


class CameraInterface(InstrumentInterface):
    """Interface for Camera."""

    def get_frame(self, timeout_sec: float | None = None) -> FrameResult:
        """Get a captured frame."""

        return self.get("frame", args=timeout_sec)

    def configure_continuous(
        self,
        exposure_time_sec: float,
        frame_rate_Hz: float | None = None,
        binning: int = 0,
        roi: dict | None = None,
    ) -> bool:
        """Configure continuous (free-run) acquisition.

        :param exposure_time_sec: (sec) exposure time in sec.
        :param frame_rate_Hz: (Hz) frame rate limit. set None for no limit.
        :param binning: (int) binning. set 0 to skip setting.
        :param roi: (dict) ROI setting. set None, empty or contain any None to skip setting.
        :param roi.width: (int) ROI width.
        :param roi.height: (int) ROI height.
        :param roi.woffset: (int) ROI offset along width direction.
        :param roi.hoffset: (int) ROI offset along height direction.

        """

        params = {
            "exposure_time": exposure_time_sec,
            "frame_rate": frame_rate_Hz,
            "binning": binning,
            "roi": roi,
        }
        return self.configure(params, label="continuous")

    def configure_soft_trigger(
        self,
        exposure_time_sec: float,
        burst_num: int = 1,
        binning: int = 0,
        roi: dict | None = None,
    ) -> bool:
        """Configure software triggered acquisition.

        :param exposure_time_sec: (sec) exposure time in sec.
        :param frame_rate_Hz: (Hz) frame rate limit. set None for no limit.
        :param binning: (int) binning. set 0 to skip setting.
        :param roi: (dict) ROI setting. set None, empty or contain any None to skip setting.
        :param roi.width: (int) ROI width.
        :param roi.height: (int) ROI height.
        :param roi.woffset: (int) ROI offset along width direction.
        :param roi.hoffset: (int) ROI offset along height direction.

        """

        params = {
            "exposure_time": exposure_time_sec,
            "burst_num": burst_num,
            "binning": binning,
            "roi": roi,
        }
        return self.configure(params, label="soft_trigger")

    def configure_hard_trigger(
        self,
        exposure_time_sec: float,
        burst_num: int = 1,
        binning: int = 0,
        roi: dict | None = None,
    ) -> bool:
        """Configure hardware triggered acquisition.

        :param exposure_time_sec: (sec) exposure time in sec.
        :param frame_rate_Hz: (Hz) frame rate limit. set None for no limit.
        :param binning: (int) binning. set 0 to skip setting.
        :param roi: (dict) ROI setting. set None, empty or contain any None to skip setting.
        :param roi.width: (int) ROI width.
        :param roi.height: (int) ROI height.
        :param roi.woffset: (int) ROI offset along width direction.
        :param roi.hoffset: (int) ROI offset along height direction.

        """

        params = {
            "exposure_time": exposure_time_sec,
            "burst_num": burst_num,
            "binning": binning,
            "roi": roi,
        }
        return self.configure(params, label="hard_trigger")
