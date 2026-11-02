#!/usr/bin/env python3

"""
Tests for mahos.inst.tdc_core.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import numpy as np
import pytest

from mahos.inst.tdc_core import TDCBase


class DummyTDC(TDCBase):
    """Dummy TDC for testing ROI extraction."""

    def __init__(self, data: np.ndarray | None):
        super().__init__("dummy")
        self._data = data

    def get_data(self, ch: int) -> np.ndarray | None:
        return self._data


DATA = np.arange(10, dtype=np.int64)

ROI_CASES = [
    pytest.param([(2, 5)], [[2, 3, 4]], id="in_bounds"),
    pytest.param([(-3, 2)], [[0, 0, 0, 0, 1]], id="left_out_of_bounds_partial"),
    pytest.param([(8, 12)], [[8, 9, 0, 0]], id="right_out_of_bounds_partial"),
    pytest.param([(-3, -1)], [[0, 0]], id="left_out_of_bounds_full"),
    pytest.param([(12, 15)], [[0, 0, 0]], id="right_out_of_bounds_full"),
    pytest.param([(3, 3)], [[]], id="empty_roi"),
    pytest.param(
        [(-3, 2), (12, 15), (8, 12)],
        [[0, 0, 0, 0, 1], [0, 0, 0], [8, 9, 0, 0]],
        id="mixed_rois",
    ),
]


@pytest.mark.parametrize("roi, expected", ROI_CASES)
def test_get_data_roi(roi, expected):
    inst = DummyTDC(DATA)

    data_roi = inst.get_data_roi(0, roi)

    assert data_roi is not None
    assert len(data_roi) == len(expected)
    for d, e in zip(data_roi, expected):
        np.testing.assert_array_equal(d, np.array(e, dtype=DATA.dtype))


def test_get_data_roi_invalid_range():
    inst = DummyTDC(DATA)

    assert inst.get_data_roi(0, [(5, 3)]) is None


def test_get_data_roi_no_data():
    inst = DummyTDC(None)

    assert inst.get_data_roi(0, [(0, 3)]) is None
