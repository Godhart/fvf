import copy
import time
from core.simple_logging import vprint, eprint, exprint


def _mc_gen():
    """
    Used by all TalkChannels when logging messages to preserve messages order
    :return:
    """
    n = 1
    while True:
        yield n
        n += 1


_mc = _mc_gen()  # An instance of _mc_gen that should be used by talk channels when getting order number for message log


class PlatformixPreferecenes(object):
    """
    Contains global platformix setup data
    """

    def __init__(self):
        self._platform_start_timeout = 10.0  # By default 10 seconds max are given for platforms to start
        self._platform_stop_timeout = 10.0   # By default 10 seconds max are given for platforms to stop

    @property
    def multithreading(self):
        return False

    @property
    def platform_start_timeout(self):
        return self._platform_start_timeout

    @platform_start_timeout.setter
    def platform_start_timeout(self, value):
        self._platform_start_timeout = value

    @property
    def platform_stop_timeout(self):
        return self._platform_stop_timeout

    @platform_stop_timeout.setter
    def platform_stop_timeout(self, value):
        self._platform_stop_timeout = value

    @property
    def send_message_print_level_change(self):
        return False


pref = PlatformixPreferecenes()


class PlatformMessage(object):
    """
    Class for information transfer between platforms (calls and replies)
    And it's called "Message"
    """
    _signature = 0x1400

    def __init__(self, sender=None, interface=None, method=None, args=None, kwargs=None):
        """
        :param sender: Source of message. Symbolic name expected
        :param interface: Symbolic name of interface that is used
        :param method: Symbolic name of method that should be called or indication of reply
        :param args: Args to method
        :param kwargs: Keyworded args to method or reply data
        """
        self.sender = sender
        self.interface = interface
        self.method = method
        self.args = args
        if self.args is None:
            self.args = []
        self.kwargs = kwargs
        if self.kwargs is None:
            self.kwargs = {}

    @classmethod
    def parse(cls, message):
        """
        Transforms message into PlatformMessage object
        :param message: serialized message of PlatformMessage object
        :return: recreated PlatformMessage object
        """
        if isinstance(message, PlatformMessage):
            inst = PlatformMessage.parse(message.serialize())
            return inst
        inst = PlatformMessage()
        if message is not None:
            assert isinstance(message, (list, tuple)), "Message is expected to be a list or a tuple"
            assert len(message) >= 4, "Message's length expected to be at least 4"
            assert message[0] == PlatformMessage._signature, "Message's signature is incorrect"
            inst.sender = message[1]
            inst.interface = message[2]
            inst.method = message[3]
            if len(message) > 4:
                assert isinstance(message[4], (list, tuple)), "Message's args expected to be list or tuple"
                inst.args = copy.deepcopy(message[4])
            if len(message) > 5:
                assert isinstance(message[5], dict), "Message's kwargs expected to be a dict"
                inst.kwargs = copy.deepcopy(message[5])
        return inst

    @classmethod
    def get_sender(cls, message):
        """
        Return sender of serialized message
        :param message:
        :return:
        """
        if message is not None:
            if isinstance(message, PlatformMessage):
                return message.sender
            assert isinstance(message, (list, tuple)), "Message is expected to be a list or a tuple"
            assert len(message) >= 4, "Message's length expected to be at least 4"
            assert message[0] == PlatformMessage._signature, "Message's signature is incorrect"
            return message[1]
        return None

    @classmethod
    def get_interface(cls, message):
        """
        Return interface of serialized message
        :param message:
        :return:
        """
        if message is not None:
            if isinstance(message, PlatformMessage):
                return message.interface
            assert isinstance(message, (list, tuple)), "Message is expected to be a list or a tuple"
            assert len(message) >= 4, "Message's length expected to be at least 4"
            assert message[0] == PlatformMessage._signature, "Message's signature is incorrect"
            return message[2]
        return None

    @classmethod
    def get_method(cls, message):
        """
        Return method of serialized message
        :param message:
        :return:
        """
        if message is not None:
            if isinstance(message, PlatformMessage):
                return message.method
            assert isinstance(message, (list, tuple)), "Message is expected to be a list or a tuple"
            assert len(message) >= 4, "Message's length expected to be at least 4"
            assert message[0] == PlatformMessage._signature, "Message's signature is incorrect"
            return message[3]
        return None

    @classmethod
    def get_args(cls, message):
        """
        Return args of serialized message
        :param message:
        :return:
        """
        if message is not None:
            if isinstance(message, PlatformMessage):
                return message.args
            assert isinstance(message, (list, tuple)), "Message is expected to be a list or a tuple"
            assert len(message) >= 4, "Message's length expected to be at least 4"
            assert message[0] == PlatformMessage._signature, "Message's signature is incorrect"
            if len(message) > 4:
                return copy.deepcopy(message[4])
            else:
                return None
        return None

    @classmethod
    def get_kwargs(cls, message):
        """
        Return kwargs of serialized message
        :param message:
        :return:
        """
        if message is not None:
            if isinstance(message, PlatformMessage):
                return message.kwargs
            assert isinstance(message, (list, tuple)), "Message is expected to be a list or a tuple"
            assert len(message) >= 4, "Message's length expected to be at least 4"
            assert message[0] == PlatformMessage._signature, "Message's signature is incorrect"
            if len(message) > 5:
                return copy.deepcopy(message[5])
            else:
                return None
        return None

    def serialize(self):
        """
        Transforms self into list with key fields values
        :return: list of values (key fields of object)
        """
        return [self._signature, self.sender, self.interface, self.method, self.args, self.kwargs]

    @classmethod
    def success(cls, retval, retvalname='value'):
        """
        Creates message with reply indicating successfull ending of method call
        :param retvalname: returned value name. By default 'value' would be used
        :param retval: return value for reply.
                       If value is a dict and retvalname is None then reply's return value is retval.
                       A field with key '__result__' and value 'success' would be added to a dict
                       Otherwise reply's return value is a dict { revalname: retval }
        :return: PlatformMessage instance
        """
        if isinstance(retval, dict) and retvalname is None:
            retval["__result__"] = "success"    # TODO: right here just modified input dict. That's not good
        else:
            retval = {"__result__": "success", retvalname: retval}
        return PlatformMessage(method="__reply__", kwargs=retval)

    @classmethod
    def failure(cls, state, errcode=-1):
        """
        Creates message with reply indicating failiing ending of method call
        :param state: failing explanation
        :param errcode: error code for specific situations. By default -1 would be used
        :return: PlatformMessage instance
        """
        return PlatformMessage(method="__reply__", kwargs={"__result__": "fail", "state": state, "errcode": errcode})

    @classmethod
    def failure_exception(cls, state, exception):
        """
        Creates message with reply indicating failiing ending of method call by exception
        :param state: failing explanation
        :param exception: exception object
        :return: PlatformMessage instance
        """
        return PlatformMessage(method="__reply__", kwargs={"__result__": "fail", "state": state, "errcode": -2,
                                                           "e": exception})

    @classmethod
    def notify(cls, state):
        """
        Creates message with reply indicating some stage of method call is taken place
        :param state: current stage explanation
        :return: PlatformMessage instance
        """
        return PlatformMessage(method="__reply__", kwargs={"state": state})

    @classmethod
    def message_is_reply(cls, message):
        """
        :param message:
        :return: True if message is reply otherwise False
        """
        if message.method == "__reply__":
            return True
        return False

    @classmethod
    def message_is_success(cls, message):
        """
        :param message: PlatformMessage instance
        :return: True if message is success reply
        """
        if cls.message_is_reply(message) and message.kwargs.get("__result__", None) == "success":
            return True
        return False

    @classmethod
    def message_is_failure(cls, message):
        """
        :param message: PlatformMessage instance
        :return: True if message is failure reply
        """
        if cls.message_is_reply(message) and message.kwargs.get("__result__", None) == "fail":
            return True
        return False

    @classmethod
    def message_is_notify(cls, message):
        """
        :param message: PlatformMessage instance
        :return: True if message is notification reply otherwise False
        """
        if cls.message_is_reply(message) and message.kwargs.get("__result__", None) is None:
            return True
        return False

    @property
    def is_reply(self):
        """
        :return: True if message is reply
        """
        return self.message_is_reply(self)

    @property
    def is_success(self):
        """
        :return: True if message is success reply
        """
        return self.message_is_success(self)

    @property
    def is_failure(self):
        """
        :return: True if message is failure reply
        """
        return self.message_is_failure(self)

    @property
    def is_notify(self):
        """
        :return: True if message is notification reply
        """
        return self.message_is_notify(self)

    @property
    def reply_data(self):
        if self.is_reply:
            return self.kwargs
        else:
            return None


