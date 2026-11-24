#!/usr/bin/env python3

"""
Tests for mahos.util.image.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import csv
import os

import numpy as np
import pytest
from matplotlib.figure import Figure

from mahos.util.image import apply_binning, plot_image, plot_map, save_image, save_map


def test_save_map_format(tmp_path):
    fn = tmp_path / "map.txt"
    x = np.array([0.0, 0.5, 1.0])
    y = np.array([0.0, 2.0])
    image = np.array([[1.0, np.nan, 3.0], [4.0, 5.0, 6.0]])

    save_map(str(fn), x, y, image, xlabel="x", ylabel="z", clabel="I")

    expected = os.linesep.join(
        ["z\\I/x,0.0,0.5,1.0", "0.0,1.0,,3.0", "2.0,4.0,5.0,6.0", ""]
    ).encode()
    assert fn.read_bytes() == expected


@pytest.mark.parametrize(
    "image, expected",
    [
        (np.array([[1, 2], [3, 4]]).view(np.matrix), [["0", "1", "2"], ["1", "3", "4"]]),
        (
            np.ma.array([[1.0, 2.0], [np.nan, 4.0]], mask=[[False, True], [False, False]]),
            [["0", "1.0", ""], ["1", "", "4.0"]],
        ),
    ],
)
def test_save_map_array_subclasses(tmp_path, image, expected):
    fn = tmp_path / "map.csv"
    save_map(str(fn), [0, 1], [0, 1], image)
    with fn.open(encoding="utf-8", newline="") as f:
        assert list(csv.reader(f)) == [["y\\I/x", "0", "1"], *expected]


def test_map_shape_mismatch(tmp_path):
    x = np.arange(3.0)
    y = np.arange(2.0)
    with pytest.raises(ValueError):
        save_map(str(tmp_path / "map.txt"), x, y, np.zeros((3, 2)))
    with pytest.raises(ValueError):
        plot_map(None, x, y, np.zeros((3, 2)))


def test_save_map_quotes_header(tmp_path):
    fn = tmp_path / "map.csv"
    label = 'I, "normalized"\r\nmean'
    save_map(str(fn), [0, 1], [2], [[3, 4]], clabel=label)
    with fn.open(encoding="utf-8", newline="") as f:
        assert list(csv.reader(f)) == [[f"y\\{label}/x", "0", "1"], ["2", "3", "4"]]


@pytest.mark.parametrize(
    "plot, args", [(plot_map, ([0, 1], [0, 1], [[1, 2], [3, 4]])), (plot_image, ([[1]],))]
)
@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("explicit_figure", [False, True])
def test_plot_uses_figure_owning_axes(tmp_path, plot, args, nested, explicit_figure):
    fig = Figure()
    owner = fig.subfigures(1, 1).subfigures(1, 1) if nested else fig
    ax = owner.add_subplot()
    fn = tmp_path / "plot.png"
    assert plot(str(fn), *args, fig=fig if explicit_figure else None, ax=ax) is fig
    assert fn.stat().st_size > 0
    assert len(ax.collections) == 1
    assert len(fig.axes) == 2  # image and colorbar

    with pytest.raises(ValueError, match="fig must own the supplied axes"):
        plot(None, *args, fig=Figure(), ax=ax)


def test_apply_binning():
    data = np.arange(16.0).reshape(4, 4)
    np.testing.assert_allclose(apply_binning(data, 2), [[2.5, 4.5], [10.5, 12.5]])
    np.testing.assert_allclose(apply_binning(data, 1), data)
    with pytest.raises(ValueError):
        apply_binning(data, 3)
    with pytest.raises(ValueError):
        apply_binning(data, 0)
