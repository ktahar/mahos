#!/usr/bin/env python3

"""
Tests for mahos.util.image.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import os

import numpy as np
import pytest

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


def test_map_shape_mismatch(tmp_path):
    x = np.arange(3.0)
    y = np.arange(2.0)
    with pytest.raises(ValueError):
        save_map(str(tmp_path / "map.txt"), x, y, np.zeros((3, 2)))
    with pytest.raises(ValueError):
        plot_map(None, x, y, np.zeros((3, 2)))


def test_apply_binning():
    data = np.arange(16.0).reshape(4, 4)
    np.testing.assert_allclose(apply_binning(data, 2), [[2.5, 4.5], [10.5, 12.5]])
    np.testing.assert_allclose(apply_binning(data, 1), data)
    with pytest.raises(ValueError):
        apply_binning(data, 3)
    with pytest.raises(ValueError):
        apply_binning(data, 0)
