from core.helpers import Wrapper
from core.platformix_core import PlatformProtocolCore, ProtocolReply, PlatformInterfaceCore, \
    proto_failure, proto_success
from core.simple_logging import eprint, exprint


class PlatformixInterface(PlatformInterfaceCore):
    _base_id = "platformix"
    _methods = ("start", "stop", "get", "set", "call", "report")
    # Methods:
    # * start - starts platform, no args required
    # * stop - stops platform, no args required
    # * get - get platform's attribute value. arg is attribute name
    # * set - set platform's attribute value. args are attribute name, attribute value
    # * call - calls platforms method. args: method name, list with args to method, dict with kwargs to method
    #  TODO: Ensure in call args
    # * report - used to get platform's instance run state. args:
    #     state of interest:
    #       * "running" (returns state)
    #       * "is_running" (returns True/False)
    # TODO: below is core function, all protocols have it. Bring out to proper place
    # * testing - used for testing purposes. args:
    #     testing function
    #       * fake_next_op tells platform to send certain reply on next operation with specified conditions


class PlatformixProtocol(PlatformProtocolCore):
    """
    Implements platformix interface that is used to start/stop platforms, control their state
    and do general operations (get/set platform's property, call platform's method)
    """
    _default_interface = PlatformixInterface
    _protocol_fields = ("running", "starting", "start_in_progress", "stopping", "stop_in_progress",
                        "start_max_wait", "stop_max_wait", "farm", "wait")
    _protocol_methods = ("start", "stop",
                         "reply_all", "reply", "register_reply_handler", "unregister_reply_handler")
    # TODO: methods signature specification

    def __init__(self, host, interface=None, name=""):
        super(PlatformixProtocol, self).__init__(host, host.platformix, interface, name)
        # NOTE: PlatformixProtocol can be used only with host.platformix as worker

    def _platformix_start_reply_handler(self, context, message, dry_run, timeouted):
        """
        Handles replies for start operation (required when platform is waiting another one)
        :param context: messaging context
        :param message: message content
        :param dry_run: True if it's only required to check whether this message would be processed
        :param timeouted: True if handler were called due to timeout. In this case message and context are invalid
        :return: True if message were processed (can be processed) otherwise False
        """
        if not timeouted:
            # Ignore messages other than success or failure
            if not message.is_failure and not message.is_success:
                return False
        if not self._validate_context({"action": "start"}):
            return False
        if timeouted or message.sender in self._context["waiting_for"]:
            if dry_run:
                if timeouted:
                    return False
                else:
                    return True
            if timeouted or message.is_failure:
                self._worker.starting = False
                self._worker.start_in_progress = False
                self._context["action"] = "start_failed"
                for c in self._context["reply_to"]:
                    try:
                        status = {}
                        if timeouted:
                            status["__timeouted__"] = True
                        if message.is_failure:
                            status["dependency failed to start"] = message.sender
                        self._worker.unregister_reply_handler(c, False, status, dont_check=True)
                    except AssertionError:
                        pass
                if not timeouted:
                    self._reply_all(self._context["reply_to"], proto_failure(
                        "Aborting start due to platform {} failed to start".format(message.sender)), None)
                else:
                    self._reply_all(self._context["reply_to"], proto_failure(
                        "Aborting start due to wait timeout. Platforms {} have not started within "
                        "timeout {}".format(self._context["waiting_for"], self._worker.start_max_wait)), None)
                self._context = None
                if timeouted:
                    return False
                else:
                    return True
            else:   # Success
                self._platformix_start(context, None)
                return True
        return False

    def _platformix_stop_reply_handler(self, context, message, dry_run, timeouted):
        """
        Handles replies for stop operation (required when platform is waiting another one)
        :param context: messaging context
        :param message: message content
        :param dry_run: True if it's only required to check whether this message would be processed
        :param timeouted: True if handler were called due to timeout. In this case message and context are invalid
        :return: True if message were processed (can be processed) otherwise False
        """
        if not timeouted:
            if message.is_failure is False and message.is_success is False:
                return False
        if not self._validate_context({"action": "stop"}):
            return False
        if timeouted or message.sender in self._context["waiting_for"]:
            if dry_run:
                if timeouted:
                    return False
                else:
                    return True
            if timeouted or message.is_failure:
                if timeouted:
                    self._context["wait_ignore"] += self._context["wait_ignore"]
                    self._notify_all(
                        self._context["reply_to"],
                        "Subplatforms {} have not stopped within timeout {}. Ignoring them (may cause exception "
                        "later)".format(self._context["waiting_for"], self._worker.stop_max_wait))
                else:
                    self._context["wait_ignore"].append(message.sender)
                    self._notify_all(
                        self._context["reply_to"],
                        "Subplatform {} failed to stop, "
                        "ignoring it (but it may cause exception later)".format(message.sender))
                if not timeouted:
                    self._platformix_stop(context, None)
                    return True
                else:
                    self._platformix_stop(self._context["reply_to"][0], None)
                    return False
            else:   # Success
                if message.sender in self._context["waiting_for"]:
                    self._platformix_stop(context, None)
                    return True
        return False

    def _platformix_start(self, context, fake_reply):   # TODO: Recursive option to start nested platforms
        """
        Starts platform instance (actually checks that necessary conditions are met and calls startup worker method)
        If parent platform or platforms in wait list are not running yet - will wait for them
        If start were deferred due to waiting of other platforms then start method should be called again later
        Usually it happens automatically after other platforms are replying on their's startup end
        :param context: messaging context
        :return: None
        """
        assert fake_reply is None, "platformix_start replies shouldn't be faked!"
        if self._worker.running:   # If already running - just do nothing
            self._reply(context, proto_success("already running", "state"), None)
            return
        if self._worker.stopping:  # If in the middle of stop - do nothing
            self._reply(context, proto_failure("stop is in progress"), None)
            return
        new_thread = False
        if self._worker.starting:   # If were already starting - update reply list
            if context not in self._context["reply_to"]:
                new_thread = True
                self._context["reply_to"].append(context)
                self._notify(context, "waiting")
        else:
            new_thread = True
            self._worker.starting = True
            self._context = {"action": "start", "reply_to": [context],
                             "waiting_for": [], "wait_ignore": []}
            self._notify(context, "received start signal")
            # TODO: do recursive start? parent->childs? and call only root platforms to get up and running?
        # TODO: lock as validation can intersect with stop action since stop can be called from different threads
        if not self._validate_context({"action": "start"}):
            return
        if not self._worker.starting:  # NOTE: in case if starting were interrupted by stop - just return
            return
        # Update waiting list
        self._context["waiting_for"] = [w for w in self._worker.wait if self._worker.farm.is_running(w) is False]
        # If there is some platforms to wait - notify about this
        if self.waiting_count > 0 and new_thread:
            self._worker.register_reply_handler(context,
                                                self._platformix_start_reply_handler, [], {},
                                                timeout=self._worker.start_max_wait, force=True)
            self._notify(context, "waiting")
        # If no one left to wait for - do stop at last
        elif not self._worker.start_in_progress and self.waiting_count == 0:
            for c in self._context["reply_to"]:
                try:
                    self._worker.unregister_reply_handler(c, True, {}, dont_check=True)
                except AssertionError:
                    pass
            self._worker.start_in_progress = True
            self._notify_all(self._context["reply_to"], "launching")
            if self._validate_context({"action": "start"}):
                result = self._worker.start(self._context["reply_to"])
                result_error = not isinstance(result, ProtocolReply)
            else:
                result = None
                result_error = False
            if self._validate_context({"action": "start"}):
                reply_to = self._context["reply_to"]
                self._context = None
            else:
                return  # TODO: probably need to fid a way to reply failure in that case
            assert result_error is False, "Worker should return result as ProtocolReply instance"
            if result is not None:
                if result.success:
                    self._reply_all(reply_to, result, None)
                else:
                    self._reply_all(reply_to, result, None)

    def _platformix_stop(self, context, fake_reply):    # TODO: Force parameter
        """
        Stops platform instance
        Breaks startup process if the platform is in middle of startup
        Waits before nested platforms are stopped before actually do stop
        # TODO: also should wait platforms which are waiting for this one on start
        If parent platform or platforms in wait list are not running yet - will wait for them
        If stop were deferred due to waiting of other platforms then stop method should be called again later
        Usually it happens automatically after other platforms are replying on their's stopping end
        :param context: messaging context
        :return: None
        """
        assert fake_reply is None, "platformix_stop replies shouldn't be faked!"

        stopping = self._worker.stopping   # Store current stopping state
        need_stop = self._worker.stopping = self._worker.running or self._worker.starting
        self._worker.stopping = True  # Set _stopping right in the beginning

        new_thread = False
        if not stopping and self._context is not None:  # Break startup process if necessary
            self._reply_all(self._context["reply_to"], proto_failure("interrupted by stop"), None)
            if self._worker.starting:
                self._worker.starting = False
                self._worker.start_in_progress = False
            self._context = None
        if not stopping and not need_stop:  # If not running and not starting - do nothing more
            self._worker.stopping = False
            self._reply(context, proto_success("already stopped", "state"), None)
            return
        if stopping:  # If were already stopping - update reply list
            if context not in self._context["reply_to"]:
                new_thread = True
                self._context["reply_to"].append(context)
        else:         # Otherwise initiate context
            new_thread = True
            self._context = {"action": "stop", "reply_to": [context],
                             "waiting_for": [], "wait_ignore": []}
            self._notify(context, "received stop signal")
            # TODO: do recursive stop? parent->childs? and call only root platforms stop?
        assert self._worker.stopping, "At this point stopping should be True"
        # Update waiting list
        # TODO: also wait those that are depends on this one
        self._context["waiting_for"] = [w.name for w in self.host.subplatforms + self.host.depended
                                        if w.running is True or w.stopping is True
                                        and w.name not in self._context["wait_ignore"]]

        # If there is some platforms to wait - notify about this
        if self.waiting_count > 0 and new_thread:
            self._worker.register_reply_handler(context,
                                                self._platformix_stop_reply_handler, [], {},
                                                timeout=self._worker.stop_max_wait, force=True)
            self._notify_all(self._context["reply_to"], "waiting")
        # If no one left to wait for - do stop at last
        elif not self._worker.stop_in_progress and self.waiting_count == 0:
            for c in self._context["reply_to"]:
                self._worker.unregister_reply_handler(c, True, {}, dont_check=True)
            self._worker.running = False
            self._worker.stop_in_progress = True
            self._notify_all(self._context["reply_to"], "stopping")
            result = self._worker.stop(self._context["reply_to"])
            reply_to = self._context["reply_to"]
            self._context = None
            assert isinstance(result, ProtocolReply), "Worker should return result as ProtocolReply instance"
            if result.success:
                self._reply_all(reply_to, proto_success(None), None)
            else:
                self._reply_all(reply_to, result, None)

    def _platformix_get(self, context, fake_reply, prop):
        """
        Get host's property.
        Value is returned in a success message as item with index same as property name
        :param context: messaging context
        :param prop: property symbolic name
        :return: None
        """
        if hasattr(self.host, prop):
            self._reply(context, proto_success(getattr(self.host, prop), prop), fake_reply)
        else:
            self._reply(context, proto_failure("Property {} not found on {}".format(prop, self.host.name)), fake_reply)

    def _platformix_set(self, context, fake_reply, prop, value):
        """
        Set host's property to a value
        :param context: messaging context
        :param prop: property symbolic name
        :param value: value to set
        :return: None
        """
        if hasattr(self.host, prop):
            if not callable(getattr(self.host, prop)):
                try:
                    setattr(self.host, prop, value)
                except Exception as e:
                    eprint("Platformix protocol: failed to set attribute {} of {} to value {} "
                           "due to exception {}".format(prop, self.host.name, value, e))
                    exprint()
                    self._reply(context, proto_failure(
                        "Failed to set attribute {} of {} to value {} "
                        "due to exception {}".format(prop, self.host.name, value, e)), fake_reply)
                    return
                self._reply(context, proto_success(getattr(self.host, prop), prop), fake_reply)
            else:
                self._reply(context, proto_failure("Attribute {} of {} is a method".format(
                    prop, self.host.name)), fake_reply)
        else:
            self._reply(context, proto_failure("Property {} not found on {}".format(prop, self.host.name)), fake_reply)

    def _platformix_call(self, context, fake_reply, method, *args, **kwargs):
        """
        Calls host's method
        Call result is returned in a success message as value item
        :param context: messaging context
        :param method: method symbolic name
        :param args: args to method call
        :param kwargs: kwargs to method call
        :return: None
        """
        if hasattr(self.host, method):
            if not callable(getattr(self.host, method)):
                self._reply(context, proto_failure("Attribute {} of {} is a property".format(
                    property, self.host.name)), fake_reply)
                return
            try:
                result = getattr(self.host, method)(*args, **kwargs)
            except Exception as e:
                eprint("Platformix protocol: failed to call method {} of {} with args {}, kwargs {} "
                       "due to exception {}".format(method, self.host.name, args, kwargs, e))
                exprint()
                self._reply(context, proto_failure(
                    "Failed to call method {} of {} with args {}, kwargs {} "
                    "due to exception {}".format(method, self.host.name, args, kwargs, e)), fake_reply)
                return
            self._reply(context, proto_success(result), fake_reply)
        else:
            self._reply(context, proto_failure("Method {} not found on {}".format(property, self.host.name)),
                        fake_reply)

    def _platformix_report(self, context, fake_reply, kind):
        """
        Reports about platform's state
        Currently only running and is_running supported
        * running - replies with retval True if platform is running, and False otherwise
        * is_running - successful reply if platform is running, and failure otherwise
        :param context:
        :param kind:
        :return:
        """
        if kind == "running":
            self._reply(context, proto_success(["False", "True"][self._worker.running]), fake_reply)
            return
        elif kind == "is_running":
            if self._worker.running:
                self._reply(context, proto_success("True", "state"), fake_reply)
            else:
                self._reply(context, proto_failure("False"), fake_reply)
        else:
            self._reply(context, proto_failure("Unknown report request"), fake_reply)


class PlatformixWrapper(Wrapper):
    """
    Use to map platform's methods and fields into worker, required by PlatformixProtocol
    """
    _methods = PlatformixProtocol._protocol_methods
    _fields = PlatformixProtocol._protocol_fields
