#!/usr/bin/env python3

"""
Tests for mahos_dq.meas.podmr.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import copy

import numpy as np
import pytest

from mahos_dq.meas.podmr import PODMRClient, PODMRIO
from mahos_dq.msgs.podmr_msgs import PODMRData, MWMode
from mahos.msgs.common_msgs import BinaryState
from mahos.inst.tdc_core import TDCBase
from mahos.msgs.inst.tdc_msgs import ChannelStatus
from mahos.msgs import param_msgs as P
from mahos_dq.meas.podmr_generator.generator import make_generators
from mahos_dq.meas.podmr_worker import Pulser, PODMRDataOperator
from util import get_some, expect_value, save_load_test
from fixtures import ctx, gconf, server, podmr, server_conf, podmr_conf
from podmr_patterns import patterns


def expect_podmr(cli: PODMRClient, num: int, poll_timeout_ms):
    def get():
        data: PODMRData = cli.get_data()
        if data is not None and data.data0 is not None:
            return len(data.data0)
        else:
            return None

    return expect_value(get, num, poll_timeout_ms, trials=500)


def pattern_equal(pattern0, pattern1):
    blocks0, freq0, laser_timing0 = pattern0
    blocks1, freq1, laser_timing1 = pattern1
    return blocks0 == blocks1 and abs(freq0 - freq1) < 1e-5 and laser_timing0 == laser_timing1


def pattern_equivalent(pattern0, pattern1):
    blocks0, freq0, laser_timing0 = pattern0
    blocks1, freq1, laser_timing1 = pattern1
    return (
        blocks0.equivalent(blocks1)
        and abs(freq0 - freq1) < 1e-5
        and laser_timing0 == laser_timing1
    )


class DummyTDC(TDCBase):
    def __init__(self, histogram: np.ndarray, sweeps: int = 5):
        super().__init__("dummy_tdc")
        self.histogram = np.array(histogram, dtype=np.float64)
        self.sweeps = sweeps
        self.get_data_calls = 0
        self.get_data_roi_calls = 0

    def get_data(self, ch: int) -> np.ndarray:
        self.get_data_calls += 1
        return self.histogram.copy()

    def get_data_roi(self, ch: int, roi: list[tuple[int, int]]) -> list[np.ndarray] | None:
        self.get_data_roi_calls += 1
        return super().get_data_roi(ch, roi)

    def get_status(self, ch: int) -> ChannelStatus:
        return ChannelStatus(True, 1.0, int(np.sum(self.histogram)), self.sweeps)


def _podmr_params_for_tdc_test(
    partial: int,
    enable_roi: bool,
    sigwidth: float,
    refwidth: float,
    refdelay: float,
    roi_margin: float,
) -> dict:
    margin = roi_margin if enable_roi else -1.0
    return {
        "num_pattern": 2,
        "partial": partial,
        "start": 1.0,
        "num": 2,
        "step": 1.0,
        "log": False,
        "invert_sweep": False,
        "pulse": {},
        "plot": {
            "plotmode": "data01",
            "taumode": "raw",
            "refmode": "ignore",
            "refaverage": False,
            "flipY": False,
            "sigdelay": 0.0,
            "sigwidth": sigwidth,
            "refdelay": refdelay,
            "refwidth": refwidth,
        },
        "instrument": {"tbin": 1.0, "trange": 100.0},
        "laser_width": 1.0,
        "roi_head": margin,
        "roi_tail": margin,
    }


def _run_update_with_histogram(
    histogram: np.ndarray,
    partial: int,
    enable_roi: bool,
    sigwidth: float,
    refwidth: float,
    refdelay: float,
    roi_margin: float,
):
    params = _podmr_params_for_tdc_test(
        partial=partial,
        enable_roi=enable_roi,
        sigwidth=sigwidth,
        refwidth=refwidth,
        refdelay=refdelay,
        roi_margin=roi_margin,
    )
    data = PODMRData(params, "rabi")
    n_laser = len(data.xdata) * data.num_pattern() if partial < 0 else len(data.xdata)
    data.laser_timing = np.arange(n_laser, dtype=np.float64) * 10.0 + 5.0
    data.start()

    tdc = DummyTDC(histogram, sweeps=5)
    pulser = Pulser.__new__(Pulser)
    pulser.data = data
    pulser.tdc = tdc
    pulser.op = PODMRDataOperator()
    pulser._tdc_ch0 = 0
    pulser._tdc_ch1 = 1
    pulser._tdc_ch1_enable = False
    pulser._resume_raw_data = None
    pulser._resume_tdc_status = None

    assert pulser.update()
    return data, tdc


def _make_pulse_histogram(
    length: int, edge_bins: np.ndarray, width: float, amplitude: float, noise_sigma: float
) -> np.ndarray:
    x = np.arange(length, dtype=np.float64)
    y = np.full(length, 5.0, dtype=np.float64)
    for edge in edge_bins:
        y += amplitude / (1.0 + np.exp(-(x - edge) / 1.3))
        y -= amplitude / (1.0 + np.exp(-(x - (edge + width)) / 1.3))
    rng = np.random.default_rng(7)
    y += rng.normal(0.0, noise_sigma, size=length)
    return np.clip(y, 0.0, None)


def _find_laser_timing_case(enable_roi: bool, monotonic: bool = True):
    tbin = 1.0e-9
    scope = (20.0 * tbin, 20.0 * tbin)
    nominal_bins = np.array([60, 150, 240, 330, 420], dtype=np.float64)
    drift_bins = np.array([0.0, 0.4, 0.9, 1.4, 2.1], dtype=np.float64)
    edge_bins = nominal_bins + drift_bins

    params = _podmr_params_for_tdc_test(
        partial=0,
        enable_roi=enable_roi,
        sigwidth=2.0e-9,
        refwidth=2.0e-9,
        refdelay=1.0e-9,
        roi_margin=40.0e-9,
    )
    params["instrument"]["tbin"] = tbin
    params["instrument"]["trange"] = 600.0 * tbin
    params["laser_width"] = 16.0e-9

    data = PODMRData(params, "rabi")
    data.laser_timing = nominal_bins * tbin

    hist = _make_pulse_histogram(560, edge_bins, width=16.0, amplitude=120.0, noise_sigma=1.0)
    if enable_roi:
        rois = data.get_rois()
        data.raw_data = np.array([hist[start:stop] for start, stop in rois], dtype=np.float64)
    else:
        data.raw_data = hist

    op = PODMRDataOperator()
    assert op.find_laser_timing(data, scope, smooth_window=5, monotonic=monotonic)

    expected = (drift_bins - drift_bins[0]) * tbin
    np.testing.assert_allclose(data.laser_timing_offset, expected, atol=1.0 * tbin)


def test_find_laser_timing_noroi():
    _find_laser_timing_case(enable_roi=False)


def test_find_laser_timing_roi():
    _find_laser_timing_case(enable_roi=True)


def test_find_laser_timing_noroi_no_monotonic():
    _find_laser_timing_case(enable_roi=False, monotonic=False)


@pytest.mark.parametrize("partial", (-1, 0), ids=("complementary", "partial"))
@pytest.mark.parametrize(
    ("sigwidth", "refwidth", "refdelay", "roi_margin"),
    (
        (0.0, 0.0, 1.0, 1.0),
        (2.0, 2.0, 1.0, 5.0),
    ),
    ids=("single_bin", "multi_bin"),
)
def test_podmr_roi_noroi_analysis_equivalence(partial, sigwidth, refwidth, refdelay, roi_margin):
    histogram = np.arange(50, dtype=np.float64)
    data_roi, tdc_roi = _run_update_with_histogram(
        histogram,
        partial=partial,
        enable_roi=True,
        sigwidth=sigwidth,
        refwidth=refwidth,
        refdelay=refdelay,
        roi_margin=roi_margin,
    )
    data_noroi, tdc_noroi = _run_update_with_histogram(
        histogram,
        partial=partial,
        enable_roi=False,
        sigwidth=sigwidth,
        refwidth=refwidth,
        refdelay=refdelay,
        roi_margin=roi_margin,
    )

    assert tdc_roi.get_data_roi_calls > 0
    assert tdc_roi.get_data_calls == tdc_roi.get_data_roi_calls
    assert tdc_noroi.get_data_calls > 0
    assert tdc_noroi.get_data_roi_calls == 0
    assert data_roi.tdc_status.sweeps == data_noroi.tdc_status.sweeps

    for i in range(data_roi.num_pattern()):
        d_roi = data_roi.data(i)
        d_noroi = data_noroi.data(i)
        r_roi = data_roi.data_ref(i)
        r_noroi = data_noroi.data_ref(i)
        if d_roi is None or d_noroi is None:
            assert d_roi is None and d_noroi is None
        else:
            np.testing.assert_allclose(d_roi, d_noroi)
        if r_roi is None or r_noroi is None:
            assert r_roi is None and r_noroi is None
        else:
            np.testing.assert_allclose(r_roi, r_noroi)

    y_roi = data_roi.get_ydata()
    y_noroi = data_noroi.get_ydata()
    for roi_part, noroi_part in zip(y_roi, y_noroi):
        if roi_part is None or noroi_part is None:
            assert roi_part is None and noroi_part is None
        else:
            np.testing.assert_allclose(roi_part, noroi_part)


def test_podmr_pattern_divide():
    params = {
        "base_width": 320e-9,
        "laser_delay": 45e-9,
        "laser_width": 5e-6,
        "mw_delay": 1e-6,
        "trigger_width": 20e-9,
        "init_delay": 0.0,
        "final_delay": 5e-6,
        "partial": -1,
        "nomw": False,
        "start": 100e-9,
        "num": 2,
        "step": 100e-9,
        "divide_block": False,
    }
    params["pulse"] = {
        "90pulse": 10e-9,
        "180pulse": 20e-9,
        "tauconst": 150e-9,
        "tau2const": 160e-9,
        "Nconst": 2,
        "N2const": 2,
        "N3const": 2,
        "ddphase": "Y:X:Y:X,Y:X:Y:iX",
        "supersample": 1,
        "iq_delay": 16e-9,
        "readY": False,
        "invertY": False,
        "reinitX": False,
        "flip_head": True,
    }
    params_divide = params.copy()
    params_divide["divide_block"] = True

    tau = np.array([100e-6, 200e-6])
    generators = make_generators()
    # for meth in ("rabi", "fid", "spinecho", "trse", "cp", "cpmg", "xy4", "xy8", "xy16", "180train",
    #              "se90sweep", "spinlock", "xy8cl", "xy8cl1flip", "ddgate"):
    for meth in ("rabi", "spinecho"):
        ptn = generators[meth].generate(tau, params)
        ptn_divide = generators[meth].generate(tau, params_divide)
        assert pattern_equivalent(ptn, ptn_divide)


def test_podmr_mw_offset():
    tau = np.array([100e-9, 200e-9])
    params = {
        "base_width": 320e-9,
        "laser_delay": 45e-9,
        "laser_width": 5e-6,
        "mw_delay": 1e-6,
        "trigger_width": 20e-9,
        "init_delay": 0.0,
        "final_delay": 5e-6,
        "partial": -1,
        "nomw": False,
        "start": 100e-9,
        "num": 2,
        "step": 100e-9,
        "divide_block": False,
    }
    params["pulse"] = {
        "90pulse": 10e-9,
        "180pulse": 20e-9,
        "tauconst": 150e-9,
        "tau2const": 160e-9,
        "Nconst": 2,
        "N2const": 2,
        "N3const": 2,
        "ddphase": "Y:X:Y:X,Y:X:Y:iX",
        "supersample": 1,
        "iq_delay": 16e-9,
        "readY": False,
        "invertY": False,
        "reinitX": False,
        "flip_head": True,
    }

    generators = make_generators()

    ptn_ref = generators["rabi"].generate(tau, params)
    params_zero = copy.deepcopy(params)
    params_zero["mw_offset"] = 0.0
    ptn_zero = generators["rabi"].generate(tau, params_zero)
    assert pattern_equal(ptn_ref, ptn_zero)

    blocks_ref, freq, laser_timing = ptn_ref
    total_length = blocks_ref.total_length()
    offset_ticks = 37

    params_offset = copy.deepcopy(params)
    params_offset["mw_offset"] = offset_ticks / freq
    blocks_ofs, freq_ofs, laser_timing_ofs = generators["rabi"].generate(tau, params_offset)
    assert abs(freq_ofs - freq) < 1e-5
    assert laser_timing_ofs == laser_timing
    assert blocks_ofs.total_length() == total_length

    channels_ref, patterns_ref = blocks_ref.decode_all()
    channels_ofs, patterns_ofs = blocks_ofs.decode_all()
    assert channels_ofs == channels_ref
    for ch, p_ref, p_ofs in zip(channels_ref, patterns_ref, patterns_ofs):
        if isinstance(ch, str) and ch.startswith("mw"):
            assert np.array_equal(p_ofs, np.roll(p_ref, offset_ticks))
        else:
            assert np.array_equal(p_ofs, p_ref)

    params_wrap = copy.deepcopy(params)
    params_wrap["mw_offset"] = (total_length + offset_ticks) / freq
    blocks_wrap, freq_wrap, laser_timing_wrap = generators["rabi"].generate(tau, params_wrap)
    assert abs(freq_wrap - freq) < 1e-5
    assert laser_timing_wrap == laser_timing
    assert blocks_wrap.equivalent(blocks_ofs)

    # negative offset: advance mw patterns
    params_adv = copy.deepcopy(params)
    params_adv["mw_offset"] = -offset_ticks / freq
    blocks_adv, freq_adv, laser_timing_adv = generators["rabi"].generate(tau, params_adv)
    assert abs(freq_adv - freq) < 1e-5
    assert laser_timing_adv == laser_timing
    assert blocks_adv.total_length() == total_length

    channels_adv, patterns_adv = blocks_adv.decode_all()
    assert channels_adv == channels_ref
    for ch, p_ref, p_adv in zip(channels_ref, patterns_ref, patterns_adv):
        if isinstance(ch, str) and ch.startswith("mw"):
            assert np.array_equal(p_adv, np.roll(p_ref, -offset_ticks))
        else:
            assert np.array_equal(p_adv, p_ref)


def test_podmr_patterns():
    tau = np.array([100e-9, 200e-9])
    Ns = [1, 2]

    params = {
        "base_width": 320e-9,
        "laser_delay": 45e-9,
        "laser_width": 5e-6,
        "mw_delay": 1e-6,
        "trigger_width": 20e-9,
        "init_delay": 0.0,
        "final_delay": 5e-6,
        "partial": -1,
        "nomw": False,
        "start": 100e-9,
        "num": 2,
        "step": 100e-9,
        "divide_block": False,
    }
    params["pulse"] = {
        "90pulse": 10e-9,
        "180pulse": 20e-9,
        "tauconst": 150e-9,
        "tau2const": 160e-9,
        "Nconst": 2,
        "N2const": 2,
        "N3const": 2,
        "ddphase": "Y:X:Y:X,Y:X:Y:iX",
        "supersample": 1,
        "iq_delay": 16e-9,
        "readY": False,
        "invertY": False,
        "reinitX": False,
        "flip_head": True,
    }

    generators = make_generators()

    # normal (sweep tau)
    for meth in (
        "rabi",
        "t1",
        "fid",
        "spinecho",
        "trse",
        "cp",
        "cpmg",
        "xy4",
        "xy8",
        "xy16",
        "180train",
        "se90sweep",
        "spinlock",
        "xy8cl",
        "xy8cl1flip",
        "ddgate",
    ):
        ptn = generators[meth].generate(tau, params)
        assert pattern_equal(ptn, patterns[meth])

    for meth in ("xy8", "xy16"):
        ps = copy.copy(params)
        ps["pulse"]["supersample"] = 2
        data = PODMRData(ps, meth)
        ptn = generators[meth].generate(data.xdata, ps)
        assert pattern_equal(ptn, patterns[meth + "ss"])

    # sweepN
    for meth in ("cpN", "cpmgN", "xy4N", "xy8N", "xy16N", "xy8clNflip", "ddgateN"):
        ptn = generators[meth].generate(Ns, params)
        assert pattern_equal(ptn, patterns[meth])

    # partial
    for partial in (0, 1):
        ps = copy.copy(params)
        ps["partial"] = partial
        ptn = generators["rabi"].generate(tau, ps)
        assert pattern_equal(ptn, patterns[f"rabi-p{partial:d}"])


def test_podmr(server, podmr, server_conf, podmr_conf):
    poll_timeout_ms = podmr_conf["poll_timeout_ms"]
    expected_mw_modes = [MWMode.parse(m).name for m in podmr_conf["pulser"]["mw_modes"]]

    podmr.wait()

    assert get_some(podmr.get_status, poll_timeout_ms).state == BinaryState.IDLE
    for m in (
        "rabi",
        "t1",
        "fid",
        "spinecho",
        "trse",
        "cp",
        "cpmg",
        "xy4",
        "xy8",
        "xy16",
        "180train",
        "se90sweep",
        "spinlock",
        "xy8cl",
        "xy8cl1flip",
        "ddgate",
    ):
        print(m)
        params = podmr.get_param_dict(m)
        params["num"].set(2)  # small num for quick test
        assert podmr.validate(params, m)
        assert podmr.start(params, m)
        assert expect_podmr(podmr, params["num"].value(), poll_timeout_ms)
        data = get_some(podmr.get_data, poll_timeout_ms)
        assert data.params["instrument"]["mw_modes"] == expected_mw_modes
        assert podmr.stop()
        if m == "rabi":
            save_load_test(PODMRIO(), data)

    for m in ("cpN", "cpmgN", "xy4N", "xy8N", "xy16N", "xy8clNflip", "ddgateN"):
        params = podmr.get_param_dict(m)
        params["Nnum"].set(3)  # small num for quick test
        assert podmr.validate(params, m)
        assert podmr.start(params, m)
        assert expect_podmr(podmr, params["Nnum"].value(), poll_timeout_ms)
        assert podmr.stop()


def test_podmr_plotmode_options(server, podmr, podmr_conf):
    podmr.wait()
    labels = podmr.get_param_dict_labels()
    assert "dq2ramsey" in labels
    assert "dq4ramsey" in labels

    p2 = podmr.get_param_dict("dq2ramsey")
    p4 = podmr.get_param_dict("dq4ramsey")
    m2 = p2["plot"]["plotmode"].options()
    m4 = p4["plot"]["plotmode"].options()

    assert "normalize" in m2
    assert "ref" in m2
    assert "data23" not in m2

    assert "normalize" not in m4
    assert "ref" not in m4
    assert "data23" in m4
    assert "diff01-23" in m4
    assert "ref01" in m4
    assert "ref23" in m4

    raw4 = P.unwrap(p4)
    raw4["plot"]["plotmode"] = "normalize"
    assert not podmr.validate(raw4, "dq4ramsey")
