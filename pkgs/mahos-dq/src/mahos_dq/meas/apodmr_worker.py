#!/usr/bin/env python3

"""
Worker for Analog-PD Pulse ODMR.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import numpy as np

from mahos.msgs import param_msgs as P
from mahos.msgs.pulse_msgs import PulsePattern
from mahos.inst.fg_interface import FGInterface
from mahos.inst.pg_interface import PGInterface, Block, Blocks
from mahos.inst.pd_interface import PDInterface
from mahos.inst.daq_interface import ClockSourceInterface
from mahos.meas.common_worker import Worker
from mahos.inst.sg_interface import SGInterface
from mahos_dq.meas.podmr_generator.generator import make_generators
from mahos_dq.meas.podmr_generator import generator_kernel as K
from mahos_dq.meas.podmr_worker import Bounds, Pulser as PODMRPulser, PODMRDataOperator
from mahos_dq.msgs.apodmr_msgs import APODMRData


class APODMRDataOperator(PODMRDataOperator):
    """Operations (set / get / analyze) on :class:`APODMRData`."""

    def set_trace_laser_timing(self, data: APODMRData, trace_laser_timing):
        data.trace_laser_timing = float(trace_laser_timing)

    def set_trigger_timing(self, data: APODMRData, trigger_timing):
        data.trigger_timing = np.array(trigger_timing, dtype=np.float64)

    def set_instrument_params(
        self, data: APODMRData, samples_per_trace, sample_period, pg_freq, length, offsets, pd_rate
    ):
        if "instrument" in data.params:
            return
        data.params["instrument"] = {}
        data.params["instrument"]["samples_per_trace"] = int(samples_per_trace)
        data.params["instrument"]["trange"] = float(samples_per_trace) * sample_period
        data.params["instrument"]["tbin"] = sample_period
        data.params["instrument"]["pg_freq"] = pg_freq
        data.params["instrument"]["length"] = int(length)
        data.params["instrument"]["pd_rate"] = pd_rate
        if all([ofs == 0 for ofs in offsets]):
            data.params["instrument"]["offsets"] = []
        else:
            data.params["instrument"]["offsets"] = offsets

    def append_record(self, data: APODMRData, traces: np.ndarray):
        traces = np.array(traces, copy=True)
        if data.raw_data is None:
            data.raw_data = traces[np.newaxis, :, :]
        else:
            data.raw_data = np.concatenate((data.raw_data, traces[np.newaxis, :, :]), axis=0)

    def get_marker_indices(self, data: APODMRData):
        tbin = data.get_bin()
        if (
            data.params is None
            or tbin is None
            or getattr(data, "trace_laser_timing", None) is None
        ):
            return None

        sigdelay, sigwidth, refdelay, refwidth = [
            data.params["plot"][k] for k in ("sigdelay", "sigwidth", "refdelay", "refwidth")
        ]

        signal_head = data.trace_laser_timing + sigdelay
        signal_tail = signal_head + sigwidth
        reference_head = signal_tail + refdelay
        reference_tail = reference_head + refwidth

        signal_head = np.round(signal_head / tbin).astype(np.int64)
        signal_tail = np.round(signal_tail / tbin).astype(np.int64)
        reference_head = np.round(reference_head / tbin).astype(np.int64)
        reference_tail = np.round(reference_tail / tbin).astype(np.int64)

        data.marker_indices = np.array(
            (signal_head, signal_tail, reference_head, reference_tail), dtype=np.int64
        )
        return data.marker_indices

    def _analyze_record(self, traces: np.ndarray, marker_indices: np.ndarray):
        sig_head, sig_tail, ref_head, ref_tail = (int(v) for v in marker_indices)
        sig = np.mean(traces[:, sig_head : sig_tail + 1], axis=1)
        ref = np.mean(traces[:, ref_head : ref_tail + 1], axis=1)
        return np.asarray(sig, dtype=np.float64), np.asarray(ref, dtype=np.float64)

    def _analysis_error(self, data: APODMRData) -> str | None:
        if not data.has_raw_data():
            return "raw data is unavailable"
        if data.marker_indices is None:
            return "marker indices are unavailable"

        samples_per_trace = data.get_samples_per_trace()
        if samples_per_trace is None or samples_per_trace < 1:
            return "samples_per_trace is invalid"

        sig_head, sig_tail, ref_head, ref_tail = (int(v) for v in data.marker_indices)
        if not (0 <= sig_head <= sig_tail < samples_per_trace):
            return (
                "signal window is out of range "
                f"(head={sig_head}, tail={sig_tail}, samples={samples_per_trace})"
            )
        if not (0 <= ref_head <= ref_tail < samples_per_trace):
            return (
                "reference window is out of range "
                f"(head={ref_head}, tail={ref_tail}, samples={samples_per_trace})"
            )
        return None

    def analyze_with_error(self, data: APODMRData) -> str | None:
        error = self._analysis_error(data)
        if error is not None:
            return error

        N = data.num_pattern()
        traces = np.mean(data.raw_data, axis=0)
        sig_avg, ref_avg = self._analyze_record(traces, data.marker_indices)

        for i in range(4):
            data.set_data(i, None)
            data.set_data_ref(i, None)

        if data.is_partial():
            p = data.partial()
            data.set_data(p, sig_avg)
            data.set_data_ref(p, ref_avg)
        else:
            for i in range(N):
                data.set_data(i, sig_avg[i::N])
                data.set_data_ref(i, ref_avg[i::N])
        return None

    def analyze(self, data: APODMRData) -> bool:
        return self.analyze_with_error(data) is None


class APODMRBlockBuilder(object):
    """Build PODMR raw blocks into APODMR-ready blocks with per-laser triggers."""

    def __init__(
        self,
        minimum_block_length: int,
        block_base: int,
        mw_modes: tuple[int],
        iq_amplitude: float,
        channel_remap: dict | None,
    ):
        self.minimum_block_length = minimum_block_length
        self.block_base = block_base
        self.mw_modes = mw_modes
        self.iq_amplitude = iq_amplitude
        self.channel_remap = channel_remap

    def _inject_trigger(self, op_block: Block, roi_head: int, trigger_width: int) -> Block:
        if roi_head < trigger_width:
            raise ValueError("roi_head must be equal to or longer than trigger_width")
        total_length = op_block.total_length()
        if roi_head > total_length:
            raise ValueError("roi_head must fit in the operation block before each laser pulse")

        trigger_start = total_length - roi_head
        trigger_tail = roi_head - trigger_width
        pattern = []
        if trigger_start > 0:
            pattern.append(((), trigger_start))
        pattern.append((("trigger",), trigger_width))
        if trigger_tail > 0:
            pattern.append(((), trigger_tail))

        return op_block.union(Block(op_block.name + "_trig", pattern))

    def build_blocks(
        self, blocks: list[Blocks[Block]], freq: float, common_pulses, params: dict, num_mw: int
    ) -> tuple[Blocks[Block], list[int], list[int], int]:
        (
            base_width,
            _laser_delay,
            laser_width,
            _mw_delay,
            trigger_width,
            init_delay,
            final_delay,
        ) = common_pulses

        if trigger_width <= 0:
            raise ValueError("trigger_width must be positive")

        roi_head = int(round(params["roi_head"] * freq))
        roi_tail = int(round(params["roi_tail"] * freq))
        if roi_head < 0 or roi_tail < 0:
            raise ValueError("roi_head and roi_tail must be non-negative")
        shots_per_point = int(params.get("shots_per_point", 1))
        if shots_per_point < 1:
            raise ValueError("shots_per_point must be positive")

        out = Blocks()
        laser_timing = []
        trigger_timing = []
        all_trigger_timing = []
        t = 0

        init_block_width = max(init_delay + laser_width, self.minimum_block_length)
        init_block_width = K.offset_base_inc(init_block_width, base_width)
        final_block_width = max(final_delay + laser_width, self.minimum_block_length)
        final_block_width = K.offset_base_inc(final_block_width, base_width)

        phases = K.init_final_phases(num_mw)

        init = Block(
            "INIT",
            [
                (("sync",) + phases, init_delay),
                (
                    (
                        "laser",
                        "sync",
                    )
                    + phases,
                    init_block_width - init_delay,
                ),
            ],
        )
        out.append(init)
        t += init.total_length()

        for blks in blocks:
            for i in range(0, len(blks), 2):
                op = self._inject_trigger(blks[i], roi_head, trigger_width)
                rd = blks[i + 1]
                unit = op.concatenate(rd)
                trigger_offset = op.total_length() - roi_head
                laser_offset = op.total_length()
                trigger_timing.append(t + trigger_offset)
                laser_timing.append(t + laser_offset)
                for j in range(shots_per_point):
                    all_trigger_timing.append(t + trigger_offset + j * unit.total_length())
                out.append(unit.repeat(shots_per_point))
                t += unit.total_length() * shots_per_point

        out.append(Block("FINAL", [(("sync",) + phases, final_block_width)]))

        if params.get("pulse", {}).get("invertY", False):
            out = K.invert_y_phase(out)
        out = K.encode_mw_phase(out, params, self.mw_modes, num_mw, self.iq_amplitude)

        mw_offset_ticks = int(round(params.get("mw_offset", 0.0) * freq))
        if mw_offset_ticks:
            out = K.apply_mw_offset(out, mw_offset_ticks)

        if self.channel_remap is not None:
            out = out.replace(self.channel_remap)

        sample_duration = roi_head + laser_width + roi_tail
        for t0, t1 in zip(all_trigger_timing, all_trigger_timing[1:]):
            if (t1 - t0) < sample_duration:
                raise ValueError(
                    "trace window overlaps the next trigger; reduce margins or pulse rate"
                )

        return out.simplify(), laser_timing, trigger_timing, laser_width + roi_head + roi_tail


class Pulser(PODMRPulser):
    """Worker for APODMR using PG-triggered, DAQ-read AnalogPD traces."""

    def __init__(self, cli, logger, conf: dict):
        Worker.__init__(self, cli, logger, conf)
        self.load_conf_preset(cli)

        self.sgs = {"sg": SGInterface(cli, "sg")}
        _default_channels = [{"sg": "sg"}]
        for i in range(1, 10):
            name = f"sg{i}"
            if name in cli.insts():
                self.sgs[name] = SGInterface(cli, name)
                _default_channels.append({"sg": name})

        self.mw_modes = tuple(self.conf.get("mw_modes", (0,) * len(self.sgs)))
        self.mw_channels = self.conf.get("mw_channels", _default_channels)

        self.pg = PGInterface(cli, "pg")
        self.clock = ClockSourceInterface(cli, self.conf.get("clock_name", "clock"))
        self.pd_names = self.conf.get("pd_names", ["pd0"])
        self.pds = [PDInterface(cli, n) for n in self.pd_names]
        if "fg" in cli:
            self.fg = FGInterface(cli, "fg")
        else:
            self.fg = None
        self.add_instruments(self.pg, self.clock, self.fg, *self.pds, *self.sgs.values())

        self.length = self.offsets = self.freq = None
        self.trace_count = None
        self.samples_per_trace = None
        self._pd_trigger = self.conf["pd_trigger"]
        self._pd_data_transfer = self.conf.get("pd_data_transfer")
        self._quick_resume = self.conf.get("quick_resume", True)

        self.check_required_conf(
            ["pd_trigger", "block_base", "pg_freq", "reduce_start_divisor", "minimum_block_length"]
        )
        self.generators = make_generators(
            freq=self.conf["pg_freq"],
            reduce_start_divisor=self.conf["reduce_start_divisor"],
            split_fraction=self.conf.get("split_fraction", 4),
            minimum_block_length=self.conf["minimum_block_length"],
            block_base=self.conf["block_base"],
            mw_modes=self.mw_modes,
            iq_amplitude=self.conf.get("iq_amplitude", 0.0),
            channel_remap=self.conf.get("channel_remap"),
            generators=self.conf.get("generators"),
            print_fn=self.logger.info,
        )
        self.builder = APODMRBlockBuilder(
            self.conf["minimum_block_length"],
            self.conf["block_base"],
            self.mw_modes,
            self.conf.get("iq_amplitude", 0.0),
            self.conf.get("channel_remap"),
        )

        self.data = APODMRData()
        self.op = APODMRDataOperator()
        self.bounds = Bounds()
        self.pulse_pattern = None
        self._analysis_warned = False

    def _pd_rate(self, params: dict) -> float:
        return float(params["pd"]["rate"])

    def _sweeps_per_record(self, params: dict) -> int:
        return int(params.get("sweeps_per_record", 1))

    def _shots_per_point(self, params: dict) -> int:
        return int(params.get("shots_per_point", 1))

    def generate_blocks(self, data: APODMRData | None = None):
        if data is None:
            data = self.data
        self._validate_partial(data)
        self._validate_plotmode(data)

        generator = self.generators[data.label]
        raw_blocks, freq, common_pulses = generator.generate_raw_blocks(
            data.xdata, data.get_params()
        )
        blocks, laser_timing, trigger_timing, trace_length_ticks = self.builder.build_blocks(
            raw_blocks, freq, common_pulses, data.get_params(), generator.num_mw()
        )
        return blocks, freq, laser_timing, trigger_timing, trace_length_ticks

    def validate_params(
        self, params: P.ParamDict[str, P.PDValue] | dict[str, P.RawPDValue], label: str
    ) -> bool:
        params = P.unwrap(params)
        d = APODMRData(params, label)
        try:
            blocks, freq, _, _, _ = self.generate_blocks(d)
        except ValueError as e:
            self.logger.error(f"Invalid params for {label}: {e}")
            return False
        offsets = self.pg.validate_blocks(blocks, freq)
        return offsets is not None

    def init_pg(self, params: dict) -> bool:
        if not (self.pg.stop() and self.pg.clear()):
            self.logger.error("Error stopping PG.")
            return False

        blocks, self.freq, laser_timing, trigger_timing, trace_length_ticks = (
            self.generate_blocks()
        )
        pd_rate = self._pd_rate(params)
        sample_period = 1.0 / pd_rate
        self.samples_per_trace = max(1, int(round(trace_length_ticks / self.freq * pd_rate)))
        self.trace_count = len(laser_timing)

        self.op.set_laser_timing(self.data, np.array(laser_timing) / self.freq)
        self.op.set_trace_laser_timing(self.data, params["roi_head"])
        self.op.set_trigger_timing(self.data, np.array(trigger_timing) / self.freq)
        self.pulse_pattern = PulsePattern(blocks, self.freq, markers=trigger_timing)

        if not (self.pg.configure_blocks(blocks, self.freq) and self.pg.get_opc()):
            self.logger.error("Error configuring PG.")
            return False

        self.length = self.pg.get_length()
        self.offsets = self.pg.get_offsets()
        self.op.set_instrument_params(
            self.data,
            self.samples_per_trace,
            sample_period,
            self.freq,
            self.length,
            self.offsets,
            pd_rate,
        )
        return True

    def init_start_pds(self) -> bool:
        params = self.data.get_params()
        rate = self._pd_rate(params)
        sweeps_per_record = self._sweeps_per_record(params)
        shots_per_point = self._shots_per_point(params)

        params_clock = {
            "freq": rate,
            "samples": self.samples_per_trace,
            "finite": True,
            "trigger_source": self._pd_trigger,
            "trigger_dir": True,
            "retriggerable": True,
        }
        if not self.clock.configure(params_clock):
            self.logger.error("failed to configure clock.")
            return False
        clock_pd = self.clock.get_internal_output()

        cb_samples = self.trace_count * self.samples_per_trace
        buffer_size = cb_samples * self.conf.get("buffer_size_coeff", 20)
        params_pd = {
            "clock": clock_pd,
            "cb_samples": cb_samples,
            "samples": buffer_size,
            "buffer_size": buffer_size,
            "rate": rate,
            "finite": False,
            "clock_mode": True,
            "oversample": 1,
            "block_reduce_factor": shots_per_point,
            "block_reduce_samples": self.samples_per_trace,
            "block_reduce_op": "mean",
            "reduce_factor": sweeps_per_record,
            "reduce_op": "mean",
            "bounds": params["pd"].get("bounds", (-10.0, 10.0)),
        }
        if self._pd_data_transfer:
            params_pd["data_transfer"] = self._pd_data_transfer

        if not (
            all([pd.configure(params_pd) for pd in self.pds])
            and self.clock.start()
            and all([pd.start() for pd in self.pds])
        ):
            self.logger.error("Error starting PDs.")
            return False

        return True

    def init_inst(self, params: dict) -> bool:
        if not self.init_sg(params):
            self.logger.error("Error initializing SG.")
            return False
        if not self.init_fg(params):
            self.logger.error("Error initializing FG.")
            return False
        if not self.init_pg(params):
            self.logger.error("Error initializing PG.")
            return False

        return True

    def _reshape_sweep(self, line: np.ndarray) -> np.ndarray:
        expected = self.trace_count * self.samples_per_trace
        if len(line) != expected:
            raise ValueError(
                f"Unexpected PD record size {len(line)} for trace_count={self.trace_count}, "
                f"samples_per_trace={self.samples_per_trace}"
            )
        traces = line.reshape(self.trace_count, self.samples_per_trace)
        return traces

    def update(self) -> bool:
        if not self.data.running:
            return False

        lines = []
        for pd in self.pds:
            ls = pd.pop_block()
            if isinstance(ls, list):
                lines.extend(ls)
            else:
                lines.append(ls)

        line = np.sum(lines, axis=0)
        traces = self._reshape_sweep(line)
        self.op.append_record(self.data, traces)
        self.op.get_marker_indices(self.data)
        error = self.op.analyze_with_error(self.data)
        if error is not None:
            if not self._analysis_warned:
                self.logger.warn(f"Skipping APODMR analysis: {error}")
                self._analysis_warned = True
            return True
        self._analysis_warned = False
        return True

    def update_plot_params(self, params: dict) -> bool:
        if self.data.params is None:
            return False
        if "plotmode" in params:
            try:
                options = self._plotmode_options(self.data.label, self.data.get_params())
            except ValueError as e:
                self.logger.error(f"Cannot validate plotmode for {self.data.label}: {e}")
                return False
            if params["plotmode"] not in options:
                self.logger.error(
                    f"Unknown plotmode '{params['plotmode']}' for method '{self.data.label}'. "
                    f"available: {options}"
                )
                return False
        if self.op.update_plot_params(self.data, params):
            self.data.remove_fit_data()
        if not self.data.running:
            self.op.get_marker_indices(self.data)
            error = self.op.analyze_with_error(self.data)
            if error is not None:
                self.logger.warn(f"Cannot analyze APODMR data with current plot params: {error}")
        return True

    def start(
        self, params: None | P.ParamDict[str, P.PDValue] | dict[str, P.RawPDValue], label: str
    ) -> bool:
        if params is not None:
            params = P.unwrap(params)
        resume = params is None or ("resume" in params and params["resume"])
        if params is None:
            quick_resume = resume and self._quick_resume
        else:
            quick_resume = resume and params.get("quick_resume", self._quick_resume)
        if not resume:
            self.data = APODMRData(params, label)
            self.op.update_axes(self.data)
        else:
            if params is not None:
                self.data.update_params(params)
        self._analysis_warned = False
        try:
            self._validate_partial(self.data)
            self._validate_plotmode(self.data)
        except ValueError as e:
            self.logger.error(f"Invalid params for {label}: {e}")
            return False

        sweeps_limit = self.data.params.get("sweeps", 0)
        sweeps_per_record = self._sweeps_per_record(self.data.params)
        if sweeps_limit > 0 and sweeps_limit % sweeps_per_record:
            self.logger.warn(
                "sweeps is not divisible by sweeps_per_record; measurement will stop on the "
                "next completed record boundary."
            )

        if not self.lock_instruments():
            return self.fail_with_release("Error acquiring instrument locks.")

        if quick_resume:
            self.logger.info("Quick resume enabled: skipping initial inst configurations.")
        if not quick_resume and not self.init_inst(self.data.params):
            return self.fail_with_release("Error initializing instruments.")
        # PD/clock configuration is always refreshed on each start, even with quick resume.
        if not self.init_start_pds():
            return self.fail_with_release("Error initializing or starting PDs.")

        success = self.start_sg(self.data.params)
        if self._fg_enabled(self.data.params):
            success &= self.fg.set_output(True)
        success &= self.pg.start()

        if not success:
            self.pg.stop()
            if self._fg_enabled(self.data.params):
                self.fg.set_output(False)
            self.stop_sg()
            for pd in self.pds:
                pd.stop()
            self.clock.stop()
            return self.fail_with_release("Error starting pulser.")

        if resume:
            self.data.resume()
            self.logger.info("Resumed pulser.")
        else:
            self.data.start()
            self.logger.info("Started pulser.")
        return True

    def is_finished(self) -> bool:
        if not self.data.has_params():
            return False
        if (
            self.data.params.get("sweeps", 0) > 0
            and self.data.sweeps() >= self.data.params["sweeps"]
        ):
            return True
        if (
            self.data.params.get("duration", 0.0) > 0.0
            and self.data.measurement_time() >= self.data.params["duration"]
        ):
            return True
        return False

    def stop(self) -> bool:
        if not self.data.running:
            return False

        success = self.pg.stop() and self.pg.release() and self.stop_sg()
        success &= all([pd.stop() for pd in self.pds]) and all([pd.release() for pd in self.pds])
        success &= self.clock.stop() and self.clock.release()
        if self._fg_enabled(self.data.params):
            success &= self.fg.set_output(False)
        if self.fg is not None:
            success &= self.fg.release()

        if success:
            self.data.finalize()
            self.logger.info("Stopped pulser.")
        else:
            self.logger.error("Error stopping pulser.")
        return success

    def get_param_dict(self, label: str) -> P.ParamDict[str, P.PDValue] | None:
        d = super().get_param_dict(label)
        if d is None:
            return None
        if "head" in d["plot"]["taumode"].options():
            taumodes = tuple(m for m in d["plot"]["taumode"].options() if m != "head")
            d["plot"]["taumode"] = P.StrChoiceParam("raw", taumodes)

        if "timebin" in d:
            del d["timebin"]
        d["roi_head"] = P.FloatParam(
            self.conf.get("roi_head", 20e-9),
            0.0,
            10e6,
            unit="s",
            doc="margin at head of sampled trace and trigger-to-laser offset",
        )
        d["roi_tail"] = P.FloatParam(
            self.conf.get("roi_tail", 100e-9),
            0.0,
            10e6,
            unit="s",
            doc="margin at tail of sampled trace",
        )
        d["sweeps_per_record"] = P.IntParam(
            self.conf.get("sweeps_per_record", 10),
            1,
            1000000,
            doc="number of sweeps accumulated in one stored raw trace record",
        )
        d["shots_per_point"] = P.IntParam(
            self.conf.get("shots_per_point", 1),
            1,
            1000000,
            doc="number of repeated shots per sweep point",
        )
        d["pd"] = P.ParamDict()
        d["pd"]["rate"] = P.FloatParam(
            self.conf.get("pd_rate", 2e6),
            1e3,
            1e9,
            unit="Hz",
            SI_prefix=True,
            doc="PD sampling rate",
        )
        lb, ub = self.conf.get("pd_bounds", (-10.0, 10.0))
        d["pd"]["bounds"] = [
            P.FloatParam(lb, -10.0, +10.0, doc="PD voltage lower bound"),
            P.FloatParam(ub, -10.0, +10.0, doc="PD voltage upper bound"),
        ]
        return d

    def work(self):
        return self.update()

    def data_msg(self) -> APODMRData:
        return self.data

    def pulse_msg(self) -> PulsePattern | None:
        return self.pulse_pattern
