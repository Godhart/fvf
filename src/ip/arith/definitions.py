from core.helpers import Wrapper
from core.platformix_core import PlatformProtocolCore, PlatformInterfaceCore, PlatformMessage as PM


class ArithInterface(PlatformInterfaceCore):
    _base_id = "arith"
    _methods = ("sum", "sub", "mult", "div", "power")
    # Methods:
    # * sum - returns A + B, args: A, B
    # * sub - returns A - B, args: A, B
    # * mult - returns A * B, args: A, B
    # * div - returns A / B, args: A, B
    # * power - returns A**M, args: A, M
    # TODO: methods signature


class ArithProtocol(PlatformProtocolCore):
    """
    Implements SoftwareRunner interface
    """
    _default_interface = ArithInterface
    _protocol_fields = ("running", )
    _protocol_methods = ("sum", "sub", "mult", "div", "power", "reply", "reply_all")

    def _arith_sum(self, context, fake_reply, a, b):
        if not self._ensure_running(context, fake_reply):
            if fake_reply is not None:
                self._reply(context, fake_reply, None)
            return
        self._notify(context, "Calling sum...")
        self._reply(context, self._worker.sum(context, a, b), fake_reply)

    def _arith_sub(self, context, fake_reply, a, b):
        if not self._ensure_running(context, fake_reply):
            if fake_reply is not None:
                self._reply(context, fake_reply, None)
            return
        self._notify(context, "Calling sub...")
        self._reply(context, self._worker.sub(context, a, b), fake_reply)

    def _arith_mult(self, context, fake_reply, a, b):
        if not self._ensure_running(context, fake_reply):
            if fake_reply is not None:
                self._reply(context, fake_reply, None)
            return
        self._notify(context, "Calling mult...")
        self._reply(context, self._worker.mult(context, a, b), fake_reply)

    def _arith_div(self, context, fake_reply, a, b):
        if not self._ensure_running(context, fake_reply):
            if fake_reply is not None:
                self._reply(context, fake_reply, None)
            return
        self._notify(context, "Calling div...")
        self._reply(context, self._worker.div(context, a, b), fake_reply)

    def _arith_power(self, context, fake_reply, a, m):
        if not self._ensure_running(context, fake_reply):
            if fake_reply is not None:
                self._reply(context, fake_reply, None)
            return
        self._notify(context, "Calling power...")
        self._reply(context, self._worker.power(context, a, m), fake_reply)


class ArithWrapper(Wrapper):
    """
    Use to map platform's methods and fields into worker, required by ArithProtocol
    """
    _methods = ArithProtocol._protocol_methods
    _fields = ArithProtocol._protocol_fields
