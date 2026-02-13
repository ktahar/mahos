#!/usr/bin/env python3

"""
Tests for GridSweeper.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np

from mahos.meas.grid_sweeper import GridSweeperClient, GridSweeperIO
from mahos.msgs.common_msgs import BinaryState
from util import get_some, expect_value, save_load_test
from fixtures import (
    ctx,
    gconf,
    server,
    grid_sweeper,
    server_conf,
    grid_sweeper_conf,
)


def expect_grid_sweeper(cli: GridSweeperClient, poll_timeout_ms, sweeps: int):
    def get():
        data = cli.get_data()
        if data is not None and data.has_data():
            return data.sweeps() >= sweeps
        else:
            return None

    return expect_value(get, True, poll_timeout_ms, trials=500)


def expect_first_line_filled(cli: GridSweeperClient, poll_timeout_ms):
    def get():
        data = cli.get_data()
        if data is not None and data.has_data():
            return np.isfinite(data.data[:, 0, 0]).all()
        else:
            return None

    return expect_value(get, True, poll_timeout_ms, trials=500)


def expect_second_plane_has_nan(cli: GridSweeperClient, poll_timeout_ms):
    def get():
        data = cli.get_data()
        if data is None or not data.has_data() or data.data.shape[2] < 2:
            return None
        return np.isnan(data.data[:, :, 1]).any()

    return expect_value(get, True, poll_timeout_ms, trials=500)


def test_grid_sweeper(server, grid_sweeper, server_conf, grid_sweeper_conf):
    poll_timeout_ms = grid_sweeper_conf["poll_timeout_ms"]

    grid_sweeper.wait()

    assert get_some(grid_sweeper.get_status, poll_timeout_ms).state == BinaryState.IDLE

    # need to configure the mock dmm (measure instrument)
    label = "ch1_dcv"
    dmm_params = server.get_param_dict("dmm0", label)
    assert server.configure("dmm0", dmm_params, label)

    params = grid_sweeper.get_param_dict()
    assert params["x"]["start"].step() == grid_sweeper_conf["x"]["step"]
    assert params["x"]["stop"].step() == grid_sweeper_conf["x"]["step"]
    assert params["x"]["start"].adaptive_step() == grid_sweeper_conf["x"]["adaptive_step"]
    assert params["x"]["stop"].adaptive_step() == grid_sweeper_conf["x"]["adaptive_step"]
    assert params["y"]["start"].step() == grid_sweeper_conf["y"]["step"]
    assert params["y"]["stop"].step() == grid_sweeper_conf["y"]["step"]
    assert params["y"]["start"].adaptive_step() == grid_sweeper_conf["y"]["adaptive_step"]
    assert params["y"]["stop"].adaptive_step() == grid_sweeper_conf["y"]["adaptive_step"]
    invalid_log_params = {
        "x": {
            "start": 0.0,
            "stop": 1.0,
            "num": 5,
            "log": True,
            "delay": 0.0,
        },
        "y": {
            "start": 0.0,
            "stop": 1.0,
            "num": 3,
            "log": False,
            "delay": 0.0,
        },
        "sweeps": 1,
    }
    assert not grid_sweeper.change_state(BinaryState.ACTIVE, invalid_log_params)
    assert get_some(grid_sweeper.get_status, poll_timeout_ms).state == BinaryState.IDLE

    x_num = 31
    y_num = 7
    sweep_num = 2
    params["x"]["num"].set(x_num)
    params["y"]["num"].set(y_num)
    params["x"]["delay"].set(1e-3)
    params["y"]["delay"].set(1e-4)
    params["sweeps"].set(sweep_num)

    assert grid_sweeper.change_state(BinaryState.ACTIVE, params)
    assert expect_first_line_filled(grid_sweeper, poll_timeout_ms)
    assert expect_grid_sweeper(grid_sweeper, poll_timeout_ms, 1)
    assert expect_second_plane_has_nan(grid_sweeper, poll_timeout_ms)
    assert expect_grid_sweeper(grid_sweeper, poll_timeout_ms, sweep_num)

    data = get_some(grid_sweeper.get_data, poll_timeout_ms)
    status = get_some(grid_sweeper.get_status, poll_timeout_ms)

    assert status.state == BinaryState.IDLE
    assert data.sweeps() == sweep_num
    assert data.data.shape == (x_num, y_num, sweep_num)
    assert np.isfinite(data.data[:, :, 0]).all()
    assert np.isfinite(data.data[:, :, 1]).all()
    assert data.get_image(999) is None
    assert data.get_image(-999) is None

    save_load_test(GridSweeperIO(), data)
