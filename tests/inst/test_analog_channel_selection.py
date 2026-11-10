"""
Verify DAQ task inputs without requiring the NI driver.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import mahos.inst
import pytest


class Task:
    def __init__(self):
        self.inputs = []

    def CreateAIVoltageChan(self, line, name, terminal, low, high, unit, scale):
        self.inputs.append((line, low, high))

    def SetSampTimingType(self, mode):
        pass

    def ClearTask(self):
        pass


@pytest.fixture
def analog_class(monkeypatch):
    driver = SimpleNamespace(Task=Task, DAQmx_Val_RSE=0, DAQmx_Val_Volts=0, DAQmx_Val_OnDemand=0)
    monkeypatch.setitem(sys.modules, "PyDAQmx", driver)
    spec = importlib.util.spec_from_file_location(
        "selection_test_daq", Path(mahos.inst.__file__).parent / "daq.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.AnalogIn


def test_daq_task_selection_and_restore(analog_class):
    inst = analog_class("pd", {"lines": ["Dev1/ai0", "Dev1/ai2", "Dev1/ai4"]})
    bounds = [(-1, 1), (-2, 2), (-4, 4)]
    assert inst.configure({"channel_selection": [1], "bounds": bounds})
    assert inst.task.inputs == [("Dev1/ai2", -2, 2)]
    inst.queue.append([1])
    assert inst.configure({"bounds": bounds})
    assert inst.task.inputs == [("Dev1/ai0", -1, 1), ("Dev1/ai2", -2, 2), ("Dev1/ai4", -4, 4)]
    assert inst.pop_opt() is None


def test_paired_input_requirement(analog_class):
    inst = analog_class("pd", {"lines": ["Dev1/ai0", "Dev1/ai1"]})
    inst._requires_all_channels = True
    assert not inst.configure({"channel_selection": [0]})
    assert inst.task is None
    assert inst.configure({"channel_selection": [0, 1]})
