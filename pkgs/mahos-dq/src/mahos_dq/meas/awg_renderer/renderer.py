#!/usr/bin/env python3

"""
AWG renderer: render PODMR ``Blocks[Block]`` for an AWG.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

Behavior:

- Rendering/validation (:meth:`render`) does no hardware writes, so workers
  can fail early (before arming detectors) on amplitude/memory violations.
- Each card-output amplitude is set to its summed tone peaks (exact per-tone dBm).

"""

from __future__ import annotations

import math
import os
import typing as T
import uuid

import numpy as np

from mahos.inst.awg_interface import AWGInterface
from mahos.inst.awg_file import save_waveforms
from mahos.node.log import DummyLogger
import mahos_dq.meas.awg_renderer.renderer_kernel as K
from mahos.msgs.inst.pg_msgs import Block, Blocks
from mahos.msgs.inst.awg_msgs import TriggerType, AWGWaveform


def _minmax_preview(data: np.ndarray, max_points: int) -> tuple[np.ndarray, np.ndarray]:
    """Reduce data to bounded extrema and their original indices."""

    n = len(data)
    if n <= max_points:
        return np.arange(n, dtype=np.uint64), np.asarray(data, dtype=np.float32)

    num_bins = max_points // 2
    bin_size = math.ceil(n / num_bins)
    num_full = n // bin_size
    indices = []

    if num_full:
        shaped = data[: num_full * bin_size].reshape(num_full, bin_size)
        bases = np.arange(num_full, dtype=np.int64) * bin_size
        i_min = bases + np.argmin(shaped, axis=1)
        i_max = bases + np.argmax(shaped, axis=1)
        first = np.minimum(i_min, i_max)
        second = np.maximum(i_min, i_max)
        paired = np.column_stack((first, second)).ravel()
        distinct = np.column_stack((np.ones(num_full, dtype=bool), first != second)).ravel()
        indices.append(paired[distinct])

    tail_start = num_full * bin_size
    if tail_start < n:
        tail = data[tail_start:]
        i_min = tail_start + int(np.argmin(tail))
        i_max = tail_start + int(np.argmax(tail))
        indices.append(np.array(sorted(set((i_min, i_max))), dtype=np.int64))

    index = np.concatenate(indices).astype(np.uint64, copy=False)
    return index, np.asarray(data[index], dtype=np.float32)


