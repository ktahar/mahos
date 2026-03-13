#!/usr/bin/env python3

"""
GUI frontend of Analog-PD Pulse ODMR.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg

from mahos.gui.Qt import QtCore, QtGui, QtWidgets
from mahos.gui.param import apply_widgets
from mahos.msgs.common_msgs import BinaryState
from mahos.node.node import local_conf, join_name
from mahos.gui.gui_node import GUINode
from mahos.gui.dialog import load_dialog

from mahos_dq.gui.ui.apodmr import Ui_APODMR
from mahos_dq.gui.apodmr_client import QAPODMRClient
from mahos_dq.gui.podmr import (
    AltPlotWidget,
    PlotWidget,
    PODMRAutoSaveWidget,
    PODMRFitWidget,
    PODMRWidgetBase,
)
from mahos_dq.msgs.apodmr_msgs import APODMRData


Policy = QtWidgets.QSizePolicy.Policy


class APODMRFitWidget(PODMRFitWidget):
    def load_dialog(self, default_path: str) -> str:
        return load_dialog(self, default_path, "APODMR", ".apodmr")


class APODMRAutoSaveWidget(PODMRAutoSaveWidget):
    AUTOSAVE_EXTENSION = ".apodmr.h5"


class APODMRRawPlotWidget(QtWidgets.QWidget):
    """Raw-trace plot widget for APODMR aggregated AnalogPD traces."""

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.init_widgets()
        self.update_font_size()
        self.fontsizeBox.editingFinished.connect(self.update_font_size)
        self.meanBox.toggled.connect(self.recordBox.setDisabled)
        self.meanBox.setChecked(True)
        self.cmap = pg.colormap.get("viridis")

    def sizeHint(self):
        return QtCore.QSize(1400, 600)

    def init_widgets(self):
        marker_colors = ((255, 0, 0), (255, 128, 0), (0, 0, 255), (0, 128, 255))

        glw = pg.GraphicsLayoutWidget(parent=self)
        self.raw_plot = glw.addPlot(lockAspect=False)
        self.raw_plot.showGrid(x=True, y=True)
        self.raw_plot.setLabel("bottom", "Time", "s")
        self.raw_plot.setLabel("left", "Signal")
        self.raw_plot.addLegend()
        self._trace_items: list[pg.PlotDataItem] = []
        self._empty_item = self.raw_plot.plot([0, 1], [0, 0], pen=pg.mkPen((150, 150, 150)))
        self._marker_lines: list[pg.InfiniteLine] = []
        for c in marker_colors:
            line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(c, width=1))
            line.setVisible(False)
            line.setZValue(10)
            self.raw_plot.addItem(line)
            self._marker_lines.append(line)

        self.showBox = QtWidgets.QCheckBox("Show")
        self.showBox.setChecked(True)

        self.meanBox = QtWidgets.QCheckBox("Mean records")

        self.recordBox = QtWidgets.QSpinBox()
        self.recordBox.setPrefix("record: ")
        self.recordBox.setMinimum(0)
        self.recordBox.setMaximum(9999)

        self.indexBox = QtWidgets.QSpinBox()
        self.indexBox.setPrefix("trace index: ")
        self.indexBox.setMinimum(0)
        self.indexBox.setMaximum(9999)

        self.numBox = QtWidgets.QSpinBox()
        self.numBox.setPrefix("num traces: ")
        self.numBox.setMinimum(1)
        self.numBox.setMaximum(9999)

        self.fontsizeBox = QtWidgets.QSpinBox(parent=self)
        self.fontsizeBox.setPrefix("font size: ")
        self.fontsizeBox.setSuffix(" pt")
        self.fontsizeBox.setMinimum(1)
        self.fontsizeBox.setValue(12)
        self.fontsizeBox.setMaximum(99)

        for w in (self.recordBox, self.indexBox, self.numBox, self.fontsizeBox):
            w.setSizePolicy(Policy.MinimumExpanding, Policy.Minimum)
            w.setMaximumWidth(200)

        spacer = QtWidgets.QSpacerItem(40, 20, Policy.Expanding, Policy.Minimum)

        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(self.showBox)
        hl.addWidget(self.meanBox)
        hl.addWidget(self.recordBox)
        hl.addWidget(self.indexBox)
        hl.addWidget(self.numBox)
        hl.addWidget(self.fontsizeBox)
        hl.addItem(spacer)

        vl = QtWidgets.QVBoxLayout()
        vl.addLayout(hl)
        vl.addWidget(glw)
        self.setLayout(vl)

    def _clear_traces(self):
        for item in self._trace_items:
            self.raw_plot.removeItem(item)
        self._trace_items = []

    def _update_marker_lines(self, marker_indices, x):
        for line in self._marker_lines:
            line.setVisible(False)
        if marker_indices is None or x is None:
            return

        inds = np.asarray(marker_indices).reshape(-1)
        for idx, line in zip(inds, self._marker_lines):
            i = int(idx)
            if 0 <= i < len(x):
                line.setPos(float(x[i]))
                line.setVisible(True)

    def _show_empty(self):
        self._empty_item.setData([0, 1], [0, 0])
        self._empty_item.setVisible(True)
        self._update_marker_lines(None, None)

    def plot_raw(self, data: APODMRData):
        if not self.isVisible():
            return

        self._clear_traces()

        if not data.has_raw_data() or not self.showBox.isChecked():
            self._show_empty()
            return

        x = data.get_raw_xdata()
        traces = data.raw_data
        if x is None or traces is None:
            self._show_empty()
            return

        self._empty_item.setVisible(False)
        records, trace_count, _ = traces.shape
        self.recordBox.setMaximum(records - 1)
        self.indexBox.setMaximum(trace_count - 1)
        self.numBox.setMaximum(trace_count)

        tstart = self.indexBox.value()
        tstop = min(tstart + self.numBox.value(), trace_count)
        if tstop <= tstart:
            return

        if self.meanBox.isChecked():
            plot_traces = np.mean(traces, axis=0, keepdims=True)
        else:
            record = min(self.recordBox.value(), records - 1)
            plot_traces = traces[record : record + 1]

        tnum = tstop - tstart
        for i, trace_idx in enumerate(range(tstart, tstop)):
            y = plot_traces[0, trace_idx]
            pen = self.cmap.map(i / (tnum - 1)) if tnum > 1 else self.cmap.map(0.5)
            self._trace_items.append(self.raw_plot.plot(x, y, pen=pen, name=f"t{trace_idx:d}"))

        self._update_marker_lines(data.marker_indices, x)

    def refresh(self, data: APODMRData):
        try:
            self.plot_raw(data)
        except TypeError as e:
            print("Error in plot_raw " + repr(e))

    def update_font_size(self):
        font = QtGui.QFont()
        font.setPointSize(self.fontsizeBox.value())
        for p in ("bottom", "left"):
            self.raw_plot.getAxis(p).label.setFont(font)
            self.raw_plot.getAxis(p).setTickFont(font)


class APODMRWidget(PODMRWidgetBase, Ui_APODMR):
    """Widget for Analog-PD Pulse ODMR."""

    CLIENT_CLASS = QAPODMRClient
    DATA_CLASS = APODMRData
    FIT_WIDGET_CLASS = APODMRFitWidget
    AUTOSAVE_WIDGET_CLASS = APODMRAutoSaveWidget
    MEASUREMENT_NAME = "APODMR"
    FILE_EXTENSION = ".apodmr"

    def setup_measurement_ui(self):
        Ui_APODMR.setupUi(self, self)

    def supports_discard(self) -> bool:
        return False

    def init_widgets_with_params(self):
        params = self.cli.get_param_dict("rabi")

        if "fg" in params:
            self._has_fg = True
            apply_widgets(
                params["fg"],
                [
                    ("ampl", self.fg_amplBox),
                    ("freq", self.fg_freqBox, 1e-3),
                    ("phase", self.fg_phaseBox),
                ],
            )
        else:
            self._has_fg = False

        apply_widgets(
            params,
            [
                ("power", self.powerBox),
                ("freq", self.freqBox, 1e-6),
                ("interval", self.intervalBox, 1e3),
                ("duration", self.durationBox),
                ("roi_head", self.roiheadBox, 1e9),
                ("roi_tail", self.roitailBox, 1e9),
                ("sweeps_per_record", self.sweepsPerRecordBox),
                ("shots_per_point", self.shotsPerPointBox),
                ("divide_block", self.divideblockBox),
                ("base_width", self.basewidthBox, 1e9),
                ("laser_delay", self.ldelayBox, 1e9),
                ("laser_width", self.lwidthBox, 1e9),
                ("mw_delay", self.mdelayBox, 1e9),
                ("trigger_width", self.trigwidthBox, 1e9),
                ("init_delay", self.initdelayBox, 1e9),
                ("final_delay", self.finaldelayBox, 1e9),
                ("mw_offset", self.moffsetBox, 1e9),
            ],
        )
        apply_widgets(
            params["plot"],
            [
                ("sigdelay", self.sigdelayBox, 1e9),
                ("sigwidth", self.sigwidthBox, 1e9),
                ("refdelay", self.refdelayBox, 1e9),
                ("refwidth", self.refwidthBox, 1e9),
            ],
        )

    def apply_meas_widgets(self):
        p = self.data.params

        self.intervalBox.setValue(int(round(p.get("interval", 0.0) * 1e3)))
        self.sweepsBox.setValue(p.get("sweeps", 0))
        self.sweepsPerRecordBox.setValue(p.get("sweeps_per_record", 1))
        self.shotsPerPointBox.setValue(p.get("shots_per_point", 1))
        self.durationBox.setValue(p.get("duration", 0.0))
        self.roiheadBox.setValue(p.get("roi_head", 0.0) * 1e9)
        self.roitailBox.setValue(p.get("roi_tail", 0.0) * 1e9)

        self.set_method(self.data.label)

        self.apply_param_table()

        self.freqBox.setValue(p.get("freq", 2740e6) * 1e-6)
        self.powerBox.setValue(p.get("power", 0.0))
        self.nomwBox.setChecked(p.get("nomw", False))
        if "freq1" in p:
            self.freq1Box.setValue(p["freq1"] * 1e-6)
        if "power1" in p:
            self.power1Box.setValue(p["power1"])
        if "nomw1" in p:
            self.nomw1Box.setChecked(p["nomw1"])

        self.startBox.setValue(p.get("start", 0.0) * 1e9)
        self.numBox.setValue(p.get("num", 1))
        self.stepBox.setValue(p.get("step", 0.0) * 1e9)
        self.logBox.setChecked(p.get("log", False))
        self.NstartBox.setValue(p.get("Nstart", 1))
        self.NnumBox.setValue(p.get("Nnum", 1))
        self.NstepBox.setValue(p.get("Nstep", 1))

        self.invertsweepBox.setChecked(p.get("invert_sweep", False))
        self.reduceBox.setChecked(p.get("enable_reduce", False))
        self.divideblockBox.setChecked(p.get("divide_block", False))
        partial = p.get("partial")
        if partial in (0, 1, 2, 3) and partial + 1 < self.partialBox.count():
            self.partialBox.setCurrentIndex(partial + 1)
        else:
            self.partialBox.setCurrentIndex(0)

        self.basewidthBox.setValue(p.get("base_width", 0.0) * 1e9)
        self.ldelayBox.setValue(p.get("laser_delay", 0.0) * 1e9)
        self.lwidthBox.setValue(p.get("laser_width", 0.0) * 1e9)
        self.mdelayBox.setValue(p.get("mw_delay", 0.0) * 1e9)
        self.trigwidthBox.setValue(p.get("trigger_width", 0.0) * 1e9)
        self.initdelayBox.setValue(p.get("init_delay", 0.0) * 1e9)
        self.finaldelayBox.setValue(p.get("final_delay", 0.0) * 1e9)
        self.moffsetBox.setValue(p.get("mw_offset", 0.0) * 1e9)

    def get_params(self) -> tuple[dict, str]:
        label = self.methodBox.currentText()
        params = {}
        params["quick_resume"] = self.quickresumeBox.isChecked()
        params["freq"] = self.freqBox.value() * 1e6
        params["power"] = self.powerBox.value()
        params["interval"] = self.intervalBox.value() * 1e-3
        params["sweeps"] = self.sweepsBox.value()
        params["sweeps_per_record"] = self.sweepsPerRecordBox.value()
        params["shots_per_point"] = self.shotsPerPointBox.value()
        params["duration"] = self.durationBox.value()
        params["roi_head"] = self.roiheadBox.value() * 1e-9
        params["roi_tail"] = self.roitailBox.value() * 1e-9

        if "freq1" in self._params:
            params["freq1"] = self.freq1Box.value() * 1e6
            params["power1"] = self.power1Box.value()
            params["nomw1"] = self.nomw1Box.isChecked()

        params["base_width"] = self.basewidthBox.value() * 1e-9
        params["laser_delay"] = self.ldelayBox.value() * 1e-9
        params["laser_width"] = self.lwidthBox.value() * 1e-9
        params["mw_delay"] = self.mdelayBox.value() * 1e-9
        params["trigger_width"] = self.trigwidthBox.value() * 1e-9
        params["init_delay"] = self.initdelayBox.value() * 1e-9
        params["final_delay"] = self.finaldelayBox.value() * 1e-9
        params["mw_offset"] = self.moffsetBox.value() * 1e-9

        params["invert_sweep"] = self.invertsweepBox.isChecked()
        params["nomw"] = self.nomwBox.isChecked()
        params["enable_reduce"] = self.reduceBox.isChecked()
        params["divide_block"] = self.divideblockBox.isChecked()
        params["partial"] = self.partialBox.currentIndex() - 1

        if "Nstart" in self._params:
            params["Nstart"] = self.NstartBox.value()
            params["Nnum"] = self.NnumBox.value()
            params["Nstep"] = self.NstepBox.value()
        else:
            params["start"] = self.startBox.value() * 1e-9
            params["num"] = self.numBox.value()
            params["step"] = self.stepBox.value() * 1e-9
            params["log"] = self.logBox.isChecked()

        self.add_param_table_params(params)
        params["plot"] = self.get_plot_params()
        params["fg"] = self.get_fg_params()

        return params, label

    def _update_swept_label(self):
        sweeps = int(self.data.sweeps())
        records = int(self.data.records())
        self.sweptLabel.setText(f"{sweeps} swept / {records} records")

    def update_widgets(self):
        self._update_elapsed_time()
        self._update_swept_label()
        trange = self.data.get_range()

        if trange is not None:
            samples = self.data.get_samples_per_trace()
            if samples is None:
                samples = 0
            self.rangeLabel.setText(f"trace: {trange * 1e6:.2f} us ({samples} samples)")

    def update_state(self, state: BinaryState, last_state: BinaryState):
        for w in (
            self.startButton,
            self.saveButton,
            self.exportButton,
            self.exportaltButton,
            self.loadButton,
            self.quickresumeBox,
            self.freqBox,
            self.powerBox,
            self.nomwBox,
            self.methodBox,
            self.partialBox,
            self.intervalBox,
            self.sweepsBox,
            self.sweepsPerRecordBox,
            self.shotsPerPointBox,
            self.durationBox,
            self.roiheadBox,
            self.roitailBox,
            self.invertsweepBox,
            self.reduceBox,
            self.divideblockBox,
            self.basewidthBox,
            self.ldelayBox,
            self.lwidthBox,
            self.mdelayBox,
            self.trigwidthBox,
            self.initdelayBox,
            self.finaldelayBox,
            self.moffsetBox,
            self.paramTable,
        ):
            w.setEnabled(state == BinaryState.IDLE)

        if state == BinaryState.IDLE:
            if last_state == BinaryState.ACTIVE:
                self.update_cond_widgets()
        else:
            self.update_cond_widgets(force_disable=True)

        if self.has_fg():
            for w in (self.fg_disableButton, self.fg_cwButton, self.fg_gateButton):
                w.setEnabled(state == BinaryState.IDLE)

            if state == BinaryState.IDLE:
                self.switch_fg()
            else:
                for w in (self.fg_waveBox, self.fg_freqBox, self.fg_amplBox, self.fg_phaseBox):
                    w.setEnabled(False)

        self.stopButton.setEnabled(state == BinaryState.ACTIVE)

        self.autosave.update_state(state, last_state)


class APODMRMainWindow(QtWidgets.QMainWindow):
    """MainWindow with APODMRWidget and plot docks."""

    def __init__(self, gconf: dict, name, context, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)

        lconf = local_conf(gconf, name)
        target = lconf["target"]

        self.plot = PlotWidget(parent=self)
        self.alt_plot = AltPlotWidget(parent=self)
        self.raw_plot = APODMRRawPlotWidget(parent=self)
        self.apodmr = APODMRWidget(
            gconf,
            target["apodmr"],
            target["gparams"],
            self.plot,
            self.alt_plot,
            self.raw_plot,
            context,
            parent=self,
        )

        self.setWindowTitle(f"MAHOS.APODMRGUI ({join_name(target['apodmr'])})")
        self.setAnimated(False)
        self.setCentralWidget(self.apodmr)
        self.d_plot = QtWidgets.QDockWidget("Plot", parent=self)
        self.d_plot.setWidget(self.plot)
        self.d_alt_plot = QtWidgets.QDockWidget("Alt Plot", parent=self)
        self.d_alt_plot.setWidget(self.alt_plot)
        self.d_raw_plot = QtWidgets.QDockWidget("Raw Plot", parent=self)
        self.d_raw_plot.setWidget(self.raw_plot)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.d_alt_plot)
        self.tabifyDockWidget(self.d_alt_plot, self.d_plot)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.d_raw_plot)

        self.view_menu = self.menuBar().addMenu("View")
        self.view_menu.addAction(self.d_plot.toggleViewAction())
        self.view_menu.addAction(self.d_alt_plot.toggleViewAction())
        self.view_menu.addAction(self.d_raw_plot.toggleViewAction())

        self.option_menu = self.menuBar().addMenu("Option")
        act = QtGui.QAction("Auto range", parent=self.option_menu)
        act.setCheckable(True)
        act.setChecked(self.plot.auto_range())
        self.option_menu.addAction(act)
        act.toggled.connect(self.plot.set_auto_range)

    def closeEvent(self, event):
        self.apodmr.close_clients()
        QtWidgets.QMainWindow.closeEvent(self, event)


class APODMRGUI(GUINode):
    """GUINode for Analog-PD Pulse ODMR using APODMRWidget.

    :param target.apodmr: Target APODMR node full name.
    :type target.apodmr: tuple[str, str] | str
    :param target.gparams: Target GlobalParams node full name.
    :type target.gparams: tuple[str, str] | str

    """

    def init_widget(self, gconf: dict, name, context):
        return APODMRMainWindow(gconf, name, context)
