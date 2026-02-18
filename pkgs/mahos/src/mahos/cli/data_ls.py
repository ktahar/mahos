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

from mahos.msgs.camera_msgs import Image as CameraImage

exts_to_data = {
    ".camera.h5": CameraImage,
}
try:
    from mahos_dq.cli import data as dq

    exts_to_data.update(dq.exts_to_data)
except ImportError:
    pass


def parse_args(args):
    parser = build_parser()
    args = parser.parse_args(args)

    return args


def build_parser(add_help: bool = True):
    parser = argparse.ArgumentParser(
        prog="mahos data ls",
        description="Print list attributes and types of h5 data file(s).",
        add_help=add_help,
    )
    parser.add_argument("names", nargs="+", help="file names")
    return parser


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
