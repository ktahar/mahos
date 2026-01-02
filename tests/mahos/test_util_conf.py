#!/usr/bin/env python3

"""
Tests for mahos.util.conf.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from mahos.util.conf import PresetLoader


class DummyLogger:
    def __init__(self):
        self.messages = []

    def warn(self, msg):
        self.messages.append(("warn", msg))

    def info(self, msg):
        self.messages.append(("info", msg))

    def debug(self, msg):
        self.messages.append(("debug", msg))


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
