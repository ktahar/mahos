"""Tests for confocal GUI plotting behavior."""

import numpy as np


def test_growing_trace_view(gconf, qtbot):
    from mahos_dq.gui.confocal import traceView
    from mahos_dq.msgs.confocal_msgs import Trace

    view = traceView(gconf, "localhost::confocal", "localhost::gparams", [], None)
    qtbot.addWidget(view)
    try:
        view.showtotalBox.setChecked(True)
        view.showrawBox.setChecked(True)
        view.smaBox.setValue(1)
        trace = Trace(size=1_000_000)
        for timestamp in (False, True):
            view.timestampBox.setChecked(timestamp)
            view.update(trace)
        trace.traces = [np.array([1.0, 2.0, 3.0]), np.array([10.0, 20.0])]
        trace.stamps = [
            np.array([1, 2, 3], dtype="datetime64[ns]"),
            np.array([2, 3], dtype="datetime64[ns]"),
        ]
        view.timestampBox.setChecked(False)
        view.update(trace)
        np.testing.assert_equal(view._channel[0].curve.getData(), ([0, 1, 2], [1.0, 2.0, 3.0]))
        np.testing.assert_equal(view._channel[1].curve.getData(), ([1, 2], [10.0, 20.0]))
        np.testing.assert_equal(view.curve_total.getData(), ([1, 2], [12.0, 23.0]))
        view.smaBox.setValue(2)
        view.update(trace)
        np.testing.assert_equal(view._channel[0].sma_curve.getData(), ([0.5, 1.5], [1.5, 2.5]))
        np.testing.assert_equal(view._channel[1].sma_curve.getData(), ([1.5], [15.0]))
        np.testing.assert_equal(view.curve_total_sma.getData(), ([1.5], [17.5]))
        view.timestampBox.setChecked(True)
        view.update(trace)
        trace.clear()
        for timestamp in (False, True):
            view.timestampBox.setChecked(timestamp)
            view.update(trace)
            for curve in (view.curve_total, view.curve_total_sma):
                assert curve.getData()[1] is None or not len(curve.getData()[1])
    finally:
        view.close_clients()
