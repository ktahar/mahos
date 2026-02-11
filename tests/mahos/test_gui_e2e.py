#!/usr/bin/env python3

"""
GUI end-to-end tests for mahos.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytestmark = pytest.mark.gui_e2e

from mahos.gui.Qt import QtCore
from mahos.gui.camera import CameraWidget
from mahos.gui.grid_sweeper import GridSweeperWidget
from mahos.gui.recorder import RecorderMainWindow
from mahos.gui.sweeper import SweeperWidget
from mahos.msgs.common_msgs import BinaryState
from mahos.node.node import local_conf
from fixtures import (
    ctx,
    gconf,
    server,
    global_params,
    camera,
    sweeper,
    grid_sweeper,
    recorder,
)


GUI_TIMEOUT_MS = 15_000


def wait_until_ready(qtbot, widget):
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitUntil(lambda: widget.isEnabled(), timeout=GUI_TIMEOUT_MS)


def stop_if_active(qtbot, stop_button, get_state):
    if get_state() == BinaryState.ACTIVE and stop_button.isEnabled():
        qtbot.mouseClick(stop_button, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: get_state() == BinaryState.IDLE, timeout=GUI_TIMEOUT_MS)


def has_valid_camera_data(data):
    return data is not None and data.image is not None and data.count > 1


def has_valid_sweeper_data(data):
    return data is not None and data.has_data()


def has_valid_recorder_data(data):
    return data is not None and data.has_data() and len(data.get_channels()) > 0


def has_valid_grid_sweeper_data(data):
    return data is not None and data.has_data()


@pytest.mark.timeout(30)
def test_camera_gui_start_and_receive_data(server, camera, global_params, gconf, qtbot):
    camera.wait()
    global_params.wait()

    target = local_conf(gconf, "localhost::camera_gui")["target"]
    widget = CameraWidget(gconf, target["camera"], target["gparams"], context=None)
    wait_until_ready(qtbot, widget)

    qtbot.mouseClick(widget.startButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: has_valid_camera_data(widget.cli.get_data()), timeout=GUI_TIMEOUT_MS)

    stop_if_active(qtbot, widget.stopButton, widget.cli.get_state)


@pytest.mark.timeout(30)
def test_recorder_gui_start_and_receive_data(server, recorder, global_params, gconf, qtbot):
    recorder.wait()
    global_params.wait()

    window = RecorderMainWindow(gconf, "localhost::recorder_gui", context=None)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.meas.isEnabled(), timeout=GUI_TIMEOUT_MS)

    qtbot.mouseClick(window.meas.startButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: has_valid_recorder_data(window.meas.cli.get_data()), timeout=GUI_TIMEOUT_MS
    )

    stop_if_active(qtbot, window.meas.stopButton, window.meas.cli.get_state)


@pytest.mark.timeout(30)
def test_sweeper_gui_start_and_receive_data(server, sweeper, global_params, gconf, qtbot):
    sweeper.wait()
    global_params.wait()

    # Configure the mock DMM used by sweeper.
    label = "ch1_dcv"
    dmm_params = server.get_param_dict("dmm0", label)
    assert server.configure("dmm0", dmm_params, label)

    target = local_conf(gconf, "localhost::sweeper_gui")["target"]
    widget = SweeperWidget(gconf, target["sweeper"], target["gparams"], context=None)
    wait_until_ready(qtbot, widget)

    widget.sweepsBox.setValue(1)
    widget.delayBox.setValue(1e-5)
    widget.logBox.setChecked(False)

    qtbot.mouseClick(widget.startButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: has_valid_sweeper_data(widget.cli.get_data()), timeout=GUI_TIMEOUT_MS)

    stop_if_active(qtbot, widget.stopButton, widget.cli.get_state)


@pytest.mark.timeout(30)
def test_grid_sweeper_gui_start_and_receive_data(
    server, grid_sweeper, global_params, gconf, qtbot
):
    grid_sweeper.wait()
    global_params.wait()

    # Configure the mock DMM used by grid sweeper.
    label = "ch1_dcv"
    dmm_params = server.get_param_dict("dmm0", label)
    assert server.configure("dmm0", dmm_params, label)

    target = local_conf(gconf, "localhost::grid_sweeper_gui")["target"]
    widget = GridSweeperWidget(gconf, target["grid_sweeper"], target["gparams"], context=None)
    wait_until_ready(qtbot, widget)

    widget.xnumBox.setValue(5)
    widget.ynumBox.setValue(3)
    widget.xdelayBox.setValue(1e-4)
    widget.ydelayBox.setValue(1e-4)
    widget.xlogBox.setChecked(False)
    widget.ylogBox.setChecked(False)
    widget.sweepsBox.setValue(1)

    qtbot.mouseClick(widget.startButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: has_valid_grid_sweeper_data(widget.cli.get_data()),
        timeout=GUI_TIMEOUT_MS,
    )

    stop_if_active(qtbot, widget.stopButton, widget.cli.get_state)
