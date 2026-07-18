#!/usr/bin/env python3

"""
Worker for Analog-PD Pulse ODMR.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations
import time

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
from mahos_dq.msgs.apodmr_msgs import APODMRData, MWMode
from mahos_dq.util.segments import round_segment_samples_up


class APODMRDataOperator(PODMRDataOperator):
    """Operations (set / get / analyze) on :class:`APODMRData`."""

    def set_trace_laser_timing(self, data: APODMRData, trace_laser_timing):
        data.trace_laser_timing = float(trace_laser_timing)

    def set_trigger_timing(self, data: APODMRData, trigger_timing):
        data.trigger_timing = np.array(trigger_timing, dtype=np.float64)

    def set_instrument_params(
        self,
        data: APODMRData,
        samples_per_trace,
        sample_period,
        pg_freq,
        length,
        offsets,
        pd_rate,
        mw_modes,
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
        data.params["instrument"]["mw_modes"] = [MWMode.parse(m).name for m in mw_modes]

    def append_record(self, data: APODMRData, traces: np.ndarray):
        traces = np.asarray(traces, dtype=np.float64)
        data.records += 1
        if data.raw_data_sum is None:
            data.raw_data_sum = traces.copy()
        else:
            data.raw_data_sum += traces

        try:
            max_records = int(data.params.get("max_records", 0))
        except (AttributeError, TypeError, ValueError):
            max_records = 0

        if max_records == 1 or data.raw_data is None:
            data.raw_data = traces[np.newaxis].copy()
        else:
            start = max(0, data.raw_data.shape[0] + 1 - max_records) if max_records else 0
            data.raw_data = np.concatenate((data.raw_data[start:], traces[np.newaxis]), axis=0)

    def get_marker_indices(self, data: APODMRData):
        tbin = data.get_bin()
        if data.params is None or tbin is None or data.trace_laser_timing is None:
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
        if not data.has_raw_data_sum() or data.records < 1:
            return "aggregated raw data is unavailable"
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
        traces = data.raw_data_sum / data.records
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
        mw_modes: tuple[MWMode],
        iq_amplitude: float,
        channel_remap: dict | None,
    ):
        self.minimum_block_length = minimum_block_length
        self.block_base = block_base
        self.mw_modes = mw_modes
        self.iq_amplitude = iq_amplitude
        self.channel_remap = channel_remap
        self.eos_deadtime_ticks = 0
        self.all_trigger_timing = []

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

        if params.get("divide_block", False):
            raise ValueError("divide_block=True is TODO and not implemented in APODMR.")

        if trigger_width <= 0:
            raise ValueError("trigger_width must be positive")

        roi_head = int(round(params["roi_head"] * freq))
        roi_tail = int(round(params["roi_tail"] * freq))
        if roi_head < 0 or roi_tail < 0:
            raise ValueError("roi_head and roi_tail must be non-negative")
        shots_per_point = int(params.get("shots_per_point", 1))
        if shots_per_point < 1:
            raise ValueError("shots_per_point must be positive")
        point_init_delay = float(params.get("point_init_delay", 0.0))
        if point_init_delay < 0.0:
            raise ValueError("point_init_delay must be non-negative")
        point_init_delay_ticks = int(round(point_init_delay * freq))
        if point_init_delay > 0.0 and point_init_delay_ticks <= 0:
            raise ValueError("point_init_delay must be at least one pulse-generator tick")

        out = Blocks()
        laser_timing = []
        trigger_timing = []
        self.all_trigger_timing = []
        self.eos_deadtime_ticks = int(round(params.get("pd", {}).get("eos_deadtime", 0.0) * freq))
        t = 0

        init_block_width = max(init_delay + laser_width, self.minimum_block_length)
        init_block_width = K.offset_base_inc(init_block_width, base_width)
        final_block_width = max(final_delay, self.minimum_block_length)
        final_block_width = K.offset_base_inc(final_block_width, base_width)

        phases = K.init_final_phases(num_mw)

        if not point_init_delay_ticks:
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

        point_index = 0
        for blks in blocks:
            for i in range(0, len(blks), 2):
                if point_init_delay_ticks:
                    delay = point_init_delay_ticks + (init_delay if point_index == 0 else 0)
                    block_length = K.offset_base_inc(
                        max(delay + laser_width, self.minimum_block_length), base_width
                    )
                    pattern = [
                        (("sync",) + phases, block_length - laser_width),
                        (("laser", "sync") + phases, laser_width),
                    ]
                    point_init = Block(f"POINT_INIT{point_index}", pattern)
                    out.append(point_init)
                    t += point_init.total_length()

                op = K.inject_trigger(blks[i], roi_head, trigger_width)
                rd = blks[i + 1]
                unit = op.concatenate(rd)
                trigger_offset = op.total_length() - roi_head
                laser_offset = op.total_length()
                trigger_timing.append(t + trigger_offset)
                laser_timing.append(t + laser_offset)
                for j in range(shots_per_point):
                    self.all_trigger_timing.append(t + trigger_offset + j * unit.total_length())
                out.append(unit.repeat(shots_per_point))
                t += unit.total_length() * shots_per_point
                point_index += 1

        out.append(Block("FINAL", [(("sync",) + phases, final_block_width)]))

        # TODO: block shaping based on params["divide_block"], self.minimum_block_length,
        # and self.block_base. But we must care about concat and repeat above;
        # it cannot be simply copied from generator_kernel.build_blocks.

        if params.get("pulse", {}).get("invertY", False):
            out = K.invert_y_phase(out)
        out = K.encode_mw_phase(out, params, self.mw_modes, num_mw, self.iq_amplitude)

        mw_offset_ticks = int(round(params.get("mw_offset", 0.0) * freq))
        if mw_offset_ticks:
            out = K.apply_mw_offset(out, mw_offset_ticks)

        if self.channel_remap is not None:
            out = out.replace(self.channel_remap)

        trace_length_ticks = roi_head + laser_width + roi_tail
        if not self.check_sample_duration(trace_length_ticks):
            raise ValueError(
                "trace window overlaps the next trigger; reduce margins or pulse rate"
            )

        return out.simplify(), laser_timing, trigger_timing, trace_length_ticks

    def check_sample_duration(self, trace_length_ticks) -> bool:
        if not self.all_trigger_timing:
            raise ValueError("check_sample_duration is called but all_trigger_timing is not set.")

        for t0, t1 in zip(self.all_trigger_timing, self.all_trigger_timing[1:]):
            if t1 - t0 < trace_length_ticks + self.eos_deadtime_ticks:
                return False
        return True


class Pulser(PODMRPulser):
    """Worker for APODMR using PG-triggered, AnalogPD traces."""

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

        self.mw_modes = tuple(
            MWMode.parse(m) for m in self.conf.get("mw_modes", (0,) * len(self.sgs))
        )
        self.mw_channels = self.conf.get("mw_channels", _default_channels)

        self.pg = PGInterface(cli, "pg")
        self._pd_spectrum = self.conf.get("pd_spectrum", False)
        if self._pd_spectrum:
            self.clock = None
        else:
            self.clock = ClockSourceInterface(cli, self.conf.get("clock_name", "clock"))
        self.pd_names = self.conf.get("pd_names", ["pd0"])
        self.pds = [PDInterface(cli, n) for n in self.pd_names]
        if "fg" in cli:
            self.fg = FGInterface(cli, "fg")
        else:
            self.fg = None
        self.add_instruments(self.pg, self.fg, self.clock, *self.pds, *self.sgs.values())

        self.length = self.offsets = self.freq = None
        self.trace_count = None
        self.samples_per_trace = None

        self.check_required_conf(
            ["pd_trigger", "block_base", "pg_freq", "reduce_start_divisor", "minimum_block_length"]
        )
        self._pd_trigger = self.conf["pd_trigger"]
        self._pd_data_transfer = self.conf.get("pd_data_transfer")
        self._quick_resume = self.conf.get("quick_resume", True)
        self._start_delay = self._conf_nonneg_num("start_delay", 0.5)

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
        self._acquisition_failed = False

    def _sweeps_per_record(self, params: dict) -> int:
        return int(params.get("sweeps_per_record", 1))

    def _validate_sweep_params(self, params: dict) -> bool:
        sweeps = int(params.get("sweeps", 0))
        sweeps_per_record = self._sweeps_per_record(params)
        if sweeps_per_record < 1:
            self.logger.error(
                f"sweeps_per_record must be at least 1: sweeps_per_record={sweeps_per_record}"
            )
            return False
        if params.get("hardware_sweep_limit", False) and sweeps > 0 and sweeps % sweeps_per_record:
            self.logger.error(
                "sweeps must be an integer multiple of sweeps_per_record: "
                f"sweeps={sweeps}, sweeps_per_record={sweeps_per_record}"
            )
            return False
        return True

    def _remaining_records(self, params: dict, records: int) -> int | None:
        sweeps = int(params.get("sweeps", 0))
        if not params.get("hardware_sweep_limit", False) or sweeps == 0:
            return None
        target_records = sweeps // self._sweeps_per_record(params)
        remaining_records = target_records - int(records)
        if remaining_records <= 0:
            self.logger.error(
                "finite sweep target has already been reached: "
                f"target_records={target_records}, records={records}"
            )
            return 0
        return remaining_records

    def _shots_per_point(self, params: dict) -> int:
        return int(params.get("shots_per_point", 1))

    def generate_blocks(self, data: APODMRData | None = None):
        if data is None:
            data = self.data
        self._set_num_pattern_and_validate_params(data)
        generator = self.generators[data.label]
        params = data.get_params()
        raw_blocks, freq, common_pulses = generator.generate_raw_blocks(data.xdata, params)
        blocks, laser_timing, trigger_timing, trace_length_ticks = self.builder.build_blocks(
            raw_blocks, freq, common_pulses, params, generator.num_mw()
        )
        return blocks, freq, laser_timing, trigger_timing, trace_length_ticks

    def validate_params(
        self, params: P.ParamDict[str, P.PDValue] | dict[str, P.RawPDValue], label: str
    ) -> bool:
        params = P.unwrap(params)
        if not self._validate_sweep_params(params):
            return False
        d = APODMRData(params, label)
        try:
            blocks, freq, _, _, _ = self.generate_blocks(d)
        except (ValueError, KeyError) as e:
            self.logger.error(f"Invalid params for {label}: {e}")
            return False
        offsets = self.pg.validate_blocks(blocks, freq)
        return offsets is not None

    def init_pg(self, params: dict) -> bool:
        if not (self.pg.stop() and self.pg.clear()):
            self.logger.error("Error stopping PG.")
            return False

        try:
            blocks, self.freq, laser_timing, trigger_timing, trace_length_ticks = (
                self.generate_blocks()
            )
        except (ValueError, KeyError) as e:
            self.logger.error(f"Invalid params for {self.data.label}: {e}")
            return False
        pd_rate = params["pd"]["rate"]
        sample_period = 1.0 / pd_rate
        self.samples_per_trace = max(1, int(round(trace_length_ticks / self.freq * pd_rate)))
        if self._pd_spectrum:
            granularity = self.conf.get("pd_segment_granularity", 16)
            offset = self.conf.get("pd_segment_offset", 0)
            try:
                adjusted = round_segment_samples_up(
                    self.samples_per_trace, granularity=granularity
                )
                adjusted -= offset
            except ValueError:
                self.logger.exception("failed to round samples_per_trace to segment granularity")
                return False
            if adjusted != self.samples_per_trace:
                self.logger.info(
                    "PD samples_per_trace adjusted: "
                    f"{self.samples_per_trace} to {adjusted} (granularity = {granularity} "
                    f"offset = {offset})"
                )
            self.samples_per_trace = adjusted
            trace_length_ticks = int(np.ceil(self.samples_per_trace * self.freq / pd_rate))
            if not self.builder.check_sample_duration(trace_length_ticks):
                self.logger.error(
                    "trace window overlaps the next trigger; reduce margins or pulse rate"
                )
                return False
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
            self.mw_modes,
        )
        return True

    def init_start_pds(self, remaining_records: int | None) -> bool:
        params = self.data.get_params()
        rate = params["pd"]["rate"]
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
        if self.clock is None:
            clock_pd = self._pd_trigger
        else:
            if not self.clock.configure(params_clock):
                self.logger.error("failed to configure clock.")
                return False
            clock_pd = self.clock.get_internal_output()

        cb_samples = self.trace_count * self.samples_per_trace
        drop_first = params["pd"].get("drop_first", 0)
        finite = remaining_records is not None
        buffer_size = cb_samples * params["pd"].get(
            "buffer_size_coeff", self.conf.get("buffer_size_coeff", 20)
        )
        samples = cb_samples * (remaining_records + drop_first) if finite else buffer_size
        if not (
            all(
                [
                    pd.configure_triggered(
                        clock_pd,
                        cb_samples,
                        samples,
                        rate,
                        buffer_size=buffer_size,
                        finite=finite,
                        drop_first=drop_first,
                        oversample=1,
                        block_samples=self.samples_per_trace,
                        block_reduce_factor=shots_per_point,
                        block_reduce_op="mean",
                        reduce_factor=sweeps_per_record,
                        reduce_op="mean",
                        bounds=params["pd"].get("bounds", (-10.0, 10.0)),
                        data_transfer=self._pd_data_transfer,
                        hardware_average=params["pd"].get("hardware_average", True),
                    )
                    for pd in self.pds
                ]
            )
            and (self.clock is None or self.clock.start())
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

        hardware_limited = bool(
            self.data.params.get("hardware_sweep_limit", False)
            and int(self.data.params.get("sweeps", 0)) > 0
        )
        lines = []
        for name, pd in zip(self.pd_names, self.pds):
            if hardware_limited:
                ls, overflowed = pd.pop_block_with_status()
                if overflowed:
                    self.logger.error(
                        f"PD queue overflowed during finite acquisition ({name}); "
                        "acquired records were dropped."
                    )
                    self._acquisition_failed = True
                    return False
            else:
                ls = pd.pop_block()
            if isinstance(ls, list):
                # PD has multi channel
                lines.extend(ls)
            else:
                # single channel, assume ls is np.ndarray
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
                options = self._plotmode_options(self.data.label)
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
        self._acquisition_failed = False
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
            self.data.update_params(params)
        if not self._validate_sweep_params(self.data.params):
            return False
        remaining_records = self._remaining_records(self.data.params, self.data.records)
        if remaining_records == 0:
            return False
        try:
            self._set_num_pattern_and_validate_params(self.data)
        except ValueError as e:
            self.logger.error(f"Invalid params for {label}: {e}")
            return False

        self._analysis_warned = False
        sweeps_limit = self.data.params.get("sweeps", 0)
        sweeps_per_record = self._sweeps_per_record(self.data.params)
        if sweeps_limit > 0 and sweeps_limit % sweeps_per_record:
            self.logger.warn(
                "sweeps is not divisible by sweeps_per_record; measurement will stop on the "
                "next completed record boundary. Enable hardware_sweep_limit to require an "
                "exact limit."
            )
        if not self.lock_instruments():
            return self.fail_with_release("Error acquiring instrument locks.")

        if quick_resume:
            self.logger.info("Quick resume enabled: skipping initial inst configurations.")
        if not quick_resume and not self.init_inst(self.data.params):
            return self.fail_with_release("Error initializing instruments.")
        # PD/clock configuration is always refreshed on each start, even with quick resume.
        if not self.init_start_pds(remaining_records):
            return self.fail_with_release("Error initializing or starting PDs.")

        success = self.start_sg(self.data.params)
        if self._fg_enabled(self.data.params):
            success &= self.fg.set_output(True)

        time.sleep(self._start_delay)

        success &= self.pg.start()

        if not success:
            self.pg.stop()
            if self._fg_enabled(self.data.params):
                self.fg.set_output(False)
            self.stop_sg()
            for pd in self.pds:
                pd.stop()
            if self.clock is not None:
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
        if self._acquisition_failed:
            return True
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
        if self.clock is not None:
            success &= self.clock.stop() and self.clock.release()
        if self._fg_enabled(self.data.params):
            success &= self.fg.set_output(False)
        if self.fg is not None:
            success &= self.fg.release()

        self.data.finalize()
        if success:
            self.logger.info("Stopped pulser.")
        else:
            self.logger.error("Error stopping pulser.")
        return success

    def _pd_rate_param(self):
        rate = self.conf.get("pd_rate", 2e6)
        if isinstance(rate, (tuple, list)) and isinstance(rate[0], int):
            return P.IntChoiceParam(rate[0], rate, doc="PD sampling rate")
        elif isinstance(rate, int):
            return P.IntParam(
                rate, 1e3, 1e9, unit="Hz", SI_prefix=True, digit=9, doc="PD sampling rate"
            )
        elif isinstance(rate, float):
            return P.FloatParam(
                rate, 1e3, 1e9, unit="Hz", SI_prefix=True, digit=9, doc="PD sampling rate"
            )
        raise TypeError("conf['pd_rate'] has invalid type.")

    def get_param_dict(self, label: str) -> P.ParamDict[str, P.PDValue] | None:
        d = super().get_param_dict(label)
        if d is None:
            return None
        if "head" in d["plot"]["taumode"].options():
            taumodes = tuple(m for m in d["plot"]["taumode"].options() if m != "head")
            d["plot"]["taumode"] = P.StrChoiceParam("raw", taumodes)

        # Since divide_block is TODO and not implemented, default it to False anyway.
        if "divide_block" in d:
            d["divide_block"] = P.BoolParam(False)
        # remove unused params
        if "timebin" in d:
            del d["timebin"]
        if "interval" in d:
            del d["interval"]

        d["hardware_sweep_limit"] = P.BoolParam(
            False,
            doc=(
                "stop detector acquisition at the exact sweep limit in hardware; requires "
                "sweeps divisible by sweeps_per_record; acquisition is aborted if the detector "
                "software queue discards a record"
            ),
        )

        # set defaults which won't result in marker out-of-bounds
        d["plot"]["sigdelay"].set(200e-9)
        d["plot"]["sigwidth"].set(300e-9)
        d["plot"]["refdelay"].set(1000e-9)
        d["plot"]["refwidth"].set(500e-9)

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
        d["max_records"] = P.IntParam(
            self.conf.get("max_records", 1),
            0,
            100000000,
            doc="maximum number of raw trace records to retain (0 for unlimited)",
        )
        d["shots_per_point"] = P.IntParam(
            self.conf.get("shots_per_point", 1),
            1,
            1000000,
            doc="number of repeated shots per sweep point",
        )
        d["point_init_delay"] = P.FloatParam(
            self.conf.get("point_init_delay", 0.0),
            0.0,
            1.0,
            unit="s",
            SI_prefix=True,
            doc="dark delay before the initialization laser for each sweep point",
        )
        d["pd"] = P.ParamDict()
        d["pd"]["rate"] = self._pd_rate_param()
        lb, ub = self.conf.get("pd_bounds", (-10.0, 10.0))
        d["pd"]["buffer_size_coeff"] = P.IntParam(
            self.conf.get("buffer_size_coeff", 20),
            1,
            10_000,
            doc="ratio of requested buffer size to record data size",
        )
        d["pd"]["bounds"] = [
            P.FloatParam(lb, -10.0, +10.0, doc="PD voltage lower bound"),
            P.FloatParam(ub, -10.0, +10.0, doc="PD voltage upper bound"),
        ]
        d["pd"]["drop_first"] = P.IntParam(0, 0, 100, doc="drop first N records to stabilize")
        if self._pd_spectrum:
            d["pd"]["hardware_average"] = P.BoolParam(True, doc="use hardware block averaging")
        d["pd"]["eos_deadtime"] = P.FloatParam(
            200e-9, 0.0, 1.0, unit="s", SI_prefix=True, doc="end-of-sample deadtime"
        )

        return d

    def work(self):
        return self.update()

    def data_msg(self) -> APODMRData:
        return self.data

    def pulse_msg(self) -> PulsePattern | None:
        return self.pulse_pattern
