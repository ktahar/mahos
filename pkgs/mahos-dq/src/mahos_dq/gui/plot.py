"""Shared plot formatting routines.

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


def update_cursor_label(
    pos: QtCore.QPointF,
    plot: pg.PlotItem,
    label: QtWidgets.QLabel,
    *,
    xunit: str | None = None,
    yunit: str | None = None,
    xsi: bool = True,
    ysi: bool = True,
) -> None:
    """Update a cursor label when the scene position is inside the plot.

    Map the position to view coordinates and format each value using its axis scale
    and unit. Optional ``xunit`` and ``yunit`` override the respective axis units.
    Set ``xsi=False`` or ``ysi=False`` to disable SI prefix scaling on that axis.

    """

    if not plot.sceneBoundingRect().contains(pos):
        return
    point = plot.getViewBox().mapSceneToView(pos)
    sx = format_axis_value(point.x(), plot.getAxis("bottom"), unit=xunit, si=xsi)
    sy = format_axis_value(point.y(), plot.getAxis("left"), unit=yunit, si=ysi)
    label.setText(f"{sx}, {sy}")
