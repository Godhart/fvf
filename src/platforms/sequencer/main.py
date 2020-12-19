from core.platformix import PlatformBase
from core.platformix_core import new_message, proto_success
from core.platformix_core import PlatformMessage as PM
from ip.sequencer.definitions import SequencerProtocol, SequencerWrapper
from core.eval_sandbox import evaluate
from .generators import *
from core.simple_logging import tprint
import time


class Sequencer(PlatformBase):
    """
    Class for testing purposes that produces requests sequence to parent platform
    """

    def __init__(self, expr, runs=0, **kwargs):
        super(Sequencer, self).__init__(**kwargs)
        self._expr_ = expr
        self._expr = None
        self._runs = runs
        self._remaining = 0
        self._complete = 0
        self._exiting = False
        # TODO: threaded option with valules [True, False, None] - default for run methods

        # Register Sequencer protocol support
        self._support_protocol(SequencerProtocol(self, SequencerWrapper.get_wrapper(self, "_")))

        self.subscribe("#sequencer")

    @property
    def runs(self):
        return self._runs

    @property
    def remaining(self):
        return self._remaining

    @property
    def complete(self):
        return self._complete

    def _request_gen(self, expr):
        # TODO: precompile eval to a function
        while True:
            yield(eval(expr))
            if self._stopping:
                break

    @property
    def expr(self):
        return self._expr_

    @expr.setter
    def expr(self, value):
        if self._expr is not None:
            self._expr = None
        self._expr_ = value
        self._expr = self._request_gen(self._expr_)

    def _start(self, reply_contexts):
        self._expr = self._request_gen(self._expr_)
        return super(Sequencer, self)._start(reply_contexts)

    def _stop(self, reply_contexts):
        """
        1. Stops request genertor
        :return:
        """
        self._expr = None
        return super(Sequencer, self)._stop(reply_contexts)

    def _run(self, context, runs=None):  # TODO: threaded arg
        if runs is None:
            runs = self._runs
        if runs <= 0:
            runs = 0
        self._complete = 0
        self._remaining = runs
        if self._remaining > 0:
            self._reply(context, PM.notify("started sequence"))
        while self._remaining > 0:
            assert self._expr is not None, "Sequencer {} wasn't started!".format(self.name)
            start_time = time.time()
            expr_result = next(self._expr)
            # TODO: replace assertions with proto_fails?
            assert isinstance(expr_result, (list, tuple)), "Expression should return list or tuple"
            assert len(expr_result) > 0, "Expression should return list or tuple with length at least" \
                                         "3 if there is no channel specification and " \
                                         "4 if there is channel specification"
            if isinstance(expr_result[0], str) and expr_result[0][0] in ('@', '#'):
                channel = expr_result.pop(0)
            else:
                channel = None
            assert len(expr_result) >= 3, "Expression should return list or tupple with length at least" \
                                          "3 if there is no channel specification and " \
                                          "4 if there is channel specification"
            request_message = new_message(*expr_result)
            c = self.request(request_message,
                             None, [], {}, channel=channel, store_state=False)
            # NOTE: used default request handler (which just waits for success or failure reply)
            tprint("sequencer {} request elapsed {}".format(self.name, time.time()-start_time))
            # TODO: option to treat request completed when specific message is passed by over special interface
            self._complete += 1
            self._remaining -= 1
        return proto_success({"breaked": runs != self._complete, "runs_completed": self._complete}, None)

    def _do_break(self, context):
        # NOTE: make's sense only in threaded run or if among reactions to sequencer request would be sequencer break
        # NOTE: just for LOL - try to use sequencer to test sequencer
        self._remaining = 0
        return proto_success("Breaked sequence. After last issued request is complete sequencer would stop",
                             retval_name="state")


class RootClass(Sequencer):
    pass
