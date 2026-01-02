#!/usr/bin/env python3

"""
mahos data plot command.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""


def _main(args=None):
    print("mahos data plot only works with mahos_dq installed")


try:
    from mahos_dq.cli import plot as dq_plot

    main = dq_plot.main
except ImportError:
    main = _main
