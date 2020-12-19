from core.helpers import Wrapper
from core.platformix_core import PlatformProtocolCore, PlatformInterfaceCore, PlatformMessage as PM, proto_failure


class StreamIOInterface(PlatformInterfaceCore):
    _base_id = "stream_io"
    _methods = ("send", "receive")
    # Methods:
    # * send - send data
    #   * args: data - string/bytearray or list of strings/bytearrays
    # * receive - receives data
    #   * args: count - amount of lines to receive
    # TODO: methods signature


class StreamIOProtocol(PlatformProtocolCore):
    """
    Implements StreamIO interface
    """
    _default_interface = StreamIOInterface
    _protocol_fields = ("running", )
    _protocol_methods = ("send", "receive", "reply", "reply_all")

    def _stream_io_send(self, context, fake_reply, data):
        if not self._ensure_running(context, fake_reply):
            return
        self._notify(context, "Calling send...")
        self._reply(context, self._worker.send(context, data), fake_reply)

    def _stream_io_receive(self, context, fake_reply, count=0, timeout=None, decode='UTF-8'):
        if not self._ensure_running(context, fake_reply):
            return
        self._notify(context, "Calling receive...")
        self._reply(context, self._worker.receive(context, count, timeout, decode), fake_reply)


class StreamIOWrapper(Wrapper):
    """
    Use to map platform's methods and fields into worker, required by SoftwareRunnerProtocol
    """
    _methods = StreamIOProtocol._protocol_methods
    _fields = StreamIOProtocol._protocol_fields


