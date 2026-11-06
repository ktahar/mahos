"""Shared plot formatting and crosshair routines.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import pyqtgraph as pg

from mahos.gui.Qt import QtCore, QtWidgets


def format_axis_value(
    value: float, axis: pg.AxisItem, *, unit: str | None = None, si: bool = True
) -> str:
    """Format a plot coordinate using the axis scale and unit.

    Convert logarithmic view coordinates back to linear values before formatting.
    Use the axis unit unless ``unit`` is provided; an empty string selects unitless
    formatting with six decimal places. Set ``si=False`` to use six decimal places
    with the unit appended verbatim, without SI prefix scaling.

    """

    if axis.logMode:
        value = 10.0**value
    if unit is None:
        unit = axis.labelUnits
    if unit and si:
        return pg.siFormat(value, precision=6, suffix=unit)
    return f"{value:.6f}" + (f" {unit}" if unit else "")


def update_cursor(
    pos: QtCore.QPointF,
    plot: pg.PlotItem,
    label: QtWidgets.QLabel,
    lines: tuple[pg.InfiniteLine, pg.InfiniteLine],
    *,
    xunit: str | None = None,
    yunit: str | None = None,
    xsi: bool = True,
    ysi: bool = True,
) -> None:
    """Update the cursor label and visible crosshair inside the plot's view box.

    Map the position to view coordinates and format each value using its axis scale
    and unit. Optional ``xunit`` and ``yunit`` override the respective axis units.
    Set ``xsi=False`` or ``ysi=False`` to disable SI prefix scaling on that axis.

    """

    view = plot.getViewBox()
    if not view.sceneBoundingRect().contains(pos):
        return
    point = view.mapSceneToView(pos)
    sx = format_axis_value(point.x(), plot.getAxis("bottom"), unit=xunit, si=xsi)
    sy = format_axis_value(point.y(), plot.getAxis("left"), unit=yunit, si=ysi)
    label.setText(f"{sx}, {sy}")
    if lines[0].isVisible():
        lines[0].setPos(point.x())
        lines[1].setPos(point.y())


def create_crosshair(plot: pg.PlotItem) -> tuple[pg.InfiniteLine, pg.InfiniteLine]:
    """Add hidden crosshair lines without affecting the plot's autorange."""

    lines = (pg.InfiniteLine(angle=90, movable=False), pg.InfiniteLine(angle=0, movable=False))
    for line in lines:
        line.setVisible(False)
        line.setZValue(20)
        plot.addItem(line, ignoreBounds=True)
    return lines


def set_crosshair_visible(
    plot: pg.PlotItem,
    lines: tuple[pg.InfiniteLine, pg.InfiniteLine],
    visible: bool,
    *,
    center: bool = False,
) -> None:
    """Show or hide the crosshair, optionally centering it in the current view."""

    if visible and center:
        for line, (lower, upper) in zip(lines, plot.getViewBox().viewRange()):
            line.setPos((lower + upper) / 2)
    for line in lines:
        line.setVisible(visible)
