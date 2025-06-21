#!/usr/bin/env python3

"""
InstrumentOverlay for sweeping ODMR.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import time
import threading

import numpy as np

from .overlay import InstrumentOverlay
from ...msgs import param_msgs as P
from ...msgs.inst.pg_msgs import TriggerType
from ...util.locked_queue import LockedQueue
from ...util.conf import PresetLoader
from ...meas.odmr_pg import ODMRPGMixin


class ODMRSweeperCommandBase(InstrumentOverlay):
    """ODMRSweeperCommandBase provides primitive operations for ODMR sweep.

    This class performs the sweep by issuing SG / PD commands every step.
    Thus, sweep speed will not be very good.

    :param sg: The reference to SG Instrument.
    :param pd: The reference to PD Instrument.
    :param queue_size: (default: 8) Size of queue of scanned line data.
    :type queue_size: int

    """

    def __init__(self, name, conf, prefix=None):
        InstrumentOverlay.__init__(self, name, conf=conf, prefix=prefix)
        self.sg = self.conf.get("sg")
        self.pd = self.conf.get("pd")
        self.add_instruments(self.sg, self.pd)

        self._queue_size = self.conf.get("queue_size", 8)
        self._queue = LockedQueue(self._queue_size)
        self._stop_ev = self._thread = None
        self.running = False

    def _set_attrs(self, params):
        self.start_f, self.stop_f = params["start"], params["stop"]
        self.freqs = np.linspace(self.start_f, self.stop_f, params["num"])
        self.power = params["power"]
        self.delay = params["delay"]
        self.background = params.get("background", False)
        self.bg_delay = params.get("background_delay", 0.0)
        self._continue_mw = params.get("continue_mw", False)

    def get_line(self):
        return self._queue.pop_block()

    def sweep_loop(self, ev: threading.Event):
        while True:
            line = []
            for f in self.freqs:
                self.sg.set_freq_CW(f)
                time.sleep(self.delay)
                res = self.get_pd_data()
                if ev.is_set():
                    self.logger.info("Quitting sweep loop.")
                    return
                line.append(res)

                if self.background:
                    self.sg.set_output(False, silent=True)
                    time.sleep(self.bg_delay)
                    res = self.get_pd_data()
                    if ev.is_set():
                        self.logger.info("Quitting sweep loop.")
                        return
                    line.append(res)
                    self.sg.set_output(True, silent=True)

            self._queue.append(np.array(line))

    def configure_pd(self):
        raise NotImplementedError("configure_pd is not implemented.")

    def get_pd_data(self):
        raise NotImplementedError("get_pd_data is not implemented.")

    def get_pd_param_dict(self) -> P.ParamDict[str, P.PDValue] | None:
        raise NotImplementedError("get_pd_param_dict is not implemented.")

    # Standard API

    def get_param_dict_labels(self) -> list[str]:
        return ["pd"]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        if label == "pd":
            return self.get_pd_param_dict()

    def configure(self, params: dict, label: str = "") -> bool:
        if label == "pulse":
            return self.fail_with("label='pulse' is not supported.")
        if not self.check_required_params(params, ("start", "stop", "num", "power", "delay")):
            return False

        self._set_attrs(params)
        self.params = params
        self._queue = LockedQueue(self._queue_size)

        if not self.configure_pd():
            return self.fail_with("failed to configure PD.")

        mod = params.get("mod", {})
        success = self.sg.configure_cw(self.start_f, self.power)
        if label == "iq_ext":
            success &= self.sg.configure_iq_ext()
        elif label == "iq_int":
            success &= self.sg.configure_iq_int()
        elif label == "fm_ext":
            success &= self.sg.configure_fm_ext(mod["fm_deviation"])
        elif label == "fm_int":
            success &= self.sg.configure_fm_int(mod["fm_deviation"], mod["fm_rate"])
        elif label == "am_ext":
            success &= self.sg.configure_am_ext(mod["am_depth"], mod["am_log"])
        elif label == "am_int":
            success &= self.sg.configure_am_int(mod["am_depth"], mod["am_log"], mod["am_rate"])
        if not success:
            return self.fail_with("failed to configure SG.")

        return True

    def start(self, label: str = "") -> bool:
        if self.running:
            self.logger.warn("start() is called while running.")
            return True

        if not self.sg.set_output(True):
            return self.fail_with("Failed to start sg.")
        if not self.pd.start():
            return self.fail_with("Failed to start pd.")

        self._stop_ev = threading.Event()
        self._thread = threading.Thread(target=self.sweep_loop, args=(self._stop_ev,))
        self._thread.start()

        self.running = True

        return True

    def stop(self, label: str = "") -> bool:
        if not self.running:
            return True
        self.running = False

        self.logger.info("Stopping sweeper.")

        self._stop_ev.set()
        self._thread.join()

        if self._continue_mw:
            self.logger.warn("Skipping to turn off MW output")
            success = True
        else:
            success = self.sg.set_output(False)
        success &= self.pd.stop()

        if not success:
            return self.fail_with("failed to stop SG or PD.")

        return True

    def get(self, key: str, args=None, label: str = ""):
        if key == "line":
            return self.get_line()
        elif key == "bounds":
            return self.sg.get_bounds()
        elif key == "unit":
            return self.pd.get("unit")
        else:
            self.logger.error(f"unknown get() key: {key}")
            return None


class ODMRSweeperCommandAnalogPD(ODMRSweeperCommandBase):
    """ODMRSweeperCommand for AnalogPD (Photo Diode read with NI-DAQ AnalogIn)."""

    def get_pd_param_dict(self) -> P.ParamDict[str, P.PDValue] | None:
        d = P.ParamDict()
        d["bounds"] = [
            P.FloatParam(-10.0, -10.0, 10.0, unit="V", doc="lower bound of expected voltage"),
            P.FloatParam(10.0, -10.0, 10.0, unit="V", doc="upper bound of expected voltage"),
        ]
        return d

    def configure_pd(self):
        t = self.params["timing"]["time_window"]
        # TODO we are not sure if AnalogIn samples at max rate for on demand readout.
        rate = self.pd.get_max_rate()
        self._oversample = int(round(t * rate))
        self.logger.info(f"AnalogPD oversample: {self._oversample}")

        return self.pd.configure_on_demand(self.params["pd"])

    def get_pd_data(self):
        return self.pd.read_on_demand(self._oversample)


class ODMRSweeperCommandAnalogPDMM(ODMRSweeperCommandBase):
    """ODMRSweeperCommand for AnalogPDMM (Photo Diode read with DMM)."""

    def get_pd_param_dict(self) -> P.ParamDict[str, P.PDValue] | None:
        return self.pd.get_param_dict("pd")

    def configure_pd(self):
        return self.pd.configure(self.params["pd"])

    def get_pd_data(self):
        return self.pd.get_data()


class ODMRSweeperPG(InstrumentOverlay, ODMRPGMixin):
    """ODMRSweeperPG provides primitive operations for ODMR sweep.

    This class performs the sweep by
    - change SG frequency by set_freq()
    - software-triggering PG

    :param sg: The reference to SG Instrument.
    :param pg: The reference to PG Instrument.
    :param pd_names: Name of PD Instruments.
    :param queue_size: (default: 8) Size of queue of scanned line data.
    :type queue_size: int

    """

    def __init__(self, name, conf, prefix=None):
        InstrumentOverlay.__init__(self, name, conf=conf, prefix=prefix)

        self.sg = self.conf.get("sg")
        self.pg = self.conf.get("pg")
        self.pd_names = self.conf.get("pd_names", ["pd0", "pd1"])
        self.pds = [self.conf.get(n) for n in self.pd_names]
        self._pd_analog = self.conf.get("pd_analog", False)
        if self._pd_analog:
            self.clock = self.conf.get("clock")
        else:
            self.clock = None
        self.add_instruments(self.sg, self.pg, *self.pds)

        self.load_pg_conf_preset()

        self._queue_size = self.conf.get("queue_size", 8)
        self._queue = LockedQueue(self._queue_size)
        self._stop_ev = self._thread = None
        self.running = False

        self.check_required_conf(["pd_clock", "block_base", "minimum_block_length"])
        self._pd_clock = self.conf["pd_clock"]
        self._pd_data_transfer = self.conf.get("pd_data_transfer")
        self._minimum_block_length = self.conf["minimum_block_length"]
        self._block_base = self.conf["block_base"]
        self._channel_remap = self.conf.get("channel_remap")
        self._continue_mw = False

    def load_pg_conf_preset(self):
        loader = PresetLoader(self.logger, PresetLoader.Mode.FORWARD)
        loader.add_preset(
            "DTG",
            [
                ("block_base", 4),
                ("pg_freq_cw", 1.0e6),
                ("pg_freq_pulse", 2.0e9),
                ("minimum_block_length", 1000),
            ],
        )
        loader.add_preset(
            "PulseStreamer",
            [
                ("block_base", 8),
                ("pg_freq_cw", 1.0e9),
                ("pg_freq_pulse", 1.0e9),
                ("minimum_block_length", 1),
            ],
        )
        loader.load_preset(self.conf, self.pg.__class__.__name__)

    def _set_attrs(self, params):
        self.start_f, self.stop_f = params["start"], params["stop"]
        self.freqs = np.linspace(self.start_f, self.stop_f, params["num"])
        self.power = params["power"]
        self._continue_mw = params.get("continue_mw", False)

    def get_point(self):
        return self._queue.pop_block()

    def sweep_loop(self, ev: threading.Event):
        while True:
            for f in self.freqs:
                self.sg.set_freq_CW(f)
                self.pg.trigger()
                self._queue.append(self.get_pd_data())
                if ev.is_set():
                    self.logger.info("Quitting sweep loop.")
                    return

    def get_pd_data(self):
        """returns 1D array of length 1 (without BG) or 2 (with BG)."""

        data = []
        for pd in self.pds:
            d = pd.pop_block()
            if isinstance(d, list):
                # PD has multi channel
                data.extend(d)
            else:
                # single channel, assume ls is np.ndarray
                data.append(d)
        return np.sum(data, axis=0)

    def configure_sg(self, params: dict, label: str):
        mod = params.get("mod", {})
        success = self.sg.configure_cw(self.start_f, self.power)
        if label == "iq_ext":
            success &= self.sg.configure_iq_ext()
        elif label == "iq_int":
            success &= self.sg.configure_iq_int()
        elif label == "fm_ext":
            success &= self.sg.configure_fm_ext(mod["fm_deviation"])
        elif label == "fm_int":
            success &= self.sg.configure_fm_int(mod["fm_deviation"], mod["fm_rate"])
        elif label == "am_ext":
            success &= self.sg.configure_am_ext(mod["am_depth"], mod["am_log"])
        elif label == "am_int":
            success &= self.sg.configure_am_int(mod["am_depth"], mod["am_log"], mod["am_rate"])
        success &= self.sg.query_opc()
        return success

    # Standard API

    def get_param_dict_labels(self) -> list[str]:
        return ["pd"]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue] | None:
        if label == "pd":
            return self.get_pd_param_dict()

    def configure(self, params: dict, label: str = "") -> bool:
        if not self.check_required_params(params, ("start", "stop", "num", "power", "delay")):
            return False

        self._set_attrs(params)
        self.params = params
        self._queue = LockedQueue(self._queue_size)

        if not self.configure_sg(params, label):
            return self.fail_with("failed to configure SG.")
        if not self.configure_pg(params, label, TriggerType.SOFTWARE):
            return self.fail_with("failed to configure PG.")
        if not self.configure_pd(params, label):
            return self.fail_with("failed to configure PD.")

        return True

    def start(self, label: str = "") -> bool:
        if self.running:
            self.logger.warn("start() is called while running.")
            return True

        if not self.sg.set_output(True):
            return self.fail_with("Failed to start sg.")
        if not self.start_pd():
            return self.fail_with("Failed to start pd.")

        self._stop_ev = threading.Event()
        self._thread = threading.Thread(target=self.sweep_loop, args=(self._stop_ev,))
        self._thread.start()

        self.running = True

        return True

    def stop(self, label: str = "") -> bool:
        if not self.running:
            return True
        self.running = False

        self.logger.info("Stopping sweeper.")

        self._stop_ev.set()
        self._thread.join()

        if self._continue_mw:
            self.logger.warn("Skipping to turn off MW output")
            success = True
        else:
            success = self.sg.set_output(False)
        success &= all([pd.stop() for pd in self.pds])
        if self._pd_analog:
            success &= self.clock.stop()
        success &= self.pg.stop()

        if not success:
            return self.fail_with("failed to stop SG, PG, or PD.")

        return True

    def get(self, key: str, args=None, label: str = ""):
        if key == "point":
            return self.get_point()
        elif key == "bounds":
            return self.sg.get_bounds()
        elif key == "unit":
            return self.pds[0].get("unit")
        else:
            self.logger.error(f"unknown get() key: {key}")
            return None

    def get_pd_param_dict(self) -> P.ParamDict[str, P.PDValue] | None:
        if not self._pd_analog:
            return None
        d = P.ParamDict()
        d["rate"] = P.FloatParam(
            self.conf.get("pd_rate", 400e3), 1e3, 10000e3, doc="PD sampling rate"
        )
        lb, ub = self.conf.get("pd_bounds", (-10.0, 10.0))
        d["bounds"] = [
            P.FloatParam(lb, -10.0, 10.0, unit="V", doc="lower bound of expected voltage"),
            P.FloatParam(ub, -10.0, 10.0, unit="V", doc="upper bound of expected voltage"),
        ]
        return d

    def configure_pd(self, params, label):
        if self._pd_analog:
            return self.configure_analog_pd(params, label)
        else:
            return self.configure_apd(params, label)

    def start_pd(self):
        if self._pd_analog:
            return self.clock.start() and all([pd.start() for pd in self.pds])
        else:
            return all([pd.start() for pd in self.pds])

    def configure_apd(self, params: dict, label: str) -> bool:
        if label != "pulse":
            time_window = params["timing"]["time_window"]
        else:
            # time_window is used to compute APD's count rate.
            # gate is opened for whole burst sequence, but meaning time window for APD
            # is just burst_num * laser_width.
            t = params["timing"]
            time_window = t["burst_num"] * t["laser_width"]

        # max. expected sampling rate. double expected freq due to gate mode.
        # this max rate is achieved if freq switching time was zero (it's non-zero in reality).
        rate = 2.0 / time_window
        num = 1
        if params.get("background", False):
            num *= 2
        buffer_size = num * self.conf.get("buffer_size_coeff", 20)
        params_pd = {
            "clock": self._pd_clock,
            "cb_samples": num,
            "samples": buffer_size,
            "buffer_size": buffer_size,
            "rate": rate,
            "finite": False,
            "every": False,
            "drop_first": False,
            "gate": True,
            "time_window": time_window,
        }

        return all([pd.configure(params_pd) for pd in self.pds])

    def configure_analog_pd(self, params: dict, label: str) -> bool:
        rate = params["pd"]["rate"]
        if label != "pulse":
            oversamp = round(params["timing"]["time_window"] * rate)
        else:
            # t = params["timing"]
            # oversamp = round(t["laser_width"] * rate * t["burst_num"])
            # won't reach here but just in case
            self.logger.error("Pulse for Analog PD is not implemented yet.")
            return False

        self.logger.info(f"Analog PD oversample: {oversamp}")

        params_clock = {
            "freq": rate,
            "samples": oversamp,
            "finite": True,
            "trigger_source": self._pd_clock,
            "trigger_dir": True,
            "retriggerable": True,
        }
        if not self.clock.configure(params_clock):
            return self.fail_with("failed to configure clock.")
        clock_pd = self.clock.get_internal_output()

        num = 1
        if params.get("background", False):
            num *= 2
        buffer_size = num * self.conf.get("buffer_size_coeff", 20)
        params_pd = {
            "clock": clock_pd,
            "cb_samples": num,
            "samples": buffer_size,
            "buffer_size": buffer_size,
            "rate": rate,
            "finite": False,
            "every": False,
            "drop_first": False,
            "clock_mode": True,
            "oversample": oversamp,
            "bounds": params["pd"].get("bounds", (-10.0, 10.0)),
        }
        if self._pd_data_transfer:
            params_pd["data_transfer"] = self._pd_data_transfer

        return all([pd.configure(params_pd) for pd in self.pds])
