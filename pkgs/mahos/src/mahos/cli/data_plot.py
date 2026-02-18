#!/usr/bin/env python3

"""
mahos data plot command.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import argparse


def build_parser(add_help: bool = True):
    try:
        from mahos_dq.cli import plot as dq_plot

        return dq_plot.build_parser(add_help=add_help)
    except ImportError:
        parser = argparse.ArgumentParser(
            prog="mahos data plot", description="Plot data file(s).", add_help=add_help
        )
        # Accept and ignore any extra tokens in the no-dq fallback parser.
        parser.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
        return parser


def _main(args=None):
    print("mahos data plot only works with mahos_dq installed")


try:
    from mahos_dq.cli import plot as dq_plot

    main = dq_plot.main
except ImportError:
    main = _main
