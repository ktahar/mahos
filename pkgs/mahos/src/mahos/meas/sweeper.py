#!/usr/bin/env python3

"""
Sweeper measurement node and worker.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import time

import numpy as np
from numpy.typing import NDArray

from mahos.inst.interface import InstrumentInterface
from mahos.inst.server import MultiInstrumentClient
from mahos.meas.common_meas import BasicMeasClient, BasicMeasNode
from mahos.meas.common_worker import Worker
from mahos.meas.sweeper_io import SweeperIO
from mahos.msgs import param_msgs as P
from mahos.msgs import sweeper_msgs
from mahos.msgs.common_msgs import BinaryState, BinaryStatus, Reply, StateReq
from mahos.msgs.common_msgs import ExportDataReq, LoadDataReq, SaveDataReq
from mahos.msgs.param_msgs import GetParamDictLabelsReq, GetParamDictReq
from mahos.msgs.sweeper_msgs import SweeperData
from mahos.util.timer import IntervalTimer
from mahos.util.typing import NodeName


class SweeperClient(BasicMeasClient):
    """Client for Sweeper node."""

    M = sweeper_msgs

    def get_data(self) -> SweeperData:
        return self._get_data()


class SweepWorker(Worker):
    """Worker for parameter sweep measurement."""

    def __init__(self, cli: MultiInstrumentClient, logger, conf: dict):
        Worker.__init__(self, cli, logger, conf)
        self.check_required_conf(["x", "measure"])

        x_conf = conf["x"]
        meas_conf = conf["measure"]

        self.x_inst = InstrumentInterface(cli, x_conf["inst"])
        self.meas_inst = InstrumentInterface(cli, meas_conf["inst"])
        self.add_instruments(self.x_inst, self.meas_inst)

        # Store x-axis sweep config
        self.x_key = x_conf["key"]
        self.x_label = x_conf.get("label", "")
        self.x_unit = x_conf.get("unit", "")
        self.x_SI_prefix = x_conf.get("SI_prefix", True)
        self.x_digit = x_conf.get("digit", 6)
        self.x_step = x_conf.get("step", 1.0)
        self.x_adaptive_step = x_conf.get("adaptive_step", False)
        self.x_bounds = x_conf.get("bounds")

        # Store measure config
        self.meas_key = meas_conf["key"]
        self.meas_label = meas_conf.get("label", "")
        self.meas_unit = meas_conf.get("unit", "")

        self.data = SweeperData()
        self._x_values: NDArray | None = None

    def get_param_dict_labels(self) -> list[str]:
        return [""]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        bounds = self._get_bounds()

        pd = P.ParamDict()
        pd["start"] = P.FloatParam(
            bounds[0],
            bounds[0],
            bounds[1],
            unit=self.x_unit,
            SI_prefix=self.x_SI_prefix,
            digit=self.x_digit,
            step=self.x_step,
            adaptive_step=self.x_adaptive_step,
            doc="start value",
        )
        pd["stop"] = P.FloatParam(
            bounds[1],
            bounds[0],
            bounds[1],
            unit=self.x_unit,
            SI_prefix=self.x_SI_prefix,
            digit=self.x_digit,
            step=self.x_step,
            adaptive_step=self.x_adaptive_step,
            doc="stop value",
        )
        pd["num"] = P.IntParam(51, 2, 10001, doc="number of points")
        pd["delay"] = P.FloatParam(
            0.01,
            0.0,
            100.0,
            unit="s",
            SI_prefix=True,
            step=0.1,
            adaptive_step=True,
            doc="delay after set",
        )
        pd["sweeps"] = P.IntParam(1, 0, 10000, doc="number of sweeps (0 for infinite)")
        pd["log"] = P.BoolParam(False, doc="use log-space sweep")

        return pd

    def _get_bounds(self) -> tuple[float, float]:
        """Get sweep parameter bounds."""

        # Priority 1: conf
        if self.x_bounds is not None:
            return tuple(self.x_bounds)

        # Priority 2: instrument
        try:
            inst_bounds = self.x_inst.get("bounds", label=self.x_label)
            if inst_bounds is not None:
                if isinstance(inst_bounds, dict):
                    return inst_bounds[self.x_key]
                else:
                    return tuple(inst_bounds)
        except Exception:
            pass

        # Priority 3: fallback with warning
        self.logger.warning("Using default bounds (-1e6, 1e6). Consider setting bounds in config.")
        return (-1e6, 1e6)

    def _generate_x_values(self, params: dict) -> NDArray[np.float64]:
        """Generate sweep values array."""

        if params.get("log", False):
            if params["start"] <= 0.0 or params["stop"] <= 0.0:
                raise ValueError("start and stop must be positive for log sweep.")
            return np.logspace(
                np.log10(params["start"]),
                np.log10(params["stop"]),
                params["num"],
            )
        else:
            return np.linspace(params["start"], params["stop"], params["num"])

    def start(self, params: P.ParamDict[str, P.PDValue] | dict) -> bool:
        params = P.unwrap(params)
        if params is None:
            self.logger.error("params is None.")
            return False

        req_keys = ["start", "stop", "num"]
        if not self.check_required_params(params, req_keys):
            return False

        if not self.lock_instruments():
            return self.fail_with_release("Failed to acquire instrument locks.")

        # Add axis labels to params for data class
        params["x_key"] = self.x_key
        params["x_unit"] = self.x_unit
        params["meas_key"] = self.meas_key
        params["meas_unit"] = self.meas_unit

        try:
            self._x_values = self._generate_x_values(params)
        except Exception:
            return self.fail_with_release("Failed to generate sweep values.")

        self.data = SweeperData(params)
        self.data.start()
        self.logger.info("Started sweeper.")
        return True

    def stop(self) -> bool:
        if not self.data.running:
            return False

        success = self.release_instruments()
        self.data.finalize()

        if success:
            self.logger.info("Stopped sweeper.")
        else:
            self.logger.error("Error stopping sweeper.")
        return success

    def sweep_once(self) -> NDArray[np.float64] | None:
        if self._x_values is None:
            return None

        delay = self.data.params.get("delay", 0.0)
        data = []

        for val in self._x_values:
            # Set sweep parameter
            if not self.x_inst.set(self.x_key, val, label=self.x_label):
                self.logger.error(f"Failed to set {self.x_key} to {val}")
                return None

            # Wait for settling
            if delay > 0:
                time.sleep(delay)

            # Measure
            result = self.meas_inst.get(self.meas_key, label=self.meas_label)
            if result is None:
                self.logger.error(f"Failed to get {self.meas_key}")
                return None

            data.append(result)

        return np.array(data)

    def append_sweep(self, line: NDArray[np.float64]):
        line = np.array(line, ndmin=2).T
        if self.data.data is None:
            self.data.data = line
        else:
            self.data.data = np.append(self.data.data, line, axis=1)

    def work(self) -> bool:
        """Perform one sweep iteration."""

        line = self.sweep_once()
        if line is None:
            return False
        self.append_sweep(line)
        return True

    def is_finished(self) -> bool:
        """Check if measurement is complete."""

        if self.data.params is None or self.data.data is None:
            return False
        sweeps = self.data.params.get("sweeps", 0)
        if sweeps <= 0:
            return False  # Infinite sweeps
        return self.data.sweeps() >= sweeps

    def data_msg(self) -> SweeperData:
        return self.data


class Sweeper(BasicMeasNode):
    """One-dimensional parameter sweep measurement node.

    Sweeper controls one instrument parameter (``x`` config section) and reads one
    measurement quantity (``measure`` section) at each point. Each run produces line data
    (:class:`~mahos.msgs.sweeper_msgs.SweeperData`) with optional repeated sweeps.

    Runtime behavior:

    - Uses ``set()`` and ``get()`` APIs for target instruments.
    - At each sweep point, calls ``set(x.key, value, label=x.label)`` on ``x.inst``,
      waits for ``delay``, and calls ``get(measure.key, label=measure.label)`` on
      ``measure.inst``.
    - Does not call ``get_param_dict()``, ``configure()``, ``start()``, or ``stop()``
      for target instruments by design.

    If a target instrument requires pre-configuration or start/stop signaling, users
    should invoke those APIs manually via Tweaker, scripts, or interactive sessions
    before running Sweeper.

    Supported basic requests are inherited from
    :class:`~mahos.meas.common_meas.BasicMeasNode`:
    start / stop, parameter dict query, save / load / export, and fit / clear_fit.

    :param x: Sweep-axis instrument configuration dictionary.
    :type x: dict
    :param x.inst: Instrument name to control for the sweep axis.
    :type x.inst: str
    :param measure: Measurement instrument configuration dictionary.
    :type measure: dict
    :param measure.inst: Instrument name to read at each sweep point.
    :type measure.inst: str
    :param pub_interval_sec: Maximum interval between periodic status/data publications.
    :type pub_interval_sec: float

    """

    CLIENT = SweeperClient
    DATA = SweeperData

    def __init__(self, gconf: dict, name: NodeName, context=None):
        BasicMeasNode.__init__(self, gconf, name, context=context)
        self.worker = SweepWorker(self.cli, self.logger, self.conf)
        self.io = SweeperIO(self.logger)
        self.pub_timer = IntervalTimer(self.conf.get("pub_interval_sec", 0.5))

    def close_resources(self):
        if hasattr(self, "worker"):
            self.worker.stop()

    def change_state(self, msg: StateReq) -> Reply:
        if self.state == msg.state:
            return Reply(True, "Already in that state")

        if msg.state == BinaryState.IDLE:
            if not self.worker.stop():
                return Reply(False, "Failed to stop worker.", ret=self.state)
        elif msg.state == BinaryState.ACTIVE:
            if not self.worker.start(msg.params):
                return Reply(False, "Failed to start worker.", ret=self.state)

        self.state = msg.state
        return Reply(True)

    def get_param_dict_labels(self, msg: GetParamDictLabelsReq) -> Reply:
        return Reply(True, ret=self.worker.get_param_dict_labels())

    def get_param_dict(self, msg: GetParamDictReq) -> Reply:
        d = self.worker.get_param_dict(msg.label)
        if d is None:
            return Reply(False, "Failed to generate param dict")
        return Reply(True, ret=d)

    def save_data(self, msg: SaveDataReq) -> Reply:
        success = self.io.save_data(msg.file_name, self.worker.data_msg(), msg.note)
        if success:
            for tweaker_name, cli in self.tweaker_clis.items():
                success &= cli.save(msg.file_name, "__" + tweaker_name + "__")
        return Reply(success)

    def export_data(self, msg: ExportDataReq) -> Reply:
        success = self.io.export_data(
            msg.file_name,
            msg.data if msg.data else self.worker.data_msg(),
            msg.params,
        )
        return Reply(success)

    def load_data(self, msg: LoadDataReq) -> Reply:
        data = self.io.load_data(msg.file_name)
        if data is None:
            return Reply(False)
        if msg.to_buffer:
            self.logger.error("Cannot load data to buffer.")
            return Reply(False, "Cannot load data to buffer.")
        if self.state == BinaryState.ACTIVE:
            return Reply(False, "Cannot load data when active.")
        self.worker.data = data
        return Reply(True, ret=data)

    def wait(self):
        self.logger.info("Waiting for instrument servers...")
        x_inst = self.conf["x"]["inst"]
        meas_inst = self.conf["measure"]["inst"]
        self.cli.wait(x_inst)
        if meas_inst != x_inst:
            self.cli.wait(meas_inst)
        self.logger.info("Instrument servers are up!")

    def main(self):
        self.poll()
        data_updated = self._work()
        finished = self._check_finished()
        time_to_pub = self.pub_timer.check()
        self._publish(data_updated or finished or time_to_pub)

    def _work(self) -> bool:
        if self.state == BinaryState.ACTIVE:
            return self.worker.work()
        return False

    def _publish(self, publish_data: bool):
        self.status_pub.publish(BinaryStatus(state=self.state))
        if publish_data:
            self.data_pub.publish(self.worker.data_msg())

    def _check_finished(self):
        if self.state == BinaryState.ACTIVE and self.worker.is_finished():
            self.change_state(StateReq(BinaryState.IDLE))