_pm = PlatformMessage  # Just a short cut name


def new_message(interface, method, *args, **kwargs):
    return _pm(None, interface, method, args, kwargs)


class TalkContext(object):
    """
    Class to hold context of conversation
    """
    def __init__(self, channel, thread, interface):
        self._channel = channel
        self._thread = thread
        self._interface = interface
        self._as_str = None

    def serialize(self):
        return self._channel, self._thread, self._interface

    @classmethod
    def deserialize(cls, serialized):
        if isinstance(serialized, (tuple, list)):
            assert len(serialized) == 3, "Expecting list/tuple with 3 items - channel, thread, interface"
            return TalkContext(*serialized)
        elif isinstance(serialized, str):
            data = serialized.split(':')
            assert len(data) != 3, "Expecting string with 3 items - channel, thread, interface, separated with ':'"
            return TalkContext(*data)
        else:
            raise ValueError("Expecting list/tuple with 3 items - channel, thread, interface"
                             " or string with 3 items - channel, thread, interface, separated with ':'")

    @property
    def channel(self):
        return self._channel

    @property
    def thread(self):
        return self._thread

    @property
    def interface(self):
        return self._interface

    @property
    def str(self):
        if self._as_str is None:
            self._as_str = ':'.join(str(l) for l in self.serialize())
        return self._as_str


