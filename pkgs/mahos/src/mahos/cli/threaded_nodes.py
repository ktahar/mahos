#!/usr/bin/env python3

"""
Runner for threaded nodes for mahos run/launch.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

import os
import time
import importlib
import multiprocessing as mp

from mahos.node.node import Node, join_name, local_conf, start_node_thread, threaded_nodes
from mahos.node.comm import Context


def is_gui_node_class(NodeClass):
    from mahos.gui.gui_node import GUINode

    return issubclass(NodeClass, GUINode)


def is_gui_like_conf(conf: dict) -> bool:
    module = conf.get("module", "")
    class_name = conf.get("class", "")
    return ".gui." in module or class_name.endswith("GUI")


def gui_nodes_in_group(gconf: dict, host: str, node_names: list[str]) -> list[str]:
    gui_names = []
    for node_name in node_names:
        conf = local_conf(gconf, join_name((host, node_name)))
        if is_gui_like_conf(conf):
            gui_names.append(node_name)
    return gui_names


def start_gui_node_thread_lazy(ctx: Context, NodeClass, gconf: dict, name: str):
    from mahos.gui.gui_node import start_gui_node_thread

    return start_gui_node_thread(ctx, NodeClass, gconf, name)


class ThreadedNodes(object):
    """Runner for threaded nodes."""

    def __init__(self, gconf, host, name):
        self.gconf = gconf
        self.host = host
        self.name = name
        self.threads = {}
        self.class_names = {}
        self.shutdown_events = {}
        self.check_interval_sec = 0.5
        self.shutdown_delay_sec = 0.5
        self.shutdown_order = ["InstrumentServer", "LogBroker"]  # GlobalParams?

    def start(self):
        ctx = Context()

        tnodes = threaded_nodes(self.gconf, self.host)
        if self.name not in tnodes:
            raise KeyError(f"Threaded nodes {self.name} at {self.host} is not defined.")
        print(
            "Starting thread::{}::{} ({}).".format(
                self.host, self.name, ", ".join(tnodes[self.name])
            )
        )
        gui_names = gui_nodes_in_group(self.gconf, self.host, tnodes[self.name])
        if gui_names and os.name == "nt":
            joined = ", ".join(gui_names)
            print(
                f"[WARN] Threaded nodes '{self.name}' include GUI node(s): {joined}. "
                "Mixing GUINode with non-GUI nodes in one threaded process is strongly "
                "discouraged on Windows "
                "because native module import order can cause crashes."
            )

        for node_name in tnodes[self.name]:
            name = join_name((self.host, node_name))
            conf = local_conf(self.gconf, name)
            module = importlib.import_module(conf["module"])
            NodeClass = getattr(module, conf["class"])

            if issubclass(NodeClass, Node):
                thread, ev = start_node_thread(ctx, NodeClass, self.gconf, name)
            elif is_gui_node_class(NodeClass):
                thread = start_gui_node_thread_lazy(ctx, NodeClass, self.gconf, name)
                ev = None

            self.threads[name] = thread
            if ev is not None:
                self.shutdown_events[name] = ev
            self.class_names[name] = conf["class"]

    def check_alive(self):
        terminated = []
        for name, thread in self.threads.items():
            if not thread.is_alive():
                print("{} has been terminated.".format(name))
                terminated.append(name)
        for name in terminated:
            del self.threads[name]

    def shutdown_nodes(self):
        """Shutdown nodes gracefully by sending shutdown events."""

        # Nodes not in shutdown_order
        for name, ev in self.shutdown_events.items():
            if self.class_names[name] not in self.shutdown_order:
                print("Sending shutdown signal to {}.".format(name))
                ev.set()

        time.sleep(self.shutdown_delay_sec)

        # Nodes in shutdown_order
        for class_name in self.shutdown_order:
            for name, ev in self.shutdown_events.items():
                if self.class_names[name] == class_name:
                    print("Sending shutdown signal to {}.".format(name))
                    ev.set()
            time.sleep(self.shutdown_delay_sec)

    def main_interrupt(self):
        try:
            self.start()
            while True:
                self.check_alive()
                time.sleep(self.check_interval_sec)
        except KeyboardInterrupt:
            print(f"KeyboardInterrupt: Exitting ThreadedNodes({self.name}).")
        finally:
            self.shutdown_nodes()

    def main_event(self, shutdown_ev):
        try:
            self.start()
            while not shutdown_ev.is_set():
                self.check_alive()
                time.sleep(self.check_interval_sec)
        except KeyboardInterrupt:
            print(f"KeyboardInterrupt: Exitting ThreadedNodes({self.name}).")
        finally:
            self.shutdown_nodes()


def run_threaded_nodes_proc(gconf: dict, host: str, name: str, shutdown_ev: mp.Event):
    tn = ThreadedNodes(gconf, host, name)
    tn.main_event(shutdown_ev)


def start_threaded_nodes_proc(
    ctx: mp.context.BaseContext, gconf: dict, host: str, name: str
) -> (mp.Process, mp.Event):
    shutdown_ev = mp.Event()
    proc = ctx.Process(target=run_threaded_nodes_proc, args=(gconf, host, name, shutdown_ev))
    proc.start()
    return proc, shutdown_ev
