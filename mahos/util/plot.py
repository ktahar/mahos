#!/usr/bin/env python3

"""
Plot utility module.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import matplotlib as mpl
from matplotlib.colors import to_hex


def colors_tab10() -> list[str]:
    """Get list of colors using mpl's tab10 colormap.

    color is expressed in HTML (hex) format.

    """

    colors = mpl.colormaps.get("tab10").colors
    return [to_hex(c) for c in colors]


def colors_tab20_pair() -> list[tuple[str, str]]:
    """Get paired color using mpl's tab20 colormap.

    color is expressed in HTML (hex) format.

    """

    colors = mpl.colormaps.get("tab20").colors
    return [(to_hex(c0), to_hex(c1)) for c0, c1 in zip(colors[0::2], colors[1::2])]