class TalkChannel(object):
    """
    Class to manage subscription of platforms to a channel and send messages to subscribed instances
    To isolate different conversations messages are supplied with thread ID (which should be used by messages receivers)
    """

    def __init__(self, name, print_messages=False, gather_conversation=True, gather_all=False, timeref=0):
        """
        :param name: Channels's name
        :param print_messages: When True then all conversation is printed to stdout
        :param gather_conversation: When True then messages are logged
        :param gather_all: When False then logged only messages with response
        """
        self.name = name
        self.print_messages = print_messages
        self.gather_conversation = gather_conversation
        self.gather_all = gather_all
        self._timeref = timeref

        self._subscribers = []  # List of channels subscribers (instances refs)
        self._threads = []      # List of channels threads
        self._topics = []       # List of thread topics (first message in a thread)

        self._queue = []        # Queue of messages to send.
        # When sending message to multiple subscribers incoming send_message requests are queued
        # so different messages won't be shuffled with each other in chaotic order
        self._busy = False      # True if currently busy with sending certain message to subscribers

    def __del__(self):
        self._subscribers = []

    @property
    def subscribers(self):
        """
        :return: list with refs to all subscribers
        """
        return copy.copy(self._subscribers)

    @property
    def conversations(self):
        """
        :return: list with all conversations
        """
        return [self.conversation(t) for t in range(0, len(self._threads))]

    def conversation(self, thread):
        """
        Returns conversation for a thread
        :param thread: thread ID to get conversation for
        :return: list of strings formated for plantuml
        """
        assert isinstance(thread, int) and 0 <= thread < len(self._threads), "Thread {} don't exists at channel {}!".\
            format(thread, self.name)
        return self._threads[thread]["conversation"]

    def subscribe(self, inst):
        """
        Subscribes specified instance onto channel
        :param inst: ref to instance to subscribe
        :return: Nothing
        """
        if inst not in self._subscribers:
            self._subscribers.append(inst)
            vprint("{} is subscribed to {}".format(inst.name, self.name))

    def unsubscribe(self, inst):
        """
        Unsubscribes specified instance from channel
        :param inst: ref to instance to unsubscribe
        :return: Nothing
        """
        if inst in self._subscribers:
            self._subscribers.remove(inst)
            vprint("{} is unsubscribed from {}".format(inst.name, self.name))

    def start_thread(self, topic_caster, reply_to_tc=None):
        """
        Starts new thread
        :param topic_caster - a topic caster instance
        :param reply_to_tc - defines behaviour for replies
            if None(default) then messages are sent to subscribers and topic_caster
            if False then no messages sent to topic_caster
            if True then messages are sent to topic_caster only
        :return: new thread ID
        """
        thread_id = len(self._threads)
        self._threads.append({"tc": topic_caster, "reply_to_tc": reply_to_tc, "conversation": []})
        self._topics.append(None)
        if self.print_messages:
            vprint("{}: {} started thread {} @ channel {}".format(time.time() - self._timeref, topic_caster.name,
                                                                  thread_id, self.name))
        return thread_id

    def _log_conv(self, thread, conv, idx):
        """
        Creates conversation log in plant uml format (TODO: realy plant uml?)
        :param thread:
        :param conv:
        :param idx:
        :return:
        """
        values = conv[:-2]    # NOTE: 2 last it start/stop time
        values.append(conv[-1] - conv[-2])
        self._threads[thread]["conversation"].append("#{}:{} {} {} {} : {} ({})".format(idx, conv[-2], *values))
        # TODO: format idx as 6-digit number

    def send_message(self, context, message):
        """
        Sends message into thread
        :param context: messging context
        :param message: PlatformMessage instance with message content
        :return: None
        """
        if context.channel == "__void__":
            return
        if self._busy:
            self._queue.append((context, message))
            return
        thread = context.thread
        _msg = message
        message = message.serialize()
        self._busy = True
        if self._topics[thread] is None:
            assert not _msg.is_reply, "First message shouldn't be reply!\n" \
                                         "  were told to send into {}:{} message {}".format(self.name, thread, message)
            self._topics[thread] = ' '.join(str(m) for m in message)
            first_message = True
        else:
            assert _msg.is_reply, "Messages besides first should be replies!\n" \
                                     "  were told to send into {}:{} messaage {}".format(self.name, thread, message)
            first_message = False
        assert isinstance(thread, int) and 0 <= thread < len(self._threads), "Thread {} don't exists at channel {}!".\
            format(thread, self.name)
        if self.print_messages:
            if first_message:
                vprint("{}: Sending message {} to {}::{}".format(time.time() - self._timeref,
                                                                 message, self.name, thread))
            else:
                vprint("{}: Sending reply {} to {}::{}({})".format(time.time()  - self._timeref,
                                                                   message, self.name, thread,
                       self._topics[thread]))
        fail_idx = next(_mc)
        received_by = 0
        if self.gather_conversation:
            conv = [_msg.sender, "-->", None, message[2:], 0, 0]
        if not _msg.is_reply or self._threads[thread]["reply_to_tc"] is not True:
            for s in self._subscribers:
                if s.name == _msg.sender:    # Don't send message back to it's source
                    continue
                if s.name == self._threads[thread]["tc"].name \
                        and self._threads[thread]["reply_to_tc"] is not False:
                    # If s is topic caster and it would get reply - send it later (to avoid double sends)
                    continue
                if self.gather_conversation:
                    conv[-2] = time.time()
                idx = next(_mc)
                r = s.receive_message(context, message)
                if self.gather_conversation:
                    conv[-1] = time.time()
                if r not in (False, True):
                    self._busy = False
                    assert r in (False, True), \
                        "{}: Reply from {} contains no result or value({}) not in (False, True)".format(
                            time.time() - self._timeref, s.name, r)
                if r:
                    received_by += 1
                if self.gather_conversation and (r or self.gather_all):
                    if r:
                        conv[1] = "-->"
                    else:
                        conv[1] = "-->x"
                    conv[2] = s.name
                    self._log_conv(thread, conv, idx)

        if self._threads[thread]["reply_to_tc"] is not False:
            idx = next(_mc)
            r = self._threads[thread]["tc"].receive_message(context, message)
            if self.gather_conversation:
                conv[-1] = time.time()
            if r not in (False, True):
                self._busy = False
                assert r in (False, True), \
                    "{}: Reply from {} contains no result or value({}) not in (False, True)".format(
                        time.time() - self._timeref, self._threads[thread]["tc"].name, r)
            if r:
                received_by += 1
            if self.gather_conversation and (r or self.gather_all):
                if r:
                    conv[1] = "-->"
                else:
                    conv[1] = "-->x"
                conv[2] = self._threads[thread]["tc"].name
                self._log_conv(thread, conv, idx)

        if received_by < 1:
            if self.gather_conversation:
                conv[-1] = time.time()
            if self.print_messages:
                vprint("{}:  Message {} to {}::{} had no effect".format(time.time()  - self._timeref,
                                                                        message, self.name, thread))
            if self.gather_conversation:
                conv[1] = "-->x"
                conv[2] = None
                self._log_conv(thread, conv, fail_idx)
        self._busy = False
        if len(self._queue) > 0:
            queued = self._queue.pop(0)
            self.send_message(*queued)


class PlatformInterfaceCore(object):
    _base_id = "__None__"   # Base ID, used as a part of name to distinguish messages addressed to interface instance
                            # in common messages flow and to automatically bind worker's methods implementation
    _methods = ()           # List of supported methods, should be customized by derived classes
    # TODO: list of methods specification (args and output)

    """
    Defines interface (specification for methods calls)
    Used as bridge between platforms (implmentations) and talk channels
    """
    def __init__(self, host, worker=None, name="", mmap=None):
        """
        :param host: Host class that issues calls and processes replies
        :param worker: Class that handles calls. Host is used if None is specified
        :param name: Interface name to distinguish if there is multiple interfaces of same type on single
                     platform instance
        :param mmap: Map of interface functions to their implementations. By default interface is looking for method
                     on worker with name [_base_id]_[method_name]
        """
        # Common Interface
        self._host = host
        if worker is not None:
            self._worker = worker
        else:
            self._worker = self._host
        if name != "":
            self._name = "({})".format(name)
        else:
            self._name = ""
        self._id = self.name  # Use to distinguish interfaces's commands in common commands flow

        self._map = {}
        self._bind(mmap)

    @classmethod
    def base_id(cls):
        return cls._base_id

    @property
    def name(self):
        return "{}{}".format(self._base_id, self._name)

    @property
    def id(self):
        return self._id

    @property
    def host(self):
        return self._host

    def _bind(self, mmap):
        for m in self._methods:
            if mmap is not None and m in mmap and callable(mmap[m]):
                # TODO: check against method specification
                self._map = mmap[m]
            elif hasattr(self._worker, "_" + self._base_id + "_" + m) \
                    and callable(getattr(self._worker, "_" + self._base_id + "_" + m)):
                # TODO: check against method specification
                self._map[m] = getattr(self._worker, "_" + self._base_id + "_" + m)
            else:
                self._map[m] = None
                eprint("Interface {} of {} not found implmentation for method {}".format(
                    self.name, self.host.name, m))

    def supports(self, message):
        if message.interface == self._base_id \
                and message.method in self._methods and self._map[message.method] is not None:
            return True
        return False

    def _incoming_handler(self, context, message, fake_reply):
        """
        Incoming message handler that can be overridden by derived classes
        :param context: messaging context
        :param message: message content
        :return: True if message were processed, otherwise False
        """
        return self._map[message.method](context, fake_reply, *message.args, **message.kwargs)

    def incoming(self, context, message, fake_reply=None):
        """
        Common method for handling incoming messages from talk channel
        For customization redefine _incoming_handler please
        :param context: messaging context
        :param message: PlatformMessage instance with message's content
        :return: True if message were processed, otherwise False
        """
        if message.interface != self._id:
            return False
        if message.is_reply:
            return False
        if message.method not in self._methods:
            eprint("{}:{} Unsupported method {}".format(self._host.name, self._name, message.method))
            return False
        if self._map[message.method] is None:
            eprint("{}:{} Method {} is not implemented".format(self._host.name, self._name, message.method))
            return False
        self._incoming_handler(context, message, fake_reply)

    # TODO: sending messages to a channel (so interface can be used to properly form message)


