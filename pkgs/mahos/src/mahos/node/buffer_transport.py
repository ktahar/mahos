"""
Versioned measurement buffers with asynchronous exact-entry retrieval.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import copy
import logging
import time
import uuid

import zmq

from mahos.msgs.common_meas_msgs import Buffer, TrackedBuffer
from mahos.node.comm import deserialize, serialize_pickle
import mahos.util.validation as V


TOPIC = b"versioned_buffer"
VERSION = 1
BATCH_SIZE = 16


def check_manifest(message):
    """Validate a complete manifest before changing reconstruction state."""

    if not isinstance(message, (tuple, list)) or len(message) != 4:
        raise ValueError("Expected four manifest fields")
    version, epoch, revision, entries = message
    if V.check_int(version, "protocol version") != VERSION:
        raise ValueError("Unsupported buffer protocol version")
    V.check_nonempty_str(epoch, "buffer epoch")
    V.check_nonneg_int(revision, "buffer revision")
    if not isinstance(entries, (tuple, list)):
        raise ValueError("Expected manifest entries")
    seen = set()
    normalized = []
    for entry in entries:
        if not isinstance(entry, (tuple, list)) or len(entry) != 3:
            raise ValueError("Expected entry ID, revision, and filename")
        ident, rev, name = entry
        V.check_nonempty_str(ident, "entry ID")
        V.check_nonneg_int(rev, "entry revision")
        V.check_str(name, "filename")
        if ident in seen:
            raise ValueError("Duplicate entry ID")
        seen.add(ident)
        normalized.append((ident, rev, name))
    return version, epoch, revision, normalized


def check_request(request):
    """Validate one bounded batch of exact-version requests."""

    kind, version, request_id, epoch, versions = request
    if V.check_int(version, "protocol version") != VERSION or kind != "buffer":
        raise ValueError("Unsupported buffer request")
    V.check_nonempty_str(request_id, "request ID")
    V.check_nonempty_str(epoch, "buffer epoch")
    if not isinstance(versions, (tuple, list)) or not 1 <= len(versions) <= BATCH_SIZE:
        raise ValueError("Invalid buffer batch size")
    result = []
    for ident, revision in versions:
        V.check_nonempty_str(ident, "entry ID")
        V.check_nonneg_int(revision, "entry revision")
        result.append((ident, revision))
    if len(set(result)) != len(result):
        raise ValueError("Duplicate requested entry")
    return request_id, epoch, result


def response(request_id, epoch, versions, latest):
    """Respond only from a coherent immutable publication, without historical storage."""

    if latest is None:
        return VERSION, "buffer", request_id, "unavailable", None, []
    manifest, entries = latest
    stale = epoch != manifest[1] or any(key not in entries for key in versions)
    return (
        VERSION,
        "buffer",
        request_id,
        "stale" if stale else "ok",
        manifest,
        [] if stale else [(ident, rev, entries[(ident, rev)]) for ident, rev in versions],
    )


class BufferPublisher:
    """Commit changed entries once, then periodically publish their small manifest.

    Publication owns the node-thread boundary: changed objects are copied before they become
    visible to the recovery thread. Only the current publication is retained.

    The manifest contains the protocol version, buffer epoch, buffer revision, and
    ordered ``(entry_id, entry_revision, file_name)`` entries.
    Duplicate filenames have independent identities; removing and reloading a file allocates a
    fresh identity. Replacing the buffer transport state or restarting the node changes its epoch.

    """

    def __init__(self, context, endpoint, service, logger=None):
        self.publisher = context.add_pub(endpoint, TOPIC, logger=logger)
        self.service = service
        self.manifest = None
        self.entries = {}

    @staticmethod
    def make_manifest(buffer: TrackedBuffer):
        """Build the versioned wire envelope from buffer bookkeeping and filenames."""

        return (
            VERSION,
            buffer.epoch,
            buffer.revision,
            [
                (ident, revision, name)
                for (ident, revision), (name, _) in zip(buffer.entry_versions(), buffer)
            ],
        )

    def publish(self, buffer: TrackedBuffer):
        manifest = self.make_manifest(buffer)
        if manifest != self.manifest:
            previous = self.entries if self.manifest and self.manifest[1] == manifest[1] else {}
            entries = {}
            for (ident, revision, _), (_, data) in zip(manifest[3], buffer):
                key = (ident, revision)
                entries[key] = previous[key] if key in previous else copy.deepcopy(data)
            self.service.commit_buffer(manifest, entries)
            self.manifest, self.entries = manifest, entries
        self.publisher.publish(manifest)


class BufferSubscriber:
    """Reconstruct complete ordinary buffers on the subscription thread.

    Clients subscribe to the buffer manifests, cache the buffer contents,
    and request missing buffer entries. One bounded request is outstanding at a time.
    Cache entries are private and limited to the latest manifest;
    callbacks receive independent copies. Identical manifests do not repeat callbacks.

    This may skip intermediate manifests and eventually converge when changes stop
    and communication succeeds.

    """

    def __init__(self, context, conf, handler, logger=None):
        self.context = context
        self.endpoint = conf["sync_endpoint"]
        self.handler = handler
        self.logger = logger if logger is not None else logging.getLogger(__name__)

        self.socket = None
        self.manifest = None
        self.cache = {}
        self.pending = None
        self.deadline = 0.0
        self.delivered = None
        context.add_sub(conf["pub_endpoint"], TOPIC, self.handle_frames, deserial=False)
        context.add_poll_service(self)

    def _adopt(self, manifest):
        if self.manifest is not None:
            if manifest[1] == self.manifest[1] and manifest[2] <= self.manifest[2]:
                return
            if manifest[1] != self.manifest[1]:
                self.cache.clear()
        self.manifest = manifest
        required = {(ident, rev) for ident, rev, _ in manifest[3]}
        self.cache = {key: data for key, data in self.cache.items() if key in required}
        self.pending = None

    def _deliver(self):
        if self.manifest is None or self.delivered == self.manifest[:3]:
            return
        if all((ident, rev) in self.cache for ident, rev, _ in self.manifest[3]):
            result = Buffer(
                [
                    (name, copy.deepcopy(self.cache[(ident, rev)]))
                    for ident, rev, name in self.manifest[3]
                ]
            )
            self.delivered = self.manifest[:3]
            self.handler(result)

    def handle_frames(self, frames):
        try:
            if len(frames) != 2 or frames[0] != TOPIC:
                raise ValueError("Expected buffer manifest frames")
            self._adopt(check_manifest(deserialize(frames[1], None)))
        except Exception as e:
            self.logger.warning(f"Rejected buffer manifest: {e}")
            return
        self._deliver()

    def _receive(self, frames):
        if len(frames) != 1:
            raise ValueError("Expected one buffer response frame")
        message = deserialize(frames[0], None)
        if not isinstance(message, (tuple, list)) or len(message) != 6:
            raise ValueError("Expected six buffer response fields")
        version, kind, request_id, status, manifest, entries = message
        if V.check_int(version, "protocol version") != VERSION or kind != "buffer":
            raise ValueError("Unsupported buffer response")
        if self.pending is None or request_id != self.pending[2]:
            return
        if status == "unavailable":
            return
        if status not in ("ok", "stale"):
            raise ValueError("Invalid buffer response status")
        manifest = check_manifest(manifest)
        if not isinstance(entries, (tuple, list)):
            raise ValueError("Expected response entries")
        requested = set(self.pending[4])
        received = {}
        if status == "ok":
            if manifest[1] != self.pending[3]:
                raise ValueError("Response epoch differs from request")
            available = {(ident, rev) for ident, rev, _ in manifest[3]}
            for ident, rev, data in entries:
                V.check_nonempty_str(ident, "entry ID")
                V.check_nonneg_int(rev, "entry revision")
                key = (ident, rev)
                if key not in requested or key not in available or key in received:
                    raise ValueError("Unexpected entry version")
                received[key] = data
            if set(received) != requested:
                raise ValueError("Incomplete buffer response")
        elif entries:
            raise ValueError("Stale response contains entries")
        self._adopt(manifest)
        # Only the current request can change epochs. Obsolete responses are ignored above.
        required = {(ident, rev) for ident, rev, _ in self.manifest[3]}
        if manifest[1] == self.manifest[1]:
            self.cache.update({key: data for key, data in received.items() if key in required})
        self.pending = None

    def poll(self):
        """Perform bounded nonblocking work on the subscription thread."""

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
                self.logger.warning(f"Rejected buffer response: {e}")
            self._deliver()
        if self.manifest is None:
            return
        now = time.monotonic()
        if self.pending is not None and now < self.deadline:
            return
        request = self.pending
        if request is None:
            missing = [
                (ident, rev)
                for ident, rev, _ in self.manifest[3]
                if (ident, rev) not in self.cache
            ]
            if not missing:
                return
            request = ("buffer", VERSION, uuid.uuid4().hex, self.manifest[1], missing[:BATCH_SIZE])
        try:
            self.socket.send(serialize_pickle(request), zmq.NOBLOCK)
        except zmq.Again:
            return
        self.pending = request
        self.deadline = now + 5.0

    def close(self):
        """Close the socket after its subscription loop stops."""

        if self.socket is not None:
            self.socket.close()
