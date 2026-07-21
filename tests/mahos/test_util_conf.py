#!/usr/bin/env python3

"""
Tests for mahos.util.conf.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import pytest

from mahos.util.conf import ConfAccessorMixin, PresetLoader


class DummyLogger:
    def __init__(self):
        self.messages = []

    def warn(self, msg):
        self.messages.append(("warn", msg))

    def info(self, msg):
        self.messages.append(("info", msg))

    def debug(self, msg):
        self.messages.append(("debug", msg))


class ConfOwner(ConfAccessorMixin):
    def __init__(self, conf):
        self.conf = conf


def test_conf_accessor_mixin():
    owner = ConfOwner({"count": 2, "rate": 1.5})

    assert owner._conf_pos_int("count") == 2
    assert owner._conf_pos_num("rate") == 1.5
    assert owner._conf_bool("enabled", True) is True
    with pytest.raises(KeyError, match="Required configuration name is missing"):
        owner._conf_str("name")

    for method in ("_conf_float", "_conf_pos_float", "_conf_nonneg_float"):
        with pytest.raises(ValueError):
            getattr(ConfOwner({"value": float("nan")}), method)("value", 0.0)
    for method in ("_conf_num", "_conf_pos_num", "_conf_nonneg_num"):
        with pytest.raises(ValueError):
            getattr(ConfOwner({"value": float("inf")}), method)("value", 0.0)


def test_preset_loader_exact_match():
    logger = DummyLogger()
    loader = PresetLoader(logger)
    loader.add_preset("basic", [("alpha", 1), ("beta", 2)])

    conf = {}
    loader.load_preset(conf, "basic")

    assert conf == {"alpha": 1, "beta": 2}
    assert any(level == "info" for level, _ in logger.messages)


def test_preset_loader_preserves_existing_keys():
    logger = DummyLogger()
    loader = PresetLoader(logger)
    loader.add_preset("basic", [("alpha", 1), ("beta", 2)])

    conf = {"alpha": 10}
    loader.load_preset(conf, "basic")

    assert conf["alpha"] == 10
    assert conf["beta"] == 2
    assert any(level == "warn" for level, _ in logger.messages)


def test_preset_loader_matching_modes():
    logger = DummyLogger()
    loader = PresetLoader(logger, mode=PresetLoader.Mode.PARTIAL)
    loader.add_preset("basic", [("alpha", 1)])
    assert loader.search_preset("basic-v2") == "basic"

    loader = PresetLoader(logger, mode=PresetLoader.Mode.FORWARD)
    loader.add_preset("basic", [("alpha", 1)])
    assert loader.search_preset("basic-v2") == "basic"

    loader = PresetLoader(logger, mode=PresetLoader.Mode.BACKWARD)
    loader.add_preset("v2", [("alpha", 1)])
    assert loader.search_preset("basic-v2") == "v2"


def test_preset_loader_unknown_name():
    logger = DummyLogger()
    loader = PresetLoader(logger)
    loader.add_preset("basic", [("alpha", 1)])

    conf = {}
    loader.load_preset(conf, "missing")

    assert conf == {}
    assert any(level == "warn" for level, _ in logger.messages)
