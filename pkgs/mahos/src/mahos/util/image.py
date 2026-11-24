#!/usr/bin/env python3

"""
Plot / conversion functions for 2D image data.

All functions take 2D data in row-major order with shape (H, W), i.e., ``image[i, j]`` is
the value of the pixel at row ``i`` and column ``j``.

- :func:`plot_map`: map with physical coordinates. Pixel centers are given by ``x`` and ``y``
  (e.g., a confocal scan in um). The y-axis points up by default.
- :func:`plot_map_only`: same as :func:`plot_map`, but saves the colored map alone
  (no axes, labels, or colorbar).
- :func:`save_map`: save the same ``(x, y, image)`` data as a text table.
- :func:`plot_image`: image without spatial unit (e.g., camera frame). Axes are pixel indices,
  and the origin is at the top-left (row 0 at the top).
- :func:`apply_binning`: average 2D data over square blocks.

``save_image()`` is a deprecated alias for :func:`plot_image`.

:func:`plot_map` and :func:`plot_image` share the figure handling
(``fig``, ``ax``, ``figsize``, ``fontsize``, ``dpi``, and ``tight``) and the color mapping
(``cmap``, ``vmin``, and ``vmax``), and both draw a colorbar.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import csv
import os
import warnings
from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray
import matplotlib as mpl
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import mahos.util.validation as V


def _as_array(data: ArrayLike) -> NDArray:
    """Convert to an array while preserving any mask."""

    return np.ma.asarray(data) if np.ma.isMaskedArray(data) else np.asarray(data)


def _check_map(x: ArrayLike, y: ArrayLike, image: ArrayLike) -> tuple[NDArray, NDArray, NDArray]:
    """Convert map inputs to arrays and check that ``image`` has shape (len(y), len(x))."""

    x = _as_array(x)
    y = _as_array(y)
    image = _as_array(image)
    if x.ndim != 1 or y.ndim != 1:
        raise ValueError(f"x and y must be 1D arrays. Given shapes: {x.shape}, {y.shape}")
    if image.shape != (len(y), len(x)):
        raise ValueError(
            f"image shape must be (len(y), len(x)) = {(len(y), len(x))}. Given: {image.shape}"
        )
    return x, y, image


def _prepare_figure(
    fig: Figure | None,
    ax: Axes | None,
    figsize: tuple[float, float],
    tight: bool,
    use_pyplot: bool = False,
) -> tuple[Figure, Axes]:
    """Create or adopt (fig, ax) for :func:`plot_map` and :func:`plot_image`.

    If ``tight`` is True, a newly created figure uses the constrained layout.
    An existing figure gets the tight layout engine only if it has no layout engine.
    A new figure is created via ``matplotlib.pyplot`` only if ``use_pyplot`` is True.

    """

    if ax is not None:
        owner = ax.get_figure(root=True)
        if fig is not None and fig is not owner:
            raise ValueError("fig must own the supplied axes.")
        fig = owner
    if fig is None:
        layout = "constrained" if tight else None
        if use_pyplot:
            import matplotlib.pyplot as plt

            fig = plt.figure(figsize=figsize, layout=layout)
        else:
            fig = Figure(figsize=figsize, layout=layout)
    elif tight and fig.get_layout_engine() is None:
        fig.set_layout_engine("tight")
    if ax is None:
        ax = fig.add_subplot(111)
    return fig, ax


def _draw_map(ax: Axes, x, y, image, vmin, vmax, invX, invY, aspect, cmap, plot_pos, pos_color):
    """Draw a pseudo-color map on ``ax`` and return the QuadMesh."""

    ax.set_aspect(aspect)
    mesh = ax.pcolormesh(x, y, image, cmap=cmap, vmin=vmin, vmax=vmax)
    xmin, xmax = np.min(x), np.max(x)
    ymin, ymax = np.min(y), np.max(y)
    if invX:
        ax.set_xlim(xmax, xmin)
    else:
        ax.set_xlim(xmin, xmax)
    if invY:
        ax.set_ylim(ymax, ymin)
    else:
        ax.set_ylim(ymin, ymax)

    if plot_pos is not None:
        px, py = plot_pos
        ax.plot(px, py, color=pos_color, marker="x", markeredgewidth=1.0, markersize=8)
    return mesh


def plot_map(
    fn: str | None,
    x: ArrayLike,
    y: ArrayLike,
    image: ArrayLike,
    fig: Figure | None = None,
    ax: Axes | None = None,
    xlabel: str = "",
    ylabel: str = "",
    clabel: str = "",
    vmin: float | None = None,
    vmax: float | None = None,
    invX: bool = False,
    invY: bool = False,
    aspect: str | float = "auto",
    figsize: tuple[float, float] = (8, 6),
    fontsize: float | None = None,
    dpi: float | None = None,
    cmap: str = "inferno",
    plot_pos: tuple[float, float] | None = None,
    pos_color: str = "#2bb32b",
    tight: bool = True,
) -> Figure:
    """Plot 2D map data with physical coordinates as a pseudo-color image with a colorbar.

    Axes are the given ``x`` and ``y`` coordinates, with limits at the outermost pixel centers.
    The y-axis points up unless ``invY`` is True.
    Use :func:`plot_image` instead for data without spatial unit.

    If ``tight`` is True, a newly created figure uses the constrained layout.
    An existing figure gets the tight layout engine only if it has no layout engine.

    :param fn: file name to save the figure. None to draw without saving.
    :param x: x values (pixel centers) with shape (W,).
    :param y: y values (pixel centers) with shape (H,).
    :param image: map values with shape (H, W), i.e., ``image[i, j]`` is at ``(x[j], y[i])``.
    :param fig: figure to draw on. Defaults to the top-level figure of ``ax`` or a new figure.
    :param ax: axes to draw on. A new subplot of ``fig`` is created if None.
    :param clabel: colorbar label.
    :param plot_pos: position (x, y) to mark with a cross.
    :returns: the figure drawn on.
    :raises ValueError: input shapes are inconsistent or ``fig`` does not own ``ax``.

    """

    x, y, image = _check_map(x, y, image)
    with mpl.rc_context({"font.size": fontsize} if fontsize else None):
        fig, ax = _prepare_figure(fig, ax, figsize, tight)
        ax.tick_params(axis="both", direction="out")
        mesh = _draw_map(
            ax, x, y, image, vmin, vmax, invX, invY, aspect, cmap, plot_pos, pos_color
        )
        cbar = fig.colorbar(mesh, ax=ax)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        cbar.set_label(clabel)

        if fn is not None:
            fig.savefig(fn, dpi=dpi)
    return fig


def plot_map_only(
    fn: str,
    x: ArrayLike,
    y: ArrayLike,
    image: ArrayLike,
    vmin: float | None = None,
    vmax: float | None = None,
    invX: bool = False,
    invY: bool = False,
    aspect: str | float = "auto",
    figsize: tuple[float, float] = (8, 6),
    dpi: float | None = None,
    cmap: str = "inferno",
    plot_pos: tuple[float, float] | None = None,
    pos_color: str = "#2bb32b",
):
    """Save 2D map data as a pseudo-color image only (no axes, colorbar, labels, etc.).

    The parameters are the same as :func:`plot_map`.

    :raises ValueError: shapes of ``x``, ``y``, and ``image`` are inconsistent.

    """

    x, y, image = _check_map(x, y, image)
    fig = Figure(figsize=figsize, frameon=False)
    ax = Axes(fig, [0.0, 0.0, 1.0, 1.0])
    fig.add_axes(ax)
    ax.set_axis_off()
    _draw_map(ax, x, y, image, vmin, vmax, invX, invY, aspect, cmap, plot_pos, pos_color)
    fig.savefig(fn, dpi=dpi)


def save_map(
    fn: str,
    x: ArrayLike,
    y: ArrayLike,
    image: ArrayLike,
    xlabel: str = "x",
    ylabel: str = "y",
    clabel: str = "I",
    delimiter: str = ",",
):
    """Save 2D map data as a text table.

    The first row is a header: a corner label ``ylabel\\clabel/xlabel`` followed by x values.
    Each following row is a y value followed by the image values at that y.
    NaN values are written as empty cells.
    Lines end with ``os.linesep`` to keep the format written by the former pandas implementation.

    :param x: x values with shape (W,).
    :param y: y values with shape (H,).
    :param image: map values with shape (H, W), i.e., ``image[i, j]`` is at ``(x[j], y[i])``.
    :raises ValueError: shapes of ``x``, ``y``, and ``image`` are inconsistent.

    """

    x, y, image = _check_map(x, y, image)
    is_float = np.issubdtype(image.dtype, np.floating)
    with open(fn, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=delimiter, lineterminator=os.linesep)
        writer.writerow([f"{ylabel}\\{clabel}/{xlabel}", *x.astype(str).tolist()])
        for yv, row in zip(y.astype(str), image):
            cells = row.astype(str)
            if is_float:
                cells[np.isnan(row)] = ""
            writer.writerow([yv, *cells.tolist()])


def plot_image(
    fn: str | None,
    image: ArrayLike,
    fig: Figure | None = None,
    ax: Axes | None = None,
    xlabel: str = "",
    ylabel: str = "",
    title: str = "",
    aspect: str | float = "equal",
    figsize: tuple[float, float] = (8, 6),
    vmin: float | None = None,
    vmax: float | None = None,
    cmap: str = "inferno",
    patches: Sequence[Patch] = (),
    lines: Sequence[Line2D] = (),
    show: bool = False,
    dpi: float | None = None,
    fontsize: float | None = None,
    tight: bool = True,
) -> Figure:
    """Plot 2D image data without spatial unit (e.g., camera frame) as a pseudo-color image.

    Axes are pixel indices: pixel ``image[i, j]`` covers ``[j, j + 1]`` horizontally and
    ``[i, i + 1]`` vertically, and the origin is at the top-left (row 0 at the top).
    The limits cover the whole pixels.
    Use :func:`plot_map` instead for data with physical coordinates.

    The figure handling and color mapping params are the same as :func:`plot_map`.
    If ``tight`` is True, a newly created figure uses the constrained layout.
    An existing figure gets the tight layout engine only if it has no layout engine.

    :param fn: file name to save the figure. None to draw without saving.
    :param image: image values with shape (H, W).
    :param title: axes title.
    :param patches: matplotlib patches (e.g., ROI rectangle) drawn in pixel coordinates.
    :param lines: matplotlib lines drawn in pixel coordinates.
    :param show: show the figure interactively (this imports ``matplotlib.pyplot``).
    :returns: the figure drawn on.
    :raises ValueError: ``image`` is not 2D or ``fig`` does not own ``ax``.

    """

    image = _as_array(image)
    if image.ndim != 2:
        raise ValueError(f"image must be 2D. Given shape: {image.shape}")
    h, w = image.shape
    with mpl.rc_context({"font.size": fontsize} if fontsize else None):
        fig, ax = _prepare_figure(fig, ax, figsize, tight, use_pyplot=show)
        ax.set_aspect(aspect)
        # pixel centers
        mesh = ax.pcolormesh(
            np.arange(w) + 0.5, np.arange(h) + 0.5, image, cmap=cmap, vmin=vmin, vmax=vmax
        )
        fig.colorbar(mesh, ax=ax)

        ax.set_xlim(0, w)
        ax.set_ylim(h, 0)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)

        for p in patches:
            ax.add_patch(p)
        for l in lines:
            ax.add_line(l)

        if fn is not None:
            fig.savefig(fn, dpi=dpi)
        if show:
            import matplotlib.pyplot as plt

            plt.show()
            plt.close(fig)
    return fig


def save_image(*args, **kwargs):
    """Deprecated alias for :func:`plot_image`."""

    warnings.warn(
        "mahos.util.image.save_image is deprecated; use mahos.util.image.plot_image instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # accept the old param names (mahos <= 0.4.0)
    if "fpath" in kwargs:
        kwargs["fn"] = kwargs.pop("fpath")
    if "img" in kwargs:
        kwargs["image"] = kwargs.pop("img")
    return plot_image(*args, **kwargs)


def apply_binning(data: NDArray, binning: int = 1) -> NDArray:
    """Average 2D data over non-overlapping ``binning`` x ``binning`` blocks.

    :raises ValueError: ``binning`` is not a positive integer or doesn't divide the shape.

    """

    V.check_pos_int(binning, "binning")
    h, w = data.shape
    if h % binning or w % binning:
        raise ValueError(f"data shape {data.shape} is not divisible by binning {binning}")
    return data.reshape(h // binning, binning, w // binning, binning).mean(axis=(1, 3))
