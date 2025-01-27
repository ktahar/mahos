#!/usr/bin/env python3

"""
GUI frontend of ODMR.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations
import typing as T
import uuid
import os

import numpy as np
import pyqtgraph as pg

from . import Qt
from .Qt import QtCore, QtWidgets, QtGui

from .ui.odmr import Ui_ODMR
from .ui.odmr_peaks import Ui_ODMRPeaks
from .odmr_client import QODMRClient

from ..msgs.common_msgs import BinaryState, BinaryStatus
from ..msgs.common_meas_msgs import Buffer
from ..msgs.odmr_msgs import ODMRData
from ..msgs import param_msgs as P
from ..node.global_params import GlobalParamsClient
from ..meas.confocal import ConfocalIORequester
from ..util import conv, nv
from ..util.plot import colors_tab20_pair
from .gui_node import GUINode
from .common_widget import ClientWidget
from .fit_widget import FitWidget
from .param import apply_widgets
from .dialog import save_dialog, load_dialog, export_dialog
from ..node.node import local_conf, join_name


Policy = QtWidgets.QSizePolicy.Policy


class Colors(T.NamedTuple):
    color: str
    color_bg: str


_colors = [Colors(c0, c1) for c0, c1 in colors_tab20_pair()]


class ODMRFitWidget(FitWidget):
    def colors(self) -> list:
        return _colors

    def load_dialog(self, default_path: str) -> str:
        return load_dialog(self, default_path, "ODMR", ".odmr")


class PlotWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self._normalize_updated = False
        self._yunit: str = ""
        self.init_ui()
        self.init_view()
        self.update_font_size()
        self.fontsizeBox.editingFinished.connect(self.update_font_size)
        self._error_bar_items = []

    def sizeHint(self):
        return QtCore.QSize(1600, 1200)

    def init_ui(self):
        hl0 = QtWidgets.QHBoxLayout()
        self.showimgBox = QtWidgets.QCheckBox("Show image", parent=self)
        self.showimgBox.setChecked(True)
        self.showstdBox = QtWidgets.QCheckBox("Show std. dev.", parent=self)
        self.showstdBox.setChecked(False)
        self.lastnBox = QtWidgets.QSpinBox(parent=self)
        self.lastnBox.setPrefix("last_n: ")
        self.lastnBox.setMinimum(0)
        self.lastnBox.setMaximum(10000)
        self.lastnimgBox = QtWidgets.QSpinBox(parent=self)
        self.lastnimgBox.setPrefix("last_n (img): ")
        self.lastnimgBox.setMinimum(0)
        self.lastnimgBox.setMaximum(10000)
        self.normalizenBox = QtWidgets.QSpinBox(parent=self)
        self.normalizenBox.setPrefix("normalize_n: ")
        self.normalizenBox.setMinimum(-100)
        self.normalizenBox.setMaximum(100)
        self.fontsizeBox = QtWidgets.QSpinBox(parent=self)
        self.fontsizeBox.setPrefix("font size: ")
        self.fontsizeBox.setSuffix(" pt")
        self.fontsizeBox.setMinimum(1)
        self.fontsizeBox.setValue(12)
        self.fontsizeBox.setMaximum(99)
        for w in (self.lastnBox, self.lastnimgBox, self.normalizenBox, self.fontsizeBox):
            w.setSizePolicy(Policy.MinimumExpanding, Policy.Minimum)
            w.setMaximumWidth(200)
        self.complexBox = QtWidgets.QComboBox(parent=self)
        self.complexBox.addItems(["real", "imag", "abs", "angle"])
        self.complexBox.setCurrentIndex(0)
        spacer = QtWidgets.QSpacerItem(40, 20, Policy.Expanding, Policy.Minimum)
        for w in (
            self.showimgBox,
            self.showstdBox,
            self.lastnBox,
            self.lastnimgBox,
            self.normalizenBox,
            self.fontsizeBox,
            self.complexBox,
        ):
            hl0.addWidget(w)
        hl0.addItem(spacer)

        hl = QtWidgets.QHBoxLayout()
        self.graphicsView = pg.GraphicsView(parent=self)
        self.histo = pg.HistogramLUTWidget(parent=self)
        hl.addWidget(self.graphicsView)
        hl.addWidget(self.histo)

        vl = QtWidgets.QVBoxLayout()
        vl.addLayout(hl0)
        vl.addLayout(hl)
        self.setLayout(vl)

    def init_view(self):
        self.layout = pg.GraphicsLayout()
        self.graphicsView.setCentralItem(self.layout)
        self.histo.gradient.loadPreset("inferno")

        self.plot = self.layout.addPlot(row=0, col=0, lockAspect=False)

        self.img = pg.ImageItem()
        self.img_plot = self.layout.addPlot(row=1, col=0, lockAspect=False)
        self.img_plot.addItem(self.img)
        self.histo.setImageItem(self.img)

        self.plot.showGrid(x=True, y=True)
        self.plot.setLabel("bottom", "Microwave frequency", "Hz")
        self.plot.setLabel("left", "Intensity", "")
        self.img_plot.setLabel("bottom", "Microwave frequency", "Hz")
        self.img_plot.setLabel("left", "Number of accumulation")

        self.showimgBox.toggled.connect(self.toggle_image)
        self.normalizenBox.valueChanged.connect(self.update_normalize)

    def refresh_all(self, data_list: list[tuple[ODMRData, bool, str]], data: ODMRData):
        if self._yunit != data.yunit:
            self._yunit = data.yunit
            self.update_ylabel(self.normalizenBox.value())

        if data.has_data():
            self.update_image(data)
        self.update_plot(data_list)

    def refresh_plot(self, data_list: list[tuple[ODMRData, bool, str]]):
        self.update_plot(data_list)

    def update_image(self, data: ODMRData, setlevel=True):
        img = data.get_image(
            last_n=self.lastnimgBox.value(), complex_conv=self.complexBox.currentText()
        )
        self.img.updateImage(img)
        if setlevel:
            mn, mx = np.nanmin(img), np.nanmax(img)
            if mn == mx:
                mn, mx = mn - 0.1, mx + 0.1
            self.histo.setLevels(mn, mx)
        self.img.resetTransform()
        self.img.setPos(data.params["start"], 0.0)
        self.img.setTransform(QtGui.QTransform.fromScale(data.step(), 1.0))

    def add_error_bar(self, x, y, height, pen):
        item = pg.ErrorBarItem(x=x, y=y, height=height, pen=pen)
        self.plot.addItem(item)
        self._error_bar_items.append(item)

    def clear_error_bars(self):
        if not self._error_bar_items:
            return

        for item in self._error_bar_items:
            self.plot.removeItem(item)
        self._error_bar_items = []

    def update_plot(self, data_list: list[tuple[ODMRData, bool, Colors]]):
        self.plot.clearPlots()
        self.clear_error_bars()

        for data, show_fit, c in data_list:
            x = data.get_xdata()
            y, y_bg = data.get_ydata(
                last_n=self.lastnBox.value(),
                normalize_n=self.normalizenBox.value(),
                complex_conv=self.complexBox.currentText(),
            )
            if self.showstdBox.isChecked():
                ystd, ybg_std = data.get_ydata(
                    last_n=self.lastnBox.value(),
                    normalize_n=self.normalizenBox.value(),
                    complex_conv=self.complexBox.currentText(),
                    std=True,
                )
            else:
                ystd = ybg_std = None
            xfit = data.get_fit_xdata()
            yfit = data.get_fit_ydata(
                last_n=self.lastnBox.value(), normalize_n=self.normalizenBox.value()
            )

            _show_fit = show_fit and (xfit is not None) and (yfit is not None)
            w = 0.5 if _show_fit else 1
            pen = pg.mkPen(c.color, width=w)
            pen_bg = pg.mkPen(c.color_bg, width=w)

            if ystd is not None:
                self.add_error_bar(x, y, 2 * ystd, pen)
            if ybg_std is not None:
                self.add_error_bar(x, y_bg, 2 * ybg_std, pen_bg)

            self.plot.plot(
                x,
                y,
                pen=pen,
                symbolPen=None,
                symbol="o",
                symbolSize=8,
                symbolBrush=c.color,
            )
            if y_bg is not None:
                self.plot.plot(
                    x,
                    y_bg,
                    pen=pen_bg,
                    symbolPen=None,
                    symbol="o",
                    symbolSize=8,
                    symbolBrush=c.color_bg,
                )

            if _show_fit:
                self.plot.plot(xfit, yfit, pen=pg.mkPen(c.color, width=2))

        if self._normalize_updated:
            self.plot.autoRange()
            self._normalize_updated = False

    def toggle_image(self, show):
        if show:
            self.layout.addItem(self.img_plot, row=1, col=0)
        else:
            self.layout.removeItem(self.img_plot)

    def update_ylabel(self, normalize_n: int):
        if normalize_n:
            self.plot.setLabel("left", "Normalized Intensity")
        else:
            self.plot.setLabel("left", "Intensity", self._yunit)

    def update_normalize(self, normalize_n: int):
        self.update_ylabel(normalize_n)
        self._normalize_updated = True

    def update_font_size(self):
        font = QtGui.QFont()
        font.setPointSize(self.fontsizeBox.value())
        for p in (self.plot, self.img_plot):
            for l in ("bottom", "left"):
                p.getAxis(l).label.setFont(font)
                p.getAxis(l).setTickFont(font)


class ODMRPeaksWidget(QtWidgets.QWidget, Ui_ODMRPeaks):
    def __init__(self, plot, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.setupUi(self)

        self.plot = plot

        peak_cols = ["#FF0000", "#FFA500", "#00CBFF", "#0000FF"]
        self.gs_peak_pairs = []
        for col in peak_cols:
            l0 = self.plot.addLine(x=0, pen=col, movable=False)
            l1 = self.plot.addLine(x=0, pen=col, movable=False)
            self.plot.removeItem(l0)
            self.plot.removeItem(l1)
            self.gs_peak_pairs.append([l0, l1])
        self.es_peak_pairs = []

        self.es_peak_pairs = []
        for col in peak_cols:
            p = pg.mkPen(color=col, style=QtCore.Qt.PenStyle.DashLine)
            l0 = self.plot.addLine(x=0, pen=p, movable=False)
            l1 = self.plot.addLine(x=0, pen=p, movable=False)
            self.plot.removeItem(l0)
            self.plot.removeItem(l1)
            self.es_peak_pairs.append([l0, l1])

        self.init_connections()

    def init_connections(self):
        self.substrate_buttons = QtWidgets.QButtonGroup(parent=self)
        for b in (self.sub100Button, self.sub111Button):
            self.substrate_buttons.addButton(b)
            b.toggled.connect(self.update_peak_positions)
            b.toggled.connect(self.update_B_angle_label)
            b.toggled.connect(self.update_E_angle_label)
        self.substrate_buttons.setExclusive(True)
        self.sub100Button.setChecked(True)
        for b in (
            self.BfieldBox,
            self.BthetaBox,
            self.BphiBox,
            self.EfieldBox,
            self.EthetaBox,
            self.EphiBox,
            self.DgsBox,
            self.DesBox,
            self.gammaBox,
            self.kperpBox,
        ):
            b.valueChanged.connect(self.update_peak_positions)
            b.valueChanged.connect(self.update_B_angle_label)
            b.valueChanged.connect(self.update_E_angle_label)
        self.stepBox.valueChanged.connect(self.update_peak_step)
        self.B111Button.clicked.connect(lambda: self.set_B_directions(1, 1, 1))
        self.B100Button.clicked.connect(lambda: self.set_B_directions(1, 0, 0))
        self.B110Button.clicked.connect(lambda: self.set_B_directions(1, 1, 0))
        self.E111Button.clicked.connect(lambda: self.set_E_directions(1, 1, 1))
        self.E100Button.clicked.connect(lambda: self.set_E_directions(1, 0, 0))
        self.E110Button.clicked.connect(lambda: self.set_E_directions(1, 1, 0))

        self.set_B_directions(1, 1, 1)
        self.set_E_directions(1, 1, 1)

        self.showgsBox.toggled.connect(self.toggle_gs_peaks)
        self.showesBox.toggled.connect(self.toggle_es_peaks)

    def toggle_gs_peaks(self, checked):
        if checked:
            for l0, l1 in self.gs_peak_pairs:
                self.plot.addItem(l0)
                self.plot.addItem(l1)
        else:
            for l0, l1 in self.gs_peak_pairs:
                self.plot.removeItem(l0)
                self.plot.removeItem(l1)

    def toggle_es_peaks(self, checked):
        if checked:
            for l0, l1 in self.es_peak_pairs:
                self.plot.addItem(l0)
                self.plot.addItem(l1)
        else:
            for l0, l1 in self.es_peak_pairs:
                self.plot.removeItem(l0)
                self.plot.removeItem(l1)

    def get_fields(self, unit=False):
        B = self.BfieldBox.value()
        theta_B = np.radians(self.BthetaBox.value())
        phi_B = np.radians(self.BphiBox.value())
        vB = np.array(
            [np.sin(theta_B) * np.cos(phi_B), np.sin(theta_B) * np.sin(phi_B), np.cos(theta_B)]
        )
        if not unit:
            vB = B * vB

        E = self.EfieldBox.value() * 1e-3  # V / um -> V / nm
        theta_E = np.radians(self.EthetaBox.value())
        phi_E = np.radians(self.EphiBox.value())
        vE = np.array(
            [np.sin(theta_E) * np.cos(phi_E), np.sin(theta_E) * np.sin(phi_E), np.cos(theta_E)]
        )
        if not unit:
            vE = E * vE

        if self.sub100Button.isChecked():
            vB = nv.project_from100(vB)
            vE = nv.project_from100(vE)

        return vB, vE

    def get_field_intensities(self) -> tuple[float, float]:
        return self.BfieldBox.value(), self.EfieldBox.value() * 1e-3

    def update_peak_positions(self):
        Dgs = self.DgsBox.value()
        Des = self.DesBox.value()
        gamma_e = self.gammaBox.value()
        k_perp = self.kperpBox.value()  # kHz um / V = MHz nm / V

        B, E = self.get_fields()

        # Ground state
        freq = nv.peaks_of_BE(B, E, D=Dgs, gamma=gamma_e, k_perp=k_perp)
        for i in range(4):
            l0, l1 = self.gs_peak_pairs[i]
            l0.setValue(freq[i * 2] * 1e6)
            l1.setValue(freq[i * 2 + 1] * 1e6)

        f_str = set([f"{f:.1f}" for f in sorted(freq)])
        txt = ", ".join(sorted(f_str))
        self.gsEdit.setText(txt + " MHz")

        # Excited state
        freq = nv.peaks_of_B_es(B, D=Des, gamma=gamma_e)
        for i in range(4):
            l0, l1 = self.es_peak_pairs[i]
            l0.setValue(freq[i * 2] * 1e6)
            l1.setValue(freq[i * 2 + 1] * 1e6)

        f_str = set([f"{f:.1f}" for f in sorted(freq)])
        txt = ", ".join(sorted(f_str))
        self.esEdit.setText(txt + " MHz")

    def update_B_angle_label(self):
        vec_nv = nv.projector.AXIS
        vB, _ = self.get_fields(unit=True)
        B, _ = self.get_field_intensities()

        angles = np.degrees([np.arccos(np.dot(v, vB)) for v in vec_nv])
        min_angle = abs(angles[np.argmin(angles**2)])
        txt = "angle to <111>: {:.2f} degree".format(min_angle)
        self.BangleLabel.setText(txt)

        angle_rad = np.radians(min_angle)
        txtB = "B//: {:.3f} mT, B⊥: {:.3f} mT".format(B * np.cos(angle_rad), B * np.sin(angle_rad))
        self.BfieldLabel.setText(txtB)

    def update_E_angle_label(self):
        vec_nv = nv.projector.AXIS
        _, vE = self.get_fields(unit=True)
        _, E = self.get_field_intensities()

        angles = np.degrees([np.arccos(np.dot(v, vE)) for v in vec_nv])
        min_angle = abs(angles[np.argmin(angles**2)])
        txt = "angle to <111>: {:.2f} degree".format(min_angle)
        self.EangleLabel.setText(txt)

    def get_direction(self, k, l, m):
        d = np.array([k, l, m])
        d = d / np.linalg.norm(d)
        if self.sub100Button.isChecked():
            return d
        elif self.sub111Button.isChecked():
            # for (1, 1, 1) the small error is seen in phi = atan2(y, x).
            # return exact value to avoid this.
            if (k, l, m) == (1, 1, 1):
                return (0, 0, 1)
            return nv.project_from100(d)

    def set_B_directions(self, k, l, m):
        x, y, z = self.get_direction(k, l, m)

        theta = np.arccos(np.clip(z, -1, 1))
        phi = np.arctan2(y, x)

        self.BthetaBox.setValue(np.degrees(theta))
        self.BphiBox.setValue(np.degrees(phi))

    def set_E_directions(self, k, l, m):
        x, y, z = self.get_direction(k, l, m)

        theta = np.arccos(np.clip(z, -1, 1))
        phi = np.arctan2(y, x)

        self.EthetaBox.setValue(np.degrees(theta))
        self.EphiBox.setValue(np.degrees(phi))

    def update_peak_step(self, value):
        if value <= 0:
            return

        for w in (
            self.BfieldBox,
            self.BthetaBox,
            self.BphiBox,
            self.EfieldBox,
            self.EthetaBox,
            self.EphiBox,
        ):
            w.setSingleStep(value)


class ODMRWidget(ClientWidget, Ui_ODMR):
    """Widget for ODMR."""

    def __init__(
        self,
        gconf: dict,
        name,
        gparams_name,
        confocal_name,
        plot: PlotWidget,
        context,
        parent=None,
    ):
        ClientWidget.__init__(self, parent)
        self.setupUi(self)

        self.conf = local_conf(gconf, name)

        self.plot = plot
        self.data = ODMRData()

        self.cli = QODMRClient(gconf, name, context=context, parent=self)
        self.cli.statusUpdated.connect(self.init_with_status)

        self.gparams_cli = GlobalParamsClient(gconf, gparams_name, context=context)
        if confocal_name:
            self.confocal_cli = ConfocalIORequester(gconf, confocal_name, context=context)
        else:
            self.confocal_cli = None

        self.add_clients(self.cli, self.gparams_cli, self.confocal_cli)

        self._finalizing = False

        self._fiTab_layout = QtWidgets.QVBoxLayout(self.fiTab)
        self.fit = ODMRFitWidget(self.cli, self.gparams_cli, parent=self.fiTab)
        self._fiTab_layout.addWidget(self.fit)

        self._peaksTab_layout = QtWidgets.QVBoxLayout(self.peaksTab)
        self.peaks = ODMRPeaksWidget(self.plot.plot, parent=self.peaksTab)
        self._peaksTab_layout.addWidget(self.peaks)

        self._has_time_window = self._has_gate_delay = True

        self.setEnabled(False)

    def init_with_status(self, status: BinaryStatus):
        """initialize widget after receiving first status."""

        # only once.
        self.cli.statusUpdated.disconnect(self.init_with_status)

        self.init_widgets()
        self.init_connection()
        self.fit.init_with_status()

        self.update_step_label()

        # update initial GUI state
        self.update_state(status.state, last_state=BinaryState.IDLE)
        self.switch_method()

        self.cli.stateUpdated.connect(self.update_state)
        self.cli.dataUpdated.connect(self.update_data)
        self.cli.bufferUpdated.connect(self.update_buffer)
        self.cli.stopped.connect(self.finalize)

        self.setEnabled(True)

    def init_connection(self):
        self.startButton.clicked.connect(self.request_start)
        self.stopButton.clicked.connect(self.request_stop)
        self.saveButton.clicked.connect(self.save_data)
        self.exportButton.clicked.connect(self.export_data)
        self.loadButton.clicked.connect(self.load_data)

        for w in (self.startBox, self.stopBox, self.numBox):
            w.valueChanged.connect(self.update_step_label)

        for b in (
            self.laserdelayBox,
            self.laserwidthBox,
            self.mwdelayBox,
            self.mwwidthBox,
            self.bnumBox,
        ):
            b.valueChanged.connect(self.update_pulse_label)

        self.methodBox.currentIndexChanged.connect(self.switch_method)

    def init_widgets(self):
        self.tabWidget.setCurrentIndex(0)

        labels = self.cli.get_param_dict_labels()
        self.methodBox.clear()
        methods = P.filter_out_label_prefix("fit", labels)
        self.methodBox.addItems(methods)

        if "pulse" in labels:
            params = self.cli.get_param_dict("pulse")
            apply_widgets(
                params["timing"],
                [
                    ("laser_delay", self.laserdelayBox, 1e9),  # s to ns
                    ("laser_width", self.laserwidthBox, 1e9),
                    ("mw_delay", self.mwdelayBox, 1e9),
                    ("mw_width", self.mwwidthBox, 1e9),
                    ("trigger_width", self.triggerwidthBox, 1e9),
                ],
            )

        params = self.cli.get_param_dict("cw")
        self._has_time_window = "time_window" in params["timing"]
        if self._has_time_window:
            apply_widgets(
                params["timing"],
                [
                    ("time_window", self.windowBox, 1e3),
                ],
            )
        else:
            self.windowBox.setEnabled(False)
        self._has_gate_delay = "gate_delay" in params["timing"]
        if self._has_gate_delay:
            apply_widgets(
                params["timing"],
                [
                    ("gate_delay", self.gatedelayBox, 1e3),
                ],
            )
        else:
            self.gatedelayBox.setEnabled(False)

        apply_widgets(
            params,
            [
                ("power", self.powerBox),
                ("num", self.numBox),
                ("start", self.startBox, 1e-6),
                ("stop", self.stopBox, 1e-6),
                ("delay", self.delayBox, 1e3),
                ("background_delay", self.bgdelayBox, 1e3),
            ],
        )

        self.saveconfocalBox.setEnabled(self.confocal_cli is not None)
        self.saveconfocalBox.setChecked(self.confocal_cli is not None)

    def set_method(self, method: str) -> bool:
        i = self.methodBox.findText(method)
        if i >= 0:
            self.methodBox.setCurrentIndex(i)
            return True
        else:
            print(f"[ERROR] unknown method: {method}")
            return False

    def switch_method(self):
        method = self.methodBox.currentText()
        params = self.cli.get_param_dict(method)
        ps = P.ParamDict()
        if params.get("pd"):
            ps["pd"] = params["pd"]
        if params.get("mod"):
            ps["mod"] = params["mod"]
        self.paramTable.update_contents(ps)

    def update_step_label(self):
        self.stepLabel.setText(
            "step: {:.4f} MHz".format(
                conv.num_to_step(self.startBox.value(), self.stopBox.value(), self.numBox.value())
            )
        )

    def update_pulse_label(self):
        window = self.get_pulse_window()
        if not window:
            return  # avoid zero div

        tot = pg.siFormat(window * self.bnumBox.value(), suffix="s")
        single = pg.siFormat(window, suffix="s")
        rate = pg.siFormat(1.0 / window, suffix="Hz")
        self.pulseLabel.setText(f"total window: {tot} single window: {single} (rate: {rate})")

    def get_pulse_window(self):
        boxes = (self.laserdelayBox, self.laserwidthBox, self.mwdelayBox, self.mwwidthBox)
        return sum([b.value() for b in boxes]) * 1e-9

    def apply_widgets(self, data: ODMRData):
        start, stop = data.bounds()
        self.startBox.setValue(start * 1e-6)
        self.stopBox.setValue(stop * 1e-6)
        self.numBox.setValue(data.params["num"])
        self.powerBox.setValue(data.params["power"])
        bg = data.params.get("background", False)
        self.backgroundBox.setChecked(bg)
        if "sweeps" in data.params:
            self.sweepsBox.setValue(data.params["sweeps"])
        if "delay" in data.params:
            self.delayBox.setValue(data.params["delay"] * 1e3)
        if bg and "background_delay" in data.params:
            self.bgdelayBox.setValue(data.params["background_delay"] * 1e3)

        if not self.set_method(data.label):
            return

        ps = {}
        if data.params.get("pd"):
            ps["pd"] = data.params["pd"]
        if data.params.get("mod"):
            ps["mod"] = data.params["mod"]
        for k, v in P.flatten(ps).items():
            self.paramTable.apply_value(k, v)

        timing = data.params["timing"]
        if data.label != "pulse":
            if "time_window" in timing:
                self.windowBox.setValue(timing["time_window"] * 1e3)
            if "gate_delay" in timing:
                self.gatedelayBox.setValue(timing["gate_delay"] * 1e3)
        else:
            self.laserdelayBox.setValue(timing["laser_delay"] * 1e9)
            self.laserwidthBox.setValue(timing["laser_width"] * 1e9)
            self.mwdelayBox.setValue(timing["mw_delay"] * 1e9)
            self.mwwidthBox.setValue(timing["mw_width"] * 1e9)
            self.triggerwidthBox.setValue(timing["trigger_width"] * 1e9)
            self.bnumBox.setValue(timing["burst_num"])

    def save_data(self):
        default_path = str(self.gparams_cli.get_param("work_dir"))
        fn = save_dialog(self, default_path, "ODMR", ".odmr")
        if not fn:
            return

        self.gparams_cli.set_param("work_dir", os.path.split(fn)[0])
        note = self.gparams_cli.get_param("note", "")
        self.cli.save_data(fn, note=note)
        n = os.path.splitext(fn)[0] + ".png"
        params = {}
        params["normalize_n"] = self.plot.normalizenBox.value()
        params["complex_conv"] = self.plot.complexBox.currentText()
        params["show_std"] = self.plot.showstdBox.isChecked()
        self.cli.export_data(n, params=params)

        if self.confocal_cli is not None and self.saveconfocalBox.isChecked():
            n = os.path.splitext(fn)[0] + ".pos.png"
            self.confocal_cli.export_view(n)

    def load_data(self):
        default_path = str(self.gparams_cli.get_param("work_dir"))
        fn = load_dialog(self, default_path, "ODMR", ".odmr")
        if not fn:
            return

        self.gparams_cli.set_param("work_dir", os.path.split(fn)[0])
        data = self.cli.load_data(fn)
        if data is None:
            return
        if data.note():
            self.gparams_cli.set_param("loaded_note", data.note())

        self.refresh_all()
        self.apply_widgets(data)

    def export_data(self):
        data_list = self.get_plottable_data()
        if not data_list:
            return

        default_path = str(self.gparams_cli.get_param("work_dir"))
        fn = export_dialog(self, default_path, "ODMR", (".png", ".pdf", ".eps", ".txt"))
        if not fn:
            return

        data = [d for (d, _, _) in data_list]
        params = {}
        params["color"] = params["color_fit"] = [c.color for (_, _, c) in data_list]
        params["color_bg"] = [c.color_bg for (_, _, c) in data_list]
        params["normalize_n"] = self.plot.normalizenBox.value()
        params["complex_conv"] = self.plot.complexBox.currentText()
        params["show_std"] = self.plot.showstdBox.isChecked()
        self.cli.export_data(fn, data=data, params=params)

    # State managements
    def request_stop(self):
        self.cli.stop()

    def get_params(self):
        params = {}
        params["start"] = self.startBox.value() * 1e6  # MHz to Hz
        params["stop"] = self.stopBox.value() * 1e6
        params["num"] = self.numBox.value()
        params["power"] = self.powerBox.value()
        params["sweeps"] = self.sweepsBox.value()
        params["background"] = self.backgroundBox.isChecked()
        params["delay"] = self.delayBox.value() * 1e-3  # ms to s
        params["background_delay"] = self.bgdelayBox.value() * 1e-3  # ms to s

        label = self.methodBox.currentText()
        if label != "pulse":
            t = {}
            if self._has_time_window:
                t["time_window"] = self.windowBox.value() * 1e-3  # ms to s
            if self._has_gate_delay:
                t["gate_delay"] = self.gatedelayBox.value() * 1e-3  # ms to s
        else:
            t = {}
            t["laser_delay"] = self.laserdelayBox.value() * 1e-9  # ns to s
            t["laser_width"] = self.laserwidthBox.value() * 1e-9
            t["mw_delay"] = self.mwdelayBox.value() * 1e-9
            t["mw_width"] = self.mwwidthBox.value() * 1e-9
            t["trigger_width"] = self.triggerwidthBox.value() * 1e-9
            t["burst_num"] = self.bnumBox.value()
        params["timing"] = t
        params["continue_mw"] = self.mwcontBox.isChecked()

        params.update(P.unwrap(self.paramTable.params()))

        return params, label

    def request_start(self):
        if self.cli.validate(*self.get_params()):
            self.start_sweep()

    def start_sweep(self):
        params, label = self.get_params()

        title = "Continue sweep?"
        body = (
            "Continue sweep with current data?"
            + " Press No to clear current data and start a new sweep."
        )
        if self.data.can_resume(params, label) and Qt.question_yn(self, title, body):
            params["resume"] = True
            params["ident"] = self.data.ident
        else:
            params["resume"] = False
            params["ident"] = uuid.uuid4()

        self.cli.start(params, label)

    def update_data(self, data: ODMRData):
        self.data = data
        self.refresh_all()

    def update_buffer(self, buffer: Buffer[tuple[str, ODMRData]]):
        self.fit.update_buffer(buffer)
        self.plot.refresh_plot(self.get_plottable_data())

    def refresh_all(self):
        self.plot.refresh_all(self.get_plottable_data(), self.data)

    def get_plottable_data(self) -> list[tuple[ODMRData, bool, Colors]]:
        return self.fit.get_plottable_data(self.data)

    def finalize(self, data: ODMRData):
        if self._finalizing:
            return
        self._finalizing = True
        # Auto save is temporarily disabled.
        self._finalizing = False

    def update_state(self, state: BinaryState, last_state: BinaryState):
        is_IDLE = state == BinaryState.IDLE
        for w in (
            self.startButton,
            self.saveButton,
            self.exportButton,
            self.loadButton,
            self.mwcontBox,
            self.startBox,
            self.stopBox,
            self.numBox,
            self.powerBox,
            self.sweepsBox,
            self.backgroundBox,
            self.delayBox,
            self.methodBox,
            self.paramTable,
        ):
            w.setEnabled(is_IDLE)

        self.bgdelayBox.setEnabled(is_IDLE and self.backgroundBox.isChecked())

        is_pulse = self.methodBox.currentText() == "pulse"
        self.windowBox.setEnabled(is_IDLE and self._has_time_window and not is_pulse)
        self.gatedelayBox.setEnabled(is_IDLE and self._has_gate_delay and not is_pulse)

        for w in (
            self.laserdelayBox,
            self.laserwidthBox,
            self.mwdelayBox,
            self.mwwidthBox,
            self.triggerwidthBox,
            self.bnumBox,
        ):
            w.setEnabled(is_IDLE and is_pulse)

        self.stopButton.setEnabled(state == BinaryState.ACTIVE)


class ODMRMainWindow(QtWidgets.QMainWindow):
    """MainWindow with ODMRWidget and PlotWidget."""

    def __init__(self, gconf: dict, name, context, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)

        lconf = local_conf(gconf, name)
        target = lconf["target"]

        self.plot = PlotWidget(parent=self)
        self.odmr = ODMRWidget(
            gconf,
            target["odmr"],
            target["gparams"],
            target.get("confocal"),
            self.plot,
            context,
            parent=self,
        )

        self.setWindowTitle(f"MAHOS.ODMRGUI ({join_name(target['odmr'])})")
        self.setAnimated(False)
        self.setCentralWidget(self.odmr)
        self.d_plot = QtWidgets.QDockWidget("Plot", parent=self)
        self.d_plot.setWidget(self.plot)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.d_plot)

        self.view_menu = self.menuBar().addMenu("View")
        self.view_menu.addAction(self.d_plot.toggleViewAction())

    def closeEvent(self, event):
        """Close the clients on closeEvent."""

        self.odmr.close_clients()
        # self.plot.close_clients()
        QtWidgets.QMainWindow.closeEvent(self, event)


class ODMRGUI(GUINode):
    """GUINode for ODMR using ODMRWidget."""

    def init_widget(self, gconf: dict, name, context):
        return ODMRMainWindow(gconf, name, context)
