#!/usr/bin/env python3

"""
mahos data ls command.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import argparse


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


def print_attrs(fn):
    from mahos.cli.data_common import get_ext, get_exts_to_data, get_logger
    from mahos.util.io import list_attrs_h5

    logger = get_logger()
    print(f"## {fn} ##")
    ext = get_ext(fn)
    exts_to_data = get_exts_to_data()
    if ext not in exts_to_data:
        logger.error(f"Unknown extension {ext}")
        return

    for key, type_ in list_attrs_h5(fn, exts_to_data[ext], logger):
        print(f"{key}: {type_}")


def main(args=None):
    args = parse_args(args)
    for fn in args.names:
        print_attrs(fn)
