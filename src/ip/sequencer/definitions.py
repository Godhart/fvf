from core.helpers import Wrapper
from core.platformix_core import PlatformProtocolCore, PlatformInterfaceCore, PlatformMessage as PM, proto_failure


class SequencerInterface(PlatformInterfaceCore):
    _base_id = "sequencer"
    _methods = ("run", "break")  # TODO: "run_threaded"
    # Methods:
    # * run - starts sequence generation
    #   * args: runs - amount of requests to issue
    #           if None then platform's 'runs' property is used to determine amount
    #           if sequencer is already running then failure would occur
    # * break - breaks current sequence generation, no args
    # TODO: methods signature


class SequencerProtocol(PlatformProtocolCore):
    """
    Implements SoftwareRunner interface
    """
    _default_interface = SequencerInterface
    _protocol_fields = ("running", "remaining")
    _protocol_methods = ("run", "do_break", "reply", "reply_all")  # TODO: "run_threaded"

    def _sequencer_run(self, context, fake_reply, runs=None):
        if not self._ensure_running(context, fake_reply):
            return
        if self._worker.remaining > 0:
            self._reply(context, proto_failure("Already running"), fake_reply)
        self._notify(context, "Calling run...")
        self._reply(context, self._worker.run(context, runs), fake_reply)

    def _sequencer_break(self, context, fake_reply):
        if not self._ensure_running(context, fake_reply):
            return
        self._notify(context, "Calling break...")
        self._reply(context, self._worker.do_break(context), fake_reply)


class SequencerWrapper(Wrapper):
    """
    Use to map platform's methods and fields into worker, required by SequencerProtocol
    """
    _methods = SequencerProtocol._protocol_methods
    _fields = SequencerProtocol._protocol_fields
