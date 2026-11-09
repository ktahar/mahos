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
        self.latest_modes = {
            topic: self._conf_str(topic + "_transport", "pubsub") for topic in ("pulse", "wave")
        }
        if any(mode not in ("pubsub", "latest") for mode in self.latest_modes.values()):
            raise ValueError("pulse_transport and wave_transport must be pubsub or latest")
        self.needs_service = (
            self.mode == "incremental"
            or self.buffer_mode == "versioned"
            or "latest" in self.latest_modes.values()
        )
        self.endpoint = self._conf_nonempty_str("sync_endpoint") if self.needs_service else None

    def mode_for_topic(self, topic: str | bytes) -> str:
        """Return the configured transport mode for a subscription topic."""

        name = topic.decode() if isinstance(topic, bytes) else topic
        if name in ("data", "trace"):
            return self.mode
        if name == "buffer":
            return self.buffer_mode
        return self.latest_modes.get(name, "pubsub")