class ProtocolReply(object):

    def __init__(self, success, retval, retval_name, state, errcode):
        self._success = success
        if self._success:
            self.retval = retval
            self.retval_name = retval_name
            self.state = ""
            self.errcode = 0
        else:
            self.retval = {}
            self.retval_name = None
            self.state = state
            self.errcode = errcode

    @property
    def success(self):
        return self._success


def proto_success(retval, retval_name="value"):
    return ProtocolReply(True, retval, retval_name, None, None)


def proto_failure(state, errcode=-1):
    return ProtocolReply(False, None, None, state, errcode)


def fake_op_message(interface, reply, on_channel=None, on_message=None, after=None, execute=False,
                    on_success=None, on_failure=None):
    """
    Prepares message for fake_next_op method
    :param interface: interface to fake op on
    :param reply: reply to op to be sent
    :param on_channel: if not None (string expected) then reply would be faked to op on this very channel
    :param on_message: if not None (PlatformMessage expected ) then reply would be faked only for that very op
    :param after: if not None (natural integer expected) then reply would be sent after that amount of messages, that
                  were matched conditions on_channel and on_message
    :param execute: if True then op would be actually executed, but reply would be faked. Default False
    :param on_success: if execute and (True or is None and on_failure is False) then success reply would be faked
    :param on_failure: if execute and (True or is None and on_success is False) then failure reply would be faked
    :return:
    """
    assert isinstance(interface, str), "fake_op_info: interface should be a string"
    assert isinstance(reply, ProtocolReply), "fake_op_info: reply should be a ProtocolReply instance"
    options = {"reply": reply}
    if on_channel is not None:
        assert isinstance(on_channel, str), "fake_op_info: on_channel should be a string"
        options["on_channel"] = on_channel
    if on_message is not None:
        assert isinstance(on_message, PlatformMessage), "fake_op_info: on_message should be a PlatformMessage instance"
        options["on_message"] = on_message
    if after is not None:
        assert isinstance(after, int) and after >= 0, "fake_op_info: after should be a natural integer"
        options["after"] = after
    if execute is not None:
        assert isinstance(execute, bool) or execute in (1, 0) >= 0, "fake_op_info: execute should be a boolean " \
                                                                    "or 0 or 1"
        options["execute"] = execute

        if on_success is None and on_failure is None:
            on_success = True
            on_failure = False
        if on_success is None and on_failure is False:
            on_success = True
        if on_failure is None and on_success is False:
            on_failure = True

        if on_success is True:
            assert isinstance(on_success, bool), "fake_op_info: on_success should be a boolean"
            options["on_success"] = on_success

        if on_failure is True:
            assert isinstance(on_failure, bool), "fake_op_info: on_failure should be a boolean"
            options["on_failure"] = on_failure
        else:
            options["on_failure"] = False

    return new_message(interface, "__testing__", "fake_next_op", options)


