#!/usr/bin/env python3

"""
ZMQ-based loggers for mahos Nodes.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations
import sys
import io
import logging
from logging.handlers import QueueHandler
from collections import deque
import threading
import traceback

import zmq

TOPIC_DELIM = "->"
TIME_DELIM = ";"


class PUBHandler(logging.Handler):
    """A basic logging handler that emits log messages through a PUB socket.

    :param socket: a PUB socket already bound to interfaces.

    Log messages handled by this handler are broadcast with ZMQ topics
    `(self.root_topic->)loglevel(->additional_topic)`.
    Here, the log level is DEBUG, INFO, WARN, etc.
    The additional_topic can be included by submitting the log message like:
    log.info("additional_topic->real message")

    """

    def __init__(self, socket: zmq.Socket, root_topic: str = ""):
        logging.Handler.__init__(self)
        self._socket_closed = False
        self._root_topic = root_topic
        self.formatters = {
            logging.DEBUG: logging.Formatter(
                f"%(asctime)s{TIME_DELIM}%(message)s (%(filename)s:%(lineno)d)\n"
            ),
            logging.INFO: logging.Formatter(f"%(asctime)s{TIME_DELIM}%(message)s\n"),
            logging.WARN: logging.Formatter(
                f"%(asctime)s{TIME_DELIM}%(message)s (%(filename)s:%(lineno)d)\n"
            ),
            logging.ERROR: logging.Formatter(
                f"%(asctime)s{TIME_DELIM}%(message)s (%(filename)s:%(lineno)d)\n"
            ),
            logging.CRITICAL: logging.Formatter(
                f"%(asctime)s{TIME_DELIM}%(message)s (%(filename)s:%(lineno)d)\n"
            ),
        }
        if not isinstance(socket, zmq.Socket):
            raise ValueError("zmq.Socket must be given")

        self.socket = socket

    @property
    def root_topic(self):
        return self._root_topic

    @root_topic.setter
    def root_topic(self, value):
        self.setRootTopic(value)

    def setRootTopic(self, root_topic):
        """Set the root topic for this handler.

        This value is prepended to all messages published by this handler, and it
        defaults to the empty string ''. When you subscribe to this socket, you must
        set your subscription to an empty string, or to at least the first letter of
        the binary representation of this string to ensure you receive any messages
        from this handler.

        If you use the default empty string root topic, messages will begin with
        the binary representation of the log level string (INFO, WARN, etc.).
        Note that ZMQ SUB sockets can have multiple subscriptions.
        """

        self._root_topic = root_topic

    def setFormatter(self, fmt, level=logging.NOTSET):
        """Set the Formatter for this handler.

        If no level is provided, the same format is used for all levels. This
        will overwrite all selective formatters set in the object constructor.
        """

        if level == logging.NOTSET:
            for fmt_level in self.formatters.keys():
                self.formatters[fmt_level] = fmt
        else:
            self.formatters[level] = fmt

    def format(self, record):
        """Format a record."""

        return self.formatters[record.levelno].format(record)

    def emit(self, record):
        """Emit a log message on my socket."""

        if self._socket_closed:
            return

        try:
            topic, record.msg = record.msg.split(TOPIC_DELIM, 1)
        except Exception:
            topic = ""
        try:
            bmsg = self.format(record).encode("utf-8")
        except Exception:
            self.handleError(record)
            return

        topic_list = []

        if self.root_topic:
            topic_list.append(self.root_topic)

        topic_list.append(record.levelname)

        if topic:
            topic_list.append(topic)

        btopic = TOPIC_DELIM.join(topic_list).encode("utf-8")

        self.socket.send_multipart([btopic, bmsg])

    def close(self):
        """Close the PUB socket and this handler."""

        self.acquire()
        try:
            if self._socket_closed:
                return
            self._socket_closed = True
            try:
                self.socket.close()
            finally:
                logging.Handler.close(self)
        finally:
            self.release()


class TopicLogger(logging.Logger):
    def __init__(self, name):
        logging.Logger.__init__(self, name)
        self._topic = None

    def set_topic(self, topic):
        self._topic = topic

    def _fix_msg(self, msg):
        if self._topic:
            return TOPIC_DELIM.join((self._topic, msg))
        else:
            return msg

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        msg = self._fix_msg(msg)
        logging.Logger._log(
            self,
            level,
            msg,
            args,
            exc_info=exc_info,
            extra=extra,
            stack_info=stack_info,
            stacklevel=stacklevel + 1,
        )


class QueuedLogger(logging.Logger):
    """Forward worker-thread records only from the thread that created this logger.

    ``poll()`` drains a bounded queue through the destination logger. Exception text is
    captured at enqueue time, without retaining traceback frames. On overflow new records
    are dropped and a warning is emitted at the next drain. ``close()`` performs a final
    drain after producers have stopped and rejects subsequent records. ``closed`` becomes
    true after that drain, allowing parent contexts to remove their registration. Calls
    to ``poll()`` from other threads are no-ops.

    """

    def __init__(self, destination):
        super().__init__(getattr(destination, "name", "queued"), logging.DEBUG)
        self.destination = destination
        self.owner_thread = threading.get_ident()
        self._records = deque()
        self._queue_lock = threading.Lock()
        self._dropped = 0
        self._closing = False
        self._closed = False
        self._prepare = QueueHandler(None).prepare

    def handle(self, record):
        """Capture a record without invoking any destination handlers."""

        with self._queue_lock:
            if self._closing:
                return
        record = self._prepare(record)
        with self._queue_lock:
            if self._closing:
                return
            if len(self._records) >= 1024:
                self._dropped += 1
            else:
                self._records.append(record)

    def _forward(self, record):
        if isinstance(self.destination, logging.Logger):
            if not self.destination.isEnabledFor(record.levelno):
                return
            record.name = self.destination.name
            if isinstance(self.destination, TopicLogger):
                record.msg = self.destination._fix_msg(record.msg)
            self.destination.handle(record)
        else:
            if record.levelno >= logging.ERROR:
                method = "error"
            elif record.levelno >= logging.WARNING:
                method = "warning"
            elif record.levelno >= logging.INFO:
                method = "info"
            else:
                method = "debug"
            getattr(self.destination, method)(record.getMessage())

    def poll(self):
        """Forward queued records on the owning thread, preserving their origin."""

        if threading.get_ident() != self.owner_thread:
            return
        with self._queue_lock:
            if self._closed:
                return
            records = list(self._records)
            self._records.clear()
            dropped, self._dropped = self._dropped, 0
        for record in records:
            self._forward(record)
        if dropped:
            self._forward(
                logging.LogRecord(
                    self.name,
                    logging.WARNING,
                    __file__,
                    0,
                    f"Dropped {dropped} queued log records",
                    (),
                    None,
                )
            )

        with self._queue_lock:
            self._closed = self._closing and not self._records and not self._dropped

    @property
    def closed(self) -> bool:
        """Return whether closure and the final owning-thread drain have completed."""

        with self._queue_lock:
            return self._closed

    def close(self):
        """Stop accepting records and flush on the owner, now or at its next poll."""

        with self._queue_lock:
            self._closing = True
        self.poll()


class DummyLogger(object):
    """Dummy logger. Just prints messages."""

    def __init__(self, name: str = ""):
        self.name = name

    def debug(self, msg, *args, **kwargs):
        print(f"[DEBUG] {self.name} {msg}")

    def info(self, msg, *args, **kwargs):
        print(f"[INFO] {self.name} {msg}")

    def warn(self, msg, *args, **kwargs):
        print(f"[WARN] {self.name} {msg}")

    def warning(self, msg, *args, **kwargs):
        print(f"[WARN] {self.name} {msg}")

    def exception(self, msg, *args, exc_info=True, **kwargs):
        self.error(msg, *args, exc_info=exc_info, **kwargs)

    def format_exc(self, ei):
        """Taken from logging.Formatter.formatException()."""

        sio = io.StringIO()
        tb = ei[2]
        traceback.print_exception(ei[0], ei[1], tb, None, sio)
        s = sio.getvalue()
        sio.close()
        if s[-1:] == "\n":
            s = s[:-1]
        return s

    def print_exc(self):
        print(self.format_exc(sys.exc_info()))

    def error(self, msg, *args, **kwargs):
        print(f"[ERROR] {self.name} {msg}")
        if kwargs.get("exc_info"):
            self.print_exc()


class NullLogger(DummyLogger):
    """Dummy logger. Silently discards debug/info messages."""

    def __init__(self, name: str = ""):
        self.name = name

    def debug(self, msg, *args, **kwargs):
        pass

    def info(self, msg, *args, **kwargs):
        pass


def get_topic_logger(prefix, name):
    if prefix:
        full_name = ".".join((prefix, name))
    else:
        full_name = name
    logging.setLoggerClass(TopicLogger)
    logger = logging.getLogger(full_name)
    logger.set_topic(name)
    return logger


def init_topic_logger(
    topic: str, prefix: str | None = None
) -> tuple[TopicLogger | DummyLogger, str]:
    """Initialize TopicLogger and return (TopicLogger, full_name).

    If prefix is None, return (DummyLogger, topic).

    """

    if prefix is None:
        return DummyLogger(topic), topic

    return get_topic_logger(prefix, topic), TOPIC_DELIM.join((prefix, topic))
