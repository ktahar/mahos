#!/usr/bin/env python3

"""Mock instruments for iv_smu example."""

from __future__ import annotations

import enum
import time

import numpy as np

from mahos.inst.instrument import Instrument
from mahos.msgs import param_msgs as P


class Mode(enum.Enum):
    """Operation mode for mock SMU."""

    UNCONFIGURED = 0
    IV = 1
    IV_sweep = 2


class SMU_mock(Instrument):
    """Mock Source Meter Unit compatible with :class:`mahos.inst.smu_interface.SMUInterface`.

    The class provides a deterministic virtual IV characteristic with Gaussian noise.
    It implements the subset of Keithley 2450 behavior used by ``examples/iv_smu/iv.py``
    so that the example can run without VISA hardware.

    :param resource: Dummy resource string (only used on log message).
    :type resource: str
    :param volt_bounds: Source voltage bounds in V.
    :type volt_bounds: list[float] | tuple[float, float]
    :param curr_bounds: Measurement current bounds in A.
    :type curr_bounds: list[float] | tuple[float, float]
    :param resistance_ohm: Resistance used for mock I = V / R model.
    :type resistance_ohm: float
    :param noise_std: Gaussian noise std added to generated current values in A.
    :type noise_std: float
    :param seed: RNG seed for reproducible dummy data.
    :type seed: int

    """

    def __init__(self, name, conf, prefix=None):
        """Initialize mock SMU state."""

        Instrument.__init__(self, name, conf=conf, prefix=prefix)

        self.check_required_conf(["resource"])
        self.logger.info(f"Open mock SMU at {self.conf['resource']}.")

        self.volt_min, self.volt_max = self.conf.get("volt_bounds", (-200.0, 200.0))
        self.curr_min, self.curr_max = self.conf.get("curr_bounds", (-105e-3, 105e-3))
        self.resistance_ohm = float(self.conf.get("resistance_ohm", 1_000.0))
        self.noise_std = float(self.conf.get("noise_std", 1e-6))

        if self.resistance_ohm <= 0.0:
            raise ValueError("conf.resistance_ohm must be positive.")
        if self.noise_std < 0.0:
            raise ValueError("conf.noise_std must be non-negative.")

        seed = self.conf.get("seed")
        self._rng = np.random.default_rng(seed)

        self._mode = Mode.UNCONFIGURED
        self._output = False
        self._source_v = 0.0
        self._delay = 0.0
        self._sweep_points = 2
        self._sweep_start = 0.0
        self._sweep_stop = 0.1
        self._sweep_log = False
        self._compliance = self.curr_max
        self._nplc = 10.0

    def get_voltage_bounds(self) -> tuple[float, float]:
        """Get voltage bounds."""

        return self.volt_min, self.volt_max

    def get_current_bounds(self) -> tuple[float, float]:
        """Get current bounds."""

        return self.curr_min, self.curr_max

    def get_bounds(self) -> dict[str, tuple[float, float]]:
        """Get voltage/current bounds."""

        return {
            "voltage": self.get_voltage_bounds(),
            "current": self.get_current_bounds(),
        }

    def _in_voltage_bounds(self, value: float) -> bool:
        """Check if voltage is inside configured bounds."""

        return self.volt_min <= value <= self.volt_max

    def set_source_volt(self, volt: float) -> bool:
        """Set source voltage for IV mode."""

        if not self._in_voltage_bounds(volt):
            return self.fail_with(
                f"Voltage {volt:.6f} is out of bounds [{self.volt_min}, {self.volt_max}]."
            )
        self._source_v = float(volt)
        return True

    def configure_IV(self, compliance: float, nplc: float) -> bool:
        """Configure fixed-voltage current readout mode."""

        self._compliance = float(compliance)
        self._nplc = float(nplc)
        self._mode = Mode.IV
        self.logger.info("Configured mock SMU for DC IV mode.")
        return True

    def configure_IV_sweep(
        self,
        compliance: float = 105e-3,
        delay: float = 0.1,
        start: float = 0.0,
        stop: float = 0.1,
        point: int = 2,
        nplc: float = 10.0,
        auto_range: bool | None = None,
        log: bool = False,
    ) -> bool:
        """Configure IV sweep mode."""

        if point < 2:
            return self.fail_with("point must be >= 2 for IV_sweep.")
        if not self._in_voltage_bounds(start) or not self._in_voltage_bounds(stop):
            return self.fail_with(
                f"Sweep bounds ({start}, {stop}) are out of voltage bounds "
                f"[{self.volt_min}, {self.volt_max}]."
            )
        if log and (start <= 0.0 or stop <= 0.0):
            return self.fail_with("Log sweep requires both start and stop > 0.")
        if nplc <= 0.0:
            return self.fail_with("nplc must be positive.")
        if delay < 0.0:
            return self.fail_with("delay must be non-negative.")
        if auto_range is not None:
            self.logger.debug(f"Ignoring auto_range={auto_range} in mock SMU.")

        self._sweep_start = float(start)
        self._sweep_stop = float(stop)
        self._sweep_points = int(point)
        self._sweep_log = bool(log)
        self._compliance = float(compliance)
        self._nplc = float(nplc)
        self._delay = float(delay)
        self._mode = Mode.IV_sweep
        self.logger.info("Configured mock SMU for IV sweep mode.")
        return True

    def _current_model(self, voltages: np.ndarray) -> np.ndarray:
        """Generate mock current values from source voltages."""

        currents = voltages / self.resistance_ohm
        if self.noise_std > 0.0:
            currents = currents + self._rng.normal(0.0, self.noise_std, size=voltages.shape)
        clip = min(abs(self._compliance), abs(self.curr_min), abs(self.curr_max))
        return np.clip(currents, -clip, clip)

    def _sweep_voltages(self) -> np.ndarray:
        """Generate configured sweep voltages."""

        if self._sweep_log:
            return np.logspace(
                np.log10(self._sweep_start), np.log10(self._sweep_stop), self._sweep_points
            )
        return np.linspace(self._sweep_start, self._sweep_stop, self._sweep_points)

    def get_data_IV(self) -> float:
        """Get one current sample for IV mode."""

        value = self._current_model(np.array([self._source_v], dtype=np.float64))[0]
        return float(value)

    def get_data_IV_sweep(self) -> np.ndarray:
        """Get current samples for one IV sweep."""

        time.sleep(self._delay * self._sweep_points)
        return self._current_model(self._sweep_voltages())

    def get_data(self) -> float | np.ndarray | None:
        """Get measurement data for current mode."""

        if self._mode == Mode.IV:
            return self.get_data_IV()
        if self._mode == Mode.IV_sweep:
            return self.get_data_IV_sweep()
        self.logger.error("get_data() is called but not configured.")
        return None

    def get_unit(self) -> str:
        """Get measurement unit string."""

        if self._mode in (Mode.IV, Mode.IV_sweep):
            return "A"
        self.logger.error("get_unit() is called but not configured.")
        return ""

    def start(self, label: str = "") -> bool:
        """Start output after configuration."""

        if self._mode in (Mode.IV, Mode.IV_sweep):
            self._output = True
            return True
        return self.fail_with("start() is called but not configured.")

    def stop(self, label: str = "") -> bool:
        """Stop output."""

        if self._mode in (Mode.IV, Mode.IV_sweep):
            self._output = False
            return True
        return self.fail_with("stop() is called but not configured.")

    def get_param_dict_labels(self) -> list[str]:
        """Get available ParamDict labels."""

        return ["IV_source", "IV", "IV_sweep"]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        """Get ParamDict for ``label``."""

        if label == "IV_source":
            return P.ParamDict(
                volt=P.FloatParam(0.0, self.volt_min, self.volt_max, unit="V", SI_prefix=True)
            )
        if label == "IV":
            return P.ParamDict(
                compliance=P.FloatParam(
                    self.curr_max, self.curr_min, self.curr_max, unit="A", SI_prefix=True
                ),
                nplc=P.FloatParam(10.0, 0.01, 10.0),
            )
        if label == "IV_sweep":
            return P.ParamDict(
                start=P.FloatParam(0.0, self.volt_min, self.volt_max, unit="V", SI_prefix=True),
                stop=P.FloatParam(0.1, self.volt_min, self.volt_max, unit="V", SI_prefix=True),
                auto_range=P.BoolParam(True),
                log=P.BoolParam(False),
                point=P.IntParam(2, 2, 1_000_000),
                nplc=P.FloatParam(10.0, 0.01, 10.0),
                compliance=P.FloatParam(
                    self.curr_max, self.curr_min, self.curr_max, unit="A", SI_prefix=True
                ),
                delay=P.FloatParam(0.1, 0.0, 10.0),
            )
        return self.fail_with(f"unknown label {label}")

    def configure(self, params: dict, label: str = "") -> bool:
        """Configure mock SMU by ``label``."""

        label = label.lower()
        if label == "iv_source":
            return self.set_source_volt(volt=params.get("volt", 0.0))
        if label == "iv":
            return self.configure_IV(
                compliance=params.get("compliance", self.curr_max),
                nplc=params.get("nplc", 10.0),
            )
        if label == "iv_sweep":
            return self.configure_IV_sweep(
                start=params.get("start", 0.0),
                stop=params.get("stop", 0.1),
                log=params.get("log", False),
                point=params.get("point", 2),
                nplc=params.get("nplc", 10.0),
                auto_range=params.get("auto_range", True),
                delay=params.get("delay", 0.1),
                compliance=params.get("compliance", self.curr_max),
            )
        return self.fail_with(f"unknown label: {label}")

    def set(self, key: str, value=None, label: str = "") -> bool:
        """Set a value in current mode."""

        if key == "volt":
            return self.set_source_volt(float(value))
        return self.fail_with(f"unknown set() key: {key}")

    def get(self, key: str, args=None, label: str = ""):
        """Get status/data values."""

        if key == "opc":
            return True
        if key == "bounds":
            return self.get_bounds()
        if key == "data":
            return self.get_data()
        if key == "unit":
            return self.get_unit()
        self.logger.error(f"unknown get() key: {key}")
        return None