class PlatformProtocolCore(object):
    """
    An instance that implements interface's methods
    Used to separate platform from protocols implementation
    This class is base class and shouldn't be used by itself
    Derive class from this one and set _default_interface to class of Interface that is supported
    """
    _default_interface = None   # Protocol is a worker for that Interface Class (and it supports interface's methods)
    # NOTE: all protocols supports method 'testing'. It's built-in into PlatformProtocolCore
    _protocol_fields = ()    # Set of fields that should be supported by worker (look __init__ for details)
    _protocol_methods = ()   # Set of methods that should be supported by worker (look __init__ for details)

    def __init__(self, host, worker, interface=None, name=""):
        """
        :param host: PlatformBase derived object that hosts protocol
        :param worker: Object that is used to store protocol related data and provides actual protocol related methods
                       implementation. By default (if None) protocol itself is used
                       It is necessary that worker object have fields specified in _protcol_fields
                       and methods specified in _protocol_methods
        :param interface: Interface implementation class or instance
        :param name: Protocol's name if necessary to distinguish if platform hosts multiple protocols of same type
        """
        assert self._default_interface is not None, "No _default_interface is set to a protocol class {}.{}".format(
            self.__module__, self.__class__.__name__)
        # Ensure that worker holds all necessary variables
        for v in self._protocol_fields:
            assert hasattr(worker, v), "Not found protocol field {} in worker {} for protocol {} of {}".format(
                v, worker, self.name, self.host.name)
        for v in self._protocol_methods:
            assert hasattr(worker, v), "Not found protocol method {} in worker {} for protocol {} of {}".format(
                v, worker, self.name, self.host.name)
            assert callable(getattr(worker, v)), "Attribute {} in worker {} for protocol {} of {} should be callable".\
                format(v, worker, self.name, self.host.name)
        if hasattr(interface, "__name__"):  # TODO: is there better way to distinguish class from instance?
            assert interface.base_id() == self._default_interface.base_id(), "Only interface of type {} is supported".\
                format(self._default_interface.base_id())

        self._host = host
        self._worker = worker
        if interface is None:
            interface = self._default_interface
        if hasattr(interface, "__name__"):  # TODO: is there better way to distinguish class from instance?
            self._interface = interface(host=host, worker=self, name=name)
        else:
            self._interface = interface

        self._context = None    # Context for FSM methods
        self._fake_ops = {}     # Directions to fake some ops when running

    @property
    def name(self):
        return self._interface.name

    @property
    def id(self):
        return self._interface.id

    @property
    def host(self):
        return self._host

    @property
    def waiting_count(self):
        """
        :return: Amount of platforms in waiting list
        """
        if self._context is not None and "waiting_for" in self._context:
            return len(self._context["waiting_for"])
        else:
            return 0

    @property
    def waiting(self):
        """
        :return: List of platforms (their names) that are delaying protocol's operation
        """
        if self._context is not None and "waiting_for" in self._context:
            return copy.deepcopy(self._context["waiting_for"])
        else:
            return []

    @property
    def wait_ignore(self):
        """
        :return: List of platforms (their names) that are ignored to wait due to their errors
        """
        if self._context is not None and "wait_ignore" in self._context:
            return copy.deepcopy(self._context["wait_ignore"])
        else:
            return []

    @property
    def active_action(self):
        """
        :return: Current active protocol's action
        """
        if self._context is not None and "action" in self._context:
            return self._context["action"]
        else:
            return None

    def supports(self, message):
        """
        Checks whether incoming message could be processed
        :param message:
        :return: True if message can be processed otherwise False
        """
        if message.method == '__testing__':
            return True
        return self._interface.supports(message)

    def _notify(self, context, message):
        self._worker.reply(context, PlatformMessage.notify(message))

    def _notify_all(self, contexts, message):
        for c in contexts:
            self._notify(c, message)

    def _reply(self, context, result, fake_reply):
        assert isinstance(result, ProtocolReply), "Worker should return result as ProtocolReply instance"
        if fake_reply is not None:
            if result.success and "on_success" in fake_reply:
                result = fake_reply["on_success"]
            if (not result.success) and "on_failure" in fake_reply:
                result = fake_reply["on_failure"]
        if result.success:
            # TODO: Protocol (or even Interface) should define retval naming depending on context
            # i.e. which interface method were called
            self._worker.reply(context, PlatformMessage.success(result.retval, result.retval_name))
        else:
            self._worker.reply(context, PlatformMessage.failure(result.state, result.errcode))

    def _reply_all(self, contexts, result, fake_reply):
        for c in contexts:
            self._reply(c, result, fake_reply)

    def _ensure_running(self, context, fake_reply):
        if not self._worker.running:
            self._reply(context, proto_failure("Wasn't started!"), fake_reply)
            return False
        else:
            return True

    @staticmethod
    def _fake_message_compare(m1, m2):
        """
        Checks whether or not reply to message m2 should be faked
        If m1's field is None then m2's field value is not compared at all
        :param m1: Message template. Expected PlatformMessage instance
        :param m2: Message to check. Expected PlatformMessage instance
        :return: True if message are treated as equal otherwise - False
        """
        m1 = m1.serialize()
        m2 = m2.serialize()
        diff = False
        for i in range(len(m1)):
            if m1[i] is None:
                continue
            if m1[i] != m2[i]:
                diff = True
                break
        return not diff

    def _register_fake_next_op(self, channel, fake_info):
        """
        Registers information for faking replies
        :param channel: channel on which fake reply should be made. used if there is no "on_channel" in fake_info
        :param fake_info: faking information. A dict with info for single message or a list/tuple of dicts with info
            for multiple messages faking
            Each dict should contain fields:
                "reply" with ProtocolReply instance that would be sent as reply
            Each dict could contain fields:
                "execute" which set to True if along with faking command should be actually executed.
                          False or skip this field otherwise
                "on_channel" with channel name or list of channel names
                "on_message" with PlatformMessage object that would be used as template for comparing incoming messages
                          reply would be sent only to the one that will pass comparsion against template
                          If some fields should be skipped on comparsion - set them to None
                "after"   with Integer Number that specifies amount of messages that should be skipped before faking
                          If "message" is specified the only messages that passed comparsion are counted
        :return: None
        """
        assert isinstance(fake_info, (list, tuple, dict)), "fake_info should be a dict or list of dict or tuple of dict"
        if isinstance(fake_info, (tuple, list)):
            for f in fake_info:
                assert isinstance(f, dict), "fake_info should be a dict or list of dict or tuple of dict"

        if isinstance(fake_info, dict):
            fake_info = [copy.deepcopy(fake_info)]
        else:
            fake_info = [copy.deepcopy(f) for f in fake_info]
        for f in fake_info:
            assert "reply" in f, "fake_info should contain 'reply'"
            assert isinstance(f["reply"], ProtocolReply), "fake_info's reply should be a ProtocolReply instance"
            for o in f:
                assert o in ("reply", "execute", "on_message", "on_channel", "after", "on_success", "on_failure"), \
                    "Unsupported fake_info options: {}".format(o)
            if "execute" in f:
                assert isinstance(f["execute"], bool) or f["execute"] in (0, 1), \
                    "fake_info option 'execute' should be a bool or 0 or 1"

                if "on_success" in f:
                    assert isinstance(f["on_success"], bool), \
                        "fake_info option 'on_success' should be a boolean"

                if "on_failure" in f:
                    assert isinstance(f["on_failure"], bool), \
                        "fake_info option 'on_failure' should be a boolean"

                on_success = f.get("on_success", None)
                on_failure = f.get("on_failure", None)

                if on_success is None and on_failure is None:
                    on_success = True
                    on_failure = False

                if on_success is True or on_success is None and on_failure is False:
                    on_success = True

                if on_failure is True or on_success is None and on_success is False:
                    on_failure = True

                if on_success is True:
                    f["on_success"] = True
                else:
                    f["on_success"] = False
                if on_failure is True:
                    f["on_failure"] = True
                else:
                    f["on_failure"] = False

            if "on_message" in f:
                assert isinstance(f["on_message"], PlatformMessage), \
                    "fake_info option 'on_message' should be PlatformMessage"
            if "on_channel" in f:
                assert isinstance(f["on_channel"], (str, list, tuple)), \
                    "fake_info option 'on_channel' should be a string or list/tuple of strings"
            if isinstance(f["on_channel"], (list, tuple)):
                for c in f["on_channel"]:
                    assert isinstance(c, str), \
                        "fake_info option 'on_channel' should be a string or list/tuple of strings"
            if "after" in f:
                assert isinstance(f["after"], int), "fake_info option 'after' should be an integer"
            if "on_channel" not in f:
                on_channel = channel,
            elif isinstance(f["on_channel"], (list, tuple)):
                on_channel = f["on_channel"]
            else:
                on_channel = f["on_channel"],

            for c in on_channel:
                if c not in self._fake_ops:
                    self._fake_ops[c] = [f]
                else:
                    self._fake_ops[c].append(f)

    def _general_testing(self, context, kind, *args, **kwargs):
        """
        Implements method "__testing__" that would be supported by all protocols
        :param context: messaging context
        :param kind: kind of testing function. Only "fake_next_op" supported yet
        :param args: additional args, depends on kind
        :param kwargs: additional keyworded args, depends on kind
        :return: True if completed sucessfully otherwise False
        """
        if kind == "fake_next_op":
            self._register_fake_next_op(context.channel, *args, **kwargs)
            self._reply(context, proto_success({}, None), None)
            return True
        self._reply(context, proto_failure({"Unsupported testing function '{}'".format(kind)}), None)
        return False

    def _fake_next_op(self, context, message, dry_run=False):
        """
        Checks whether reply to this message should be faked and fakes it if required
        :param context: messaging context
        :param message: message content
        :return: True if reply were faked otherwise False
        """
        if context.channel in self._fake_ops:
            channel = context.channel
            if len(self._fake_ops[channel]) > 0:
                if "on_message" not in self._fake_ops[channel][0] \
                        or self._fake_message_compare(self._fake_ops[channel][0]["on_message"], message):
                    if "after" in self._fake_ops[channel][0] and self._fake_ops[channel][0]["after"] > 0:
                        if dry_run:
                            return False
                        self._fake_ops[channel][0]["after"] -= 1
                        return False
                    if dry_run:
                        return True
                    instruction = self._fake_ops[channel].pop(0)
                    if len(self._fake_ops[channel]) == 0:
                        del self._fake_ops[channel]
                    vprint("{}: faking reply".format(self.name))
                    reply = instruction["reply"]
                    if "execute" in instruction and instruction["execute"] == True:
                        result = {}
                        if instruction["on_success"]:
                            result["on_success"] = reply
                        if instruction["on_failure"]:
                            result["on_failure"] = reply
                        return result
                    if reply.success:
                        self._worker.reply(context, PlatformMessage.success(reply.retval, reply.retval_name))
                    else:
                        self._worker.reply(context, PlatformMessage.failure(reply.state, reply.errcode))
                    return True
            else:
                # TODO: Shouln't be here actually. Raise error!
                del self._fake_ops[channel]
        return False

    def _process_message_general(self, context, message):
        """
        Implements built-in methods of protocol base class
        :param context: messaging context
        :param message: message content
        :return: True if message were processed otherwise False
        """
        f = self._fake_next_op(context, message)

        if f is True:
            return True
        elif f is not False:
            return f
        elif message.method == "__testing__":
            self._general_testing(context, *message.args, **message.kwargs)
            return True
        else:
            return False

    def process_message(self, context, message):
        """
        Processes incoming message
        First tries to process protocol's builtins
        If message weren't processed by builtins then message is passed to protocol's interface object
        :param context: messaging context
        :param message: message content
        :return: None
        """
        r = self._process_message_general(context, message)
        if r is True:
            return
        elif r is not False:
            self._interface.incoming(context, message, r)
        else:
            self._interface.incoming(context, message, None)

    def _validate_context(self, content):
        """
        Validates that certain fields are exist in self._context and are having specified value
        Use to make sure if protocol's FSM is in right state
        :param content: dict. pairs of keys and values to compare self's context with
        :return: True if context's values are coresponding to specified, otherwise - False
        """
        result = False
        if self._context is not None:
            for k in content:
                if k not in self._context or self._context[k] != content[k]:
                    break
            result = True
        return result


