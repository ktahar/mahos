#!/usr/bin/env python3

"""
Shared helpers for mahos data CLI commands.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from os import path

_exts_to_data = None

_logger = None


def get_ext(fn):
    head, e0 = path.splitext(fn)
    head, e1 = path.splitext(head)
    return e1 + e0


def get_exts_to_data():
    global _exts_to_data

    from mahos.msgs.camera_msgs import Image as CameraImage

    if _exts_to_data is None:
        _exts_to_data = {
            ".camera.h5": CameraImage,
            ".tweak.h5": None,
            ".ptweak.h5": None,
        }
        try:
            from mahos_dq.cli import data as dq

            _exts_to_data.update(dq.exts_to_data)
        except ImportError:
            pass
    return _exts_to_data


def get_logger():
    global _logger

    if _logger is None:
        from mahos.node.log import DummyLogger

        _logger = DummyLogger()
    return _logger
