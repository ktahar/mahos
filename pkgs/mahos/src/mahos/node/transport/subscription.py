"""
Select a transport subscriber for a configured topic.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from mahos.node.transport.config import TransportConfig
from mahos.node.transport.incremental import IncrementalSubscriber
from mahos.node.transport.buffer import BufferSubscriber
from mahos.node.transport.latest import LatestSubscriber


def add_subscription(context, conf, topic, handler, msg_type=None, logger=None):
    """Subscribe to ordinary messages or reconstruct an advanced transport topic."""

    mode = TransportConfig(conf).mode_for_topic(topic)
    if mode == "incremental":
        return IncrementalSubscriber(context, conf, handler, logger=logger)
    if mode == "versioned":
        return BufferSubscriber(context, conf, handler, logger=logger)
    if mode == "latest":
        return LatestSubscriber(context, conf, topic, handler, logger=logger)
    context.add_sub(conf["pub_endpoint"], topic, handler, msg_type)