class _ExposedFarmData(object):
    def __init__(self, platforms, awaiting, channels):
        self.platforms = platforms
        self.awaiting = awaiting
        self.channels = channels


class PlatformsFarm(object):
    """
    Class that hosts platforms instances
    Contains:
    * platforms instances itself
    * talk channels to allow communications between platforms
    """

    def __init__(self, env, verbose=False):
        self._timeref = time.time()
        self._env = env         # Reference to environment object
        self.verbose = verbose
        self._platforms = {}    # dict with platforms. Key is platform name and value is ref to instance
        self._awaiting = {}     # dict with platforms that were not registerd yet into main dict due to dependencies
        self._channels = {"__void__": TalkChannel("__void__", print_messages=self.verbose, timeref=self._timeref)
                          }     # dict with talk channels. Key is channel's name and value is ref to channel instance
        self._send_message_level = 0  # current nesting level of send message method
        # Since every message can invoke other message sending, send_message would be called multiple times
        # _send_message_level helps to track send_message nesting

        self._replies = {}      # nested dict structure:
        # level_1     - keys are channels
        #   level 2   - keys are threads
        #     level 3 - keys are message senders (names), values is last sent message

    def expose_data(self):
        """
        Exposes protected data to a caller. Be extremely careful with it contains originals, not a copies
        :return: class containing Farm's protected members
        """
        return _ExposedFarmData(self._platforms, self._awaiting, self._channels)

    def is_running(self, platform):
        """
        Returns running state for specified platform
        :param platform: platform to get state
        :return: True if platform is running otherwise - False
        """
        if platform not in self._platforms:
            raise ValueError("Platform {} is not registered".format(platform))
        return self._platforms[platform].running

    @property
    def channels(self):
        return self._channels.keys()

    @property
    def all_is_running(self):
        """
        Checks whether all platforms are running or not
        :return: True if all platforms are running otherwise False
        """
        return all(p.running for p in self._platforms.values())

    @property
    def all_is_stopped(self):
        """
        Checks whether all platforms are stopped or not
        :return: True if all platforms are NOT running otherwise False
        """
        return all(not p.running for p in self._platforms.values())

    def register_platform(self, factory, kind, parent=None, wait=None):
        """
        Registers new platform (or at least tries).
        If new platform depends on platforms that were not registered yet then registration of this platform
        would be deferred.
        Registration would be continued after registering all the platforms that this platform depends on
        :param factory: Factory instance that would create Platform's instance in case of success
        :param kind:    Platform's kind (it's module name)
        :param parent:  Parent's platform name
        :param wait:    List of platforms names that new platform depends on
        :return: Nothing
        """
        self._try_register_platform(factory, kind, parent, wait)

    def _try_register_platform(self, factory, kind, parent, wait, awaiting=False):
        """
        Worker method that do actually registers platform
        :param factory: Factory instance that would create Platform's instance
        :param kind:    Platform's kind (it's module name)
        :param parent:  Parent's platform name
        :param wait:    List of platforms names that new platform depends on
        :return: Nothing
        """
        name = factory.name
        assert kind is not None, "instance kind can't be None (instance name is {})".format(name)

        if factory.name is None:
            factory.name = name = "random_name"    # TODO: use GUID

        assert name not in self._platforms and (awaiting or name not in self._awaiting),\
            "encountered second platform with name {}".format(name)

        # TODO: analyze args and update wait if there are references to other platforms
        assert wait is None or name not in wait, "platform {} can't wait for self!".format(name)

        # If all necessary parent and co-platforms are already created - finish registration of this one
        if (parent is None or parent in self._platforms) \
                and (wait is None or all(w in self._platforms for w in wait)):
            np = factory.finish_registration()
            self._platforms[name] = np
            if parent is not None:
                assert np not in self._platforms[parent].subplatforms, "Subplatform {} is already within " \
                                                                       "parent's ({}) subplatforms list, " \
                                                                       "but shouldn't be".format(name, parent)
                np.parent = self._platforms[parent]
                self._platforms[parent].subplatforms.append(np)
            if wait is not None:
                for w in wait:
                    assert np not in self._platforms[w].depended, "Subplatform {} is already within " \
                                                                  "depended's list of {}, " \
                                                                  "but shouldn't be".format(name, w)
                    self._platforms[w].depended.append(np)
            if awaiting:
                del self._awaiting[name]
            self._check_awaiting()
        # Otherwise put it into waiting list
        else:
            self._awaiting[name] = {
                "instance": factory,
                "kind": kind,
                "parent": parent,
                "wait": wait}

    def _check_awaiting(self):
        """
        Runs through platforms which registration were deferred and tries to register them again
        :return: Nothing
        """
        # TODO: check for wait loops
        for w in list(self._awaiting.values()):
            self._try_register_platform(w["instance"], w["kind"], w["parent"], w["wait"], awaiting=True)

    def emergency_stop(self):
        """
        Stops platforms as it can
        :return: True if stopped successfully, False otherwise
        """
        eprint("Emergency platforms stop")
        stop_list = []
        for p in self._platforms:
            stop_list.append(self._platforms[p])

        success = True
        while len(stop_list) > 0: # NOTE: stop platforms in reverse order
            p = stop_list.pop(-1)
            vprint("Emergency stop for {}".format(p))
            try:
                r = p._stop([])
            except Exception as e:
                success = False
                eprint("Exception occurred while stopping platform {} emergently: {}".format(p, e))
                exprint()
                continue
            if not r.success:
                success = False
        return success


    def unregister_platform_instance(self, instance, recursive=False):
        """
        Unregisters platform instance.
        Can recursively unregister all instance's nested platforms.
        If recursion is not used and by the instant unregister is called there is still nested platforms
        then exception would be rised
        :param instance: platform's instance to unregister
        :param recursive: True(default) if recursive action is required, otherwise False
        :return:
        """
        platform_to_remove = None
        for k, v in self._platforms.items():
            if v == instance:
                platform_to_remove = k
                break
        if platform_to_remove is None:
            raise ValueError("No platform instance have been found to unregister")
        if len(instance.subplatforms) > 0:
            if recursive:
                for sp in list(instance.subplatforms):
                    self.unregister_platform_instance(sp, recursive)
            else:
                raise ValueError("Can't unregister platform with subplatforms. Set recursive to True")
        if instance.parent is not None:
            if instance in instance.parent.subplatforms:
                instance.parent.subplatforms.remove(instance)
                if instance in instance.parent.subplatforms:
                    raise IndexError("Instance were registered multiple times in parent's subplatforms list")
            else:
                raise IndexError("Instance is not found in parent's subplatforms list")
        del self._platforms[platform_to_remove]

    def unregister_platform(self, name, recursive=False):
        """
        Wrap for unregister_platform_instance method
        :param name: Name of platform to unregister
        :param recursive: True(default) if recursive action is required, otherwise False
        :return:Nothing
        """
        if name in dict(self._platforms):
            self.unregister_platform_instance(self._platforms[name], recursive)

    def unregister_factory(self, instance):
        """
        Unregisters platforms factory. Usually happens after successful platform registration
        :param instance: factory instance to unregister
        :return: Nothing
        """
        to_remove = None
        for k, v in self._awaiting.items():
            if v["instance"] == instance:
                to_remove = k
                break
        if to_remove is not None:
            del self._awaiting[to_remove]

    def is_subscribed(self, inst, channel):
        """
        Says whether or not specified platform (by instance) is subscribed to channel
        :param inst: platform instance to check
        :param channel: channel's name
        :return: True if subscribed, otherwise - Noet
        """
        if channel not in self._channels:
            return False
        return inst in self._channels[channel].subscribers

    def subscribe(self, inst, channel):
        """
        Subscribes specified platform to channel
        :param inst: platform instance to subscribe
        :param channel: channel's name
        :return: Nothing
        """
        if channel not in self._channels:
            self._channels[channel] = TalkChannel(channel, print_messages=self.verbose, timeref=self._timeref)
        self._channels[channel].subscribe(inst)

    def unsubscribe(self, inst, channel):
        """
        Unsubscribes specified platform to channel
        :param inst: platform instance to unsubscribe
        :param channel: channel's name
        :return: Nothing
        """
        if channel not in self._channels:
            raise ValueError("Channel {} not exists!".format(channel))
        self._channels[channel].unsubscribe(inst)
        return
        # TODO: ?delete channels if there is no subscribers
        # if len(self._channels[channel].subscribers) == 0:
        #     del self._channels[channel]

    def start_thread(self, topic_caster, channel, interface, reply_to_tc=None):
        """
        Starts new thread on specified channel
        :param topic_caster: ref to platform that starts thread (aka topic caster)
        :param channel: channel's name
        :param interface: interface to send messages to
        :param reply_to_tc - defines behaviour for replies
            if None(default) then messages are sent to subscribers and topic_caster
            if False then no messages sent to topic_caster
            if True then messages are sent to topic_caster only
        :return: new messaging context
        """
        if channel not in self._channels:
            raise ValueError("Channel {} not exists!".format(channel))
        return TalkContext(channel, self._channels[channel].start_thread(topic_caster, reply_to_tc), interface)

    @property
    def send_message_in_progress(self):
        return self._send_message_level > 0

    def send_message(self, context, message, processing=None):
        # TODO: chained context to trace consequent requests
        """
        Sends message to specified channel.
        Also updates Message with Sources's Name (puts it as first component of message)
        :param context: messaging context
        :param message: PlatformMessage instance with message's content
        :param processing: If 2 then keep processing messages queues until every participant get answer or timeout
                               i.e. wait for async replies
                           If 1 then don't waits for async replies but other messages queues would be processed
                           If 0 then messages are only sent without even processing by platforms
        :return: if processing is 2 then replies to specified messaging context are returned, otherwise None
        """
        # TODO: option to build UML out of conversation

        if processing is None:
            if message.is_reply:
                processing = 0
            else:
                processing = 2
        if processing == 2 and message.is_reply:
            raise ValueError("Processing level 2 can be set only for initial (non-reply) messages")

        if context.channel not in self._channels:
            raise ValueError("Channel {} not exists!".format(context.channel))

        print_level_change = pref.send_message_print_level_change

        if processing == 2:
            self._send_message_level += 1   # Increase level if processing == 2
            if print_level_change:
                vprint("send message level changed to: {}".format(self._send_message_level))

        try:
            # Send message into channel
            self._channels[context.channel].send_message(context, message)
            # Register replies
            if message.is_reply:
                self._replies[context.channel][context.thread][message.sender] = message
            else:
                if context.channel not in self._replies:
                    self._replies[context.channel] = {}
                assert context.thread not in self._replies[context.channel], \
                    "PlatformsFarm:send_message Unexpectedly received second initial (non-reply) message " \
                    "for {}:{}".format(context.channel, context.thread)
                self._replies[context.channel][context.thread] = {}
        except Exception as e:
            if processing == 2:
                self._send_message_level -= 1
                if print_level_change:
                    vprint("send message level changed to: {}".format(self._send_message_level))
            raise e

        # Just exit here if processing is 0
        if processing == 0:
            return None

        stay_in_loop = True
        while stay_in_loop:
            stay_in_loop = False
            # Process messages if any platform received messages
            if any(p.received_messages > 0 for p in self._platforms.values()):
                self.process_messages()
                if processing == 2:       # If processing is 2, then stay in loop as there could be responses
                    stay_in_loop = True
            if processing == 2 and not stay_in_loop:    # If no more processing expected
                # But it's multithreadning case and not all final replies were received yet
                if pref.multithreading and not all(m.is_failure or m.is_success
                                                   for m in self._replies[context.channel][context.thread].values()):
                    # And some platforms are still waiting for reply - just wait a bit
                    if any(p.waiting_reply for p in self._platforms.values()):
                        time.sleep(0.001)
                        stay_in_loop = True

        if processing == 2:
            self._send_message_level -= 1
            if print_level_change:
                vprint("send message level changed to: {}".format(self._send_message_level))
            result = self._replies[context.channel].pop(context.thread)
            return result
        else:
            return None

    def process_messages(self):
        """
        Invokes received messages processing by platforms
        Usualy is called automatically from send_message method
        :return:
        """
        for p in self._platforms.values():
            if p.received_messages > 0:
                p.queue_received_messages()
        for p in self._platforms.values():
            if p.queued_messages > 0:
                p.process_queued_messages()


