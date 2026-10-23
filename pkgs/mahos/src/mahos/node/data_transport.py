"""
Incremental measurement data transport with snapshot recovery.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import copy
import logging
import threading
import time
import uuid
from dataclasses import dataclass

import numpy as np
import zmq

from mahos.node.comm import serialize_pickle, deserialize
from mahos.util.conf import ConfAccessorMixin
import mahos.util.validation as V


TOPIC = b"incremental_data"
VERSION = 1


def check_envelope(message, length):
    """Validate the protocol version before interpreting version-specific fields."""

    if not isinstance(message, (tuple, list)) or not message:
        raise ValueError("Expected a nonempty protocol envelope")
    version = V.check_int(message[0], "protocol version")
    if version != VERSION:
        raise ValueError(
            f"Incompatible incremental protocol version {version}; expected {VERSION}"
        )
    if len(message) != length:
        raise ValueError(f"Expected {length} envelope fields, got {len(message)}")
    return message


def check_state(state):
    """Require an attribute-based data object, rather than a scalar or container."""

    if isinstance(state, type) or not hasattr(state, "__dict__"):
        raise ValueError("Expected an attribute-based data object")
    return state


class TransportConfig(ConfAccessorMixin):
    """Validate the shared node/client transport configuration."""

    def __init__(self, conf):
        self.conf = conf
        self.mode = self._conf_str("data_transport", "pubsub")
        if self.mode not in ("pubsub", "incremental"):
            raise ValueError("data_transport must be 'pubsub' or 'incremental'")
        self.endpoint = (
            self._conf_nonempty_str("sync_endpoint") if self.mode == "incremental" else None
        )


@dataclass(frozen=True)
class ArrayPolicy:
    """Describe append-only, mutable-tail, or counted rolling arrays.

    For counted rolling arrays, ``count_attr`` names the cumulative number of appended slices.
    The array contains the latest slices ending at that count; retained slices must be immutable.

    For the array which is subject to individual reset (c.f. whole data reset by ``invalidate()``),
    ``generation_attr`` names a scalar token whose change forces replacement, including
    same-shaped rebuilds. A missing token (for older saved data) is treated as ``None``.

    """

    axis: int
    mutable_tail: int = 0
    count_attr: str | None = None
    generation_attr: str | None = None

    def __post_init__(self):
        V.check_nonneg_int(self.axis, "axis")
        V.check_nonneg_int(self.mutable_tail, "mutable_tail")
        for name in (self.count_attr, self.generation_attr):
            if name is not None:
                V.check_nonempty_str(name, "array policy attribute")
        if self.count_attr is not None and self.mutable_tail:
            raise ValueError("Counted arrays must have immutable records")


def assemble(previous, metadata, operations):
    """Build a complete private replica without modifying the previous revision."""

    check_state(metadata)
    if not isinstance(operations, dict) or not operations:
        raise ValueError("Expected a nonempty array operation mapping")
    result = copy.copy(metadata)
    for name, operation in operations.items():
        V.check_nonempty_str(name, "array attribute")
        if (
            name.startswith("__")
            or name not in vars(metadata)
            or getattr(metadata, name) is not None
        ):
            raise ValueError("Array operation must name an empty metadata attribute")
        if not isinstance(operation, (tuple, list)) or len(operation) != 4:
            raise ValueError("Expected four array operation fields")
        axis, drop, start, payload = operation
        V.check_nonneg_int(axis, "axis")
        V.check_nonneg_int(drop, "drop")
        V.check_nonneg_int(start, "start")
        if payload is not None:
            if (
                not isinstance(payload, np.ndarray)
                or payload.dtype.hasobject
                or axis >= payload.ndim
            ):
                raise ValueError("Invalid array payload or axis")
        elif start:
            raise ValueError("Cannot append None to an array")
        if start == 0:
            value = payload
        else:
            old = getattr(previous, name)
            if (
                not isinstance(old, np.ndarray)
                or old.ndim != payload.ndim
                or old.dtype != payload.dtype
                or old.shape[:axis] != payload.shape[:axis]
                or old.shape[axis + 1 :] != payload.shape[axis + 1 :]
                or drop + start > old.shape[axis]
            ):
                raise ValueError("Invalid incremental array base or offset")
            prefix = [slice(None)] * old.ndim
            prefix[axis] = slice(drop, drop + start)
            if drop == 0 and start == old.shape[axis] and payload.shape[axis] == 0:
                value = old
            else:
                value = np.concatenate((old[tuple(prefix)], payload), axis=axis)
        setattr(result, name, value)
    return result


class SnapshotService:
    """Serve committed replicas on a dedicated thread with a one-revision byte cache.

    The owning node replaces the latest immutable publication under a short lock.
    This serves committed publications, never the worker's live data.

    Socket creation, request processing, serialization, and socket closure belong solely to
    the service thread.  Shutdown waits for any serialization already in progress to finish.

    This serializes a revision only when a snapshot is requested, and caches the most recently
    serialized revision for reuse across clients.
    Queued duplicate requests from the same client are coalesced within bounded batches;
    later retries still receive responses. No historical snapshot queue is maintained.

    """

    def __init__(self, context, endpoint, initial, logger):
        self._context = context
        self._endpoint = endpoint
        self._latest = initial
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

    def commit(self, epoch, revision, state):
        """Replace the latest publication; callers must never mutate committed state."""

        with self._lock:
            self._latest = (epoch, revision, state)

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
                request = check_envelope(deserialize(payload, None), 5)
                _version, request_id, epoch, revision, snapshot = request
                V.check_nonempty_str(request_id, "request ID")
                if epoch is not None:
                    V.check_nonempty_str(epoch, "epoch")
                V.check_nonneg_int(revision, "revision")
                V.check_bool(snapshot, "snapshot")
                if epoch is None and revision != 0:
                    raise ValueError("A request without an epoch must have revision zero")
                key = (identity, request_id)
                arguments = (epoch, revision, snapshot)
                if key in requests and requests[key] != arguments:
                    raise ValueError("Retry changed its request arguments")
                requests[key] = arguments
            except Exception:
                self.logger.exception("Rejected incremental recovery request")
        return requests

    def _serve_batch(self, router, requests):
        """Respond from one captured publication, serializing it only when needed."""

        with self._lock:
            epoch, revision, state = self._latest
        for (identity, request_id), (base_epoch, base_revision, snapshot) in requests.items():
            if self._stop.is_set():
                break
            include_state = (
                snapshot and state is not None and (base_epoch, base_revision) != (epoch, revision)
            )
            if include_state and self._cache_key != (epoch, revision):
                # Now, the transport owns its wire format, independently of Message.serialize().
                payload = serialize_pickle(state)
                self._cache_key = (epoch, revision)
                self._cache_payload = payload
            header = (VERSION, request_id, epoch, revision, include_state)
            frames = [identity, serialize_pickle(header)]
            if include_state:
                frames.append(self._cache_payload)
            try:
                router.send_multipart(frames, zmq.NOBLOCK)
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
                        self.logger.exception("Failed to serve incremental snapshot batch")
        finally:
            if router is not None:
                router.close()
            self._cache_payload = None
            self._cache_key = None
            with self._lock:
                self._latest = None

    def close(self):
        """Stop the service and join its thread before the ZMQ context is closed."""

        self._stop.set()
        self._thread.join()


class IncrementalPublisher:
    """Publish array suffixes and serve immutable, revisioned snapshots.

    Published prefixes must be immutable except for the configured mutable tail;
    call ``invalidate()`` after other in-place edits.

    Publication runs on the node thread; a dedicated service handles snapshot requests.
    The context owns snapshot service shutdown.
    This removes recovery serialization from the measurement thread, but does not eliminate
    CPU or memory-bandwidth contention. Publications (and client reconstructions) copy arrays.

    Replacing the source object automatically starts a new epoch; in-place mutations on arrays
    require ``invalidate()``.  Each publication captures metadata and payloads before
    returning to the worker. Committed replicas are never mutated by the publisher.

    """

    def __init__(self, context, pub_endpoint, sync_endpoint, policies, logger=None):
        if not policies:
            raise ValueError("This measurement does not define incremental array policies")
        self.policies = policies
        self.publisher = context.add_pub(pub_endpoint, TOPIC, logger=logger)
        self.epoch = uuid.uuid4().hex
        self.revision = 0
        self.state = None
        self.source = None
        self.logger = self.publisher.logger
        self.snapshot_service = SnapshotService(
            context.zmq_context(),
            sync_endpoint,
            (self.epoch, self.revision, self.state),
            self.logger if logger is not None else logging.getLogger(__name__),
        )
        context.add_close_service(self.snapshot_service)

    def invalidate(self):
        """Start a new generation on the next publication."""

        self.source = None

    def _extract(self, msg, reset, name, policy):
        """extract incremental array update operation."""

        value = getattr(msg, name)
        old = getattr(self.state, name) if self.state is not None else None
        axis = policy.axis
        start = drop = 0
        if value is not None:
            if not isinstance(value, np.ndarray) or value.dtype.hasobject:
                raise ValueError(f"{name} must be a non-object ndarray or None")
            if axis >= value.ndim:
                raise ValueError(f"{name}: growth axis exceeds array dimensions")
            if (
                not reset
                and old is not None
                and old.dtype == value.dtype
                and old.ndim == value.ndim
                and old.shape[:axis] == value.shape[:axis]
                and old.shape[axis + 1 :] == value.shape[axis + 1 :]
                and (
                    policy.generation_attr is None
                    or getattr(msg, policy.generation_attr, None)
                    == getattr(self.state, policy.generation_attr, None)
                )
            ):
                if policy.count_attr is not None:
                    count = V.check_nonneg_int(getattr(msg, policy.count_attr), policy.count_attr)
                    old_count = getattr(self.state, policy.count_attr)
                    new_begin = count - value.shape[axis]
                    old_begin = old_count - old.shape[axis]
                    if count >= old_count and new_begin >= old_begin:
                        start = max(0, old_count - new_begin)
                        drop = old.shape[axis] - start
                elif old.shape[axis] <= value.shape[axis]:
                    start = max(0, old.shape[axis] - policy.mutable_tail)
            if policy.count_attr is not None:
                count = V.check_nonneg_int(getattr(msg, policy.count_attr), policy.count_attr)
                if count < value.shape[axis]:
                    raise ValueError(f"{name}: cumulative count is smaller than retained length")
            suffix = [slice(None)] * value.ndim
            suffix[axis] = slice(start, None)
            value = value[tuple(suffix)].copy()

        return axis, drop, start, value

    def publish(self, msg):
        """Commit and publish one coherent revision of ``msg``."""

        reset = self.source is not msg
        metadata = copy.copy(msg)
        for name in self.policies:
            setattr(metadata, name, None)
        metadata = copy.deepcopy(metadata)
        operations = {}
        for name, policy in self.policies.items():
            operations[name] = self._extract(msg, reset, name, policy)
        state = assemble(self.state, metadata, operations)
        if reset:
            self.epoch = uuid.uuid4().hex
            self.revision = 0
        update = (VERSION, self.epoch, self.revision, self.revision + 1, metadata, operations)
        self.source = msg
        self.state = state
        self.revision += 1
        self.snapshot_service.commit(self.epoch, self.revision, state)
        self.publisher.publish(update)


class IncrementalSubscriber:
    """Reconstruct data and periodically recover missing revisions.

    Clients request a snapshot on startup and after a missing revision,
    and check the latest revision about once per second even while acquisition is idle.
    Updates without a matching base are discarded and trigger a snapshot request;
    this avoids an unbounded startup buffer.
    Unanswered requests are retried after five seconds using the same request ID and arguments,
    so responses remain valid when acquisition or transfer takes longer. Duplicate responses
    are ignored once the logical request completes.
    Recovery is asynchronous and does not use the client's ordinary measurement request socket.

    A disconnected client retains its last complete data object.

    """

    def __init__(self, context, conf, handler, logger=None):
        self.context = context
        self.endpoint: str = TransportConfig(conf).endpoint
        self.handler = handler
        self.logger = logger if logger is not None else logging.getLogger(__name__)

        self.socket: zmq.Socket | None = None
        self.state = None
        self.epoch = None
        self.revision = 0
        self.pending = None
        self._pending_request = None
        self.needs_snapshot = True
        self.next_query = 0.0
        self.deadline = 0.0
        context.add_sub(conf["pub_endpoint"], TOPIC, self.handle_frames, deserial=False)
        context.add_poll_service(self)

    def deliver(self):
        """Expose an independent object so callers cannot corrupt the private replica."""

        self.handler(copy.deepcopy(self.state))

    def _reject(self, e):
        """Retain the last replica and schedule recovery after a transport error."""

        self.logger.warning(f"Rejected incremental message: {e}")
        self.needs_snapshot = True
        self.next_query = 0.0

    def handle_frames(self, frames):
        """Decode publication frames inside the transport error boundary."""

        try:
            if len(frames) != 2 or frames[0] != TOPIC:
                raise ValueError("Expected incremental topic and payload frames")
            update = deserialize(frames[1], None)
        except Exception as e:
            self._reject(e)
            return
        self.handle_update(update)

    def handle_update(self, update):
        """Validate and assemble a publication before committing its revision."""

        try:
            _version, epoch, base, revision, metadata, operations = check_envelope(update, 6)
            V.check_nonempty_str(epoch, "epoch")
            V.check_nonneg_int(base, "base revision")
            V.check_pos_int(revision, "revision")
            if revision != base + 1:
                raise ValueError("Update revision must immediately follow its base")
            if epoch == self.epoch and revision <= self.revision:
                return
            if self.state is None or epoch != self.epoch or base != self.revision:
                self.needs_snapshot = True
                self.next_query = 0.0
                return
            if type(metadata) is not type(self.state):
                raise ValueError("Data type changed within an epoch")
            state = assemble(self.state, metadata, operations)
        except Exception as e:
            self._reject(e)
            return
        self.state = state
        self.revision = revision
        self.needs_snapshot = False
        self.deliver()  # Application handler exceptions must propagate normally.

    def _deserialize(self, frames):
        if len(frames) not in (1, 2):
            raise ValueError("Expected a recovery header and optional snapshot frame")
        _version, request_id, epoch, revision, has_state = check_envelope(
            deserialize(frames[0], None), 5
        )
        V.check_nonempty_str(request_id, "request ID")
        if request_id != self.pending:
            return None
        V.check_nonempty_str(epoch, "epoch")
        V.check_nonneg_int(revision, "revision")
        V.check_bool(has_state, "snapshot present")
        if len(frames) != 1 + int(has_state):
            raise ValueError("Snapshot flag does not match response frames")
        if has_state:
            state = deserialize(frames[1], None)
            check_state(state)
            if revision == 0:
                raise ValueError("Snapshot revision must be positive")
            if (
                epoch == self.epoch
                and self.state is not None
                and type(state) is not type(self.state)
            ):
                raise ValueError("Data type changed within an epoch")
        else:
            state = None
        return epoch, revision, state

    def _open_dealer_socket(self) -> zmq.Socket:
        if self.socket is None:
            self.socket: zmq.Socket = self.context.zmq_context().socket(zmq.DEALER)
            self.socket.setsockopt(zmq.LINGER, 0)
            self.socket.setsockopt(zmq.SNDHWM, 1)
            self.socket.connect(self.endpoint)
            self.context.poller.register(self.socket, zmq.POLLIN)
        return self.socket

    def poll(self):
        """Perform nonblocking recovery on the subscription thread."""

        # open socket here (not __init__()) to make sure it's owned by subscription thread
        self.socket = self._open_dealer_socket()

        now = time.monotonic()
        for _ in range(8):
            try:
                frames = self.socket.recv_multipart(zmq.NOBLOCK)
            except zmq.Again:
                break
            try:
                res = self._deserialize(frames)
                if res is None:
                    continue
                epoch, revision, state = res
            except Exception as e:
                self._reject(e)
                continue
            self.pending = None
            self._pending_request = None
            if (epoch, revision) == (self.epoch, self.revision):
                self.needs_snapshot = False
                self.next_query = now + 1.0
            elif state is not None and (epoch != self.epoch or revision > self.revision):
                self.state, self.epoch, self.revision = state, epoch, revision
                self.needs_snapshot = False
                self.next_query = now + 1.0
                self.deliver()
            elif revision and (epoch != self.epoch or revision > self.revision):
                self.needs_snapshot = True
                self.next_query = 0.0
        if now >= self.next_query and (self.pending is None or now >= self.deadline):
            # A timeout retries the same logical request. Its original response remains
            # valid even if acquisition or transfer takes longer than the retry interval.
            request = self._pending_request
            if request is None:
                request = (
                    VERSION,
                    uuid.uuid4().hex,
                    self.epoch,
                    self.revision,
                    self.needs_snapshot,
                )
            try:
                self.socket.send(serialize_pickle(request), zmq.NOBLOCK)
            except zmq.Again:
                pass
            else:
                self.pending = request[1]
                self._pending_request = request
                self.deadline = now + 5.0
            self.next_query = now + 1.0

    def close(self):
        """Close the recovery socket after the subscription loop stops."""

        if self.socket is not None:
            self.socket.close()


def add_data_subscription(context, conf, topic, handler, msg_type=None, logger=None):
    """Select reconstruction only for the configured measurement data topic."""

    if topic in (b"data", "data") and TransportConfig(conf).mode == "incremental":
        return IncrementalSubscriber(context, conf, handler, logger=logger)
    context.add_sub(conf["pub_endpoint"], topic, handler, msg_type)
