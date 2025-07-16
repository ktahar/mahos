#!/usr/bin/env python3

"""
PI part of Positioner module.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

from pipython import GCSDevice

from ..exceptions import InstError
from ..instrument import Instrument
from ...msgs import param_msgs as P


class PI_OneAxis_USB(Instrument):
    """Base class for PI's One-Axis positioner with USB connection.

    You need to install PI GCS software and pipython.

    :param dev: The device model number.
    :type dev: str
    :param mask: (default: dev) Mask string to discriminate multiple devices.
        Blank will be fine if only one device is connected.
    :type mask: str
    :param range: (default: limits defined for the device) travel range.
        (lower, upper) bounds of the position.
    :type range: tuple[float, float]

    """

    def __init__(self, name, conf=None, prefix=None):
        Instrument.__init__(self, name, conf, prefix=prefix)

        self.dev = GCSDevice(self.conf["dev"])
        devs = self.dev.EnumerateUSB(mask=self.conf.get("mask", self.conf["dev"]))
        if len(devs) != 1:
            raise InstError(
                self.full_name(),
                f"Cannot initialize as there's no device or multiple devices: {devs}",
            )
        self.dev.ConnectUSB(devs[0])
        self.logger.info(f"Connected to {devs[0]}.")

        ids = self.dev.qSAI()
        if len(ids) != 1:
            raise InstError(
                self.full_name(),
                f"Cannot initialize as there's more than one axes: {ids}",
            )
        self.ax = ids[0]
        self.logger.info(f"Axis ID is {self.ax}.")

        self.limits = [self.dev.qNLM(self.ax), self.dev.qPLM(self.ax)]
        self.logger.debug(f"limits: {self.limits[0]:.3f} {self.limits[1]:.3f}")
        self.range = self.conf.get("range", self.limits)
        if self.range[0] < self.limits[0]:
            msg = f"Given range is out of limit: {self.range[0]} < {self.limits[0]}"
            self.logger.error(msg)
            raise ValueError(msg)
        if self.range[1] > self.limits[1]:
            msg = f"Given range is out of limit: {self.range[1]} > {self.limits[1]}"
            self.logger.error(msg)
            raise ValueError(msg)
        self.logger.info(f"range: {self.range[0]:.3f} {self.range[1]:.3f}")

    def _stop(self) -> bool:
        self.dev.STP(noraise=True)
        return True

    def move(self, pos: float) -> bool:
        if pos < self.range[0] or pos > self.range[1]:
            return self.fail_with(f"Target pos {pos:.3f} is out of range {self.range}.")
        self.dev.MOV(self.ax, pos)
        return True

    def get_moving(self) -> bool:
        # Maybe we can use ONT as well?
        return self.dev.IsMoving(self.ax)[self.ax]

    def home(self) -> bool:
        # Assume the device is already homed.
        return True

    def is_homed(self) -> bool:
        # Assume the device is already homed.
        return True

    def get_status(self) -> dict:
        return {
            "homed": self.is_homed(),
            "moving": self.get_moving(),
        }

    def get_pos(self) -> float:
        self.dev.qPOS(self.ax)[self.ax]

    def get_target(self) -> float:
        self.dev.qMOV(self.ax)[self.ax]

    def get_all(self) -> dict[str, [float, bool]]:
        """Get all important info about this device packed in a dict.

        :returns pos: current position.
        :returns target: target position.
        :returns range: travel range.
        :returns homed: True if device is homed.
        :returns moving: True if device is moving.

        """

        d = self.get_status()
        d["pos"] = self.get_pos()
        d["target"] = self.get_target()
        d["range"] = self.get_range()

        return d

    def get_range(self) -> tuple[float, float]:
        return self.range

    def close_resources(self):
        if hasattr(self, "dev"):
            self.dev.CloseConnection()
            self.logger.info("Closed PI Device connection.")

    # Standard API

    def reset(self, label: str = "") -> bool:
        """Perform homing of this device."""

        return self.home()

    def stop(self, label: str = "") -> bool:
        """Stop motion of this device."""

        return self._stop()

    def get_param_dict_labels(self) -> list[str]:
        return ["pos"]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        """Get ParamDict for `label`."""

        if label == "pos":
            return P.ParamDict(
                target=P.FloatParam(
                    self.get_target(), self.range[0], self.range[1], doc="target position"
                )
            )
        else:
            self.logger.error(f"Unknown label: {label}")
            return None

    def configure(self, params: dict, label: str = "") -> bool:
        if label == "pos":
            return self.move(params["target"])
        else:
            return self.fail_with(f"Unknown label {label}")

    def set(self, key: str, value=None, label: str = "") -> bool:
        if key == "target":
            return self.move(value)
        else:
            return self.fail_with(f"unknown set() key: {key}")

    def get(self, key: str, args=None, label: str = ""):
        if key == "all":
            return self.get_all()
        elif key == "pos":
            return self.get_pos()
        elif key == "target":
            return self.get_target()
        elif key == "status":
            return self.get_status()
        elif key == "range":
            return self.get_range()
        else:
            self.logger.error(f"unknown get() key: {key}")
            return None
