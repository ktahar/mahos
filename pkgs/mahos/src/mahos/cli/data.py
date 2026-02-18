#!/usr/bin/env python3

"""
mahos data command.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import argparse
import importlib

data_usage = """usage: mahos data COMMAND args

COMMAND (l[s] | n[ote] | p[lot] | pr[int]) :
    the command to execute.

"""


def _add_subcommand(subparsers, name: str, module_name: str):
    module = importlib.import_module(module_name)
    parent = module.build_parser(add_help=False)
    subparsers.add_parser(
        name,
        add_help=True,
        help=parent.description,
        parents=[parent],
    )


def build_parser(add_help: bool = True):
    parser = argparse.ArgumentParser(
        prog="mahos data", description="Data operation commands.", add_help=add_help
    )
    subparsers = parser.add_subparsers(dest="data_command")
    _add_subcommand(subparsers, "ls", "mahos.cli.data_ls")
    _add_subcommand(subparsers, "note", "mahos.cli.data_note")
    _add_subcommand(subparsers, "plot", "mahos.cli.data_plot")
    _add_subcommand(subparsers, "print", "mahos.cli.data_print")
    return parser


def main(args):
    if len(args) < 1:
        print(data_usage)
        return 1

    pkg = args[0].lower()

    if "ls".startswith(pkg):
        return importlib.import_module("mahos.cli.data_ls").main(args[1:])
    elif "note".startswith(pkg):
        return importlib.import_module("mahos.cli.data_note").main(args[1:])
    elif "plot".startswith(pkg):
        return importlib.import_module("mahos.cli.data_plot").main(args[1:])
    elif "print".startswith(pkg):
        return importlib.import_module("mahos.cli.data_print").main(args[1:])
    else:
        print(data_usage)
        return 1
