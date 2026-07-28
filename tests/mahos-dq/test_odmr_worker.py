#!/usr/bin/env python3

"""
Tests for ODMR worker data assembly.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np
import pytest

from mahos_dq.meas.odmr_pd import sum_pd_channels
from mahos_dq.meas.odmr_worker import Sweeper, SweeperOverlay
from mahos_dq.msgs.odmr_msgs import ODMRData


def _overlay_worker(num: int, background: bool = False) -> SweeperOverlay:
    worker = SweeperOverlay.__new__(SweeperOverlay)
    worker.data = ODMRData({"num": num, "background": background}, "cw")
    return worker


def _direct_worker(num: int, background: bool = False) -> Sweeper:
    worker = Sweeper.__new__(Sweeper)
    worker._sg_first = False
    worker._pg_immediate = False
    worker.data = ODMRData({"num": num, "background": background}, "cw")
    return worker


@pytest.mark.parametrize("worker_factory", (_overlay_worker, _direct_worker))
def test_append_line_without_background(worker_factory):
    worker = worker_factory(3)

    worker.append_line(np.array([1.0, 2.0, 3.0]))
    worker.append_line(np.array([4.0, 5.0, 6.0]))

    np.testing.assert_array_equal(
        worker.data.data,
        np.array(
            [
                [1.0, 4.0],
                [2.0, 5.0],
                [3.0, 6.0],
            ]
        ),
    )
    assert worker.data.bg_data is None


@pytest.mark.parametrize("worker_factory", (_overlay_worker, _direct_worker))
def test_append_line_splits_interleaved_background(worker_factory):
    worker = worker_factory(3, background=True)

    worker.append_line(np.array([1.0, 10.0, 2.0, 20.0, 3.0, 30.0]))
    worker.append_line(np.array([4.0, 40.0, 5.0, 50.0, 6.0, 60.0]))

    np.testing.assert_array_equal(
        worker.data.data,
        np.array(
            [
                [1.0, 4.0],
                [2.0, 5.0],
                [3.0, 6.0],
            ]
        ),
    )
    np.testing.assert_array_equal(
        worker.data.bg_data,
        np.array(
            [
                [10.0, 40.0],
                [20.0, 50.0],
                [30.0, 60.0],
            ]
        ),
    )


@pytest.mark.parametrize(("sg_first", "pg_immediate"), ((True, False), (False, True)))
def test_direct_append_line_restores_frequency_order(sg_first, pg_immediate):
    worker = _direct_worker(3, background=True)
    worker._sg_first = sg_first
    worker._pg_immediate = pg_immediate

    worker.append_line(np.array([3.0, 30.0, 1.0, 10.0, 2.0, 20.0]))

    np.testing.assert_array_equal(worker.data.data[:, 0], np.array([1.0, 2.0, 3.0]))
    np.testing.assert_array_equal(worker.data.bg_data[:, 0], np.array([10.0, 20.0, 30.0]))


def test_append_point_starts_new_partial_line_without_background():
    worker = _overlay_worker(3)

    for value in (1.0, 2.0, 3.0, 4.0):
        worker.append_point(np.array([value]))

    np.testing.assert_array_equal(worker.data.data[:, 0], np.array([1.0, 2.0, 3.0]))
    np.testing.assert_array_equal(worker.data.data[0, :], np.array([1.0, 4.0]))
    assert np.isnan(worker.data.data[1:, 1]).all()


def test_append_point_starts_new_partial_line_with_background():
    worker = _overlay_worker(2, background=True)

    for point in ((1.0, 10.0), (2.0, 20.0), (3.0, 30.0)):
        worker.append_point(np.array(point))

    np.testing.assert_array_equal(worker.data.data[:, 0], np.array([1.0, 2.0]))
    np.testing.assert_array_equal(worker.data.bg_data[:, 0], np.array([10.0, 20.0]))
    assert worker.data.data[0, 1] == 3.0
    assert worker.data.bg_data[0, 1] == 30.0
    assert np.isnan(worker.data.data[1, 1])
    assert np.isnan(worker.data.bg_data[1, 1])


def test_sum_pd_channels_flattens_multi_channel_blocks():
    channel = np.array([1.0, 2.0, 3.0])

    result = sum_pd_channels([channel, [2.0 * channel, 3.0 * channel]])

    np.testing.assert_array_equal(result, 6.0 * channel)
