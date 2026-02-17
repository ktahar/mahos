#!/usr/bin/env python3

"""
Message Types for the StateManager.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from pprint import pformat

from mahos.msgs.common_msgs import Request, Status


class ManagerStatus(Status):
    """Aggregated state snapshot published by StateManager.

    :ivar states: Mapping from node name to its current state object.

    """

    def __init__(self, states: dict):
        self.states = states

    def __repr__(self):
        return f"ManagerStatus({self.states})"

    def __str__(self):
        return "Manager->states:\n" + pformat(self.states)


class CommandReq(Request):
    """Request to apply a named state-manager command profile.

    :ivar name: Command profile name defined in StateManager configuration.

    """

    def __init__(self, name: str):
        self.name = name


class RestoreReq(Request):
    """Request to restore a previously stored state-manager profile.

    :ivar name: Restore-point name to re-apply.

    """

    def __init__(self, name: str):
        self.name = name
