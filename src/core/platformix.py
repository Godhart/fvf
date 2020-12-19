from core.platformix_core import pref
from core.platformix_core import proto_success
from core.platformix_core import PlatformMessage as PM, TalkContext
from ip.platformix.definitions import PlatformixProtocol, PlatformixWrapper
from core.simple_logging import vprint, eprint
import time


class PlatformBase(object):
    """
    A Class that should be used as Base Class for Abstraction classes (Wrappers) to actual subjects in test environment,
    e.g. device under test, stimulus generator, data checker and so on
    Instances of Wrappers are called Platforms
    Platforms could interact with their subject directly or via other Platforms
    Platforms should override following methods to expand Base Class functionality:
    * _start - for managing necessary actions on platform's start
               (binding with actual subject and setting it to ready state)
    * _stop - for managing necessary actions on platform's stop
               (ending interaction with actual subject and disconecting)
    See description of those methods for more info
    All other methods can be overridden by Derived Classes only in case of urge
    and only with total understanding of PlatformBase Class and it's role in whole system
    """

    def __init__(self, name, farm, base_platform=None, platform=None, wait=None):
        """
        Inits platform
        During init setups necessary binding with co-operating platforms

        :param name: Name for platform. Expected to be unique in whole testing environment
        :param farm: a Platform's Farm reference which contains all platforms in test environment
        :param base_platform: Name of Package in which Wrapper Class is contained (used for Information)
        :param  platform: a Name of Platform which hosts this very Platform (i.e. Parent Platform)
        :param wait: list with Names of Platforms that should be started before this one
        """
        self._farm = farm
        self._base_platform = base_platform
        self._name = name
        platform = platform
        self.parent = None  # NOTE: parent instance is set by Farm due to late bindings.
                            # It refers to instance with name equal to self.platform
        self._wait = wait
        if self._wait is None:
            self._wait = []
        if platform is not None:
            self._wait.append(platform)
        self._wait = tuple(self._wait)  # Protect wait from changing further
        self.subplatforms = []
        self.depended = []
        self._subscriptions = []
        self.subscribe("@{}".format(self._name))  # Subscribe personal channel to receive direct addressed messages
        self.subscribe("#platforms")              # Subscribe channel which coordinates all platforms actions

        # Platformix protocol variables
        self._running = False       # True if platform is running
                                    # (successfully started and all necessary things were done) and is not going to stop
        self._starting = False      # True if platform is going to start or already is starting
        self._start_in_progress = \
            False                   # True if platform is actually starting up
                                    #     If _sarting but not _start_in_progress then platform is waiting
                                    #     until other platforms would start
        self._stopping = False      # True if platform is going to stop or already is stopping
                                    #    If _stopping but not _stop_in_progress then platforms is waiting
                                    # until other platforms (subplatforms and depended platforms) would stop
        self._stop_in_progress = False  # True if platform is actually stopping up
        self._start_max_wait = pref.platform_start_timeout  # Max time in sec to wait before other platforms would start
                                                            #     Start is failed if timeout is reached
        self._stop_max_wait = pref.platform_stop_timeout    # Max time in sec to wait before other platforms would stop
                                                            #     Stop is started if timeout is reached, no matter
                                                            #     if subplatforms stopped or not

        self._wait_reply_from = {}  # Map with context to wait reply on as a key
                                    # and callback function with args as a value
        self._request_end_state = {}  # Map with request's context as key and requests completition results as value
        self._receive_queue = []    # When message is received it's put in this queue
        self._messages_queue = []   # Received messages are transfered into this queue before processing
                                    # by queue_received_messages method
        self._protocols = {}        # Protocols map. Key is interface name and value is protocol implementation instance

        self.platformix = PlatformixWrapper.get_wrapper(self, "_")  # Self's private properties and methods
        # are gathered into single wrapper-class with public access

        # Regiser PlatformixProtocol implementation
        self._support_protocol(PlatformixProtocol(self))    # In the end register PlatformixProtocol support

    def __del__(self):
        for c in list(self._subscriptions):
            self.unsubscribe(c)
        self._farm.unregister_platform(self.name, recursive=True)

    def _support_protocol(self, protocol):
        assert protocol.name not in self._protocols, "Protocol with name {} is already supported by {}".format(
            protocol.name, self.name)
        self._protocols[protocol.name] = protocol

    @property
    def name(self):
        """
        :return: Platform's name
        """
        return self._name

    @property
    def base_platform(self):
        """
        :return: Name of Package in which Wrapper Class is contained
        """
        return self._base_platform

    @property
    def wait(self):
        """
        :return: list with Names of Platforms that should be started before this one
        """
        return self._wait

    @property
    def running(self):
        """
        :return: True if Running (is binded to corresponding subject and it's in operational state)
        """
        return self._running

    @property
    def starting(self):
        """
        :return: True if platform is in middle of start process
                 (start conditions are met and necessary actions are taking place)
        """
        return self._starting

    @property
    def stopping(self):
        """
        :return: True if platform is in middle of stop process
                 (stop conditions are met and necessary actions are taking place)
        """
        return self._stopping

    @property
    def received_messages(self):
        """
        :return: Amount of received messages
        :return:
        """
        return len(self._receive_queue)

    @property
    def queued_messages(self):
        """
        :return: Amount of queued messages for processing
        """
        return len(self._messages_queue)

    def waiting_reply_on(self, context, interface):
        """
        Checks if there is handlers assigned and waiting for replies with specific context and or interface
        Also checks if there is timeouted waits and invokes handlers with timeouted set to True to release handler
        :param context: messaging context. If None specified then all contexts are checked
        :param interface: interface. If None specified then context for all interfaces are checked
        :return:
        """
        if len(self._wait_reply_from) == 0:
            return False
        if context is not None:
            if context.str not in self._wait_reply_from:
                return False
            else:
                contexts = [context.str]
        else:
            contexts = list(self._wait_reply_from.keys())
        now = time.time()
        r = False
        for c in contexts:
            if interface is not None and TalkContext.deserialize(c).interface != interface:
                continue
            d = self._wait_reply_from[c]
            if now < d["timeout"]:
                r = True
            else:
                if not d["send_message"]:
                    r = d["method"](context, False, True, *d["args"], **d["kwargs"])
                else:
                    r = d["method"](context, PM.failure(state={"timeouted": True}),
                                    False, True, *d["args"], **d["kwargs"])
                eprint("{}:{} didn't get reply on {}:{}".format(
                    self.name, context.interface, context.channel, context.thread))
        return r

    @property
    def waiting_reply(self):
        """
        Checks if there is handlers assigned and waiting for replies
        Also checks if there is timeouted waits and invokes handlers with timeouted set to True to release handler
        :return: True if there is any not timeouted handler assigned and waiting for replies otherwise False
        """
        return self.waiting_reply_on(None, None)

    def _start(self, reply_contexts):
        """
        Startup worker method. Does all necessary actions to start platform instance after all start conditions were met
        Derrived classes should call this in the end when overriding _start method
        :return: True if successfully started (binded to subject and subject is in operational state), otherwise - False
        """
        self._running = True
        self._start_in_progress = False
        self._starting = False
        vprint("platform {} just started".format(self.name))
        return proto_success(None)

    def _stop(self, reply_contexts):
        """
        Stopping worker method. Does all necessary actions to stop platform after all stop conditions were met
        Derrived classes should call this in the end when overriding _stop method
        :return: True if successfully stopped - subject were stopped (whatever that means) and disconnected,
                 otherwise - False
        """
        self._running = False
        self._stopping = False
        vprint("platform {} has been stopped".format(self.name))
        return proto_success(None)

    def subscribe(self, channel):
        """
        Subscribes platform to receive messages on certain messaging channel
        Messaging channels are hosted by Platforms Farm
        :param channel: string, channel's name to subscribe to. If channel don't exists it would be created
        :return: Nothing
        """
        self._farm.subscribe(self, channel)
        self._subscriptions.append(channel)

    def unsubscribe(self, channel):
        """
        Unsubscribes platform from receiving messages on certain messaging channel
        Messaging channels are hosted by Platforms Farm
        :param channel: string, channel's name to unsubscribe from
        :return: Nothing
        """
        assert channel in self._subscriptions, "Not subscribed to {}!".format(channel)
        self._farm.unsubscribe(self, channel)
        del self._subscriptions[self._subscriptions.index(channel)]

    def receive_message(self, context, message):
        """
        Method that is used by messaging channel to pass messages into platform.
        Messages are queued but not processed. Messages processing is invoked by process_queued_messages method
        receive_message shouldn't be overridden by dervied classes.
        _receive_message_handler and _fsm_message_handler should be overridden instead if necessary
        :param context: messaging context
        :param message: PlatformMessage instance with message's content
        """
        message = PM.parse(message)
        if message.sender == self.name:
            return False
        if message.is_reply and context.str in self._wait_reply_from:
            d = self._wait_reply_from[context.str]
            if d["timeout"] is not None and time.time() >= d["timeout"]:
                return False
            if not d["send_message"]:
                r = d["method"](context, True, False, *d["args"], **d["kwargs"])
            else:
                r = d["method"](context, message, True, False, *d["args"], **d["kwargs"])
            if r:
                self._receive_queue.append((context, message))
                return True
            else:
                return False
        elif message.interface in self._protocols and self._protocols[message.interface].supports(message):
            self._receive_queue.append((context, message))
            return True
        return False

    def queue_received_messages(self):
        """
        Move received messages queue into processing queue
        :return: None
        """
        self._messages_queue += self._receive_queue
        self._receive_queue = []

    def process_queued_messages(self):
        """
        Used to invoke processing of queued message
        :return: None
        """
        while len(self._messages_queue) > 0:
            c, m = self._messages_queue.pop(0)
            if m.is_reply and c.str in self._wait_reply_from:  # Pass replies to registered handler
                d = self._wait_reply_from[c.str]
                if d["timeout"] is not None and time.time() >= d["timeout"]:
                    continue
                if not d["send_message"]:
                    d["method"](c, False, False, *d["args"], **d["kwargs"])
                else:
                    d["method"](c, m, False, False, *d["args"], **d["kwargs"])
            else:
            # TODO: ?? check whether protocol is ready to process message and stop processing if not ??
            #       queue processing would be continued
            #       OR this should be done by protocol ??
                self._protocols[m.interface].process_message(c, m)

    def _register_reply_handler(self, context, method, args, kwargs, timeout, send_message=True, force=False,
                                store_state=True):
        assert force or context.str not in self._wait_reply_from, "Reply handler for {} of {} " \
            "is already registered ({}({},{})!".format(context.str, self.name, *self._wait_reply_from[context.str])
        if timeout is not None:
            timeout += time.time()
        self._wait_reply_from[context.str] = {
            "method": method, "args": args, "kwargs": kwargs,
            "send_message": send_message, "timeout": timeout, "store_state": store_state
        }
        vprint("{} is waiting for reply on {}:{}".format(self.name, context.channel, context.thread))

    def _unregister_reply_handler(self, context, success, state, dont_check=False):
        assert dont_check or context.str in self._wait_reply_from, "Reply handler for {} of {} not found!".format(
            context.str, self.name)
        if not dont_check or context.str in self._wait_reply_from:
            if self._wait_reply_from[context.str]["store_state"]:
                assert isinstance(state, dict), "state expected to be a dict"
                assert context.str not in self._request_end_state, "unexpected to see a state in a storage " \
                                                               "before it was actually stored"
                state["__success__"] = success
                self._request_end_state[context.str] = state
            del self._wait_reply_from[context.str]

    def start_conversation(self, channel, interface, reply_to_tc=None):
        """
        A helper method to easily start new thread on specified channel and get pair of channel and thread as tuple
        :param channel: messaging channel's name
        :param interface: messaging interface
        :param reply_to_tc - defines behaviour for replies
            if None(default) then messages are sent to subscribers and topic_caster
            if False then no messages sent to topic_caster
            if True then messages are sent to topic_caster only
        :return: TalkContext instance containing channel, interface, thread ID
        """
        return self._farm.start_thread(self, channel, interface, reply_to_tc)

    def send_message(self, context, message):
        # TODO: "strict" parameter - if True then anyone received this message should support it or fail
        """
        Sends message into messaging channel and into thread with specified ID
        If thread is None then new thread would be created
        Will fail if channel or thread is not exists
        :param context: messaging context - channel, thread, interface
        :param message: PlatformMessage instance with message's content
        :return: None
        """
        message.sender = self.name
        message.interface = context.interface
        self._farm.send_message(context, message)

    def request(self, request, handler, hargs, hkwargs, hsend_message=True,
                channel=None, timeout=1.0, store_state=True):
        """
        Sends request into specified channel and waits until it would be completed (successfully or not)
        Timeout is set to wait for requests's completition
        A new thread would be used for conversation during request
        This method sends request and wait's while it would be processed
        Judgement whether it's processed or not should be done in _receive_message_handler
        :param request: PlatformMessage instance with request message's content including interface
        :param handler: Reference to handler method that would process ending reply (success of failure)
                        Handler signature should be (context, message, dry_run, timeouted, *args, **kwargs)
                        or (context, dry_run, timeouted, *args, **kwargs) if handler don't requires message itself
                        Handler method's args should be:
                        1st - context - Messaging context
                        2nd - message - Reply message. Optional.
                                        If handler don't have message argument for some reason then
                        hsend_message should be set tp False
                        3rd - dry_run - Boolean. If True then handler should evaluate would it be processing message
                                        or not without actualy changing things
                                        Used by messaging system to detemine wether message have reached any target
                                        ot not
                        4th - timeouted - Boolean. If True it's indicates that message were receoved after specified
                                        timeout. Expected action from handler on timeout is to unregister self
                                        and do fall back scenario
                                        Expected that on dry_run with timeouted True handler just replies with False
        :param hargs: Args to send to handler method on call
        :param hkwargs: Keyworded args to send to handler method on call
        :param hsend_message: If True then message is sent to handler on call as second argument
        :param channel: messaging channel's name. If None(default) then message is sent
                        into parent's platform personal channel
        :param timeout: a time interval in which request expected to be completed
        :param store_state: if True then requests end state would be stored into self._request_end_state map
        :return: Conversation context to monitor for request completition
        """
        if handler is None:
            handler = self._default_request_handler
        if channel is None:
            if self.parent is None:
                raise ValueError("channel can't be None if parent is not set")
            else:
                channel = "@{}".format(self.parent.name)
        c = self.start_conversation(channel, request.interface)
        self._register_reply_handler(c, handler, hargs, hkwargs, timeout=timeout, send_message=hsend_message,
                                     store_state=store_state)
        self.send_message(c, request)
        return c

    def _pop_request_state(self, context):
        if context.str not in self._request_end_state:
            return None
        return self._request_end_state.pop(context.str)

    def _request_state_is_success(self, state):
        return state.get("__success__", None) is True

    def _request_handler_common(self, context, message, dry_run, timeouted):
        """
        Implements common request handler behaviour
        If nothing special - use this one in the beginning of your handler
        :param context: messaging context
        :param message: message content, PlatformMessage instance
        :param dry_run: True if should be only evaluated will handler accept this message
        :param timeouted: True if handler is called after special timeout. In this case handler shouldn't process
                    message itself, but should react to the fact of timeout
        :return: True if message would be handled (is success or failure) and message is not timeouted, otherwise False
        """
        if timeouted:
            if not dry_run:
                self._unregister_reply_handler(context, False, {"__timeouted__": True})
                #  NOTE: it's not necessary that other request handlers
                #    would unregister self on timeouted call. They could handle timeout otherway and don't
                #    unregister handler right away. For example - platformix stop handler
            return False
        if message.is_failure is False and message.is_success is False:
            return False
        return True

    def _default_request_handler(self, context, message, dry_run, timeouted, *args, **kwargs):
        """
        Implements default request handler.
        Does only one thing - unregisters handler on success, failure or timeout
        :param context: messaging context
        :param message: message content, PlatformMessage instance
        :param dry_run: True if should be only evaluated will handler accept this message
        :param timeouted: True if handler is called after special timeout. In this case handler shouldn't process
                    message itself, but should react to the fact of timeout
        :return: True if message would be handled (is success or failure) and message is not timeouted, otherwise False
        """
        if not self._request_handler_common(context, message, dry_run, timeouted):
            return False
        if dry_run:
            return True
        self._unregister_reply_handler(context, message.is_success, {"__message__": message.serialize()})
        return True

    def _generic_request_handler(self, context, message, dry_run, timeouted, on_success, on_failure):
        """
        Implements generic behaviour for handling requests were replies could be handled by simple
        method call, even by lambdas
        :param context: messaging context
        :param message: message content, PlatformMessage instance
        :param dry_run: True if should be only evaluated will handler accept this message
        :param timeouted: True if handler is called after special timeout. In this case handler shouldn't process
                    message itself, but should react to the fact of timeout
        :param on_success: Method to call in case of success. Method should have only one arg which would be set
                    with content of reply message kwargs field
        :param on_failure: Method to call in case of failure. Method should have only one arg which would be set
                    with content of reply message kwargs field
        :return: True if successfully handled, otherwise False
        """
        if not self._request_handler_common(context, message, dry_run, timeouted):
            return False
        if dry_run:
            return True
        if callable(on_success) and message.is_success:
            on_success(message.kwargs)
        if callable(on_failure) and message.is_failure:
            on_failure(message.kwargs)
        self._unregister_reply_handler(context, message.is_success, {})
        return True

    def _reply(self, context, message):
        """
        Sends reply to specified channel and tread.
        Message type isn't required in that case. It automatically set to "__reply__" by this method
        :param context: messaging context - channel, thread, interface
        :param message: PlatformMessage instance with message's content
        :return: None
        """
        assert message.method == "__reply__", "Reply message is expected but received {}\nWhole message is: {}".format(
            message.method, message.serialize())
        self.send_message(context, message)

    def _reply_all(self, contexts, message):
        """
        Sends reply to all channels and treads that are enlisted in self._context["reply_to"]
        Message type isn't required in that case. It automatically set to "__reply__" by this method
        :param message: PlatformMessage instance with message's content
        :return: None
        """
        for c in contexts:
            m = PM.parse(message.serialize())  # NOTE: Do a copy
            self._reply(c, m)