class PlatformFactory(object):
    """
    Platform Factory
    Used in intermedeate state when Platforms Farm registers new Platform
    Imposes new Platform until it can't be actually be instantiated
    Creates new Platform instance by string description of it's base platform (i.e. module)
    To successfully create new Platform following conditions should be met:
    * Python package with same name as base_platform should exist in platforms folder
    * That package should contain module main (main.py) with class RootClass derived from PlatofrmBase class
    RootClass of module main would be used for new Platform Instance
    """

    def __init__(self, farm, **kwargs):
        self._farm = farm
        self._args = copy.deepcopy(dict(kwargs))
        self.name = self._args.get("name", None)

        wait = self._args.get("wait", [])
        assert (isinstance(wait, (list, tuple, str))), "Wait should be a list, tuple or string"
        if isinstance(wait, str):
            wait = [wait]
        elif isinstance(wait, tuple):
            wait = list(wait)
        self._args["wait"] = wait

        if "name" in self._args:
            del self._args["name"]
        if "platform" not in self._args:
            self._args["platform"] = None
        self._farm.register_platform(
            factory=self,
            kind=self._args.get("base_platform", None),
            parent=self._args.get("platform", None),
            wait=self._args.get("wait", []))

    def __del__(self):
        self._farm.unregister_factory(self)

    def finish_registration(self):
        """
        Creates Platform's instance
        Should be called when conditions for creation this very instance are met - platforms that this instance
        depends on should be already registered
        :return: ref to actual Platform Instance
        """
        base_platform = self._args.get("base_platform", None)
        lcls = {}
        try:
            exec("from platforms.{}.main import RootClass as rc; cl = rc".format(base_platform), globals(), lcls)
        except ModuleNotFoundError as e:
            eprint("Package 'platforms.{}' or module 'main' wasn't found for creating platform instance '{}'!".format(
                base_platform, self.name))
            raise e
        lcls["name"] = self.name
        lcls["farm"] = self._farm
        lcls["args"] = self._args
        try:
            exec("inst = cl(name=name, farm=farm, **args)", globals(), lcls)
            inst = lcls["inst"]
        except Exception as e:
            eprint("Exception occurred when creating platform {} of {} kind!\nException: {}".format(
                self.name, base_platform, e))
            raise e
            # inst = PlatformBase(name=self.name, farm=self._farm, **self._args)  # TODO: raise exception
        return inst


