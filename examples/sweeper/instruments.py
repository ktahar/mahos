#!/usr/bin/env python3

"""
Mock instruments for Sweeper example.

These demonstrate the interface expected by Sweeper:
- sweep instrument: set(param, value) to set sweep parameter
- measure instrument: get(param) to read measurement

"""

import numpy as np

from mahos.inst.instrument import Instrument
from mahos.msgs import param_msgs as P


class VoltageSource_mock(Instrument):
    """Mock voltage source for sweep parameter."""

    def __init__(self, name, conf, prefix=None):
        Instrument.__init__(self, name, conf=conf, prefix=prefix)

        self.check_required_conf(["resource"])
        resource = self.conf["resource"]
        self.logger.info(f"Open VoltageSource at {resource}.")

        self._voltage = 0.0

    def set_output(self, on: bool, ch: str) -> bool:
        self.logger.info(f"Set {ch} output " + ("on" if on else "off"))
        return True

    def set_voltage(self, volt: float, ch: str) -> bool:
        self._voltage = volt
        self.logger.debug(f"Set {ch} voltage {volt:.3f} V")
        return True

    def get_voltage(self) -> float:
        return self._voltage

    def get_bounds(self) -> tuple[float, float]:
        return (-10.0, 10.0)

    # Standard API

    def start(self, label: str = "") -> bool:
        return self.set_output(True, label)

    def stop(self, label: str = "") -> bool:
        return self.set_output(False, label)

    def get_param_dict_labels(self) -> list[str]:
        return ["ch1", "ch2"]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        """Get ParamDict for `label`."""

        if label in ("ch1", "ch2"):
            return P.ParamDict(
                voltage=P.FloatParam(
                    self._voltage, -10.0, 10.0, SI_prefix=True, unit="V", doc="voltage value"
                )
            )
        else:
            self.logger.error(f"invalid label {label}")
            return None

    def configure(self, params: dict, label: str = "") -> bool:
        if label in ("ch1", "ch2"):
            return self.configure_voltage(params.get("voltage", 0.0), label)
        else:
            self.logger.error(f"invalid label {label}")
            return False

    def set(self, key: str, value=None, label: str = "") -> bool:
        if key == "voltage":
            return self.set_voltage(value, label)
        else:
            self.logger.error(f"Unknown set() key: {key}")
            return False

    def get(self, key: str, args=None, label: str = ""):
        if key == "voltage":
            return self.get_voltage()
        elif key == "bounds":
            return self.get_bounds()
        else:
            self.logger.error(f"Unknown get() key: {key}")
            return None


class Multimeter_mock(Instrument):
    """Mock multimeter for measurement."""

    def __init__(self, name, conf, prefix=None):
        Instrument.__init__(self, name, conf=conf, prefix=prefix)

        self.check_required_conf(["resource"])
        resource = self.conf["resource"]
        self.logger.info(f"Open Multimeter at {resource}.")

        self._rng = np.random.default_rng()

    def get_current(self) -> float:
        return self._rng.normal(scale=0.001)

    def get_voltage(self) -> float:
        return self._rng.normal(scale=0.1)

    # Standard API

    def get_param_dict_labels(self) -> list[str]:
        return ["current", "voltage"]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        """Get ParamDict for `label`."""

        if label == "current":
            return P.ParamDict(
                sensitivity=P.StrChoiceParam(
                    "1 mA", ("1 mA", "10 mA", "100 mA"), doc="current sensitivity"
                )
            )
        elif label == "voltage":
            return P.ParamDict(
                sensitivity=P.StrChoiceParam(
                    "1 mV", ("1 mV", "10 mV", "100 mV"), doc="current sensitivity"
                )
            )
        else:
            self.logger.error(f"invalid label {label}")
            return None

    def configure(self, params: dict, label: str = "") -> bool:
        if label in ("current", "voltage"):
            self.logger.info(f"Configured for {label} measurement")
            return True
        else:
            self.logger.error(f"Unknown label: {label}")
            return False

    def get(self, key: str, args=None, label: str = ""):
        if key == "current":
            return self.get_current()
        elif key == "voltage":
            return self.get_voltage()
        else:
            self.logger.error(f"Unknown get() key: {key}")
            return None
