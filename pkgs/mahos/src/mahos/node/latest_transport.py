"""
Latest immutable objects with asynchronous, on-demand payload transfer.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import copy
import logging
import time
import uuid

import zmq

from mahos.node.comm import deserialize, serialize_pickle
from mahos.node.transport_util import TransportConfig
import mahos.util.validation as V

VERSION = 1


def check_identity(identity):
    """Validate an ordered publication identity."""

    if not isinstance(identity, (tuple, list)) or len(identity) != 3:
        raise ValueError("Expected epoch, revision, and object UUID")
    epoch, revision, ident = identity
    V.check_nonempty_str(epoch, "epoch")
    V.check_nonneg_int(revision, "revision")
    if not isinstance(ident, uuid.UUID):
        raise ValueError("Expected object UUID")
    return epoch, revision, ident


def check_request(request):
    """Validate a latest-object fetch request."""

    if not isinstance(request, (tuple, list)) or len(request) != 5:
        raise ValueError("Expected five latest request fields")
    kind, version, request_id, topic, known = request
    if kind != "latest" or V.check_int(version, "version") != VERSION:
        raise ValueError("Unsupported latest request")
    V.check_nonempty_str(request_id, "request ID")
    V.check_nonempty_str(topic, "topic")
    return request_id, topic, None if known is None else check_identity(known)


class LatestPublisher:
    """Copy changed objects once and periodically announce their identity.

    Content changes must use a fresh UUID. Committed objects are private copies and only
    the current publication is retained. Passing None leaves the retained preview unchanged.

    """

    def __init__(self, context, endpoint, topic, service, logger=None):
        self.topic = topic.decode() if isinstance(topic, bytes) else topic
        self.publisher = context.add_pub(
            endpoint, ("latest_" + self.topic).encode(), logger=logger
        )
        self.service = service
        self.epoch = uuid.uuid4().hex
        self.identity = None

    def publish(self, data):
        if data is not None and (self.identity is None or data.ident != self.identity[2]):
            revision = 1 if self.identity is None else self.identity[1] + 1
            identity = check_identity((self.epoch, revision, data.ident))
            self.service.commit_latest(self.topic, identity, copy.deepcopy(data))
            self.identity = identity
        if self.identity is not None:
            self.publisher.publish((VERSION, self.identity))


class LatestSubscriber:
    """Fetch changed publications on the subscription thread without retaining history.

    One request is outstanding at a time and retries preserve its request ID. The last
    delivered object remains available to the handler while a replacement is fetched.
    Only identity metadata is retained internally; callbacks own the received objects.

    """

    def __init__(self, context, conf, topic, handler, logger=None):
        self.context = context
        self.endpoint = TransportConfig(conf).endpoint
        self.topic = topic.decode() if isinstance(topic, bytes) else topic
        self.wire_topic = ("latest_" + self.topic).encode()
        self.handler = handler
        self.logger = logger or logging.getLogger(__name__)
        self.socket = None
        self.target = None
        self.delivered = None
        self.pending = None
        self.deadline = 0.0
        context.add_sub(conf["pub_endpoint"], self.wire_topic, self.handle_frames, deserial=False)
        context.add_poll_service(self)

    def handle_frames(self, frames):
        try:
            if len(frames) != 2 or frames[0] != self.wire_topic:
                raise ValueError("Unexpected announcement topic")
            version, identity = deserialize(frames[1], None)
            if V.check_int(version, "version") != VERSION:
                raise ValueError("Unsupported latest announcement")
            identity = check_identity(identity)
            if (
                self.target is None
                or identity[0] != self.target[0]
                or identity[1] > self.target[1]
            ):
                self.target = identity
                self.pending = None
        except Exception as e:
            self.logger.warning(f"Rejected latest announcement: {e}")

    def _receive(self, frames):
        if not frames:
            raise ValueError("Empty latest response")
        version, kind, request_id, topic, identity, included = deserialize(frames[0], None)
        if V.check_int(version, "version") != VERSION or kind != "latest" or topic != self.topic:
            raise ValueError("Unexpected latest response")
        if self.pending is None or request_id != self.pending[2]:
            return
        V.check_bool(included, "payload included")
        if len(frames) != 1 + int(included):
            raise ValueError("Invalid latest response frames")
        if identity is None:
            return  # Not committed yet; retry later.
        identity = check_identity(identity)
        if (
            self.target is not None
            and identity[0] == self.target[0]
            and identity[1] < self.target[1]
        ):
            self.pending = None
            return
        if not included and identity != self.delivered:
            raise ValueError("Missing latest payload")
        data = deserialize(frames[1], None) if included else None
        if included and getattr(data, "ident", None) != identity[2]:
            raise ValueError("Payload UUID differs from publication")
        self.target = identity
        self.pending = None
        if identity != self.delivered:
            self.delivered = identity
            self.handler(data)

    def poll(self):
        """Perform bounded nonblocking retrieval and retries."""

        if self.socket is None:
            self.socket = self.context.zmq_context().socket(zmq.DEALER)
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.setsockopt(zmq.SNDHWM, 1)
            self.socket.setsockopt(zmq.RCVHWM, 2)
            self.socket.connect(self.endpoint)
            self.context.poller.register(self.socket, zmq.POLLIN)
        for _ in range(8):
            try:
                frames = self.socket.recv_multipart(zmq.NOBLOCK)
            except zmq.Again:
                break
            try:
                self._receive(frames)
            except Exception as e:
                self.logger.warning(f"Rejected latest response: {e}")
        if self.target is None or self.target == self.delivered:
            return
        now = time.monotonic()
        if self.pending is not None and now < self.deadline:
            return
        request = self.pending or ("latest", VERSION, uuid.uuid4().hex, self.topic, self.delivered)
        try:
            self.socket.send(serialize_pickle(request), zmq.NOBLOCK)
        except zmq.Again:
            return
        self.pending = request
        self.deadline = now + 5.0

    def close(self):
        """Close the request socket after the subscription loop stops."""

        if self.socket is not None:
            self.socket.close()
