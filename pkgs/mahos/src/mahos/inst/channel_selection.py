"""
Hardware input selection shared by acquisition backends.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import mahos.util.validation as V


def channel_indices(selection, count=None):
    """Validate ordered indices into configured physical inputs."""

    if selection is None:
        return list(range(count)) if count is not None else None
    V.check_nonneg_integers(selection, name="channel_selection")
    if not selection:
        raise ValueError("channel_selection must not be empty.")
    V.check_ascending_numbers(selection, name="channel_selection")
    if count is not None and selection[-1] >= count:
        raise ValueError("channel_selection index exceeds configured lines.")
    return list(selection)


def pd_selections(conf, names):
    """Validate static selections keyed by PD instrument name."""

    selections = conf.get("pd_channel_selection", {})
    if not isinstance(selections, dict) or set(selections) - set(names):
        raise ValueError("pd_channel_selection must map configured PD names to selections.")
    return {name: channel_indices(value) for name, value in selections.items()}
