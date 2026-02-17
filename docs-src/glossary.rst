Glossary
========

.. currentmodule:: mahos

.. glossary::

   node
      A node is a program that is part of a distributed system. It is implemented as a subclass of :class:`Node <node.node.Node>` or :class:`GUINode <gui.gui_node.GUINode>`.

   client
   node client
      Interface to :term:`node`'s functions. Implemented as a subclass of :class:`NodeClient <node.client.NodeClient>`.

   conf
      Configuration (dict) for something. Unlike params, conf is considered static (it will not change at runtime).

   params
      Parameters (dict) for something. Unlike conf, params are considered dynamic (they will change at runtime).

   gparams
   global params
      A dict with global parameters which is handled by :class:`GlobalParams <node.global_params.GlobalParams>`.

   Req-Rep
      Request-Reply communication pattern. The client sends a request and the server sends back a reply.

   RPC
      Abbreviation of Remote Procedure Call. Req-Rep is a typical RPC pattern.

   Pub-Sub
      Publish-Subscribe communication pattern. One-to-many data distribution.

   status
      Messages expressing the node's status. Implemented as a subclass of :class:`Status <mahos.msgs.common_msgs.Status>`. Usually published as the topic `status`.

   state
      A :class:`Node <node.node.Node>` can have an explicit state. If so, it is implemented as a subclass of :class:`State <mahos.msgs.common_msgs.State>` and is usually contained as an attribute of :term:`status`.
