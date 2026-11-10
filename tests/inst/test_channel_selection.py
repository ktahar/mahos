"""
Tests for static hardware input selection validation.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import pytest

from mahos.inst.channel_selection import channel_indices, pd_selections


def test_channel_indices():
    assert channel_indices(None, 4) == [0, 1, 2, 3]
    assert channel_indices([0, 2], 4) == [0, 2]
    assert pd_selections({"pd_channel_selection": {"pd0": [2]}}, ["pd0"]) == {"pd0": [2]}


@pytest.mark.parametrize("selection", [[], [True], [1.0], [-1], [2, 1], [1, 1], [4]])
def test_invalid_channel_indices(selection):
    with pytest.raises(ValueError):
        channel_indices(selection, 4)


def test_unknown_pd_name():
    with pytest.raises(ValueError):
        pd_selections({"pd_channel_selection": {"wrong": [0]}}, ["pd0"])
