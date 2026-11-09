"""
Incremental measurement data transport with snapshot recovery.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

import copy
import logging
import time
import uuid
from dataclasses import dataclass

import numpy as np
import zmq

from mahos.node.comm import serialize_pickle, deserialize
from mahos.node.transport.config import TransportConfig
import mahos.util.validation as V


TOPIC = b"incremental_data"
VERSION = 2


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


def check_request(request):
    """Validate a live-data recovery request before interpreting its arguments."""

    _version, request_id, epoch, revision, snapshot = check_envelope(request, 5)
    V.check_nonempty_str(request_id, "request ID")
    if epoch is not None:
        V.check_nonempty_str(epoch, "epoch")
    V.check_nonneg_int(revision, "revision")
    V.check_bool(snapshot, "snapshot")
    if epoch is None and revision != 0:
        raise ValueError("A request without an epoch must have revision zero")
    return request_id, epoch, revision, snapshot


def check_state(state):
    """Require an attribute-based data object, rather than a scalar or container."""

    if isinstance(state, type) or not hasattr(state, "__dict__"):
        raise ValueError("Expected an attribute-based data object")
    return state


@dataclass(frozen=True)
class ArrayPolicy:
    """Describe append-only, mutable-tail, or counted rolling arrays.

    For counted rolling arrays, ``count_attr`` names the cumulative number of appended slices.
    The array contains the latest slices ending at that count; retained slices must be immutable.

    With ``sequence=True``, apply the policy to each array in a list.
    ``count_attr`` then names per-element counters; the generation token remains shared.

    For the array which is subject to individual reset (c.f. whole data reset by ``invalidate()``),
    ``generation_attr`` names a scalar token whose change forces replacement, including
    same-shaped rebuilds. A missing token (for older saved data) is treated as ``None``.

    """

    axis: int
    mutable_tail: int = 0
    count_attr: str | None = None
    generation_attr: str | None = None

    sequence: bool = False

    def __post_init__(self):
        V.check_bool(self.sequence, "sequence")
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
        old = getattr(previous, name, None)
        if isinstance(operation, list):
            items = operation
            base = old if isinstance(old, list) and len(old) == len(items) else [None] * len(items)
            value = [_assemble_array(prev, op) for prev, op in zip(base, items)]
        else:
            value = _assemble_array(old, operation)
        setattr(result, name, value)
    return result


def _assemble_array(old, operation):
    """Apply one validated array operation without mutating its base."""

    if not isinstance(operation, tuple) or len(operation) != 4:
        raise ValueError("Expected a four-field array operation tuple")
    axis, drop, start, payload = operation
    V.check_nonneg_int(axis, "axis")
    V.check_nonneg_int(drop, "drop")
    V.check_nonneg_int(start, "start")
    if payload is not None:
        if not isinstance(payload, np.ndarray) or payload.dtype.hasobject or axis >= payload.ndim:
            raise ValueError("Invalid array payload or axis")
    elif start:
        raise ValueError("Cannot append None to an array")
    if start == 0:
        value = payload
    else:
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
    return value


class IncrementalPublisher:
    """Publish array suffixes and serve immutable, revisioned snapshots.

    Published prefixes must remain unchanged except for the configured mutable tail.
    Call ``invalidate()`` before the next publication after other in-place edits,
    unless a policy's generation token forces replacement of the affected array.
    Replacing the source object or calling ``invalidate()`` starts a new epoch.

    Publication runs on the node thread; a dedicated service handles snapshot requests.
    The caller supplies a service, which registers itself with its context for shutdown.
    This removes recovery serialization from the measurement thread, but does not eliminate
    CPU or memory-bandwidth contention. Publications (and client reconstructions) copy arrays.

    Each update contains the epoch, base and new revisions, a deep copy of metadata, and
    per-array ``(axis, drop, start, payload)`` tuples (lists of tuples for sequence policies).
    An operation retains ``start``
    slices after dropping ``drop`` leading slices from the previous array, then appends the
    copied payload; ``start == 0`` replaces the array.
    This supports both mutable tails and rolling arrays with cumulative slice counters.

    Each publication captures metadata and payloads before returning to the worker and
    commits the reconstructed replica before sending the update.
    Committed replicas are never mutated by the publisher.

    """

    def __init__(self, context, endpoint, policies, service, logger=None):
        if service is None:
            raise ValueError("IncrementalPublisher requires a snapshot service")
        if not policies:
            raise ValueError("This measurement does not define incremental array policies")
        self.policies = policies
        self.service = service
        self.publisher = context.add_pub(endpoint, TOPIC, logger=logger)
        self.epoch = uuid.uuid4().hex
        self.revision = 0
        self.state = None
        self.source = None
        self.logger = self.publisher.logger

    def invalidate(self):
        """Start a new generation on the next publication."""

        self.source = None

    def _extract(self, msg, reset, name, policy, index=None):
        """extract incremental array update operation."""

        value = getattr(msg, name)
        old = getattr(self.state, name) if self.state is not None else None
        if index is not None:
            value = value[index]
            old = (
                old[index]
                if isinstance(old, list) and len(old) == len(getattr(msg, name))
                else None
            )

        def counter(state):
            count = getattr(state, policy.count_attr)
            return count if index is None else count[index]

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
                    count = V.check_nonneg_int(counter(msg), policy.count_attr)
                    old_count = V.check_nonneg_int(counter(self.state), policy.count_attr)
                    new_begin = count - value.shape[axis]
                    old_begin = old_count - old.shape[axis]
                    if count >= old_count and new_begin >= old_begin:
                        start = max(0, old_count - new_begin)
                        drop = old.shape[axis] - start
                elif old.shape[axis] <= value.shape[axis]:
                    start = max(0, old.shape[axis] - policy.mutable_tail)
            if policy.count_attr is not None:
                count = V.check_nonneg_int(counter(msg), policy.count_attr)
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
            if policy.sequence:
                values = getattr(msg, name)
                if not isinstance(values, list):
                    raise ValueError(f"{name} must be a list of arrays")
                if policy.count_attr is not None:
                    counts = getattr(msg, policy.count_attr)
                    if not isinstance(counts, (list, np.ndarray)) or len(counts) != len(values):
                        raise ValueError(f"{name}: counters must match array list length")
                operations[name] = [
                    self._extract(msg, reset, name, policy, i) for i in range(len(values))
                ]
            else:
                operations[name] = self._extract(msg, reset, name, policy)
        state = assemble(self.state, metadata, operations)
        if reset:
            self.epoch = uuid.uuid4().hex
            self.revision = 0
        update = (VERSION, self.epoch, self.revision, self.revision + 1, metadata, operations)
        self.source = msg
        self.state = state
        self.revision += 1
        self.service.commit(self.epoch, self.revision, state)
        self.publisher.publish(update)


class IncrementalSubscriber:
    """Reconstruct data and periodically recover missing revisions.

    Clients request a snapshot on startup and after a missing revision,
    and check the latest revision about once per second even while acquisition is idle.
    Updates without a matching base are discarded and trigger a snapshot request;
    this avoids an unbounded startup buffer.
    Unanswered requests are retried after five seconds using the same request ID and arguments,
    so responses remain valid when acquisition or transfer takes longer.
    Duplicate responses are ignored once the logical request completes.
    Recovery uses a separate DEALER socket owned by the subscription thread, with one logical
    request outstanding at a time. Polling is nonblocking and does not use the client's ordinary
    measurement request socket. Revision checks detect missed final updates even when no
    further publications arrive.

    Updates are validated and assembled before replacing the private replica. Handlers receive
    deep copies of complete revisions, so their mutations cannot affect later reconstruction.
    A disconnected client retains its last complete data object; recovery may skip intermediate
    revisions.

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

    def _deliver(self):
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
        self._deliver()  # Application handler exceptions must propagate normally.

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
                self._deliver()
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
