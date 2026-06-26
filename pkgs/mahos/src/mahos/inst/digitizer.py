#!/usr/bin/env python3

"""
Digitizer instruments.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import threading
import time
import enum

import numpy as np

from mahos.inst.instrument import Instrument
from mahos.util.locked_queue import LockedQueue


class SpectrumAnalogIn(Instrument):
    """AnalogIn-compatible Spectrum Instrumentation digitizer.

    This class supports continuous FIFO acquisition only. In ``triggered`` mode, each hardware
    trigger records a fixed-length segment with Spectrum multiple-recording FIFO mode. In
    ``tracer`` mode, data are streamed continuously with single FIFO mode.

    :param lines: channel indices to enable, for example ``[0]`` or ``[0, 1]``.
    :type lines: list[int | str]
    :param channel_mask: explicit Spectrum channel bit mask. Takes precedence over ``lines``.
    :type channel_mask: int
    :param resource: card resource such as ``/dev/spcm0`` or ``TCPIP::192.168.1.10::inst0::INSTR``.
    :type resource: str
    :param serial_number: card serial number.
    :type serial_number: int
    :param queue_size: (default: 10000) software buffer size.
    :type queue_size: int
    :param silent: (default: False) suppress queue overflow warnings.
    :type silent: bool
    :param unit: (default: V) reported data unit.
    :type unit: str
    :param gain: (default: 1.0) conversion gain in V per output unit.
    :type gain: float
    :param timeout_sec: (default: 5.0) card timeout in seconds.
    :type timeout_sec: float
    :param notify_alignment_bytes: (default: 4096) required byte alignment for FIFO
        notify sizes. Set to ``1`` to disable alignment.
    :type notify_alignment_bytes: int

    """

    class Mode(enum.Enum):
        UNCONFIGURED = 0
        TRACER = 1
        TRIGGERED = 2

    def __init__(self, name, conf=None, prefix=None):
        Instrument.__init__(self, name, conf=conf, prefix=prefix)

        if "channel_mask" not in self.conf:
            self.check_required_conf(("lines",))
        self.lines = self.conf.get("lines", [0])
        self.queue_size = self.conf.get("queue_size", 10000)
        self.queue = LockedQueue(self.queue_size)
        self._silent = self.conf.get("silent", False)
        self.unit = self.conf.get("unit", "V")
        self.gain = float(self.conf.get("gain", 1.0))

        self._spcm = None
        self._card = None
        self._channels = None
        self._transfer = None
        self._reader = None
        self._stop_ev = threading.Event()
        self.running = False

        self._mode = self.Mode.UNCONFIGURED
        self._stamp = False
        self._line_num = 0
        self._oversample = 1
        self._block_reduce_factor = 1
        self._block_reduce_samples = 0
        self._block_reduce_op = "mean"
        self._reduce_factor = 1
        self._reduce_op = "mean"
        self._hardware_average = False
        self._averages = 1
        self._drop_records_left = 0
        self._segment_samples = 0
        self._record_samples = 0
        self._tracer_samples = 0
        self._notify_samples = 0
        self._buffer_samples = 0
        self._pending: list[list[np.ndarray]] = []

    def _import_spcm(self):
        if self._spcm is None:
            import spcm

            self._spcm = spcm
        return self._spcm

    def _open_card(self):
        spcm = self._import_spcm()
        if self._card is not None:
            return self._card

        kwargs = {"verbose": self.conf.get("verbose", False)}
        if self.conf.get("serial_number") is not None:
            kwargs["serial_number"] = self.conf["serial_number"]
            self._card = spcm.Card(**kwargs)
        elif self.conf.get("resource"):
            self._card = spcm.Card(self.conf["resource"], **kwargs)
        else:
            self._card = spcm.Card(card_type=spcm.SPCM_TYPE_AI, **kwargs)
        self._card.open()
        return self._card

    def _channel_index(self, line) -> int:
        if isinstance(line, str):
            s = line.strip().lower()
            for prefix in ("channel", "ch"):
                if s.startswith(prefix):
                    s = s[len(prefix) :]
                    break
            return int(s)
        return int(line)

    def _channel_mask(self) -> int:
        spcm = self._import_spcm()
        if "channel_mask" in self.conf:
            return int(self.conf["channel_mask"])
        mask = 0
        for line in self.lines:
            idx = self._channel_index(line)
            mask |= int(getattr(spcm, f"CHANNEL{idx}", 1 << idx))
        return mask

    def _get_amp_mV(self, termination: int, amp_V: float) -> int:
        amps = {1_000_000: [200, 500, 1000, 2000, 5000, 10000], 50: [500, 1000, 2500, 5000]}[
            termination
        ]
        target_mV = round(amp_V * 1e3)
        for a in amps:
            if target_mV <= a:
                return a
        else:
            raise ValueError(f"requested amplitude is invalid: {amp_V}")

    def _get_offset_percent(self, amp_V: float, offset_V: float) -> int:
        ofs = int(round(offset_V / amp_V * 100))
        if ofs > 100:
            raise ValueError(f"requested offset is too large: {ofs:d}% > 100%")
        return ofs

    def _setup_channels(self, bounds, params) -> bool:
        spcm = self._import_spcm()
        card = self._open_card()
        self._channels = spcm.Channels(card, card_enable=self._channel_mask())
        self._line_num = len(self._channels)

        # need to set termination before setting amp/offset
        termination = int(params.get("termination", self.conf.get("termination", 1_000_000)))
        if termination == 1_000_000:
            self._channels.termination(0)
            self.logger.debug("input termination: HighZ (1 M)")
        elif termination == 50:
            self._channels.termination(1)
            self.logger.debug("input termination: 50 Ohm")
        else:
            return self.fail_with(f"invalid termination: {termination} (must be 50 or 1 M)")

        if "DC_coupling" in params or "DC_coupling" in self.conf:
            DC_coupling = bool(params.get("DC_coupling", self.conf.get("DC_coupling", True)))
            if DC_coupling:
                self._channels.coupling(spcm.COUPLING_DC)
            else:
                self._channels.coupling(spcm.COUPLING_AC)

        for ch, bnds in zip(self._channels, bounds):
            if len(bnds) == 2 and isinstance(bnds[0], (float, int, np.integer, np.floating)):
                lb, ub = bnds
                # amp is zero-to-peak amplitude
                amp_V = float(ub - lb) / 2.0
                offset_V = float(ub + lb) / 2.0
                amp = self._get_amp_mV(termination, amp_V)
                offset = self._get_offset_percent(amp_V, offset_V)
                amp_set = ch.amp(amp * spcm.units.mV, return_unit=spcm.units.mV)
                ofs_set = ch.offset(offset * spcm.units.percent, return_unit=spcm.units.V)
                self.logger.debug(f"{ch} range: Amp = {amp_set}, Offset = {ofs_set}")
            else:
                return self.fail_with(f"invalid bounds: {bnds}")

        return True

    def _setup_clock(self, params):
        spcm = self._import_spcm()
        clock = spcm.Clock(self._open_card())
        mode = str(
            params.get("clock_mode_spcm", self.conf.get("clock_mode_spcm", "intpll"))
        ).lower()
        if mode == "intpll":
            clock.mode(spcm.SPC_CM_INTPLL)
        else:
            return self.fail_with(f"unsupported Spectrum clock mode: {mode}")
        rate_req = int(round(params["rate"])) * spcm.units.Hz
        rate_ret = clock.sample_rate(rate_req, return_unit=spcm.units.Hz)
        msg = f"Sampling rate: requested = {rate_req.magnitude:_d} Hz, "
        msg += f"actual = {rate_ret.magnitude:_d} Hz"
        self.logger.debug(msg)
        return True

    def _setup_trigger(self, params):
        spcm = self._import_spcm()
        trigger = spcm.Trigger(self._open_card())
        source = str(params.get("trigger_source", self.conf.get("trigger_source", "ext0"))).lower()
        direction = params.get("trigger_dir", True)
        mode = spcm.SPC_TM_POS if direction else spcm.SPC_TM_NEG

        if source in ("ext0", "external0"):
            trigger.or_mask(spcm.SPC_TMASK_EXT0)
            trigger.ext0_mode(mode)
            if "trigger_termination" in params or "trigger_termination" in self.conf:
                termination = int(
                    params.get("trigger_termination", self.conf.get("trigger_termination"))
                )
            else:
                termination = int(
                    params.get("termination", self.conf.get("termination", 1_000_000))
                )
            if termination == 1_000_000:
                trigger.termination(0)
                self.logger.debug("trigger ext0 termination: HighZ (1 M)")
            elif termination == 50:
                trigger.termination(1)
                self.logger.debug("trigger ext0 termination: 50 Ohm")
            else:
                return self.fail_with(f"invalid termination: {termination} (must be 50 or 1 M)")
            trigger.ext0_coupling(spcm.COUPLING_DC)
            trigger.ext0_level0(
                float(params.get("trigger_level", self.conf.get("trigger_level", 0.25)))
                * spcm.units.V
            )
            trigger.and_mask(spcm.SPC_TMASK_NONE)
        elif source in ("software", "soft"):
            trigger.or_mask(spcm.SPC_TMASK_SOFTWARE)
            trigger.and_mask(spcm.SPC_TMASK_NONE)
        elif source in ("none", ""):
            trigger.or_mask(spcm.SPC_TMASK_NONE)
            trigger.and_mask(spcm.SPC_TMASK_NONE)
        else:
            return self.fail_with(f"unsupported Spectrum trigger_source: {source}")
        return True

    def _start_transfer(self, *commands):
        self._transfer.start_buffer_transfer(*commands)

    def _notify_alignment_bytes(self) -> int:
        return max(1, int(self.conf.get("notify_alignment_bytes", 4096)))

    def _samples_to_bytes(self, samples: int) -> int:
        return int(self._transfer.samples_to_bytes(int(samples)))

    def _ceil_to_multiple(self, value: int, step: int) -> int:
        value = max(1, int(value))
        step = max(1, int(step))
        return ((value + step - 1) // step) * step

    def _align_notify_samples(self, min_samples: int, step_samples: int = 1) -> int:
        alignment = self._notify_alignment_bytes()
        samples = self._ceil_to_multiple(min_samples, step_samples)
        if alignment <= 1:
            return samples

        max_trials = int(self.conf.get("notify_alignment_trials", alignment))
        for _ in range(max_trials):
            if self._samples_to_bytes(samples) % alignment == 0:
                return samples
            samples += max(1, int(step_samples))
        raise ValueError(
            f"could not align notify_samples to {alignment} bytes "
            f"from {min_samples} samples with step {step_samples}"
        )

    def _align_buffer_samples(self, min_samples: int, notify_samples: int) -> int:
        return self._ceil_to_multiple(max(min_samples, notify_samples), notify_samples)

    def _log_fifo_sizes(
        self,
        mode: str,
        requested_notify: int,
        notify_samples: int,
        buffer_samples: int,
        segment_samples: int | None = None,
    ):
        msg = "{:s} FIFO notify_samples: requested = {:_d} ({:_d} B), ".format(
            mode,
            requested_notify,
            self._samples_to_bytes(requested_notify),
        )
        msg += "aligned = {:_d} ({:_d} B); ".format(
            notify_samples,
            self._samples_to_bytes(notify_samples),
        )
        msg += "buffer_samples = {:_d} ({:_d} B), buffer/notify = {:.1f}".format(
            buffer_samples,
            self._samples_to_bytes(buffer_samples),
            buffer_samples / notify_samples,
        )
        if segment_samples is not None:
            msg += "; segment_samples = {:_d}, ".format(segment_samples)
            msg += "notify/segment: requested = {:.1f}, aligned = {:.1f}".format(
                requested_notify / segment_samples,
                notify_samples / segment_samples,
            )
        self.logger.debug(msg)

    def _append_data(self, data: np.ndarray | list[np.ndarray]):
        data = self._convert_gain(data)
        if (
            not self.queue.append((data, time.time_ns()) if self._stamp else data)
            and not self._silent
        ):
            self.logger.warn("queue is overflowing. The oldest data is discarded.")

    def _convert_gain(self, data):
        if isinstance(data, list):
            return [d / self.gain for d in data]
        return data / self.gain

    def _as_float_array(self, data) -> np.ndarray:
        if hasattr(data, "magnitude"):
            data = data.magnitude
        return np.asarray(data, dtype=np.float64)

    def _convert_segment(self, segment) -> list[np.ndarray]:
        spcm = self._import_spcm()
        out = []
        for i, ch in enumerate(self._channels):
            raw = segment[:, i] if segment.ndim > 1 else segment
            data = ch.convert_data(raw, spcm.units.V, averages=self._averages)
            data = self._as_float_array(data)
            out.append(data)
        return out

    def _convert_fifo_block(self, block) -> list[np.ndarray]:
        spcm = self._import_spcm()
        out = []
        for i, ch in enumerate(self._channels):
            raw = block[i, :] if block.ndim > 1 else block
            data = ch.convert_data(raw, spcm.units.V, averages=self._averages)
            data = self._as_float_array(data)
            out.append(data)
        return out

    def _reduce_tracer(self, data: np.ndarray) -> np.ndarray:
        if self._oversample > 1:
            if len(data) % self._oversample:
                raise ValueError("tracer block length must be divisible by oversample")
            data = data.reshape(-1, self._oversample).mean(axis=1)
        return data

    def _reduce_record(self, data: np.ndarray) -> np.ndarray:
        if self._oversample > 1:
            if len(data) % self._oversample:
                raise ValueError("record length must be divisible by oversample")
            data = data.reshape(-1, self._oversample).mean(axis=1)
        if self._block_reduce_factor > 1 and not self._hardware_average:
            data = data.reshape(-1, self._block_reduce_factor, self._block_reduce_samples)
            if self._block_reduce_op == "sum":
                data = data.sum(axis=1)
            else:
                data = data.mean(axis=1)
            data = data.reshape(-1)
        if self._reduce_factor > 1:
            data = data.reshape(self._reduce_factor, len(data) // self._reduce_factor)
            if self._reduce_op == "sum":
                data = data.sum(axis=0)
            else:
                data = data.mean(axis=0)
        return data

    def _append_record_segments(self, segments: list[np.ndarray]):
        for ch_pending, segment in zip(self._pending, segments):
            ch_pending.append(segment)

        while all(
            sum(len(a) for a in ch_pending) >= self._record_samples for ch_pending in self._pending
        ):
            record = []
            for ch_pending in self._pending:
                data = np.concatenate(ch_pending)
                current = data[: self._record_samples]
                rest = data[self._record_samples :]
                ch_pending.clear()
                if len(rest):
                    ch_pending.append(rest)
                record.append(self._reduce_record(current))
            if self._drop_records_left > 0:
                self._drop_records_left -= 1
                continue
            self._append_data(record[0] if len(record) == 1 else record)

    def _append_tracer_samples(self, samples: list[np.ndarray]):
        for ch_pending, data in zip(self._pending, samples):
            ch_pending.append(data)

        while all(
            sum(len(a) for a in ch_pending) >= self._tracer_samples for ch_pending in self._pending
        ):
            block = []
            for ch_pending in self._pending:
                data = np.concatenate(ch_pending)
                current = data[: self._tracer_samples]
                rest = data[self._tracer_samples :]
                ch_pending.clear()
                if len(rest):
                    ch_pending.append(rest)
                block.append(self._reduce_tracer(current))
            self._append_data(block[0] if len(block) == 1 else block)

    def _reader_loop(self):
        try:
            if self._mode == self.Mode.TRIGGERED:
                for block in self._transfer:
                    if self._stop_ev.is_set():
                        break
                    for segment in block:
                        self._append_record_segments(self._convert_segment(segment))
            else:
                for block in self._transfer:
                    if self._stop_ev.is_set():
                        break
                    converted = self._convert_fifo_block(block)
                    self._append_tracer_samples(converted)
        except Exception:
            if not self._stop_ev.is_set():
                self.logger.exception("Spectrum FIFO reader stopped with an exception.")

    def _get_bounds(self, params):
        bounds = params.get("bounds", self.conf.get("bounds", (-10.0, 10.0)))
        if len(bounds) == 2 and isinstance(bounds[0], (float, int, np.integer, np.floating)):
            return [tuple(bounds)] * len(self.lines)
        return bounds

    def _validate_reduce_params(self, params) -> bool:
        self._oversample = int(params.get("oversample", 1))
        self._block_reduce_factor = int(params.get("block_reduce_factor", 1))
        self._block_reduce_samples = int(params.get("block_reduce_samples", 0))
        self._block_reduce_op = str(params.get("block_reduce_op", "mean")).lower()
        self._reduce_factor = int(params.get("reduce_factor", 1))
        self._reduce_op = str(params.get("reduce_op", "mean")).lower()

        if self._oversample < 1:
            return self.fail_with("oversample must be positive.")
        if self._block_reduce_factor < 1:
            return self.fail_with("block_reduce_factor must be positive.")
        if self._block_reduce_op not in ("sum", "mean"):
            return self.fail_with(
                f"block_reduce_op must be 'sum' or 'mean': {self._block_reduce_op}"
            )
        if self._block_reduce_factor > 1 and self._block_reduce_samples < 1:
            return self.fail_with(
                "block_reduce_samples must be positive when block_reduce_factor > 1."
            )
        if self._reduce_factor < 1:
            return self.fail_with("reduce_factor must be positive.")
        if self._reduce_op not in ("sum", "mean"):
            return self.fail_with(f"reduce_op must be 'sum' or 'mean': {self._reduce_op}")
        return True

    def configure_triggered(self, params: dict) -> bool:
        required = ("trigger_source", "cb_samples", "samples", "rate")
        if not self.check_required_params(params, required):
            return False
        if "segment_samples" not in params:
            return self.fail_with("segment_samples is required for Spectrum triggered mode.")
        if not self._validate_reduce_params(params):
            return False

        self.stop()
        spcm = self._import_spcm()
        card = self._open_card()
        self._stamp = params.get("stamp", False)
        self._segment_samples = int(params["segment_samples"])
        if self._segment_samples < 32 or self._segment_samples % 16:
            return self.fail_with(
                "segment_samples must be an integer multiple of 16 and at least 32."
            )
        self._drop_records_left = abs(int(params.get("drop_first", 0)))
        self._hardware_average = (
            bool(params.get("hardware_average", True)) and self._block_reduce_factor > 1
        )
        if self._hardware_average and self._block_reduce_op != "mean":
            return self.fail_with(
                "Spectrum hardware averaging supports block_reduce_op='mean' only."
            )
        self._averages = self._block_reduce_factor if self._hardware_average else 1
        self._record_samples = int(params["cb_samples"]) * self._oversample * self._reduce_factor
        if not self._hardware_average:
            self._record_samples *= self._block_reduce_factor
        if self._record_samples % self._segment_samples:
            return self.fail_with("record samples must be an integer multiple of segment_samples.")

        timeout_sec = float(params.get("timeout_sec", self.conf.get("timeout_sec", 5.0)))
        if self._hardware_average:
            card.card_mode(spcm.SPC_REC_FIFO_AVERAGE)
        else:
            card.card_mode(spcm.SPC_REC_FIFO_MULTI)
        card.timeout(timeout_sec * spcm.units.s)
        card.loops(0)

        if not self._setup_trigger(params):
            return False

        bounds = self._get_bounds(params)
        if not self._setup_channels(bounds, params):
            return False

        if not self._setup_clock(params):
            return False

        if self._hardware_average:
            self._transfer = spcm.BlockAverage(card)
            self._transfer.averages(self._block_reduce_factor)
        else:
            self._transfer = spcm.Multi(card)

        segments_per_record = self._record_samples // self._segment_samples
        requested_notify_samples = segments_per_record * self._segment_samples
        try:
            self._notify_samples = self._align_notify_samples(
                requested_notify_samples, step_samples=self._segment_samples
            )
        except ValueError as e:
            return self.fail_with(str(e))

        if params.get("buffer_segments"):
            requested_buffer_samples = int(params["buffer_segments"]) * self._segment_samples
        else:
            buffer_samples = int(params.get("buffer_size", params["samples"]))
            buffer_samples *= self._oversample * self._reduce_factor
            if not self._hardware_average:
                buffer_samples *= self._block_reduce_factor
            buffer_records = max(1, buffer_samples // self._record_samples)
            requested_buffer_samples = buffer_records * self._record_samples

        requested_buffer_samples = max(requested_notify_samples, requested_buffer_samples)
        self._buffer_samples = self._align_buffer_samples(
            requested_buffer_samples, self._notify_samples
        )
        buffer_segments = self._buffer_samples // self._segment_samples
        self._log_fifo_sizes(
            "triggered",
            requested_notify_samples,
            self._notify_samples,
            self._buffer_samples,
            self._segment_samples,
        )
        self._transfer.allocate_buffer(
            segment_samples=self._segment_samples, num_segments=buffer_segments
        )
        self._transfer.notify_samples(self._notify_samples)
        # set maximum post_trigger given segment_samples. as min of pre_trigger is 16 samples,
        # maximum post_trigger is segment_samples - 16.
        self._transfer.post_trigger(self._segment_samples - 16)

        self.queue = LockedQueue(self.queue_size)
        self._pending = [[] for _ in range(self._line_num)]
        self._mode = self.Mode.TRIGGERED
        self.logger.debug("Configured Spectrum triggered FIFO mode.")
        return True

    def configure_tracer(self, params: dict) -> bool:
        if not self.check_required_params(params, ("cb_samples", "samples", "rate")):
            return False
        if not self._validate_reduce_params(params):
            return False

        self.stop()
        spcm = self._import_spcm()
        card = self._open_card()
        self._stamp = params.get("stamp", False)
        self._hardware_average = False
        self._averages = 1

        card.card_mode(spcm.SPC_REC_FIFO_SINGLE)
        timeout_sec = float(params.get("timeout_sec", self.conf.get("timeout_sec", 5.0)))
        card.timeout(timeout_sec * spcm.units.s)
        if not self._setup_trigger({"trigger_source": "software"}):
            return False
        bounds = self._get_bounds(params)
        if not self._setup_channels(bounds, params):
            return False
        if not self._setup_clock(params):
            return False

        self._transfer = spcm.DataTransfer(card)
        self._tracer_samples = int(params["cb_samples"]) * self._oversample
        try:
            self._notify_samples = self._align_notify_samples(self._tracer_samples)
        except ValueError as e:
            return self.fail_with(str(e))
        requested_buffer_samples = max(
            self._tracer_samples,
            int(params.get("buffer_size", params["samples"])) * self._oversample,
        )
        self._buffer_samples = self._align_buffer_samples(
            requested_buffer_samples, self._notify_samples
        )
        self._log_fifo_sizes(
            "tracer", self._tracer_samples, self._notify_samples, self._buffer_samples
        )
        self._transfer.allocate_buffer(self._buffer_samples)
        self._transfer.notify_samples(self._notify_samples)
        pre_trigger = int(params.get("pre_trigger", self.conf.get("pre_trigger", 16)))
        self._transfer.pre_trigger(pre_trigger)

        self.queue = LockedQueue(self.queue_size)
        self._pending = [[] for _ in range(self._line_num)]
        self._mode = self.Mode.TRACER
        self.logger.debug("Configured Spectrum tracer FIFO mode.")
        return True

    def get_fifo_status(self) -> dict:
        if self._mode == self.Mode.TRIGGERED:
            return {
                "segment_samples": self._segment_samples,
                "record_samples": self._record_samples,
                "notify_samples": self._notify_samples,
                "buffer_samples": self._buffer_samples,
            }
        elif self._mode == self.Mode.TRACER:
            return {
                "tracer_samples": self._tracer_samples,
                "notify_samples": self._notify_samples,
                "buffer_samples": self._buffer_samples,
            }
        else:
            self.logger.error("fifo status is requested but not configured.")
            return {}

    # Standard API

    def configure(self, params: dict, label: str = "") -> bool:
        if not params.get("clock_mode", True):
            return self.fail_with("SpectrumAnalogIn does not support on-demand mode.")
        mode = params.get("mode", "triggered" if "trigger_source" in params else "tracer")
        if mode == "triggered":
            return self.configure_triggered(params)
        elif mode == "tracer":
            return self.configure_tracer(params)
        else:
            return self.fail_with(f"unknown SpectrumAnalogIn mode: {mode}")

    def start(self, label: str = "") -> bool:
        if self.running:
            self.logger.warn("start() is called while running.")
            return True
        if self._mode == self.Mode.UNCONFIGURED or self._transfer is None:
            return self.fail_with("Must call configure() before start().")

        spcm = self._import_spcm()
        self._stop_ev.clear()
        self._start_transfer(spcm.M2CMD_DATA_STARTDMA)
        self._card.start(spcm.M2CMD_CARD_ENABLETRIGGER)
        self._reader = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader.start()
        self.running = True
        self.logger.debug("Started SpectrumAnalogIn.")
        return True

    def stop(self, label: str = "") -> bool:
        if not self.running:
            return True
        self._stop_ev.set()
        try:
            spcm = self._import_spcm()
            self._card.stop(spcm.M2CMD_DATA_STOPDMA)
        except Exception:
            self.logger.exception("Exception while stopping Spectrum card.")
        if self._reader is not None:
            self._reader.join(timeout=float(self.conf.get("stop_join_sec", 2.0)))
            if self._reader.is_alive():
                self.logger.warn("Spectrum reader thread did not stop before timeout.")
        self._reader = None
        self.running = False
        self._mode = self.Mode.UNCONFIGURED
        self.logger.debug("Stopped SpectrumAnalogIn.")
        return True

    def close_resources(self):
        self.stop()
        if self._card is not None:
            try:
                self._card.close()
            except Exception:
                self.logger.exception("Exception while closing Spectrum card.")
            self._card = None

    def pop_opt(self):
        return self.queue.pop_opt()

    def pop_all_opt(self):
        return self.queue.pop_all_opt()

    def pop_block(self):
        return self.queue.pop_block()

    def pop_all_block(self):
        return self.queue.pop_all_block()

    def set(self, key: str, value=None, label: str = "") -> bool:
        key = key.lower()
        if key == "gain":
            self.gain = float(value)
            return True
        elif key == "unit":
            self.unit = str(value)
            return True
        return self.fail_with(f"unknown set() key: {key}")

    def get(self, key: str, args=None, label: str = ""):
        if key == "data":
            return self.pop_block() if args else self.pop_opt()
        elif key == "all_data":
            return self.pop_all_block() if args else self.pop_all_opt()
        elif key == "fifo_status":
            return self.get_fifo_status()
        elif key == "unit":
            return self.unit
        else:
            self.logger.error(f"unknown get() key: {key}")
            return None