class AWGRenderer(object):
    """Renderer interface for AWG-based PODMR.

    :ivar awg: typed client interface of the AWG instrument.
    :ivar channels: one or two physical analog output channel indices.
    :ivar logger: std-logging style logger. Defaults to the module logger.

    """

    def __init__(
        self,
        awg: AWGInterface,
        channels: T.Iterable[int] | int = (0,),
        logger=None,
        file_transport_dir: str | None = None,
        remove_transport_file: bool = True,
    ):
        self.awg = awg
        raw_channels = (channels,) if isinstance(channels, int) else tuple(channels)
        if any(
            isinstance(channel, bool) or not isinstance(channel, int) for channel in raw_channels
        ):
            raise TypeError(f"channels must contain integers: {raw_channels}")
        self.channels = tuple(sorted(set(raw_channels)))
        if not (1 <= len(self.channels) <= 2):
            raise ValueError(f"channels must contain one or two unique outputs: {raw_channels}")
        self.logger = logger or DummyLogger()
        self.file_transport_dir = (
            os.path.abspath(os.path.expanduser(file_transport_dir)) if file_transport_dir else None
        )
        if self.file_transport_dir is not None and not os.path.isdir(self.file_transport_dir):
            raise FileNotFoundError(
                f"AWG file transport directory {self.file_transport_dir!r} "
                "does not exist or is not a directory"
            )
        self.remove_transport_file = bool(remove_transport_file)
        self._pending: tuple | None = None
        self._uploaded = False
        #: render / upload metadata of the last render()/upload()
        self._meta: dict = {}

    def _validate_tone_freqs(self, rate: float | int, tones: list[K.MWTone]):
        for tone in tones:
            f = tone.freq
            if not (math.isfinite(f) and 0.0 < f < rate / 2.0):
                raise ValueError(f"freq of {tone.channel} ({f}) is invalid.")

    @staticmethod
    def _positive_finite(name: str, value) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0.0
        ):
            raise ValueError(f"{name} must be a positive finite number: {value!r}")
        return float(value)

    @staticmethod
    def _validate_digital_min_duration(
        digital: dict[str, T.Any], rate: float, min_duration: float | None
    ):
        """Validate contiguous high and low durations of synchronous digital outputs."""

        if min_duration is None:
            return
        if (
            isinstance(min_duration, bool)
            or not isinstance(min_duration, (int, float))
            or not math.isfinite(min_duration)
            or min_duration < 0.0
        ):
            raise ValueError(f"invalid digital_min_duration: {min_duration}")

        min_samples = int(math.ceil(min_duration * rate - 1e-12))
        for name, track in digital.items():
            runs = K.rle_encode(track)
            if len(runs) <= 1:
                continue

            # Equal states at both ends form one contiguous interval across the replay boundary.
            if runs[0][0] == runs[-1][0]:
                runs = [(runs[0][0], runs[0][1] + runs[-1][1]), *runs[1:-1]]

            for value, samples in runs:
                if samples < min_samples:
                    duration = samples / rate
                    level = "high" if value else "low"
                    raise ValueError(
                        f"digital channel {name!r} has a {level} interval of "
                        f"{duration:.3e} s ({samples} samples), shorter than "
                        f"digital_min_duration {min_duration:.3e} s "
                        f"({min_samples} samples)"
                    )

    def _validate_rate(self, rate: float, bounds: dict) -> float:
        rate = self._positive_finite("AWG rate", rate)
        mn, mx = bounds["sample_rate"]
        if not (mn <= rate <= mx):
            raise ValueError(f"sample rate is out of bounds: {rate}")
        return rate

    def render(
        self,
        blocks: Blocks[Block] | T.Sequence[Block],
        pg_freq: float,
        tones: list[K.MWTone],
        num_logical_mw: int,
        params: dict,
        bounds: dict,
    ) -> dict:
        """Render `blocks` and validate against the instrument bounds.

        :param pg_freq: logical time base of the blocks in Hz.
        :param params: measurement parameters including ``awg.rate`` and optional
            ``awg.local_phase``.
        :returns: render meta-data dict (also accessible through :meth:`get_meta_data`).
        :raises ValueError: on inconsistent params, amplitude limit or memory
            violation, or sequence-form incompatibility.

        """

        self._pending = None
        self._uploaded = False

        rate = self._validate_rate(params["awg"]["rate"], bounds)
        pg_freq = self._positive_finite("PG frequency", pg_freq)
        available = tuple(bounds["analog_channels"])
        unavailable = [channel for channel in self.channels if channel not in available]
        if unavailable:
            raise ValueError(
                f"analog channels {unavailable} are not available; choose from {list(available)}"
            )
        rp = K.RenderParams(
            tones=tones,
            analog_channels=self.channels,
            num_logical_mw=num_logical_mw,
            load_impedance=bounds["load_impedance"],
            local_phase=params["awg"].get("local_phase", False),
        )
        self._validate_tone_freqs(rate, tones)

        # Each output amplitude is the sum of peaks assigned to it, preserving
        # exact per-tone dBm powers after normalization.
        amplitudes_mV = {}
        required = K.required_amplitude_mV(rp)
        amp_bounds = bounds["amplitude_mV"]
        if not isinstance(amp_bounds, (tuple, list)) or len(amp_bounds) != 2:
            raise ValueError(f"invalid amplitude_mV bounds: {amp_bounds!r}")
        amp_max = self._positive_finite("maximum AWG amplitude", amp_bounds[1])
        for channel, requested in required.items():
            amplitude_mV = int(math.ceil(requested - 1e-9)) if requested > 0.0 else 0
            if amplitude_mV > amp_max:
                raise ValueError(
                    f"CH{channel} tone peak sum {requested:.1f} mV exceeds the amplitude "
                    f"limit {amp_max} mV; reduce power or raise amp_limit_mV."
                )
            amplitudes_mV[channel] = amplitude_mV
        rp.amplitude_mV = {
            channel: float(amplitude) for channel, amplitude in amplitudes_mV.items()
        }

        gran = bounds["granularity"]
        mem = bounds["memory_samples"]
        if mem is not None and (isinstance(mem, bool) or not isinstance(mem, int) or mem <= 0):
            raise ValueError(f"memory_samples must be a positive integer or None: {mem!r}")

        n = K.flat_samples_estimate(blocks, pg_freq, rate)
        total = n * len(self.channels)
        if mem and total > mem:
            raise ValueError(
                f"estimated pattern uses {total:_d} sample words across "
                f"{len(self.channels)} channels, exceeding AWG memory {mem:_d}"
            )
        res = K.render_flat(blocks, pg_freq, rate, rp, granularity=gran)

        self._validate_digital_min_duration(res.digital, rate, bounds.get("digital_min_duration"))

        # TODO: form = "sequence" will be added in the future.
        form = "waveforms"

        n = res.actual_samples
        total = n * len(self.channels)
        if mem and total > mem:
            raise ValueError(
                f"pattern uses {total:_d} sample words across {len(self.channels)} channels, "
                f"exceeding AWG memory {mem:_d}"
            )

        self._pending = (res, form, amplitudes_mV, rate)
        self._meta = {
            "form": form,
            "analog_channels": self.channels,
            "amplitude_mV": dict(amplitudes_mV),
            "sample_rate": rate,
            "rendered_samples": res.rendered_samples,
            "actual_samples": n,
            "rendered_duration": res.rendered_samples / rate,
            "actual_duration": n / rate,
            "max_rounding_error_sec": res.max_rounding_error_sec,
        }
        return dict(self._meta)

    def upload(
        self,
        trigger_type: TriggerType = TriggerType.IMMEDIATE,
        n_runs: int | None = None,
        file_transport: bool = False,
    ) -> bool:
        """Set the card amplitude and configure the rendered pattern (does not start).

        :param trigger_type: trigger type.
        :param n_runs: pattern repetitions / accepted triggers. None: infinite.

        """

        if self._pending is None:
            return self.fail_with("Call render() before upload().")
        res, form, amplitudes_mV, rate = self._pending

        for channel, amplitude_mV in amplitudes_mV.items():
            if amplitude_mV > 0 and not self.awg.set_amplitude(channel, amplitude_mV):
                return self.fail_with(f"Failed to set CH{channel} AWG amplitude")
        transport = "file" if file_transport else "zmq"
        if form == "waveforms" and file_transport:
            ok = self._upload_waveforms_file(
                res.analog,
                res.digital_rle(),
                rate,
                trigger_type=trigger_type,
                n_runs=n_runs,
            )
        elif form == "waveforms":
            ok = self.awg.configure_waveforms(
                res.analog,
                res.digital_rle(),
                rate,
                trigger_type=trigger_type,
                n_runs=n_runs,
            )
        else:
            return self.fail_with(f"Form {form} is not supported yet.")
        if not ok:
            return self.fail_with("Failed to configure the AWG.")
        self._uploaded = True
        self._meta.update(trigger_type=str(trigger_type), n_runs=n_runs, transport=transport)
        self.logger.info(
            f"Uploaded {self._meta['form']} pattern: {self._meta['actual_samples']:_d} samples, "
            f"trigger_type = {trigger_type}, n_runs = {n_runs if n_runs is not None else 'inf'}."
        )
        return True

    def _upload_waveforms_file(
        self,
        analog: dict[int, np.ndarray],
        digital: dict[str, T.Any],
        rate: float,
        trigger_type: TriggerType,
        n_runs: int | None,
    ) -> bool:
        """Write an atomic transport file and synchronously configure the AWG from it."""

        if self.file_transport_dir is None:
            return self.fail_with("AWG file transport directory is not configured.")

        file_name = f"mahos_awg_{uuid.uuid4().hex}.h5"
        final_path = os.path.join(self.file_transport_dir, file_name)
        temporary_path = final_path + ".tmp"
        try:
            save_waveforms(temporary_path, analog, digital)
            os.replace(temporary_path, final_path)
            return self.awg.configure_waveforms_file(
                file_name,
                rate,
                trigger_type=trigger_type,
                n_runs=n_runs,
            )
        except Exception:
            self.logger.exception(f"Failed AWG file transport using {final_path}.")
            return False
        finally:
            self._remove_transport_path(temporary_path)
            if self.remove_transport_file:
                self._remove_transport_path(final_path)

    def _remove_transport_path(self, path: str):
        """Best-effort removal for a temporary or completed transport file."""

        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            self.logger.exception(f"Failed to remove AWG transport file {path}.")

    def get_meta_data(self) -> dict:
        return self._meta

    def waveform_msg(
        self,
        markers: T.Iterable[int],
        marker_freq: float,
        max_samples: int = 10_000_000,
        max_points: int = 500_000,
    ) -> AWGWaveform:
        """Build a bounded visualization message from the pending rendered waveform."""

        if self._pending is None or not self._uploaded:
            raise RuntimeError("Call upload() successfully before waveform_msg().")
        if max_samples <= 0:
            raise ValueError("max_samples must be positive.")
        if max_points < 2:
            raise ValueError("max_points must be at least 2.")
        marker_freq = self._positive_finite("marker frequency", marker_freq)

        res, _, amplitudes_mV, rate = self._pending
        preview_samples = min(res.actual_samples, max_samples)
        analog = {}
        reduced = preview_samples > max_points
        for channel, samples in res.analog.items():
            analog[channel] = _minmax_preview(samples[:preview_samples], max_points)

        digital = {
            name: K.rle_encode(track[:preview_samples]) for name, track in res.digital.items()
        }
        ratio = rate / marker_freq
        converted_markers = [int(round(marker * ratio)) for marker in markers]
        converted_markers = [
            marker for marker in converted_markers if 0 <= marker <= preview_samples
        ]
        published_points = max((len(values) for _, values in analog.values()), default=0)
        return AWGWaveform(
            analog=analog,
            digital=digital,
            rate=rate,
            amplitude_mV=dict(amplitudes_mV),
            rendered_samples=res.rendered_samples,
            actual_samples=res.actual_samples,
            preview_samples=preview_samples,
            markers=converted_markers,
            reduction="minmax" if reduced else "none",
            reduction_factor=(preview_samples / published_points if published_points else 1.0),
        )

    def fail_with(self, msg: str) -> bool:
        self.logger.error(msg)
        return False
