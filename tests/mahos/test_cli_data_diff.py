#!/usr/bin/env python3

"""
Tests for mahos.cli.data_diff.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import h5py
import pytest

from mahos.cli import data
from mahos.cli.data_diff import build_parser, main
from mahos.msgs.camera_msgs import Image


def write_data(tmp_path, name, **attrs):
    filename = tmp_path / f"{name}.camera.h5"
    image = Image()
    for key, value in attrs.items():
        setattr(image, key, value)
    with h5py.File(filename, "w") as f:
        image.to_h5(f)
    return str(filename)


def test_parser_key_and_file_count():
    parser = build_parser()
    args = parser.parse_args(["-k", "fit_params", "a.camera.h5", "b.camera.h5"])
    assert args.key == "fit_params"
    assert args.names == ["a.camera.h5", "b.camera.h5"]
    assert parser.parse_args(args.names).key == "params"
    for args in (["a"], ["a", "b", "c"], ["a", "b", "-k"]):
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(args)
        assert exc.value.code == 2


def test_diff_status_and_tolerances(tmp_path, capsys):
    first = write_data(tmp_path, "first", params={"nested": {"x": 1.0}})
    second = write_data(tmp_path, "second", params={"nested": {"x": 1.01}})
    assert data.main(["d", first, second]) == 1
    out = capsys.readouterr().out
    assert out.startswith("params['nested']['x']:")
    assert len(out.splitlines()) == 1
    assert main([first, second, "--rtol", "0.02", "--atol", "0"]) == 0
    assert capsys.readouterr().out == ""
    assert main([first, second, "--rtol", "0", "--atol", "0.02"]) == 0
    assert capsys.readouterr().out == ""


def test_dotted_path(tmp_path, capsys):
    first = write_data(tmp_path, "first", fit_params={"fit": {"x": 1}, "ignored": 1})
    second = write_data(tmp_path, "second", fit_params={"fit": {"x": 1}, "ignored": 2})
    assert main(["-k", "fit_params.fit", first, second]) == 0
    assert capsys.readouterr().out == ""
    assert main([first, second, "-k", "fit_params"]) == 1
    assert "fit_params['ignored']" in capsys.readouterr().out
    third = write_data(tmp_path, "third", fit_params={"fit": {"x": 2}})
    assert main([first, third, "-k", "fit_params.fit"]) == 1
    assert "fit_params.fit['x']: 1 != 2" in capsys.readouterr().out


@pytest.mark.parametrize(
    "attrs,key,message",
    [
        ({}, "params", "attribute 'params' does not exist"),
        ({"params": 1}, "params", "'params' must be a dict, got int"),
        ({"params": {}}, "params.missing", "dictionary path 'params.missing' does not exist"),
        ({"params": {"x": 1}}, "params.x.y", "'params.x' must be a dict, got int"),
        ({"params": {"x": None}}, "params.x", "'params.x' must be a dict, got NoneType"),
    ],
)
@pytest.mark.parametrize("bad_side", [0, 1])
def test_attribute_errors(tmp_path, capsys, attrs, key, message, bad_side):
    valid = write_data(tmp_path, "valid", params={"x": {"y": {}}, "missing": {}})
    invalid = write_data(tmp_path, "invalid", **attrs)
    names = [valid, valid]
    names[bad_side] = invalid
    assert main([*names, "-k", key]) == 2
    captured = capsys.readouterr()
    assert invalid in captured.err
    assert message in captured.err
    assert captured.out == ""


@pytest.mark.parametrize(
    "name", ["missing.camera.h5", "unknown.h5", "data.tweak.h5", "data.ptweak.h5"]
)
def test_file_errors(tmp_path, capsys, name):
    filename = str(tmp_path / name)
    assert main([filename, filename]) == 2
    assert filename in capsys.readouterr().err


def test_corrupt_file(tmp_path, capsys):
    filename = tmp_path / "broken.camera.h5"
    filename.write_text("invalid HDF5")
    assert main([str(filename), str(filename)]) == 2
    assert str(filename) in capsys.readouterr().err


@pytest.mark.parametrize("option", ["--rtol", "--atol"])
@pytest.mark.parametrize("value", ["-1", "nan", "inf"])
def test_invalid_tolerances(option, value, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["first.camera.h5", "second.camera.h5", option, value])
    assert exc.value.code == 2
    assert "non-negative finite float" in capsys.readouterr().err
