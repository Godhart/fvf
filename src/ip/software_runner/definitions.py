from core.helpers import Wrapper
from core.platformix_core import PlatformProtocolCore, PlatformInterfaceCore, PlatformMessage as PM, proto_failure


class SoftwareRunnerInterface(PlatformInterfaceCore):
    _base_id = "softwarerunner"
    _methods = ("send", "receive", "log")
    # Methods:
    # * send - sends data to software instance via stdin
    #   * args: data - string/bytearray or list of strings/bytearrays
    # * receive - receives data from software instance via stdin
    #   * args: count - amount of lines to receive
    # * log - reads instance run log including stderr output
    #   * no args required
    # TODO: methods signature


class SoftwareRunnerProtocol(PlatformProtocolCore):
    """
    Implements SoftwareRunner interface
    """
    _default_interface = SoftwareRunnerInterface
    _protocol_fields = ("running", "connection")
    _protocol_methods = ("send", "receive", "log", "reply", "reply_all")

    def _ensure_connected(self, context, fake_reply):
        if self._worker.connection is None or self._worker.connection is False:
            self._reply(context, proto_failure("No connection. Ensure start is complete successfully"), fake_reply)
            return False
        else:
            return True

    def _softwarerunner_send(self, context, fake_reply, data):
        if not self._ensure_running(context, fake_reply) or not self._ensure_connected(context, fake_reply):
            return
        self._notify(context, "Calling send...")
        self._reply(context, self._worker.send(context, data), fake_reply)

    def _softwarerunner_receive(self, context, fake_reply, count=1, timeout=1.0):
        if not self._ensure_running(context, fake_reply) or not self._ensure_connected(context, fake_reply):
            return
        self._notify(context, "Calling receive...")
        self._reply(context, self._worker.receive(context, count), fake_reply)

    def _softwarerunner_log(self, context, fake_reply):
        if not self._ensure_running(context, fake_reply) or not self._ensure_connected(context, fake_reply):
            return
        self._notify(context, "Calling log...")
        self._reply(context, self._worker.log(context), fake_reply)


class SoftwareRunnerWrapper(Wrapper):
    """
    Use to map platform's methods and fields into worker, required by SoftwareRunnerProtocol
    """
    _methods = SoftwareRunnerProtocol._protocol_methods
    _fields = SoftwareRunnerProtocol._protocol_fields


