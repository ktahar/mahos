#!/usr/bin/env python3

"""
main entrypoint of mahos cli.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import sys
import os
import argparse
import importlib

try:
    import argcomplete
except ImportError:
    argcomplete = None

main_usage = """usage: mahos COMMAND args

COMMAND (r[un] | l[aunch] | lo[g] | ls | g[raph] | e[cho] | s[hell] | d[ata] | p[lot]) :
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


def build_completion_parser():
    parser = argparse.ArgumentParser(prog="mahos", description="MAHOS command line interface.")
    subparsers = parser.add_subparsers(dest="command")
    _add_subcommand(subparsers, "run", "mahos.cli.run")
    _add_subcommand(subparsers, "launch", "mahos.cli.launch")
    _add_subcommand(subparsers, "log", "mahos.cli.log")
    _add_subcommand(subparsers, "ls", "mahos.cli.ls")
    _add_subcommand(subparsers, "graph", "mahos.cli.graph")
    _add_subcommand(subparsers, "echo", "mahos.cli.echo")
    _add_subcommand(subparsers, "shell", "mahos.cli.shell")
    _add_subcommand(subparsers, "data", "mahos.cli.data")
    _add_subcommand(subparsers, "plot", "mahos.cli.data_plot")
    return parser


def main():
    if argcomplete is not None and "_ARGCOMPLETE" in os.environ:
        parser = build_completion_parser()
        argcomplete.autocomplete(parser)

    if len(sys.argv) < 2:
        print(main_usage)
        return 1

    # Let us import the modules in cwd
    sys.path.append(os.getcwd())

    pkg = sys.argv[1].lower()
    if "run".startswith(pkg):
        return importlib.import_module("mahos.cli.run").main(sys.argv[2:])
    elif "launch".startswith(pkg):
        return importlib.import_module("mahos.cli.launch").main(sys.argv[2:])
    elif "log".startswith(pkg):
        return importlib.import_module("mahos.cli.log").main(sys.argv[2:])
    elif "ls" == pkg:
        return importlib.import_module("mahos.cli.ls").main(sys.argv[2:])
    elif "graph".startswith(pkg):
        return importlib.import_module("mahos.cli.graph").main(sys.argv[2:])
    elif "echo".startswith(pkg):
        return importlib.import_module("mahos.cli.echo").main(sys.argv[2:])
    elif "shell".startswith(pkg):
        return importlib.import_module("mahos.cli.shell").main(sys.argv[2:])
    elif "data".startswith(pkg):
        return importlib.import_module("mahos.cli.data").main(sys.argv[2:])
    elif "plot".startswith(pkg):
        return importlib.import_module("mahos.cli.data_plot").main(sys.argv[2:])
    else:
        print(main_usage)
        return 1


if __name__ == "__main__":
    sys.exit(main())
