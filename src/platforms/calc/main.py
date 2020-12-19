from core.platformix_core import new_message, proto_success, proto_failure, PlatformMessage as PM
from core.platformix import PlatformBase
from core.simple_logging import tprint, exprint
from ip.arith.definitions import ArithWrapper, ArithProtocol
from core.eval_sandbox import evaluate
import time


class Calc(PlatformBase):
    """
    An Abstraction (Wrapper) of Example Calc App (calc.py)
    Totally relies on it's parent for transferring requests to an app and getting replies
    """

    def __init__(self, mock=False, io_interface="softwarerunner", **kwargs):
        super(Calc, self).__init__(**kwargs)
        self._mock = bool(mock)     # If True then requests are executed right on this platform w/o sending to real app
        self._io_interface = io_interface   # Defines parents interface that would be used for i/o

        # Register ArithRunner protocol support
        self._support_protocol(ArithProtocol(self, ArithWrapper.get_wrapper(self, "_")))

    def _start(self, reply_contexts):
        """
        Makes sure that incoming/outgoing streams are synchronised
        :return: True if all necessary actions complete successfully, otherwise - False
        """
        # Flush any junk that could occur on app start (a common case example)
        # NOTE: Or you could wait in a loop for a specific message depending on app used

        if not self._mock:
            c = self.request(new_message(self._io_interface, "receive", -1), None, [], {}, timeout=2.0)
            # TODO: cleaning required for softwarerunner only
            # TODO: reduce receive timeout instead of increasing request timeout
            c_state = self._pop_request_state(c)
            if not self._request_state_is_success(c_state):
                return proto_failure("Failed to flush i/o on start")
        return super(Calc, self)._start(reply_contexts)

    def _sum(self, context, a, b):
        return self.calculate("{}+{}".format(a, b))

    def _sub(self, context, a, b):
        return self.calculate("{}-{}".format(a, b))

    def _mult(self, context, a, b):
        return self.calculate("{}*{}".format(a, b))

    def _div(self, context, a, b):
        return self.calculate("{}/{}".format(a, b))

    def _power(self, context, a, m):
        return self.calculate("({})**({})".format(a, m))

    def calculate(self, expression):
        """
        :param expression: string with expression to send to Calc App
        :return: ProtocolReply
        """
        start_time = time.time()
        if self._mock:
            try:
                result = evaluate(expression)
            except ZeroDivisionError:
                result = None
            except Exception as e:
                result = "Platform {}: exception occurred on calculate: {}".format(self.name, e)
                exprint()
                tprint("calculate (with fail) elapsed {}".format(time.time() - start_time))
                return proto_failure(result, -2)
            tprint("calculate elapsed {}".format(time.time() - start_time))
            return proto_success(result)

        # NOTE: mock code just ended here. To avoid nesting there is no else, just flat code

        # TODO: optimize code - now it's way to hard (just send/receive and so much code!!!)
        c = self.request(new_message(self._io_interface, "send", expression),
                         None, [], {}, timeout=2.0)  # TODO: decrease timeout
        c_state = self._pop_request_state(c)
        if not self._request_state_is_success(c_state):
            tprint("calculate (with fail result) elapsed {}".format(time.time() - start_time))
            return proto_failure("IO failed to send data")

        c = self.request(new_message(self._io_interface, "receive"),
                         None, [], {}, timeout=2.0)  # TODO: decrease timeout
        c_state = self._pop_request_state(c)
        if not self._request_state_is_success(c_state):
            tprint("calculate (with fail result) elapsed {}".format(time.time() - start_time))
            return proto_failure("IO failed to receive response")
        # TODO: convert from string to number
        tprint("calculate elapsed {}".format(time.time() - start_time))
        result = PM.parse(c_state["__message__"]).reply_data["value"]
        if isinstance(result, (list, tuple)):   # NOTE: softwarerunner returns list but stream_io returns single item
            result = result[0]
        if result.strip() == 'None':
            result = None
        else:
            try:
                result = int(result)
            except ValueError:
                result = float(result)
        return proto_success(result)


class RootClass(Calc):
    pass
