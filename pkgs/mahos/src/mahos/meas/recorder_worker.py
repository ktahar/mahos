#!/usr/bin/env python3

"""
Worker for Recorder.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations
import time
from dataclasses import dataclass

from mahos.util.timer import IntervalTimer
from mahos.msgs.recorder_msgs import RecorderData
from mahos.inst.interface import InstrumentInterface
from mahos.msgs import param_msgs as P
from mahos.meas.common_worker import Worker


@dataclass(frozen=True)
class _ChannelConf:
    inst: str
    label: str = ""
    key: str = "data"
    unit: str | None = None


class Collector(Worker):
    def __init__(self, cli, logger, conf: dict, mode: dict | None = None):
        Worker.__init__(self, cli, logger)

        self.interval_sec = conf.get("interval_sec", 1.0)
        self.insts = self.cli.insts()
        self.add_instruments([InstrumentInterface(self.cli, inst) for inst in self.insts])

        self._label = ""
        self.mode_dicts = self._normalize_mode_dicts(mode)

        self.data = RecorderData()
        self.timer = None

    def _normalize_mode_dicts(self, mode: dict | None) -> dict[str, dict[str, _ChannelConf]]:
        if mode is None:
            return {"all": {inst: _ChannelConf(inst=inst) for inst in self.insts}}

        mode_dicts: dict[str, dict[str, _ChannelConf]] = {}
        for mode_label, channels in mode.items():
            if not isinstance(channels, dict):
                raise TypeError(
                    f"Mode {mode_label} must be dict[str, tuple[str, str] | dict], got {channels}."
                )
            mode_dicts[mode_label] = {}
            for channel, conf in channels.items():
                mode_dicts[mode_label][channel] = self._normalize_channel_conf(channel, conf)

        return mode_dicts

    def _normalize_channel_conf(self, channel: str, conf) -> _ChannelConf:
        if isinstance(conf, (tuple, list)):
            if len(conf) != 2:
                raise ValueError(
                    f"Channel {channel} in Recorder mode must have 2 items: [inst, label]."
                )
            inst, label = conf
            if not isinstance(inst, str) or not isinstance(label, str):
                raise TypeError(
                    f"Channel {channel} in Recorder mode must have str inst and label."
                )
            return _ChannelConf(inst=inst, label=label)

        if isinstance(conf, dict):
            if "inst" not in conf:
                raise KeyError(f"Channel {channel} in Recorder mode dict must contain 'inst'.")

            inst = conf["inst"]
            label = conf.get("label", "")
            key = conf.get("key", "data")
            unit = conf.get("unit")

            if not isinstance(inst, str):
                raise TypeError(f"Channel {channel}: 'inst' must be str.")
            if not isinstance(label, str):
                raise TypeError(f"Channel {channel}: 'label' must be str.")
            if not isinstance(key, str):
                raise TypeError(f"Channel {channel}: 'key' must be str.")
            if unit is not None and not isinstance(unit, str):
                raise TypeError(f"Channel {channel}: 'unit' must be str when specified.")

            return _ChannelConf(inst=inst, label=label, key=key, unit=unit)

        raise TypeError(
            f"Invalid channel conf for {channel}: {conf}. "
            "Use [inst, label] or {inst=..., label=..., key=..., unit=...}."
        )

    def get_param_dict_labels(self) -> list[str]:
        return list(self.mode_dicts.keys())

    def get_param_dict(self, label: str) -> P.ParamDict[str, P.PDValue] | None:
        if label not in self.mode_dicts:
            self.logger.error(f"Invalid label {label}")
            return None

        pd = P.ParamDict()
        pd["max_len"] = P.IntParam(1000, 1, 100_000_000, doc="maximum data length")
        pd["interval"] = P.FloatParam(
            self.interval_sec, 0.01, 100.0, unit="s", doc="polling interval"
        )
        pd["lock"] = P.BoolParam(True, doc="acquire the locks of instruments")
        for channel, conf in self.mode_dicts[label].items():
            d = self.cli.get_param_dict(conf.inst, conf.label)
            if d is None:
                self.logger.error(
                    f"Failed to generate param dict for {channel} ({conf.inst}, {conf.label})."
                )
                return None
            pd[channel] = d
        return pd

    def start(
        self, params: P.ParamDict[str, P.PDValue] | dict[str, P.RawPDValue], label: str = ""
    ) -> bool:
        if params is not None:
            params = P.unwrap(params)

        if label not in self.mode_dicts:
            self.logger.error(f"Invalid mode label {label}")
            return False

        self._label = label
        used_insts = {conf.inst for conf in self.mode_dicts[label].values()}

        if params.get("lock", True):
            for inst in used_insts:
                if not self.cli.lock(inst):
                    return self.fail_with_release(f"Failed to lock instrument {inst}")
        else:
            self.logger.info("Skipping to acquire locks of instruments")

        units = []
        for channel, conf in self.mode_dicts[label].items():
            if channel not in params:
                return self.fail_with_release(
                    f"Channel {channel} ({conf.inst}, {conf.label}) is not contained in params."
                )
            if not self.cli.configure(conf.inst, params[channel], conf.label):
                return self.fail_with_release(
                    f"Failed to configure channel {channel} ({conf.inst}, {conf.label})"
                )
            unit = conf.unit
            if unit is None:
                unit = self.cli.get(conf.inst, "unit", label=conf.label) or ""
            units.append((channel, unit))

        for channel, conf in self.mode_dicts[label].items():
            if not self.cli.start(conf.inst, label=conf.label):
                return self.fail_with_release(
                    f"Failed to start channel {channel} ({conf.inst}, {conf.label})"
                )

        self.timer = IntervalTimer(params.get("interval", self.interval_sec))

        unit_map = dict(units)
        params["channels"] = {}
        for channel, conf in self.mode_dicts[label].items():
            params["channels"][channel] = {
                "inst": conf.inst,
                "label": conf.label,
                "key": conf.key,
                "unit": unit_map[channel],
            }

        self.data = RecorderData(params, label)
        self.data.set_units(units)
        self.data.start()
        self.logger.info("Started collector.")

        return True

    def reset(self, label) -> bool:
        if self.data.running:
            self.logger.error("reset() is called while running.")
            return False

        if label not in self.mode_dicts:
            self.logger.error(f"Invalid mode label {label}")
            return False

        success = True
        for channel, conf in self.mode_dicts[label].items():
            if not self.cli.reset(conf.inst, label=conf.label):
                self.logger.error(f"Failed to reset channel {channel} ({conf.inst}, {conf.label})")
                success = False
        return success

    def work(self) -> bool:
        # TODO: treatment of time stamp is quite rough now

        if not self.data.running:
            return False

        if not self.timer.check():
            return False

        t_start = time.time()
        data = {}
        for channel, conf in self.mode_dicts[self._label].items():
            d = self.cli.get(conf.inst, conf.key, label=conf.label)
            if d is None:
                return False
            data[channel] = d
        t_finish = time.time()
        t = (t_start + t_finish) / 2.0
        self.data.append(t, data)
        return True

    def stop(self) -> bool:
        # avoid double-stop (abort status can be broken)
        if not self.data.running:
            return False

        success = True
        for channel, conf in self.mode_dicts[self._label].items():
            success &= self.cli.stop(conf.inst, label=conf.label) and self.cli.release(conf.inst)
        self.timer = None
        self.data.finalize()

        if success:
            self.logger.info("Stopped collector.")
        else:
            self.logger.error("Error stopping collector.")
        return success

    def data_msg(self) -> RecorderData:
        return self.data
