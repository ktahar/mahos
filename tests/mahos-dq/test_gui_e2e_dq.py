#!/usr/bin/env python3

"""
GUI end-to-end tests for mahos-dq.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytestmark = pytest.mark.gui_e2e

from mahos.gui.Qt import QtCore
from mahos.msgs.common_msgs import BinaryState
from mahos.node.node import local_conf
from mahos_dq.gui.hbt import HBTMainWindow
from mahos_dq.gui.iodmr import IODMRMainWindow
from mahos_dq.gui.odmr import ODMRMainWindow
from mahos_dq.gui.podmr import PODMRMainWindow
from mahos_dq.gui.spodmr import SPODMRMainWindow
from mahos_dq.gui.spectroscopy import SpectroscopyMainWindow
from fixtures import (
    ctx,
    gconf,
    server,
    global_params,
    spectroscopy,
    odmr,
    hbt,
    podmr,
    spodmr,
    iodmr,
)


GUI_TIMEOUT_MS = 30_000


def stop_if_active(qtbot, stop_button, get_state):
    if get_state() == BinaryState.ACTIVE and stop_button.isEnabled():
        qtbot.mouseClick(stop_button, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: get_state() == BinaryState.IDLE, timeout=GUI_TIMEOUT_MS)


def has_valid_spectroscopy_data(data):
    return data is not None and data.data is not None and data.xdata is not None


def has_valid_odmr_data(data):
    return data is not None and data.data is not None and data.data.shape[0] >= 10


def has_valid_hbt_data(data):
    return data is not None and data.data is not None and len(data.data) > 0


def has_valid_podmr_data(data):
    return data is not None and data.data0 is not None and len(data.data0) >= 2


def has_valid_spodmr_data(data):
    return data is not None and data.data0 is not None and data.data0.shape[0] >= 2


def has_valid_iodmr_data(data):
    return data is not None and data.data_sum is not None and data.data_sum.shape[0] >= 5


def set_method(method_box, method: str):
    i = method_box.findText(method)
    if i >= 0:
        method_box.setCurrentIndex(i)
        return True
    return False


@pytest.mark.timeout(40)
def test_spectroscopy_gui_start_and_receive_data(
    server, spectroscopy, global_params, gconf, qtbot
):
    spectroscopy.wait()
    global_params.wait()

    window = SpectroscopyMainWindow(gconf, "localhost::spectroscopy_gui", context=None)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.spec.isEnabled(), timeout=GUI_TIMEOUT_MS)

    window.spec.exposuretimeBox.setValue(1.0)
    window.spec.acquisitionsBox.setValue(1)

    qtbot.mouseClick(window.spec.startButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: has_valid_spectroscopy_data(window.spec.cli.get_data()), timeout=GUI_TIMEOUT_MS
    )

    stop_if_active(qtbot, window.spec.stopButton, window.spec.cli.get_state)


@pytest.mark.timeout(50)
def test_odmr_gui_start_and_receive_data(server, odmr, global_params, gconf, qtbot):
    odmr.wait()
    global_params.wait()

    window = ODMRMainWindow(gconf, "localhost::odmr_gui", context=None)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.odmr.isEnabled(), timeout=GUI_TIMEOUT_MS)

    set_method(window.odmr.methodBox, "cw")
    window.odmr.numBox.setValue(10)
    window.odmr.sweepsBox.setValue(1)

    qtbot.mouseClick(window.odmr.startButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: has_valid_odmr_data(window.odmr.cli.get_data()), timeout=GUI_TIMEOUT_MS
    )

    stop_if_active(qtbot, window.odmr.stopButton, window.odmr.cli.get_state)


@pytest.mark.timeout(50)
def test_hbt_gui_start_and_receive_data(server, hbt, global_params, gconf, qtbot):
    hbt.wait()
    global_params.wait()

    window = HBTMainWindow(gconf, "localhost::hbt_gui", context=None)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.hbt.isEnabled(), timeout=GUI_TIMEOUT_MS)

    window.hbt.windowBox.setValue(50)
    window.hbt.binBox.setValue(0.2)

    qtbot.mouseClick(window.hbt.startButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: has_valid_hbt_data(window.hbt.cli.get_data()), timeout=GUI_TIMEOUT_MS)

    stop_if_active(qtbot, window.hbt.stopButton, window.hbt.cli.get_state)


@pytest.mark.timeout(60)
def test_podmr_gui_start_and_receive_data(server, podmr, global_params, gconf, qtbot):
    podmr.wait()
    global_params.wait()

    window = PODMRMainWindow(gconf, "localhost::podmr_gui", context=None)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.podmr.isEnabled(), timeout=GUI_TIMEOUT_MS)

    set_method(window.podmr.methodBox, "rabi")
    window.podmr.numBox.setValue(2)
    window.podmr.sweepsBox.setValue(1)

    qtbot.mouseClick(window.podmr.startButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: has_valid_podmr_data(window.podmr.cli.get_data()),
        timeout=GUI_TIMEOUT_MS,
    )

    stop_if_active(qtbot, window.podmr.stopButton, window.podmr.cli.get_state)


@pytest.mark.timeout(60)
def test_spodmr_gui_start_and_receive_data(server, spodmr, global_params, gconf, qtbot):
    spodmr.wait()
    global_params.wait()

    window = SPODMRMainWindow(gconf, "localhost::spodmr_gui", context=None)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.spodmr.isEnabled(), timeout=GUI_TIMEOUT_MS)

    set_method(window.spodmr.methodBox, "rabi")
    window.spodmr.numBox.setValue(2)
    window.spodmr.sweepsBox.setValue(1)
    window.spodmr.accumwindowBox.setValue(0.1)

    qtbot.mouseClick(window.spodmr.startButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: has_valid_spodmr_data(window.spodmr.cli.get_data()),
        timeout=GUI_TIMEOUT_MS,
    )

    stop_if_active(qtbot, window.spodmr.stopButton, window.spodmr.cli.get_state)


@pytest.mark.timeout(60)
def test_iodmr_gui_start_and_receive_data(server, iodmr, global_params, gconf, qtbot):
    iodmr.wait()
    global_params.wait()

    target = local_conf(gconf, "localhost::iodmr_gui")["target"]
    window = IODMRMainWindow(gconf, target["iodmr"], target["gparams"], context=None)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.isEnabled(), timeout=GUI_TIMEOUT_MS)

    window.cw.numBox.setValue(5)
    window.cw.sweepsBox.setValue(1)
    window.cw.exposuredelayBox.setValue(0.0)

    qtbot.mouseClick(window.cw.startButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: has_valid_iodmr_data(window.cli.get_data()), timeout=GUI_TIMEOUT_MS)

    stop_if_active(qtbot, window.cw.stopButton, window.cli.get_state)
