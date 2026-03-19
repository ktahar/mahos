#!/usr/bin/env python3

"""
mahos data print command.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import argparse

from pprint import pprint


def parse_args(args):
    parser = build_parser()
    args = parser.parse_args(args)

    return args


def build_parser(add_help: bool = True):
    parser = argparse.ArgumentParser(
        prog="mahos data print",
        description=(
            "Print attributes of h5 data file(s). "
            "For .tweak.h5/.ptweak.h5 files, all root-group attributes are printed and "
            "-k/-a are ignored."
        ),
        add_help=add_help,
    )
    parser.add_argument(
        "-k",
        "--keys",
        nargs="*",
        help="attribute keys to print. default is ['params']. ignored for .tweak.h5/.ptweak.h5",
    )
    parser.add_argument(
        "-t", "--threshold", type=int, default=20, help="threshold for np.printoptions"
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help=(
            "print all the attributes. if given, -k is ignored. "
            "for .tweak.h5/.ptweak.h5, always behaves as enabled"
        ),
    )
    parser.add_argument("names", nargs="+", help="file names")
    return parser


def print_group_attrs(fn, group):
    from mahos.cli.data_common import get_logger
    from mahos.meas.tweaker_io import TweakerIO
    import h5py

    logger = get_logger()
    tio = TweakerIO()
    group = tio.mangle_group(group)

    with h5py.File(fn, "r") as f:
        if group not in f:
            logger.warn(f"{group} doesn't exist")
            return

        for key, val in f[group].items():
            if isinstance(val, h5py.Group):
                for k, v in val.attrs.items():
                    print(f"{key}.{k}: {v}")
            else:
                print(f"{key}: {val}")


def print_all_group_attrs(fn):
    import h5py

    with h5py.File(fn, "r") as f:
        for key, val in f.items():
            if isinstance(val, h5py.Group):
                for k, v in val.attrs.items():
                    print(f"{key}.{k}: {v}")
            else:
                print(f"{key}: {val}")


def print_all_attrs(tio, fn, Data_T, logger):
    from mahos.util.io import get_attrs_h5, list_attrs_h5

    for group in tio.get_groups(fn, True):
        print(f"[{group}]")
        print_group_attrs(fn, group)

    keys, _ = zip(*list_attrs_h5(fn, Data_T, logger))
    values = get_attrs_h5(fn, Data_T, keys, logger)
    if values is None:
        return
    for key, value in zip(keys, values):
        print(f"[{key}]")
        pprint(value, compact=True)


def decompose_keys(keys):
    raw_keys = []
    dict_keys = []
    for k in keys:
        ks = k.split(".")
        raw_keys.append(ks[0])
        dict_keys.append(ks[1:])
    return raw_keys, dict_keys


def print_attrs(tio, fn, Data_T, keys, logger):
    from mahos.util.io import get_attrs_h5

    groups = set(tio.get_groups(fn, True) + tio.get_groups(fn, False))
    group_keys = []
    attr_keys = []
    for key in keys:
        if key in groups:
            group_keys.append(key)
        else:
            attr_keys.append(key)

    for key in group_keys:
        print(f"[{key}]")
        print_group_attrs(fn, key)

    raw_keys, dict_keys = decompose_keys(attr_keys)
    values = get_attrs_h5(fn, Data_T, raw_keys, logger)
    if values is None:
        return
    for key, value, dkeys in zip(attr_keys, values, dict_keys):
        print(f"[{key}]")
        try:
            for dk in dkeys:
                value = value[dk]
            pprint(value, compact=True)
        except Exception:
            logger.exception("Error looking for dict values")


def main_file(args, fn):
    from mahos.cli.data_common import get_ext, get_exts_to_data, get_logger
    from mahos.meas.tweaker_io import TweakerIO

    logger = get_logger()
    tio = TweakerIO()

    print(f"## {fn} ##")
    ext = get_ext(fn)
    exts_to_data = get_exts_to_data()
    if ext not in exts_to_data:
        logger.error(f"Unknown extension {ext}")
        return
    Data_T = exts_to_data[ext]

    if Data_T is None:
        # Tweaker/PosTweaker file with attributes only.
        print_all_group_attrs(fn)
        return

    if args.all:
        print_all_attrs(tio, fn, Data_T, logger)
    else:
        print_attrs(tio, fn, Data_T, args.keys, logger)


def main(args=None):
    import numpy as np

    args = parse_args(args)
    if not args.keys:
        args.keys = ["params"]
    with np.printoptions(threshold=args.threshold):
        for fn in args.names:
            main_file(args, fn)
