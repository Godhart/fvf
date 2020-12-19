from core.platformix_core import ScoreboardRulesBase, PlatformMessage as PM
from core.simple_logging import eprint, exprint


class ScoreboardArithAll(ScoreboardRulesBase):

    # TODO: to check components with multiple interfaces where commands on one interface affects results on other interface
    # it's required to maked platform derived from scoreboard which would have model of that component
    # it may call scoreboards methods of different IPs passing additional args depending on model context

    def cmd(self, context, message):
        # TODO: call host's method instead
        if not self._accept_cmd(context, message):
            return True

        if message.method not in ("sum", "sub", "mult", "div", "power"):
            self._unhandled(context, message, "unsupported method! Check scoreboard against interface")
            return True

        if len(message.args) != 2:
            self._unhandled(context, message, "wrong format (expected 2 args)")
            return True

        if any(not isinstance(a, (int, float)) for a in message.args):
            self._handle(context, message, PM.failure("", -2))
            return True

        try:
            if message.method == "sum":
                self._handle(context, message, PM.success(message.args[0] + message.args[1]))
            elif message.method == "sub":
                self._handle(context, message, PM.success(message.args[0] - message.args[1]))
            elif message.method == "mult":
                self._handle(context, message, PM.success(message.args[0] * message.args[1]))
            elif message.method == "div":
                if message.args[1] != 0:
                    self._handle(context, message, PM.success(message.args[0] / message.args[1]))
                else:
                    self._handle(context, message, PM.success(None))
            elif message.method == "power":
                if message.args[0] == 0 and message.args[1] < 0:
                    self._handle(context, message, PM.success(None))
                else:
                    self._handle(context, message, PM.success(message.args[0] ** message.args[1]))

        except Exception as e:
            eprint("ScoreboardArithAll {}: exception occurred: {}!".format(self._host.name, e))
            exprint()
            self._unhandled(context, message, "exception occurred: {}!".format(e))
        return True

    def _response_cmp(self, resa, resb):
        if resa.is_success:
            return resa.kwargs == resb.kwargs
        else:
            return resa.kwargs["errcode"] == resb.kwargs["errcode"]

    def response(self, context, message):

        if not (message.is_success or message.is_failure):
            return False

        if not self._accept_response(context, message):
            return True

        if self._response_cmp(self._host.expected[context.str], message):
            self._success(context, message)
        else:
            self._error(context, message, "Wrong result! Expected: {}, got: {}".format(
                self._host.expected[context.str].serialize(), message.serialize()))
        return True


class Scoreboard(ScoreboardArithAll):
    pass
