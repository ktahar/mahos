#!/usr/bin/env python3

"""
mahos data ls command.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from os import path
import argparse

from mahos.util.io import list_attrs_h5
from mahos.node.log import DummyLogger

from mahos.msgs.confocal_msgs import Image, Trace
from mahos.msgs.odmr_msgs import ODMRData
from mahos.msgs.podmr_msgs import PODMRData
from mahos.msgs.spodmr_msgs import SPODMRData
from mahos.msgs.iodmr_msgs import IODMRData
from mahos.msgs.hbt_msgs import HBTData
from mahos.msgs.spectroscopy_msgs import SpectroscopyData
from mahos.msgs.camera_msgs import Image as CameraImage


def parse_args(args):
    parser = argparse.ArgumentParser(
        prog="mahos data print", description="Print list attributes and types of h5 data file(s)."
    )
    parser.add_argument("names", nargs="+", help="file names")
    args = parser.parse_args(args)

    return args


exts_to_data = {
    ".scan.h5": Image,
    ".trace.h5": Trace,
    ".odmr.h5": ODMRData,
    ".podmr.h5": PODMRData,
    ".spodmr.h5": SPODMRData,
    ".iodmr.h5": IODMRData,
    ".hbt.h5": HBTData,
    ".spec.h5": SpectroscopyData,
    ".camera.h5": CameraImage,
}

logger = DummyLogger()


def get_ext(fn):
    head, e0 = path.splitext(fn)
    head, e1 = path.splitext(head)
    return e1 + e0


def print_attrs(fn):
    print(f"## {fn} ##")
    ext = get_ext(fn)
    if ext not in exts_to_data:
        logger.error(f"Unknown extension {ext}")
        return

    for key, type_ in list_attrs_h5(fn, exts_to_data[ext], logger):
        print(f"{key}: {type_}")


def main(args=None):
    args = parse_args(args)
    for fn in args.names:
        print_attrs(fn)
