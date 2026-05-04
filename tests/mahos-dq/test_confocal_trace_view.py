#!/usr/bin/env python3

"""
Tests for mahos_dq.gui.confocal.traceView.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from mahos_dq.gui import confocal as confocal_gui
from mahos_dq.msgs.confocal_msgs import Trace


class FakeSignal:
    def connect(self, _slot):
        pass


class FakeCli:
    def __init__(self):
        self.traceUpdated = FakeSignal()
        self.paused = FakeSignal()

    def pause(self):
        pass

    def resume(self):
        pass

    def clear(self):
        pass

    def close(self):
        pass


class FakeGlobalParamsClient:
    def __init__(self, *_args, **_kwargs):
        self.params = {"work_dir": "."}

    def get_param(self, key: str, default=None):
        return self.params.get(key, default)

    def set_param(self, key: str, value):
        self.params[key] = value
        return True

    def close(self):
        pass


@pytest.fixture
def trace_view(monkeypatch, qtbot):
    def make(labels=None, size=5):
        monkeypatch.setattr(confocal_gui, "GlobalParamsClient", FakeGlobalParamsClient)
        tracer_conf = {"size": size}
        gconf = {
            "localhost": {
                "confocal": {"tracer": tracer_conf},
                "gparams": {},
            }
        }
        view = confocal_gui.traceView(
            gconf, "localhost::confocal", "localhost::gparams", labels, None, cli=FakeCli()
        )
        qtbot.addWidget(view)
        view.timestampBox.setChecked(False)
        return view

    return make


def make_trace(channels: int, size: int = 5) -> Trace:
    trace = Trace(size=size, channels=channels)
    trace.yunit = "cps"
    stamp0 = np.datetime64("2026-01-01T00:00:00", "ns")
    offsets = np.arange(size, dtype=np.int64).astype("timedelta64[ns]")
    for ch in range(channels):
        trace.traces[ch][:] = ch + 1
        trace.stamps[ch][:] = stamp0 + offsets
    return trace


def test_trace_view_uses_configured_labels_and_fallback(trace_view):
    view = trace_view(labels=["signal", "reference"])
    view.update(make_trace(3))

    assert [ch.label.text().split(":")[0] for ch in view._channel] == [
        "signal",
        "reference",
        "PD2",
    ]
    assert [ch.check.text() for ch in view._channel] == ["signal", "reference", "PD2"]
    assert view.labeltotal.text().startswith("Total: 6.00e+00 cps")


def test_trace_view_supports_nine_channels(trace_view):
    view = trace_view(labels=[f"ch{i}" for i in range(9)])
    view.update(make_trace(9))

    assert len(view._channel) == 9
    assert view._channel[-1].check.text() == "ch8"
    assert view.labeltotal.text().startswith("Total: 4.50e+01 cps")


def test_trace_view_rejects_more_than_nine_channels(trace_view):
    view = trace_view()

    with pytest.raises(ValueError, match="Unsupported number of channels"):
        view.update(make_trace(10))


def test_trace_view_toggle_channel_clears_curves(trace_view):
    view = trace_view()
    view.update(make_trace(3))

    view._channel[1].check.setChecked(False)

    assert view._channel[1].curve.getData()[1] is None
    assert view._channel[1].sma_curve.getData()[1] is None


def test_trace_view_sums_traces_by_timestamp(trace_view):
    view = trace_view()
    trace = make_trace(3)

    stamps, values = view._sum_traces_by_timestamp(trace)

    assert len(stamps) == trace.size()
    assert np.all(values == 6.0)
