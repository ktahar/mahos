"""
Common utility for advanced data transport.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

from mahos.util.conf import ConfAccessorMixin


class TransportConfig(ConfAccessorMixin):
    """Validate the shared node/client transport configuration."""

    def __init__(self, conf):
        self.conf = conf
        self.mode = self._conf_str("data_transport", "pubsub")
        if self.mode not in ("pubsub", "incremental"):
            raise ValueError("data_transport must be 'pubsub' or 'incremental'")
        self.buffer_mode = self._conf_str("buffer_transport", "pubsub")
        if self.buffer_mode not in ("pubsub", "versioned"):
            raise ValueError("buffer_transport must be 'pubsub' or 'versioned'")
        self.endpoint = (
            self._conf_nonempty_str("sync_endpoint")
            if self.mode == "incremental" or self.buffer_mode == "versioned"
            else None
        )
