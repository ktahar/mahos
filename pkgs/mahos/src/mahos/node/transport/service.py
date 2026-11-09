"""
Shared service for committed transport snapshots.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import threading

import zmq

from mahos.node.comm import serialize_pickle, deserialize
from mahos.node.transport import buffer as BT, incremental as IT, latest as LT


class SnapshotService:
    """Serve committed replicas on a dedicated thread with a one-revision byte cache.

    The owning node replaces the latest immutable publication under a short lock.
    The service captures these publications under the lock, then serializes them outside it;
    it never reads the worker's live data.

    Successful construction registers this service with the owning MAHOS Context for shutdown.
    Before the first commit, live-data queries report an empty initial publication.

    Socket creation, request processing, serialization, and socket closure belong solely to
    the service thread. Shutdown waits for any serialization already in progress to finish.

    Live-data revisions are serialized only when a snapshot is requested, caching the most
    recently serialized revision for reuse across clients. Buffer requests share this service
    but retrieve bounded batches of exact entry versions from a separate immutable publication.
    Revision-only live-data queries return without serializing the state. If a requested buffer
    version is no longer available, the response contains the latest manifest and no entries.
    Latest-object requests retrieve the current immutable publication for a named topic,
    with one lazily serialized byte cache per topic.
    No historical snapshot queue, preview objects, or buffer versions are stored.
    Serialization bypasses custom dataset serialization to preserve complete concrete objects.
    Queued duplicate requests from the same client are coalesced within bounded batches;
    later retries still receive responses.

    """

    def __init__(self, context, endpoint, logger):
        self._context = context.zmq_context()
        self._endpoint = endpoint
        self._latest = ("initial", 0, None)
        self._buffer_latest = None
        self._objects = {}
        self.logger = logger

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._startup_error = None
        self._cache_key = None
        self._cache_payload = None
        self._thread = threading.Thread(target=self._run, name="mahos-snapshot", daemon=True)
        self._thread.start()
        self._ready.wait()
        if self._startup_error is not None:
            self._thread.join()
            raise self._startup_error
        context.add_close_service(self)

    def commit(self, epoch, revision, state):
        """Replace the latest publication; callers must never mutate committed state."""

        with self._lock:
            self._latest = (epoch, revision, state)

    def commit_buffer(self, manifest, entries):
        """Commit private immutable buffer entries at the publication boundary."""

        with self._lock:
            self._buffer_latest = (manifest, entries)

    def commit_latest(self, topic, identity, state):
        """Replace one topic's immutable publication and discard its byte cache."""

        with self._lock:
            self._objects[topic] = (identity, state, None)

    def _latest_response(self, request_id, arguments):
        """Serialize a captured publication, caching only if it is still current."""

        topic, known = arguments
        with self._lock:
            publication = self._objects.get(topic)
        identity, state, payload = publication or (None, None, None)
        included = identity is not None and identity != known
        if included and payload is None:
            payload = serialize_pickle(state)
            with self._lock:
                if self._objects.get(topic) is publication:
                    self._objects[topic] = (identity, state, payload)
        header = (LT.VERSION, "latest", request_id, topic, identity, included)
        return [serialize_pickle(header)] + ([payload] if included else [])

    @staticmethod
    def _decode_request(payload):
        """Dispatch wire validation and normalize requests for shared batch handling."""

        request = deserialize(payload, None)
        if isinstance(request, (tuple, list)) and request and request[0] == "buffer":
            kind = "buffer"
            request_id, *arguments = BT.check_request(request)
        elif isinstance(request, (tuple, list)) and request and request[0] == "latest":
            kind = "latest"
            request_id, *arguments = LT.check_request(request)
        else:
            kind = "live"
            request_id, *arguments = IT.check_request(request)
        return request_id, (kind, tuple(arguments))

    def _receive_batch(self, router):
        """Drain a bounded batch, coalescing queued retries by peer and request ID."""

        requests = {}
        for _ in range(64):
            try:
                frames = router.recv_multipart(zmq.NOBLOCK)
            except zmq.Again:
                break
            try:
                if len(frames) != 2:
                    raise ValueError("Expected identity and request frames")
                identity, payload = frames
                request_id, arguments = self._decode_request(payload)
                key = (identity, request_id)
                if key in requests and requests[key] != arguments:
                    raise ValueError("Retry changed its request arguments")
                requests[key] = arguments
            except Exception:
                self.logger.exception("Rejected recovery request")
        return requests

    def _live_response(self, request_id, arguments, latest):
        """Build live-data response frames, reusing the latest serialized snapshot."""

        epoch, revision, state = latest
        base_epoch, base_revision, snapshot = arguments
        include_state = (
            snapshot and state is not None and (base_epoch, base_revision) != (epoch, revision)
        )
        if include_state and self._cache_key != (epoch, revision):
            # Transport serialization is independent of Message.serialize().
            self._cache_payload = serialize_pickle(state)
            self._cache_key = (epoch, revision)
        header = (IT.VERSION, request_id, epoch, revision, include_state)
        frames = [serialize_pickle(header)]
        if include_state:
            frames.append(self._cache_payload)
        return frames

    @staticmethod
    def _buffer_response(request_id, arguments, latest):
        """Build buffer response frames from the captured committed entries."""

        epoch, versions = arguments
        return [serialize_pickle(BT.response(request_id, epoch, versions, latest))]

    def _serve_batch(self, router, requests):
        """Respond from captured publications using one nonblocking send path."""

        with self._lock:
            live_latest = self._latest
            buffer_latest = self._buffer_latest
        for (identity, request_id), (kind, arguments) in requests.items():
            if self._stop.is_set():
                break
            if kind == "live":
                frames = self._live_response(request_id, arguments, live_latest)
            elif kind == "latest":
                frames = self._latest_response(request_id, arguments)
            else:
                frames = self._buffer_response(request_id, arguments, buffer_latest)
            try:
                router.send_multipart([identity, *frames], zmq.NOBLOCK)
            except zmq.ZMQError as e:
                if e.errno not in (zmq.EAGAIN, zmq.EHOSTUNREACH):
                    raise
                # A disconnected or slow peer retries; do not block other clients.

    def _run(self):
        """Own the recovery socket for its complete lifetime."""

        router = None
        try:
            router = self._context.socket(zmq.ROUTER)
            router.setsockopt(zmq.LINGER, 0)
            router.setsockopt(zmq.SNDHWM, 2)
            router.setsockopt(zmq.RCVHWM, 64)
            router.setsockopt(zmq.ROUTER_MANDATORY, 1)
            router.bind(self._endpoint)
        except Exception as e:
            self._startup_error = e
        finally:
            self._ready.set()
        try:
            if self._startup_error is not None:
                return
            while not self._stop.is_set():
                if router.poll(50):
                    try:
                        self._serve_batch(router, self._receive_batch(router))
                    except Exception:
                        self.logger.exception("Failed to serve recovery batch")
        finally:
            if router is not None:
                router.close()
            self._cache_payload = None
            self._cache_key = None
            with self._lock:
                self._latest = None
                self._buffer_latest = None
                self._objects.clear()

    def close(self):
        """Stop the service and join its thread before the ZMQ context is closed."""

        self._stop.set()
        self._thread.join()
