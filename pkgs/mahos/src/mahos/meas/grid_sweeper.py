#!/usr/bin/env python3

"""
GridSweeper measurement node and worker.

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
from mahos.meas.grid_sweeper_io import GridSweeperIO
from mahos.msgs import grid_sweeper_msgs
from mahos.msgs import param_msgs as P
from mahos.msgs.common_msgs import BinaryState, BinaryStatus, Reply, StateReq
from mahos.msgs.common_msgs import ExportDataReq, LoadDataReq, SaveDataReq
from mahos.msgs.grid_sweeper_msgs import GridSweeperData
from mahos.msgs.param_msgs import GetParamDictLabelsReq, GetParamDictReq
from mahos.util.timer import IntervalTimer
from mahos.util.typing import NodeName


class GridSweeperClient(BasicMeasClient):
    """Client for GridSweeper node."""

    M = grid_sweeper_msgs

    def get_data(self) -> GridSweeperData:
        return self._get_data()


class GridSweepWorker(Worker):
    """Worker for two-parameter sweep measurement."""

    def __init__(self, cli: MultiInstrumentClient, logger, conf: dict):
        Worker.__init__(self, cli, logger, conf)
        self.check_required_conf(["x", "y", "measure"])

        x_conf = conf["x"]
        y_conf = conf["y"]
        meas_conf = conf["measure"]

        self.x_inst = InstrumentInterface(cli, x_conf["inst"])
        self.y_inst = InstrumentInterface(cli, y_conf["inst"])
        self.meas_inst = InstrumentInterface(cli, meas_conf["inst"])
        self.add_instruments(self.x_inst, self.y_inst, self.meas_inst)

        # Store x-axis sweep config
        self.x_key = x_conf["key"]
        self.x_label = x_conf.get("label", "")
        self.x_unit = x_conf.get("unit", "")
        self.x_SI_prefix = x_conf.get("SI_prefix", True)
        self.x_digit = x_conf.get("digit", 6)
        self.x_step = x_conf.get("step", 1.0)
        self.x_adaptive_step = x_conf.get("adaptive_step", False)
        self.x_bounds = x_conf.get("bounds")

        # Store y-axis sweep config
        self.y_key = y_conf["key"]
        self.y_label = y_conf.get("label", "")
        self.y_unit = y_conf.get("unit", "")
        self.y_SI_prefix = y_conf.get("SI_prefix", True)
        self.y_digit = y_conf.get("digit", 6)
        self.y_step = y_conf.get("step", 1.0)
        self.y_adaptive_step = y_conf.get("adaptive_step", False)
        self.y_bounds = y_conf.get("bounds")

        # Store measure config
        self.meas_key = meas_conf["key"]
        self.meas_label = meas_conf.get("label", "")
        self.meas_unit = meas_conf.get("unit", "")

        self.data = GridSweeperData()
        self._x_values: NDArray[np.float64] | None = None
        self._y_values: NDArray[np.float64] | None = None
        self._y_idx: int = 0

    def get_param_dict_labels(self) -> list[str]:
        return [""]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        x_bounds = self._get_bounds(self.x_inst, self.x_key, self.x_label, self.x_bounds)
        y_bounds = self._get_bounds(self.y_inst, self.y_key, self.y_label, self.y_bounds)

        pd = P.ParamDict()
        pd["x"] = P.ParamDict(
            start=P.FloatParam(
                x_bounds[0],
                x_bounds[0],
                x_bounds[1],
                unit=self.x_unit,
                SI_prefix=self.x_SI_prefix,
                digit=self.x_digit,
                step=self.x_step,
                adaptive_step=self.x_adaptive_step,
                doc="start value",
            ),
            stop=P.FloatParam(
                x_bounds[1],
                x_bounds[0],
                x_bounds[1],
                unit=self.x_unit,
                SI_prefix=self.x_SI_prefix,
                digit=self.x_digit,
                step=self.x_step,
                adaptive_step=self.x_adaptive_step,
                doc="stop value",
            ),
            num=P.IntParam(51, 2, 10001, doc="number of points"),
            log=P.BoolParam(False, doc="use log-space sweep"),
            delay=P.FloatParam(
                0.01,
                0.0,
                100.0,
                unit="s",
                SI_prefix=True,
                step=0.1,
                adaptive_step=True,
                doc="delay after setting x",
            ),
        )
        pd["y"] = P.ParamDict(
            start=P.FloatParam(
                y_bounds[0],
                y_bounds[0],
                y_bounds[1],
                unit=self.y_unit,
                SI_prefix=self.y_SI_prefix,
                digit=self.y_digit,
                step=self.y_step,
                adaptive_step=self.y_adaptive_step,
                doc="start value",
            ),
            stop=P.FloatParam(
                y_bounds[1],
                y_bounds[0],
                y_bounds[1],
                unit=self.y_unit,
                SI_prefix=self.y_SI_prefix,
                digit=self.y_digit,
                step=self.y_step,
                adaptive_step=self.y_adaptive_step,
                doc="stop value",
            ),
            num=P.IntParam(51, 2, 10001, doc="number of points"),
            log=P.BoolParam(False, doc="use log-space sweep"),
            delay=P.FloatParam(
                0.0,
                0.0,
                100.0,
                unit="s",
                SI_prefix=True,
                step=0.1,
                adaptive_step=True,
                doc="delay after setting y",
            ),
        )
        pd["sweeps"] = P.IntParam(1, 0, 10000, doc="number of 2D sweeps (0 for infinite)")
        return pd

    def _get_bounds(
        self,
        inst: InstrumentInterface,
        key: str,
        label: str,
        conf_bounds: tuple[float, float] | list[float] | None,
    ) -> tuple[float, float]:
        """Get bounds for one sweep parameter."""

        # Priority 1: conf
        if conf_bounds is not None:
            return tuple(conf_bounds)

        # Priority 2: instrument
        try:
            inst_bounds = inst.get("bounds", label=label)
            if inst_bounds is not None:
                if isinstance(inst_bounds, dict):
                    return inst_bounds[key]
                else:
                    return tuple(inst_bounds)
        except Exception:
            pass

        # Priority 3: fallback with warning
        self.logger.warning(
            f"Using default bounds (-1e6, 1e6) for '{key}'. Consider setting bounds in config."
        )
        return (-1e6, 1e6)

    def _check_axis_params(self, params: dict, axis: str) -> bool:
        if axis not in params:
            self.logger.error(f"Missing '{axis}' params.")
            return False
        if not isinstance(params[axis], dict):
            self.logger.error(f"'{axis}' params must be dict.")
            return False
        for key in ("start", "stop", "num"):
            if key not in params[axis]:
                self.logger.error(f"Missing '{axis}.{key}' params.")
                return False
        return True

    def _generate_axis_values(self, params: dict, axis: str) -> NDArray[np.float64]:
        p = params[axis]
        if p.get("log", False):
            if p["start"] <= 0.0 or p["stop"] <= 0.0:
                raise ValueError(f"{axis}.start and {axis}.stop must be positive for log sweep.")
            return np.logspace(np.log10(p["start"]), np.log10(p["stop"]), p["num"])
        else:
            return np.linspace(p["start"], p["stop"], p["num"])

    def _append_empty_sweep_plane(self):
        if self.data.data is None:
            return
        empty = np.full(
            (self.data.data.shape[0], self.data.data.shape[1], 1),
            np.nan,
            dtype=np.float64,
        )
        self.data.data = np.append(self.data.data, empty, axis=2)

    def start(self, params: P.ParamDict[str, P.PDValue] | dict) -> bool:
        params = P.unwrap(params)
        if params is None:
            self.logger.error("params is None.")
            return False

        if not (self._check_axis_params(params, "x") and self._check_axis_params(params, "y")):
            return False

        if not self.lock_instruments():
            return self.fail_with_release("Failed to acquire instrument locks.")

        # Add metadata for data class.
        params["x"]["key"] = self.x_key
        params["x"]["unit"] = self.x_unit
        params["y"]["key"] = self.y_key
        params["y"]["unit"] = self.y_unit
        params["measure"] = {"key": self.meas_key, "unit": self.meas_unit}

        try:
            self._x_values = self._generate_axis_values(params, "x")
            self._y_values = self._generate_axis_values(params, "y")
        except Exception:
            return self.fail_with_release("Failed to generate x/y sweep values.")

        self.data = GridSweeperData(params)
        self.data.data = np.full(
            (self._x_values.size, self._y_values.size, 1),
            np.nan,
            dtype=np.float64,
        )
        self._y_idx = 0
        self.data.completed_sweeps = 0
        self.data.start()
        self.logger.info("Started grid sweeper.")
        return True

    def stop(self) -> bool:
        if not self.data.running:
            return False

        success = self.release_instruments()
        self.data.finalize()

        if success:
            self.logger.info("Stopped grid sweeper.")
        else:
            self.logger.error("Error stopping grid sweeper.")
        return success

    def sweep_line(self, y_val: float) -> NDArray[np.float64] | None:
        if self._x_values is None:
            return None

        x_delay = self.data.params["x"].get("delay", 0.0)
        y_delay = self.data.params["y"].get("delay", 0.0)
        line = []

        if not self.y_inst.set(self.y_key, y_val, label=self.y_label):
            self.logger.error(f"Failed to set {self.y_key} to {y_val}")
            return None
        if y_delay > 0:
            time.sleep(y_delay)

        for x_val in self._x_values:
            if not self.x_inst.set(self.x_key, x_val, label=self.x_label):
                self.logger.error(f"Failed to set {self.x_key} to {x_val}")
                return None

            if x_delay > 0:
                time.sleep(x_delay)

            result = self.meas_inst.get(self.meas_key, label=self.meas_label)
            if result is None:
                self.logger.error(f"Failed to get {self.meas_key}")
                return None

            line.append(result)

        return np.array(line, dtype=np.float64)

    def work(self) -> bool:
        """Perform one line sweep along x at current y index."""

        if self._x_values is None or self._y_values is None or self.data.data is None:
            return False

        if self._y_idx >= self._y_values.size:
            return False

        line = self.sweep_line(self._y_values[self._y_idx])
        if line is None:
            return False

        self.data.data[:, self._y_idx, -1] = line
        self._y_idx += 1

        # One 2D sweep completed.
        if self._y_idx >= self._y_values.size:
            self.data.completed_sweeps += 1
            self._y_idx = 0
            sweeps = self.data.params.get("sweeps", 0)
            if sweeps <= 0 or self.data.completed_sweeps < sweeps:
                self._append_empty_sweep_plane()

        return True

    def is_finished(self) -> bool:
        """Check if measurement is complete."""

        if self.data.params is None:
            return False
        sweeps = self.data.params.get("sweeps", 0)
        if sweeps <= 0:
            return False  # Infinite sweeps
        return self.data.completed_sweeps >= sweeps

    def data_msg(self) -> GridSweeperData:
        return self.data


class GridSweeper(BasicMeasNode):
    """Two-dimensional grid sweep measurement node.

    GridSweeper controls two independent sweep parameters (``x`` and ``y`` config sections)
    and reads one measurement quantity (``measure`` section) on each grid point. The acquired
    result is stored as image stack data (:class:`~mahos.msgs.grid_sweeper_msgs.GridSweeperData`)
    with optional repeated 2D sweeps.

    Runtime behavior:

    - Uses ``set()`` and ``get()`` APIs for target instruments.
    - For each grid point, calls ``set(y.key, value, label=y.label)`` and
      ``set(x.key, value, label=x.label)`` (with configured delays), then calls
      ``get(measure.key, label=measure.label)``.
    - Does not call ``get_param_dict()``, ``configure()``, ``start()``, or ``stop()``
      for target instruments by design.

    If a target instrument requires pre-configuration or start/stop signaling, users
    should invoke those APIs manually via Tweaker, scripts, or interactive sessions
    before running GridSweeper.

    :param x: X-axis instrument configuration dictionary.
    :type x: dict
    :param x.inst: Instrument name to control for the x-axis.
    :type x.inst: str
    :param y: Y-axis instrument configuration dictionary.
    :type y: dict
    :param y.inst: Instrument name to control for the y-axis.
    :type y.inst: str
    :param measure: Measurement instrument configuration dictionary.
    :type measure: dict
    :param measure.inst: Instrument name to read at each grid point.
    :type measure.inst: str
    :param pub_interval_sec: Maximum interval between periodic status/data publications.
    :type pub_interval_sec: float

    """

    CLIENT = GridSweeperClient
    DATA = GridSweeperData

    def __init__(self, gconf: dict, name: NodeName, context=None):
        BasicMeasNode.__init__(self, gconf, name, context=context)
        self.worker = GridSweepWorker(self.cli, self.logger, self.conf)
        self.io = GridSweeperIO(self.logger)
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
        insts = [self.conf["x"]["inst"], self.conf["y"]["inst"], self.conf["measure"]["inst"]]
        for inst in dict.fromkeys(insts):
            self.cli.wait(inst)
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
