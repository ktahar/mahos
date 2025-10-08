#!/usr/bin/env python3

"""
Lockin Amplifier module.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations
import enum

from .visa_instrument import VisaInstrument
from ..msgs import param_msgs as P


class LI5640(VisaInstrument):
    """NF LI5640 Lockin Amplifier."""

    class RefSource(enum.Enum):
        EXT = 0
        INT = 1
        SIG = 2

    class RefEdge(enum.Enum):
        SIN_POS = 0
        TTL_POS = 1
        TTL_NEG = 2

    class InputSource(enum.Enum):
        A = 0
        A_B = 1
        I_6 = 2
        I_8 = 3

    class LineFilter(enum.Enum):
        THRU = 0
        LINE = 1
        LINEx2 = 2
        LINE_LINEx2 = 3

    class DynamicReserve(enum.Enum):
        HIGH = 0
        MEDIUM = 1
        LOW = 2

    class VoltageSensitivity(enum.Enum):
        s2nV = 0
        s5nV = 1
        s10nV = 2
        s20nV = 3
        s50nV = 4
        s100nV = 5
        s200nV = 6
        s500nV = 7
        s1uV = 8
        s2uV = 9
        s5uV = 10
        s10uV = 11
        s20uV = 12
        s50uV = 13
        s100uV = 14
        s200uV = 15
        s500uV = 16
        s1mV = 17
        s2mV = 18
        s5mV = 19
        s10mV = 20
        s20mV = 21
        s50mV = 22
        s100mV = 23
        s200mV = 24
        s500mV = 25
        s1V = 26

    VoltSensitivity_to_Float = {
        VoltageSensitivity.s2nV: 2e-9,
        VoltageSensitivity.s5nV: 5e-9,
        VoltageSensitivity.s10nV: 10e-9,
        VoltageSensitivity.s20nV: 20e-9,
        VoltageSensitivity.s50nV: 50e-9,
        VoltageSensitivity.s100nV: 100e-9,
        VoltageSensitivity.s200nV: 200e-9,
        VoltageSensitivity.s500nV: 500e-9,
        VoltageSensitivity.s1uV: 1e-6,
        VoltageSensitivity.s2uV: 2e-6,
        VoltageSensitivity.s5uV: 5e-6,
        VoltageSensitivity.s10uV: 10e-6,
        VoltageSensitivity.s20uV: 20e-6,
        VoltageSensitivity.s50uV: 50e-6,
        VoltageSensitivity.s100uV: 100e-6,
        VoltageSensitivity.s200uV: 200e-6,
        VoltageSensitivity.s500uV: 500e-6,
        VoltageSensitivity.s1mV: 1e-3,
        VoltageSensitivity.s2mV: 2e-3,
        VoltageSensitivity.s5mV: 5e-3,
        VoltageSensitivity.s10mV: 10e-3,
        VoltageSensitivity.s20mV: 20e-3,
        VoltageSensitivity.s50mV: 50e-3,
        VoltageSensitivity.s100mV: 100e-3,
        VoltageSensitivity.s200mV: 200e-3,
        VoltageSensitivity.s500mV: 500e-3,
        VoltageSensitivity.s1V: 1.0,
    }

    class CurrentSensitivity(enum.Enum):
        s5fA = 1
        s10fA = 2
        s20fA = 3
        s50fA = 4
        s100fA = 5
        s200fA = 6
        s500fA = 7
        s1pA = 8
        s2pA = 9
        s5pA = 10
        s10pA = 11
        s20pA = 12
        s50pA = 13
        s100pA = 14
        s200pA = 15
        s500pA = 16
        s1nA = 17
        s2nA = 18
        s5nA = 19
        s10nA = 20
        s20nA = 21
        s50nA = 22
        s100nA = 23
        s200nA = 24
        s500nA = 25
        s1uA = 26

    class TimeConstant(enum.Enum):
        c10us = 0
        c30us = 1
        c100us = 2
        c300us = 3
        c1ms = 4
        c3ms = 5
        c10ms = 6
        c30ms = 7
        c100ms = 8
        c300ms = 9
        c1s = 10
        c3s = 11
        c10s = 12
        c30s = 13
        c100s = 14
        c300s = 15
        c1ks = 16
        c3ks = 17
        c10ks = 18
        c30ks = 19

    class Data1(enum.Enum):
        X = 0
        R = 1
        NOISE = 2
        AUX_IN1 = 3

    class Data2(enum.Enum):
        Y = 0
        Theta = 1
        AUX_IN1 = 2
        AUX_IN2 = 3

    class DataNormalization(enum.Enum):
        OFF = 0
        dB = 1
        PERCENT = 2

    PARAM_NAMES = [
        "phase_offset",
        "freq",
        "amplitude",
        "harmonics",
        "ref_source",
        "ref_edge",
        "input_source",
        "coupling",
        "ground",
        "line_filter",
        "line_freq",
        "LPF_through",
        "dynamic_reserve",
        "volt_sensitivity",
        "current_sensitivity",
        "time_constant",
        "sync_filter",
        "slope",
        "data1",
        "data2",
        "data_normalization",
        "data_normalization_voltage",
        "data_normalization_current",
        "noise_smooth",
        "Xoffset_enable",
        "Yoffset_enable",
        "Xoffset",
        "Yoffset",
        "data1_expand",
        "data2_expand",
        "ratio_enable",
        "ratio_k",
        "lamp",
    ]

    def __init__(self, name, conf, prefix=None):
        if "write_termination" not in conf:
            conf["write_termination"] = "\n"
        if "read_termination" not in conf:
            conf["read_termination"] = "\n"
        VisaInstrument.__init__(self, name, conf, prefix=prefix)

        self._locks = {p: False for p in self.PARAM_NAMES}

    def get_phase_offset(self) -> float:
        """get current phase offset in degrees."""

        return float(self.inst.query("PHAS?"))

    def set_phase_offset(self, phase_deg: float) -> bool:
        """set phase offset in degrees."""

        while phase_deg > 180.0:
            phase_deg -= 360.0
        while phase_deg < -180.0:
            phase_deg += 360.0

        self.inst.write(f"PHAS {phase_deg:.4f}")
        return True

    def get_freq(self) -> float:
        """get frequency of `internal oscillator`.

        Note that this is not measured frequency of external reference.

        """

        return float(self.inst.query("FREQ?"))

    def set_freq(self, freq: float) -> bool:
        """set frequency of `internal oscillator`."""

        self.inst.write(f"FREQ {freq:.4f}")
        return True

    def get_amplitude(self) -> float:
        """get amplitude of internal oscillator."""

        #  drop range info (after comma)
        return float(self.inst.query("AMPL?").split(",")[0])

    def set_amplitude(self, ampl: float) -> bool:
        """set amplitude of internal oscillator."""

        if not (0.0 <= ampl <= 5.0):
            return self.fail_with(f"amplitude {ampl} is out of bounds")

        if ampl <= 50e-3:
            rng = 0
        elif ampl <= 0.5:
            rng = 1
        else:
            rng = 2

        self.inst.write(f"AMPL {ampl:.5f}, {rng}")
        return True

    def get_harmonics(self) -> int:
        """get current harmonics degree."""

        return int(self.inst.query("HARM?"))

    def set_harmonics(self, harmonics_deg: int) -> bool:
        """set harmonics degree."""

        if not (1 <= harmonics_deg <= 19999):
            return self.fail_with(f"harmonics out of range: {harmonics_deg}")

        self.inst.write(f"HARM {harmonics_deg:d}")
        return True

    def get_ref_source(self) -> RefSource:
        """get current reference source."""

        return self.RefSource(int(self.inst.query("RSRC?")))

    def set_ref_source(self, src: RefSource) -> bool:
        """set reference source."""

        self.inst.write(f"RSRC {src.value}")
        return True

    def get_ref_edge(self) -> RefEdge:
        """get current reference source rdge."""

        return self.RefEdge(int(self.inst.query("REDG?")))

    def set_ref_edge(self, edge: RefEdge) -> bool:
        """set reference source edge."""

        self.inst.write(f"REDG {edge.value}")
        return True

    def get_input_source(self) -> InputSource:
        """get current signal input source."""

        return self.InputSource(int(self.inst.query("ISRC?")))

    def set_input_source(self, src: InputSource) -> bool:
        """set signal input source."""

        self.inst.write(f"ISRC {src.value}")
        return True

    def get_coupling(self) -> bool:
        """get input coupling. True (False) if DC (AC) coupling."""

        return bool(int(self.inst.query("ICPL?")))

    def set_coupling(self, DC_coupling: bool) -> bool:
        """set input coupling."""

        self.inst.write(f"ICPL {bool(DC_coupling):d}")
        return True

    def get_ground(self) -> bool:
        """get input ground. True (False) if Grounded (Floating) input."""

        return bool(int(self.inst.query("IGND?")))

    def set_ground(self, ground: bool) -> bool:
        """set input ground."""

        self.inst.write(f"IGND {bool(ground):d}")
        return True

    def get_line_filter(self) -> LineFilter:
        """get line filter."""

        return self.LineFilter(int(self.inst.query("ILIN?")))

    def set_line_filter(self, filt: LineFilter) -> bool:
        """set line filter."""

        self.inst.write(f"ILIN {filt.value}")
        return True

    def get_line_freq(self) -> bool:
        """get line frequency. True (False) if 60 Hz (50 Hz)."""

        return bool(int(self.inst.query("IFRQ?")))

    def set_line_freq(self, is_60Hz: bool) -> bool:
        """set line frequency."""

        self.inst.write(f"IFRQ {bool(is_60Hz):d}")
        return True

    def get_LPF_through(self) -> bool:
        """get LPF pass through. True if LPF is passed through."""

        return bool(int(self.inst.query("ITHR?")))

    def set_LPF_through(self, pass_through: bool) -> bool:
        """set LPF pass through."""

        self.inst.write(f"ITHR {bool(pass_through):d}")
        return True

    def get_dynamic_reserve(self) -> DynamicReserve:
        """get dynamic reserve."""

        return self.DynamicReserve(int(self.inst.query("DRSV?")))

    def set_dynamic_reserve(self, reserve: DynamicReserve) -> bool:
        """set dynamic reserve."""

        self.inst.write(f"DRSV {reserve.value}")
        return True

    def get_volt_sensitivity(self) -> VoltageSensitivity:
        """get voltage sensitivity."""

        return self.VoltageSensitivity(int(self.inst.query("VSEN?")))

    def get_volt_sensitivity_float(self) -> float:
        return self.VoltSensitivity_to_Float[self.get_volt_sensitivity()]

    def set_volt_sensitivity(self, sens: VoltageSensitivity) -> bool:
        """set voltage sensitivity."""

        self.inst.write(f"VSEN {sens.value}")
        return True

    def get_current_sensitivity(self) -> CurrentSensitivity:
        """get current sensitivity."""

        return self.CurrentSensitivity(int(self.inst.query("ISEN?")))

    def set_current_sensitivity(self, sens: CurrentSensitivity) -> bool:
        """set current sensitivity."""

        self.inst.write(f"ISEN {sens.value}")
        return True

    def get_time_constant(self) -> TimeConstant:
        """get time constant."""

        return self.TimeConstant(int(self.inst.query("TCON?")))

    def set_time_constant(self, cons: TimeConstant) -> bool:
        """set time constant."""

        self.inst.write(f"TCON {cons.value}")
        return True

    def get_sync_filter(self) -> bool:
        """get sync filter. True if sync filter is enabled."""

        return bool(int(self.inst.query("SYNC?")))

    def set_sync_filter(self, enable: bool) -> bool:
        """set sync filter."""

        self.inst.write(f"SYNC {bool(enable):d}")
        return True

    def get_slope(self) -> int:
        """get slope in dB/oct."""

        i = int(self.inst.query("SLOP?"))
        if i not in (0, 1, 2, 3):
            self.logger.error(f"Unexpected response to SLOP?: {i}")
            return 0
        return {0: 6, 1: 12, 2: 18, 3: 24}[i]

    def set_slope(self, slope_dB_oct: int) -> bool:
        """set slope in dB/oct."""

        if slope_dB_oct not in (6, 12, 18, 24):
            return self.fail_with(f"Unrecongizable slope: {slope_dB_oct}")
        i = {6: 0, 12: 1, 18: 2, 24: 3}[slope_dB_oct]
        self.inst.write(f"SLOP {i}")
        return True

    def get_data1(self) -> Data1:
        """get data1."""

        return self.Data1(int(self.inst.query("DDEF? 1")))

    def set_data1(self, data: Data1) -> bool:
        """set data1."""

        self.inst.write(f"DDEF 1, {data.value}")
        return True

    def get_data2(self) -> Data2:
        """get data2."""

        return self.Data2(int(self.inst.query("DDEF? 2")))

    def set_data2(self, data: Data2) -> bool:
        """set data2."""

        self.inst.write(f"DDEF 2, {data.value}")
        return True

    def get_data_normalization(self) -> DataNormalization:
        """get data normalization enable."""

        return self.DataNormalization(int(self.inst.query("NORM?")))

    def set_data_normalization(self, norm: DataNormalization) -> bool:
        """set data normalization enable."""

        self.inst.write(f"NORM {norm.value}")
        return True

    def get_data_normalization_voltage(self) -> float:
        """get data normalization std value for voltage."""

        return float(self.inst.query("VSTD?"))

    def set_data_normalization_voltage(self, volt: float) -> bool:
        """set data normalization std value for voltage."""

        self.inst.write(f"VSTD {volt:.6e}")
        return True

    def get_data_normalization_current(self) -> float:
        """get data normalization std value for current."""

        return float(self.inst.query("ISTD?"))

    def set_data_normalization_current(self, current: float) -> bool:
        """set data normalization std value for current."""

        self.inst.write(f"ISTD {current:.6e}")
        return True

    def get_noise_smooth(self) -> int:
        """get noise measurement smoothing factor."""

        i = int(self.inst.query("NOIS?"))
        if i not in (0, 1, 2, 3):
            self.logger.error(f"Unexpected response to NOIS?: {i}")
            return 0
        return {0: 1, 1: 4, 2: 16, 3: 64}[i]

    def set_noise_smooth(self, fac: int) -> bool:
        """set noise measurement smoothing factor."""

        if fac not in (1, 4, 16, 64):
            return self.fail_with(f"Unrecongizable factor: {fac}")
        i = {1: 0, 4: 1, 16: 2, 64: 3}[fac]
        self.inst.write(f"NOIS {i}")
        return True

    def get_Xoffset_enable(self) -> bool:
        """get if offset for X is enabled."""

        return bool(int(self.inst.query("OFSO? 1")))

    def set_Xoffset_enable(self, enable: bool) -> bool:
        """set if offset for X is enabled."""

        self.inst.write(f"OFSO 1, {bool(enable):d}")
        return True

    def get_Yoffset_enable(self) -> bool:
        """get if offset for Y is enabled."""

        return bool(int(self.inst.query("OFSO? 2")))

    def set_Yoffset_enable(self, enable: bool) -> bool:
        """set if offset for Y is enabled."""

        self.inst.write(f"OFSO 2, {bool(enable):d}")
        return True

    def get_Xoffset(self) -> float:
        """get offset value for X."""

        return float(self.inst.query("OFFS? 1"))

    def set_Xoffset(self, offset_percent: bool) -> bool:
        """set offset value for X."""

        self.inst.write(f"OFFS 1, {offset_percent:.2f}")
        return True

    def get_Yoffset(self) -> float:
        """get offset value for Y."""

        return float(self.inst.query("OFFS? 2"))

    def set_Yoffset(self, offset_percent: bool) -> bool:
        """set offset value for Y."""

        self.inst.write(f"OFFS 2, {offset_percent:.2f}")
        return True

    def get_data1_expand(self) -> int:
        """get output expand factor for data1."""

        i = int(self.inst.query("OEXP? 1"))
        if i not in (0, 1, 2):
            self.logger.error(f"Unexpected response to OEXP? 1: {i}")
            return 0
        return {0: 1, 1: 10, 2: 100}[i]

    def set_data1_expand(self, fac: int) -> bool:
        """set output expand factor for data1."""

        if fac not in (1, 10, 100):
            return self.fail_with(f"Unrecongizable expand factor: {fac}")
        i = {1: 0, 10: 1, 100: 2}[fac]
        self.inst.write(f"OEXP 1, {i}")
        return True

    def get_data2_expand(self) -> int:
        """get output expand factor for data2."""

        i = int(self.inst.query("OEXP? 2"))
        if i not in (0, 1, 2):
            self.logger.error(f"Unexpected response to OEXP? 2: {i}")
            return 0
        return {0: 1, 1: 10, 2: 100}[i]

    def set_data2_expand(self, fac: int) -> bool:
        """set output expand factor for data2."""

        if fac not in (1, 10, 100):
            return self.fail_with(f"Unrecongizable expand factor: {fac}")
        i = {1: 0, 10: 1, 100: 2}[fac]
        self.inst.write(f"OEXP 2, {i}")
        return True

    def get_ratio_enable(self) -> bool:
        """get if ratio mode is enabled."""

        return bool(int(self.inst.query("RAT?")))

    def set_ratio_enable(self, enable: bool) -> bool:
        """set if ratio mode is enabled."""

        self.inst.write(f"RAT {bool(enable):d}")
        return True

    def get_ratio_k(self) -> float:
        """get k-factor in ratio mode."""

        return float(self.inst.query("KFAC?"))

    def set_ratio_k(self, fac: bool) -> bool:
        """set k-factor in ratio mode."""

        self.inst.write(f"KFAC {fac:.4f}")
        return True

    def get_lamp(self) -> bool:
        """get (physical) lamp is enabled."""

        return bool(int(self.inst.query("LAMP?")))

    def set_lamp(self, enable: bool) -> bool:
        """set (physical) lamp is enabled."""

        self.inst.write(f"LAMP {bool(enable):d}")
        return True

    # Auto settings

    def set_initialize(self) -> bool:
        """execute setting initialization."""

        self.inst.write("INIT")
        return True

    def set_auto(self) -> bool:
        """execute auto setting."""

        self.inst.write("ASET")
        return True

    def set_auto_phase_offset(self) -> bool:
        """set auto phase offset."""

        self.inst.write("APHS")
        return True

    def set_auto_sensitivity(self) -> bool:
        """execute auto sensitivity setting."""

        self.inst.write("ASEN")
        return True

    def set_auto_time_constant(self) -> bool:
        """execute auto time constant setting."""

        self.inst.write("ATIM")
        return True

    def set_auto_offset(self) -> bool:
        """execute auto offset setting."""

        self.inst.write("AOFS")
        return True

    def _check_and_set(self, key: str, value) -> bool:
        if key not in self.PARAM_NAMES:
            return self.fail_with(f"Unknown parameter: {key}")
        if not self._locks[key]:
            return getattr(self, "set_" + key)(value)

        # locked. check current value.
        v = getattr(self, "get_" + key)()
        if value != v:
            return self.fail_with(f"{key} is locked as {v}. cannot set to {value}")
        return True

    def lock_params(self, param_names: str | list[str] | tuple[str]) -> bool:
        if isinstance(param_names, str):
            param_names = [param_names]
        for n in param_names:
            if n not in self._locks:
                return self.fail_with(f"Unknown parameter: {n}")
            self._locks[n] = True

    def release_params(self, param_names: str | list[str] | tuple[str]) -> bool:
        if isinstance(param_names, str):
            param_names = [param_names]
        for n in param_names:
            if n not in self._locks:
                return self.fail_with(f"Unknown parameter: {n}")
            self._locks[n] = False

    # Standard API

    def get(self, key: str, args=None, label: str = ""):
        if key == "opc":
            return self.query_opc(delay=args)
        else:
            self.logger.error(f"unknown get() key: {key}")
            return None

    def set(self, key: str, value=None, label: str = "") -> bool:
        if key == "init":
            return self.set_initialize()
        elif key == "auto":
            return self.set_auto()
        elif key == "auto_sensitivity":
            return self.set_auto_sensitivity()
        elif key == "auto_time_constant":
            return self.set_auto_time_constant()
        elif key == "auto_phase_offset":
            return self.set_auto_phase_offset()
        elif key == "lock":
            return self.lock_params(value)
        elif key == "release":
            return self.release_params(value)
        elif key in self.PARAM_NAMES:
            return getattr(self, "set_" + key)(value)
        else:
            return self.fail_with("Unknown set() key.")

    def get_param_dict_labels(self) -> list[str]:
        return [""]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue]:
        d = P.ParamDict(
            phase_offset=P.FloatParam(
                self.get_phase_offset(), -180.0, 180.0, unit="deg", doc="phase offset in degrees"
            ),
            ref_source=P.EnumParam(self.RefSource, self.get_ref_source(), doc="reference source"),
            ref_edge=P.EnumParam(self.RefEdge, self.get_ref_edge(), doc="reference source edge"),
            input_source=P.EnumParam(
                self.InputSource, self.get_input_source(), doc="signal input source"
            ),
            coupling=P.BoolParam(
                self.get_coupling(), doc="signal input coupling (True-DC, False-AC)"
            ),
            ground=P.BoolParam(
                self.get_ground(), doc="signal input grounding (True-ground, False-float)"
            ),
            line_filter=P.EnumParam(self.LineFilter, self.get_line_filter(), doc="line filter"),
            line_freq=P.BoolParam(self.get_line_freq(), doc="line freq. (True-60, False-50 Hz)"),
            LPF_through=P.BoolParam(self.get_LPF_through(), doc="True to enable LPF pass-through"),
            dynamic_reserve=P.EnumParam(
                self.DynamicReserve, self.get_dynamic_reserve(), doc="dynamic reserve"
            ),
            volt_sensitivity=P.EnumParam(
                self.VoltageSensitivity, self.get_volt_sensitivity(), doc="voltage sensitivity"
            ),
            current_sensitivity=P.EnumParam(
                self.CurrentSensitivity, self.get_current_sensitivity(), doc="current sensitivity"
            ),
            time_constant=P.EnumParam(
                self.TimeConstant, self.get_time_constant(), doc="time constant"
            ),
            sync_filter=P.BoolParam(self.get_sync_filter(), doc="True to enable sync filter"),
            slope=P.IntChoiceParam(self.get_slope(), (6, 12, 18, 24), doc="Slope in dB/oct"),
            freq=P.FloatParam(
                self.get_freq(),
                5e-4,
                105e3,
                unit="Hz",
                SI_prefix=True,
                doc="internal oscillator frequency",
            ),
            amplitude=P.FloatParam(
                self.get_amplitude(), 0.0, 5.0, unit="V", doc="internal oscillator amplitude"
            ),
            harmonics=P.IntParam(self.get_harmonics(), 1, 19999, doc="harmonics degrees"),
            data1=P.EnumParam(self.Data1, self.get_data1(), doc="Data1 output type"),
            data2=P.EnumParam(self.Data2, self.get_data2(), doc="Data2 output type"),
            data_normalization=P.EnumParam(
                self.DataNormalization, self.get_data_normalization(), doc="Data normalization"
            ),
            data_normalization_voltage=P.FloatParam(
                self.get_data_normalization_voltage(),
                doc="Voltage standard for data normalization",
            ),
            data_normalization_current=P.FloatParam(
                self.get_data_normalization_current(),
                doc="Current standard for data normalization",
            ),
            noise_smooth=P.IntChoiceParam(
                self.get_noise_smooth(), (1, 4, 16, 64), doc="Noise measurement smoothing factor"
            ),
            Xoffset_enable=P.BoolParam(
                self.get_Xoffset_enable(), doc="True to enable offset for X"
            ),
            Yoffset_enable=P.BoolParam(
                self.get_Yoffset_enable(), doc="True to enable offset for Y"
            ),
            Xoffset=P.FloatParam(self.get_Xoffset(), doc="offset value for X"),
            Yoffset=P.FloatParam(self.get_Yoffset(), doc="offset value for Y"),
            data1_expand=P.IntChoiceParam(
                self.get_data1_expand(), (1, 10, 100), doc="Expand factor for data1"
            ),
            data2_expand=P.IntChoiceParam(
                self.get_data2_expand(), (1, 10, 100), doc="Expand factor for data2"
            ),
            ratio_enable=P.BoolParam(
                self.get_ratio_enable(), doc="True to enable ratio output mode"
            ),
            ratio_k=P.FloatParam(self.get_ratio_k(), doc="k-factor in ratio output mode"),
            lamp=P.BoolParam(self.get_lamp(), doc="True to enable physical lamp"),
        )
        return d

    def configure(self, params: dict, label: str = "") -> bool:
        for key, val in P.unwrap(params).items():
            if key in self.PARAM_NAMES:
                getattr(self, "set_" + key)(val)
            else:
                return self.fail_with(f"Unknown param: {key}")
        return True


class SR860(VisaInstrument):
    """SRS SR860 Lockin Amplifier."""

    class RefSource(enum.Enum):
        INT = 0
        EXT = 1
        DUAL = 2
        CHOP = 3

    class RefEdge(enum.Enum):
        SIN = 0
        TTL_POS = 1
        TTL_NEG = 2

    class InputRange(enum.Enum):
        r1V = 0
        r300mV = 1
        r100mV = 2
        r30mV = 3
        r10mV = 4

    class Sensitivity(enum.Enum):
        s1V = 0
        s500mV = 1
        s200mV = 2
        s100mV = 3
        s50mV = 4
        s20mV = 5
        s10mV = 6
        s5mV = 7
        s2mV = 8
        s1mV = 9
        s500uV = 10
        s200uV = 11
        s100uV = 12
        s50uV = 13
        s20uV = 14
        s10uV = 15
        s5uV = 16
        s2uV = 17
        s1uV = 18
        s500nV = 19
        s200nV = 20
        s100nV = 21
        s50nV = 22
        s20nV = 23
        s10nV = 24
        s5nV = 25
        s2nV = 26
        s1nV = 27

    Sensitivity_to_Float = {
        Sensitivity.s1nV: 1e-9,
        Sensitivity.s2nV: 2e-9,
        Sensitivity.s5nV: 5e-9,
        Sensitivity.s10nV: 10e-9,
        Sensitivity.s20nV: 20e-9,
        Sensitivity.s50nV: 50e-9,
        Sensitivity.s100nV: 100e-9,
        Sensitivity.s200nV: 200e-9,
        Sensitivity.s500nV: 500e-9,
        Sensitivity.s1uV: 1e-6,
        Sensitivity.s2uV: 2e-6,
        Sensitivity.s5uV: 5e-6,
        Sensitivity.s10uV: 10e-6,
        Sensitivity.s20uV: 20e-6,
        Sensitivity.s50uV: 50e-6,
        Sensitivity.s100uV: 100e-6,
        Sensitivity.s200uV: 200e-6,
        Sensitivity.s500uV: 500e-6,
        Sensitivity.s1mV: 1e-3,
        Sensitivity.s2mV: 2e-3,
        Sensitivity.s5mV: 5e-3,
        Sensitivity.s10mV: 10e-3,
        Sensitivity.s20mV: 20e-3,
        Sensitivity.s50mV: 50e-3,
        Sensitivity.s100mV: 100e-3,
        Sensitivity.s200mV: 200e-3,
        Sensitivity.s500mV: 500e-3,
        Sensitivity.s1V: 1.0,
    }

    class TimeConstant(enum.Enum):
        c1us = 0
        c3us = 1
        c10us = 2
        c30us = 3
        c100us = 4
        c300us = 5
        c1ms = 6
        c3ms = 7
        c10ms = 8
        c30ms = 9
        c100ms = 10
        c300ms = 11
        c1s = 12
        c3s = 13
        c10s = 14
        c30s = 15
        c100s = 16
        c300s = 17
        c1ks = 18
        c3ks = 19
        c10ks = 20
        c30ks = 21

    PARAM_NAMES = [
        "phase_offset",
        "freq",
        "amplitude",
        "harmonics",
        "ref_source",
        "ref_edge",
        "ref_imp",
        "input_mode",
        "input_source",
        "coupling",
        "ground",
        "input_range",
        "current_gain",
        "sensitivity",
        "time_constant",
        "sync_filter",
        "adv_filter",
        "slope",
        "ch1_mode",
        "ch2_mode",
        "Xoffset_enable",
        "Yoffset_enable",
        "Roffset_enable",
        "Xoffset",
        "Yoffset",
        "Roffset",
        "Xexpand",
        "Yexpand",
        "Rexpand",
        "Xratio_enable",
        "Yratio_enable",
        "Rratio_enable",
    ]

    def __init__(self, name, conf, prefix=None):
        if "write_termination" not in conf:
            conf["write_termination"] = "\n"
        if "read_termination" not in conf:
            conf["read_termination"] = "\n"
        VisaInstrument.__init__(self, name, conf, prefix=prefix)

        self._locks = {p: False for p in self.PARAM_NAMES}

    def get_phase_offset(self) -> float:
        """get current phase offset in degrees."""

        return float(self.inst.query("PHAS?"))

    def set_phase_offset(self, phase_deg: float) -> bool:
        """set phase offset in degrees."""

        while phase_deg > 180.0:
            phase_deg -= 360.0
        while phase_deg < -180.0:
            phase_deg += 360.0

        self.inst.write(f"PHAS {phase_deg:.4f}")
        return True

    def get_freq(self) -> float:
        """get frequency of `internal oscillator`.

        Note that this is not measured frequency of external reference.

        """

        return float(self.inst.query("FREQ?"))

    def set_freq(self, freq: float) -> bool:
        """set frequency of `internal oscillator`."""

        self.inst.write(f"FREQ {freq:.6f}")
        return True

    def get_amplitude(self) -> float:
        """get amplitude of internal oscillator."""

        #  drop range info (after comma)
        return float(self.inst.query("SLVL?").split(",")[0])

    def set_amplitude(self, ampl: float) -> bool:
        """set amplitude of internal oscillator."""

        if not (0.0 <= ampl <= 2.0):
            return self.fail_with(f"amplitude {ampl} is out of bounds")

        self.inst.write(f"SLVL {ampl:.4e}")
        return True

    def get_harmonics(self) -> int:
        """get current harmonics degree."""

        return int(self.inst.query("HARM?"))

    def set_harmonics(self, harmonics_deg: int) -> bool:
        """set harmonics degree."""

        if not (1 <= harmonics_deg <= 99):
            return self.fail_with(f"harmonics out of range: {harmonics_deg}")

        self.inst.write(f"HARM {harmonics_deg:d}")
        return True

    def get_ref_source(self) -> RefSource:
        """get current reference source."""

        return self.RefSource(int(self.inst.query("RSRC?")))

    def set_ref_source(self, src: RefSource) -> bool:
        """set reference source."""

        self.inst.write(f"RSRC {src.value}")
        return True

    def get_ref_edge(self) -> RefEdge:
        """get current reference source rdge."""

        return self.RefEdge(int(self.inst.query("RTRG?")))

    def set_ref_edge(self, edge: RefEdge) -> bool:
        """set reference source edge."""

        self.inst.write(f"RTRG {edge.value}")
        return True

    def get_ref_imp(self) -> bool:
        """get current reference source input impedance (True: 1M Ohm, False: 50 Ohm)."""

        return bool(self.inst.query("REFZ?"))

    def set_ref_imp(self, imp_1M: bool) -> bool:
        """set reference source imput impedance (True: 1M Ohm, False: 50 Ohm)."""

        self.inst.write(f"REFZ {bool(imp_1M):d}")
        return True

    def get_input_mode(self) -> bool:
        """get current signal input source (True: current, False: voltage)."""

        return bool(self.inst.query("IVMD?"))

    def set_input_mode(self, current: bool) -> bool:
        """set signal input source (True: current, False: voltage)."""

        self.inst.write(f"IVMD {bool(current):d}")
        return True

    def get_input_source(self) -> bool:
        """get current signal input source (True: A-B, False: A)."""

        return bool(self.inst.query("ISRC?"))

    def set_input_source(self, diff_input: bool) -> bool:
        """set signal input source (True: A-B, False: A)."""

        self.inst.write(f"ISRC {bool(diff_input):d}")
        return True

    def get_coupling(self) -> bool:
        """get input coupling (True: DC, False: AC)."""

        return bool(int(self.inst.query("ICPL?")))

    def set_coupling(self, DC_coupling: bool) -> bool:
        """set input coupling (True: DC, False: AC)."""

        self.inst.write(f"ICPL {bool(DC_coupling):d}")
        return True

    def get_ground(self) -> bool:
        """get input ground (True: Grounded, False: Floating)."""

        return bool(int(self.inst.query("IGND?")))

    def set_ground(self, ground: bool) -> bool:
        """set input ground (True: Grounded, False: Floating)."""

        self.inst.write(f"IGND {bool(ground):d}")
        return True

    def get_input_range(self) -> InputRange:
        """get input range."""

        return self.InputRange(int(self.inst.query("IRNG?")))

    def set_input_range(self, input_range: InputRange) -> bool:
        """set input range."""

        self.inst.write(f"IRNG {input_range.value}")
        return True

    def get_current_gain(self) -> bool:
        """get current gain (True: 100 M Ohm, False: 1 M Ohm)."""

        return bool(int(self.inst.query("ICUR?")))

    def set_current_gain(self, gain_100M: bool) -> bool:
        """set current gain (True: 100 M Ohm, False: 1 M Ohm)."""

        self.inst.write(f"ICUR {bool(gain_100M):d}")
        return True

    def get_sensitivity(self) -> Sensitivity:
        """get sensitivity."""

        return self.Sensitivity(int(self.inst.query("SCAL?")))

    def get_sensitivity_float(self) -> float:
        return self.Sensitivity_to_Float[self.get_sensitivity()]

    def set_sensitivity(self, sens: Sensitivity) -> bool:
        """set sensitivity."""

        self.inst.write(f"SCAL {sens.value}")
        return True

    def get_time_constant(self) -> TimeConstant:
        """get time constant."""

        return self.TimeConstant(int(self.inst.query("OFLT?")))

    def set_time_constant(self, cons: TimeConstant) -> bool:
        """set time constant."""

        self.inst.write(f"OFLT {cons.value}")
        return True

    def get_sync_filter(self) -> bool:
        """get sync filter. True if sync filter is enabled."""

        return bool(int(self.inst.query("SYNC?")))

    def set_sync_filter(self, enable: bool) -> bool:
        """set sync filter."""

        self.inst.write(f"SYNC {bool(enable):d}")
        return True

    def get_adv_filter(self) -> bool:
        """get advanced filter. True if adv filter is enabled."""

        return bool(int(self.inst.query("ADVFILT?")))

    def set_adv_filter(self, enable: bool) -> bool:
        """set adv filter."""

        self.inst.write(f"ADVFILT {bool(enable):d}")
        return True

    def get_slope(self) -> int:
        """get slope in dB/oct."""

        i = int(self.inst.query("OFSL?"))
        if i not in (0, 1, 2, 3):
            self.logger.error(f"Unexpected response to OFSL?: {i}")
            return 0
        return {0: 6, 1: 12, 2: 18, 3: 24}[i]

    def set_slope(self, slope_dB_oct: int) -> bool:
        """set slope in dB/oct."""

        if slope_dB_oct not in (6, 12, 18, 24):
            return self.fail_with(f"Unrecongizable slope: {slope_dB_oct}")
        i = {6: 0, 12: 1, 18: 2, 24: 3}[slope_dB_oct]
        self.inst.write(f"OFSL {i}")
        return True

    def get_ch1_mode(self) -> bool:
        """get ch1 output mode (True: R, False: X)."""

        return bool(self.inst.query("COUT? 0"))

    def set_ch1_mode(self, output_R: bool) -> bool:
        """set ch1 output mode (True: R, False: X)."""

        self.inst.write(f"COUT 0, {bool(output_R):d}")
        return True

    def get_ch2_mode(self) -> bool:
        """get ch2 output mode (True: Theta, False: Y)."""

        return bool(self.inst.query("COUT? 1"))

    def set_ch2_mode(self, output_Theta: bool) -> bool:
        """set ch2 output mode (True: Theta, False: Y)."""

        self.inst.write(f"COUT 1, {bool(output_Theta):d}")
        return True

    def get_Xoffset_enable(self) -> bool:
        """get if offset for X is enabled."""

        return bool(int(self.inst.query("COFA? 0")))

    def set_Xoffset_enable(self, enable: bool) -> bool:
        """set if offset for X is enabled."""

        self.inst.write(f"COFA 0, {bool(enable):d}")
        return True

    def get_Yoffset_enable(self) -> bool:
        """get if offset for Y is enabled."""

        return bool(int(self.inst.query("COFA? 1")))

    def set_Yoffset_enable(self, enable: bool) -> bool:
        """set if offset for Y is enabled."""

        self.inst.write(f"COFA 1, {bool(enable):d}")
        return True

    def get_Roffset_enable(self) -> bool:
        """get if offset for R is enabled."""

        return bool(int(self.inst.query("COFA? 2")))

    def set_Roffset_enable(self, enable: bool) -> bool:
        """set if offset for R is enabled."""

        self.inst.write(f"COFA 2, {bool(enable):d}")
        return True

    def get_Xoffset(self) -> float:
        """get offset value for X in percent."""

        return float(self.inst.query("COFP? 0"))

    def set_Xoffset(self, offset_percent: bool) -> bool:
        """set offset value for X."""

        self.inst.write(f"COFP 0, {offset_percent:.2f}")
        return True

    def get_Yoffset(self) -> float:
        """get offset value for Y in percent."""

        return float(self.inst.query("COFP? 1"))

    def set_Yoffset(self, offset_percent: bool) -> bool:
        """set offset value for Y."""

        self.inst.write(f"COFP 1, {offset_percent:.2f}")
        return True

    def get_Roffset(self) -> float:
        """get offset value for R in percent."""

        return float(self.inst.query("COFP? 2"))

    def set_Roffset(self, offset_percent: bool) -> bool:
        """set offset value for R."""

        self.inst.write(f"COFP 2, {offset_percent:.2f}")
        return True

    def get_Xexpand(self) -> int:
        """get output expand factor for X."""

        i = int(self.inst.query("CEXP? 0"))
        if i not in (0, 1, 2):
            self.logger.error(f"Unexpected response to CEXP? 0: {i}")
            return 0
        return {0: 1, 1: 10, 2: 100}[i]

    def set_Xexpand(self, fac: int) -> bool:
        """set output expand factor for X."""

        if fac not in (1, 10, 100):
            return self.fail_with(f"Unrecongizable expand factor: {fac}")
        i = {1: 0, 10: 1, 100: 2}[fac]
        self.inst.write(f"CEXP 0, {i}")
        return True

    def get_Yexpand(self) -> int:
        """get output expand factor for Y."""

        i = int(self.inst.query("CEXP? 1"))
        if i not in (0, 1, 2):
            self.logger.error(f"Unexpected response to CEXP? 1: {i}")
            return 0
        return {0: 1, 1: 10, 2: 100}[i]

    def set_Yexpand(self, fac: int) -> bool:
        """set output expand factor for Y."""

        if fac not in (1, 10, 100):
            return self.fail_with(f"Unrecongizable expand factor: {fac}")
        i = {1: 0, 10: 1, 100: 2}[fac]
        self.inst.write(f"CEXP 1, {i}")
        return True

    def get_Rexpand(self) -> int:
        """get output expand factor for R."""

        i = int(self.inst.query("CEXP? 2"))
        if i not in (0, 1, 2):
            self.logger.error(f"Unexpected response to CEXP? 2: {i}")
            return 0
        return {0: 1, 1: 10, 2: 100}[i]

    def set_Rexpand(self, fac: int) -> bool:
        """set output expand factor for R."""

        if fac not in (1, 10, 100):
            return self.fail_with(f"Unrecongizable expand factor: {fac}")
        i = {1: 0, 10: 1, 100: 2}[fac]
        self.inst.write(f"CEXP 2, {i}")
        return True

    def get_Xratio_enable(self) -> bool:
        """get if ratio mode for X is enabled."""

        return bool(int(self.inst.query("CRAT? 0")))

    def set_Xratio_enable(self, enable: bool) -> bool:
        """set if ratio mode for X is enabled."""

        self.inst.write(f"CRAT 0, {bool(enable):d}")
        return True

    def get_Yratio_enable(self) -> bool:
        """get if ratio mode for Y is enabled."""

        return bool(int(self.inst.query("CRAT? 1")))

    def set_Yratio_enable(self, enable: bool) -> bool:
        """set if ratio mode for Y is enabled."""

        self.inst.write(f"CRAT 1, {bool(enable):d}")
        return True

    def get_Rratio_enable(self) -> bool:
        """get if ratio mode for R is enabled."""

        return bool(int(self.inst.query("CRAT? 2")))

    def set_Rratio_enable(self, enable: bool) -> bool:
        """set if ratio mode for R is enabled."""

        self.inst.write(f"CRAT 2, {bool(enable):d}")
        return True

    # Auto settings

    def set_auto_phase_offset(self) -> bool:
        """set auto phase offset."""

        self.inst.write("APHS")
        return True

    def set_auto_range(self) -> bool:
        """execute auto range setting."""

        self.inst.write("ARNG")
        return True

    def set_auto_scale(self) -> bool:
        """execute auto scale setting."""

        self.inst.write("ASCL")
        return True

    def _check_and_set(self, key: str, value) -> bool:
        if key not in self.PARAM_NAMES:
            return self.fail_with(f"Unknown parameter: {key}")
        if not self._locks[key]:
            return getattr(self, "set_" + key)(value)

        # locked. check current value.
        v = getattr(self, "get_" + key)()
        if value != v:
            return self.fail_with(f"{key} is locked as {v}. cannot set to {value}")
        return True

    def lock_params(self, param_names: str | list[str] | tuple[str]) -> bool:
        if isinstance(param_names, str):
            param_names = [param_names]
        for n in param_names:
            if n not in self._locks:
                return self.fail_with(f"Unknown parameter: {n}")
            self._locks[n] = True

    def release_params(self, param_names: str | list[str] | tuple[str]) -> bool:
        if isinstance(param_names, str):
            param_names = [param_names]
        for n in param_names:
            if n not in self._locks:
                return self.fail_with(f"Unknown parameter: {n}")
            self._locks[n] = False

    # Standard API

    def get(self, key: str, args=None, label: str = ""):
        if key == "opc":
            return self.query_opc(delay=args)
        else:
            self.logger.error(f"unknown get() key: {key}")
            return None

    def set(self, key: str, value=None, label: str = "") -> bool:
        if key == "auto_phase_offset":
            return self.set_auto_phase_offset()
        elif key == "auto_range":
            return self.set_auto_range()
        elif key == "auto_scale":
            return self.set_auto_scale()
        elif key == "lock":
            return self.lock_params(value)
        elif key == "release":
            return self.release_params(value)
        elif key in self.PARAM_NAMES:
            return getattr(self, "set_" + key)(value)
        else:
            return self.fail_with("Unknown set() key.")

    def get_param_dict_labels(self) -> list[str]:
        return [""]

    def get_param_dict(self, label: str = "") -> P.ParamDict[str, P.PDValue]:
        d = P.ParamDict(
            phase_offset=P.FloatParam(
                self.get_phase_offset(), -180.0, 180.0, unit="deg", doc="phase offset in degrees"
            ),
            ref_source=P.EnumParam(self.RefSource, self.get_ref_source(), doc="ref source"),
            ref_edge=P.EnumParam(self.RefEdge, self.get_ref_edge(), doc="ref source edge"),
            ref_imp=P.BoolParam(self.get_ref_imp(), doc="ref input impedance (True:1M, False:50)"),
            input_mode=P.BoolParam(
                self.get_input_mode(), doc="signal input mode (True: current, False: voltage)"
            ),
            input_source=P.BoolParam(
                self.get_input_source(), doc="signal input source (True: A-B, False: A)"
            ),
            coupling=P.BoolParam(
                self.get_coupling(), doc="signal input coupling (True: DC, False: AC)"
            ),
            ground=P.BoolParam(
                self.get_ground(), doc="signal input grounding (True: ground, False: float)"
            ),
            input_range=P.EnumParam(self.InputRange, self.get_input_range(), doc="input range"),
            current_gain=P.BoolParam(
                self.get_current_gain(), doc="current gain (True: 100 M, False: 1 M)"
            ),
            sensitivity=P.EnumParam(self.Sensitivity, self.get_sensitivity(), doc="sensitivity"),
            time_constant=P.EnumParam(
                self.TimeConstant, self.get_time_constant(), doc="time constant"
            ),
            sync_filter=P.BoolParam(self.get_sync_filter(), doc="True to enable sync filter"),
            adv_filter=P.BoolParam(self.get_adv_filter(), doc="True to enable advanced filter"),
            slope=P.IntChoiceParam(self.get_slope(), (6, 12, 18, 24), doc="Slope in dB/oct"),
            freq=P.FloatParam(
                self.get_freq(),
                1e-3,
                500e3,
                unit="Hz",
                SI_prefix=True,
                doc="internal oscillator frequency",
            ),
            amplitude=P.FloatParam(
                self.get_amplitude(),
                0.0,
                2.0,
                unit="V",
                SI_prefix=True,
                doc="internal oscillator amplitude",
            ),
            harmonics=P.IntParam(self.get_harmonics(), 1, 99, doc="harmonics degrees"),
            ch1_mode=P.BoolParam(self.get_ch1_mode(), doc="CH1 output (True: R, False: X)"),
            ch2_mode=P.BoolParam(self.get_ch2_mode(), doc="CH2 output (True: Theta, False: Y)"),
            Xoffset_enable=P.BoolParam(
                self.get_Xoffset_enable(), doc="True to enable offset for X"
            ),
            Yoffset_enable=P.BoolParam(
                self.get_Yoffset_enable(), doc="True to enable offset for Y"
            ),
            Roffset_enable=P.BoolParam(
                self.get_Roffset_enable(), doc="True to enable offset for R"
            ),
            Xoffset=P.FloatParam(self.get_Xoffset(), doc="offset value for X"),
            Yoffset=P.FloatParam(self.get_Yoffset(), doc="offset value for Y"),
            Roffset=P.FloatParam(self.get_Roffset(), doc="offset value for R"),
            Xexpand=P.IntChoiceParam(self.get_Xexpand(), (1, 10, 100), doc="Expand factor for X"),
            Yexpand=P.IntChoiceParam(self.get_Yexpand(), (1, 10, 100), doc="Expand factor for Y"),
            Rexpand=P.IntChoiceParam(self.get_Rexpand(), (1, 10, 100), doc="Expand factor for R"),
            Xratio_enable=P.BoolParam(
                self.get_Xratio_enable(), doc="True to enable ratio output mode for X"
            ),
            Yratio_enable=P.BoolParam(
                self.get_Yratio_enable(), doc="True to enable ratio output mode for Y"
            ),
            Rratio_enable=P.BoolParam(
                self.get_Rratio_enable(), doc="True to enable ratio output mode for R"
            ),
        )
        return d

    def configure(self, params: dict, label: str = "") -> bool:
        for key, val in P.unwrap(params).items():
            if key in self.PARAM_NAMES:
                getattr(self, "set_" + key)(val)
            else:
                return self.fail_with(f"Unknown param: {key}")
        return True
