#!/usr/bin/env python3

"""
Tests for mahos_dq.msgs.podmr_msgs.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np
import pytest

from mahos_dq.msgs.podmr_msgs import PODMRData


def make_data(
    num_pattern: int,
    plotmode: str,
    *,
    refmode: str = "ignore",
    refaverage: bool = False,
    flipY: bool = False,
    partial: int = -1,
) -> PODMRData:
    params = {
        "num_pattern": num_pattern,
        "partial": partial,
        "start": 1.0e-9,
        "num": 2,
        "step": 1.0e-9,
        "log": False,
        "invert_sweep": False,
        "pulse": {},
        "plot": {
            "plotmode": plotmode,
            "taumode": "raw",
            "refmode": refmode,
            "refaverage": refaverage,
            "flipY": flipY,
        },
        "instrument": {"tbin": 1.0e-9, "trange": 1.0e-6},
    }
    return PODMRData(params, "rabi")


def set_pattern_data(data: PODMRData, signals: list[np.ndarray], refs: list[np.ndarray]):
    for i, (s, r) in enumerate(zip(signals, refs)):
        data.set_data(i, s)
        data.set_data_ref(i, r)


def test_complementary_n2_dispatch_and_diff_flip():
    data = make_data(2, "diff")
    s0 = np.array([5.0, 7.0])
    s1 = np.array([1.0, 2.0])
    r0 = np.array([10.0, 10.0])
    r1 = np.array([10.0, 10.0])
    set_pattern_data(data, [s0, s1], [r0, r1])

    y, y1 = data.get_ydata()
    assert y1 is None
    assert np.array_equal(y, s0 - s1)

    data.params["plot"]["flipY"] = True
    y, y1 = data.get_ydata()
    assert y1 is None
    assert np.array_equal(y, s1 - s0)


def test_complementary_n4_modes():
    s0 = np.array([10.0, 20.0])
    s1 = np.array([1.0, 2.0])
    s2 = np.array([3.0, 4.0])
    s3 = np.array([5.0, 6.0])
    r0 = np.array([100.0, 200.0])
    r1 = np.array([10.0, 20.0])
    r2 = np.array([30.0, 40.0])
    r3 = np.array([50.0, 60.0])

    data = make_data(4, "data23")
    set_pattern_data(data, [s0, s1, s2, s3], [r0, r1, r2, r3])

    y0, y1 = data.get_ydata()
    assert np.array_equal(y0, s2)
    assert np.array_equal(y1, s3)

    data.params["plot"]["plotmode"] = "data2"
    y0, y1 = data.get_ydata()
    assert np.array_equal(y0, s2)
    assert y1 is None

    data.params["plot"]["plotmode"] = "diff"
    data.params["plot"]["flipY"] = False
    y0, y1 = data.get_ydata()
    assert y1 is None
    assert np.array_equal(y0, s0 - s1 + s2 - s3)

    data.params["plot"]["flipY"] = True
    y0, y1 = data.get_ydata()
    assert y1 is None
    assert np.array_equal(y0, -s0 + s1 - s2 + s3)

    data.params["plot"]["plotmode"] = "average"
    y0, y1 = data.get_ydata()
    assert y1 is None
    assert np.array_equal(y0, (s0 + s1 + s2 + s3) / 4)


def test_complementary_n4_diff01_23_and_refaverage():
    s0 = np.array([10.0, 20.0])
    s1 = np.array([1.0, 2.0])
    s2 = np.array([3.0, 4.0])
    s3 = np.array([5.0, 6.0])
    r0 = np.array([100.0, 200.0])
    r1 = np.array([10.0, 20.0])
    r2 = np.array([30.0, 40.0])
    r3 = np.array([50.0, 60.0])

    data = make_data(4, "diff01-23")
    set_pattern_data(data, [s0, s1, s2, s3], [r0, r1, r2, r3])

    y0, y1 = data.get_ydata()
    assert np.array_equal(y0, s0 - s1)
    assert np.array_equal(y1, s2 - s3)

    data.params["plot"]["flipY"] = True
    y0, y1 = data.get_ydata()
    assert np.array_equal(y0, s1 - s0)
    assert np.array_equal(y1, s3 - s2)

    data.params["plot"]["plotmode"] = "data0"
    data.params["plot"]["refmode"] = "subtract"
    data.params["plot"]["refaverage"] = True
    data.params["plot"]["flipY"] = False
    y0, y1 = data.get_ydata()
    assert y1 is None
    r_mean = np.mean((r0, r1, r2, r3))
    assert np.array_equal(y0, s0 - r_mean)

    data.params["plot"]["plotmode"] = "ref01"
    y0, y1 = data.get_ydata()
    assert np.array_equal(y0, r0)
    assert np.array_equal(y1, r1)

    data.params["plot"]["plotmode"] = "ref23"
    y0, y1 = data.get_ydata()
    assert np.array_equal(y0, r2)
    assert np.array_equal(y1, r3)


def test_complementary_n4_concatenate_and_xdata_head():
    s0 = np.array([10.0, 20.0])
    s1 = np.array([1.0, 2.0])
    s2 = np.array([3.0, 4.0])
    s3 = np.array([5.0, 6.0])
    r0 = np.array([100.0, 200.0])
    r1 = np.array([10.0, 20.0])
    r2 = np.array([30.0, 40.0])
    r3 = np.array([50.0, 60.0])

    data = make_data(4, "concatenate")
    set_pattern_data(data, [s0, s1, s2, s3], [r0, r1, r2, r3])

    y0, y1 = data.get_ydata()
    assert y1 is None
    assert np.array_equal(y0, np.array([10.0, 1.0, 3.0, 5.0, 20.0, 2.0, 4.0, 6.0]))

    x = data.get_xdata()
    assert np.array_equal(
        x, np.array([1.0e-9, 1.0e-9, 1.0e-9, 1.0e-9, 2.0e-9, 2.0e-9, 2.0e-9, 2.0e-9])
    )

    data.marker_indices = np.vstack(
        (
            np.arange(8, dtype=np.int64),
            np.zeros(8, dtype=np.int64),
            np.zeros(8, dtype=np.int64),
            np.zeros(8, dtype=np.int64),
        )
    )
    x_head = data.get_xdata(force_taumode="head")
    assert np.array_equal(x_head, np.arange(8) * 1.0e-9)


def test_complementary_n4_reject_normalize_and_ref():
    data = make_data(4, "normalize")
    s = [np.array([1.0, 2.0])] * 4
    r = [np.array([1.0, 2.0])] * 4
    set_pattern_data(data, s, r)

    with pytest.raises(ValueError):
        data.get_ydata()

    data.params["plot"]["plotmode"] = "ref"
    with pytest.raises(ValueError):
        data.get_ydata()


def test_complementary_reject_n3():
    data = make_data(3, "data01")
    s0 = np.array([1.0, 2.0])
    s1 = np.array([3.0, 4.0])
    s2 = np.array([5.0, 6.0])
    r0 = np.array([1.0, 1.0])
    r1 = np.array([1.0, 1.0])
    r2 = np.array([1.0, 1.0])
    set_pattern_data(data, [s0, s1, s2], [r0, r1, r2])

    with pytest.raises(ValueError):
        data.get_ydata()

    data.params["plot"]["plotmode"] = "concatenate"
    with pytest.raises(ValueError):
        data.get_xdata()
