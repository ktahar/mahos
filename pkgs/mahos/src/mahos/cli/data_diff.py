#!/usr/bin/env python3

"""mahos data diff command.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import argparse
import sys


def build_parser(add_help: bool = True):
    parser = argparse.ArgumentParser(
        prog="mahos data diff",
        description="Compare dictionary attributes of two h5 data files.",
        epilog="Exit status: 0 if equal within tolerances, 1 if different, 2 on errors.",
        add_help=add_help,
    )
    parser.add_argument(
        "-k",
        "--key",
        default="params",
        help="attribute or dotted dictionary path (default: params)",
    )
    parser.add_argument(
        "-t", "--threshold", type=int, default=20, help="threshold for np.printoptions"
    )
    parser.add_argument(
        "--rtol", type=float, default=1e-5, help="relative tolerance (default: 1e-5)"
    )
    parser.add_argument(
        "--atol", type=float, default=1e-8, help="absolute tolerance (default: 1e-8)"
    )
    parser.add_argument("names", nargs=2, metavar="FILE", help="first and second file names")
    return parser


def read_dict(fn, key):
    """Read a dictionary attribute or dotted dictionary path from a data file."""

    import h5py

    from mahos.cli.data_common import get_ext, get_exts_to_data

    ext = get_ext(fn)
    exts_to_data = get_exts_to_data()
    if ext not in exts_to_data:
        raise ValueError(f"unknown extension {ext!r}")
    data_type = exts_to_data[ext]
    if data_type is None:
        raise ValueError(f"{ext} files do not support dictionary attribute comparison")

    keys = key.split(".")
    with h5py.File(fn, "r") as f:
        try:
            value = data_type.get_attr_h5_exn(f, keys[0])
        except KeyError:
            raise ValueError(f"attribute {keys[0]!r} does not exist") from None
    for i, part in enumerate(keys[1:], start=1):
        parent = ".".join(keys[:i])
        if not isinstance(value, dict):
            raise ValueError(f"{parent!r} must be a dict, got {type(value).__name__}")
        if part not in value:
            raise ValueError(f"dictionary path {'.'.join(keys[: i + 1])!r} does not exist")
        value = value[part]
    if not isinstance(value, dict):
        raise ValueError(f"{key!r} must be a dict, got {type(value).__name__}")
    return value


def main(args=None):
    import numpy as np

    import mahos.util.validation as V
    from mahos.util.comp import dict_isclose_inspect

    parser = build_parser()
    args = parser.parse_args(args)
    try:
        V.check_nonneg_float(args.rtol, "rtol")
        V.check_nonneg_float(args.atol, "atol")
        V.check_pos_int(args.threshold, "threshold")
    except V.ValidationError as e:
        parser.error(str(e))

    values = []
    for fn in args.names:
        try:
            values.append(read_dict(fn, args.key))
        except Exception as e:
            print(f"Error reading {args.key!r} from {fn}: {e}", file=sys.stderr)
            return 2

    with np.printoptions(threshold=args.threshold):
        equal = dict_isclose_inspect(*values, rtol=args.rtol, atol=args.atol, path=args.key)
    return 0 if equal else 1