class ScoreboardRulesBase(object):
    """
    Base class for implementing scoreboard rules
    """
    def __init__(self, host, **kwargs):
        self._host = host

    @property
    def stats(self):
        """
        Rules specific dict with accumulated (summary) statistics
        :return: dict with name/value pairs
        """
        return {}

    @property
    def details(self):
        """
        Full scoreboard information
        Like: which commands were observed / not observed, on which there were errors etc.
        :return: dict
        """
        return {}

    def cmd(self, context, message):
        """
        Scoreboard handler for incoming commands
        :param context: messaging content
        :param message: message content
        :return: True if command were accepted (even if it wasn't correct) otherwise False
        """
        return True

    def response(self, context, message):
        """
        Scoreboard handler for incoming responses
        :param context: messaging content
        :param message: message content
        :return: True if response were accepted (even if it want's correct) otherwise False
        """
        return True

    def _accept_cmd(self, context, message):
        self._host.commands += 1    # TODO: call host's method instead
        assert context.str not in self._host.expected, "{}: Context {} already in results".format(
            self._host.name, context.str)
        return True

    def _accept_response(self, context, message):
        self._host.responses += 1   # TODO: call host's method instead

        if context.str not in self._host.expected:
            self._error(context, message, "Response wasn't expected")
            return False
        return True

    def _unhandled(self, context, message, reason):
        # TODO: call host's method instead
        """
        Use for commands that can't be handled
        :param context: messaging context
        :param message: message content
        :param reason: reason why command can't be handled
        :return:
        """
        self._host.unhandled.append((context.str, message.serialize(), reason))
        self._host.expected[context.str] = None
        eprint("{}: Command {} can't be handled due to {}".format(self._host.name, message.serialize(), reason))

    def _handle(self, context, message, expected):
        # TODO: call host's method instead
        self._host.expected[context.str] = expected

    def _success(self, context, message):
        # TODO: call host's method instead
        self._host.success += 1
        vprint("{}: Response is OK".format(self._host.name))
        if self._host.clean_completed:
            del self._host.expected[context.str]

    def _error(self, context, message, reason):
        # TODO: call host's method instead
        self._host.errors.append((context.str, message.serialize(), reason))
        eprint("{}: Wrong response: {}".format(self._host.name, reason))
        if self._host.clean_completed:
            del self._host.expected[context.str]


class CoverageRulesBase(object):
    """
    Base class for implementing coverage rules
    """
    def __init__(self, host, **kwargs):
        self._host = host

    @property
    def coverage(self):
        """
        Coverage summary - tupple with amount of cases and covered cases
        May be used to determine coverage percentage
        :return: tuple
        """
        return 0, 1

    @property
    def details(self):
        """
        Full coverage information
        :return: dict
        """
        return {}

    def receive_message(self, context, message):
        """
        Coverage handler for incoming messages
        :param context: messaging content
        :param message: message content
        :return:
        """
        pass
