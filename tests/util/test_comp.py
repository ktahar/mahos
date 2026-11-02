#!/usr/bin/env python3

"""
Tests for mahos.util.comp.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import numpy as np
import pytest

from mahos.util.comp import dict_isclose, dict_isclose_inspect


@pytest.mark.parametrize("compare", [dict_isclose, dict_isclose_inspect])
@pytest.mark.parametrize("wrap", [lambda v: {"nested": v}, lambda v: {"items": [{"nested": v}]}])
@pytest.mark.parametrize("array", [False, True])
def test_nested_tolerances(compare, wrap, array):
    left, right = (np.array([1.0]), np.array([1.01])) if array else (1.0, 1.01)
    assert compare(wrap(left), wrap(right), rtol=0.02, atol=0.0)
    assert compare(wrap(left), wrap(right), rtol=0.0, atol=0.02)
    assert not compare(wrap(left), wrap(right), rtol=0.0, atol=0.0)
    # Custom strict tolerances must also override the defaults at every depth.
    assert not compare(wrap(1.0), wrap(1.0 + 1e-7), rtol=0.0, atol=0.0)


def test_inspect_reports_all_paths(capsys):
    left = {"nested": {"a": 1, "b": 2}, "items": [0, 1], "left": None}
    right = {"nested": {"a": 3, "b": 4}, "items": [2, 3, 4], "right": None}
    assert not dict_isclose_inspect(left, right)
    out = capsys.readouterr().out
    assert "dict['nested']['a']: 1 != 3" in out
    assert "dict['nested']['b']: 2 != 4" in out
    assert "dict['items']: list or tuple size mismatch" in out
    assert "dict['items'][0]: 0 != 2" in out
    assert "dict['items'][1]: 1 != 3" in out
    assert "dict['left']: missing from second dict" in out
    assert "dict['right']: missing from first dict" in out


@pytest.mark.parametrize(
    "left,right,message",
    [
        (1, 1.0, "type mismatch"),
        (np.zeros(2), np.zeros(3), "array shape / dtype mismatch"),
        (np.zeros(2), np.zeros(2, dtype=int), "array shape / dtype mismatch"),
        (np.array([1.0]), np.array([2.0]), "float arrays are not allclose"),
        (np.array([1]), np.array([2]), "non-float arrays are not all equal"),
        (float("nan"), float("nan"), "float values are not close"),
    ],
)
def test_inspect_mismatches(left, right, message, capsys):
    assert not dict_isclose_inspect({"value": left}, {"value": right})
    assert f"dict['value']: {message}" in capsys.readouterr().out


def test_inspect_equal_is_silent(capsys):
    values = {"array": np.array([1.0]), "items": [{"x": None}, "a", True]}
    assert dict_isclose_inspect(values, values)
    assert dict_isclose_inspect({}, {})
    assert capsys.readouterr().out == ""


def test_inspect_custom_path(capsys):
    assert not dict_isclose_inspect({"items": [1]}, {"items": [0]}, path="params.fit")
    assert capsys.readouterr().out == "params.fit['items'][0]: 1 != 0\n"
