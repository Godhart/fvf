from core.platformix_core import PlatformFactory, PlatformsFarm, PlatformMessage, new_message
from core.simple_logging import vprint, eprint, exprint
from core.scheme import Scheme

import copy
import time
import pprint


class _ExpectedResults:

    @property
    def all_success(self):
        return [("all", "s")]

    @property
    def any_success(self):
        return [("any", "s")]

    @property
    def none_success(self):
        return [("none", "s")]

    @property
    def others_success(self):
        return [("others", "s")]

    @property
    def all_fail(self):
        return [("all", "f")]

    @property
    def any_fail(self):
        return [("any", "f")]

    @property
    def none_fail(self):
        return [("none", "f")]

    @property
    def others_fail(self):
        return [("others", "f")]

    @staticmethod
    def success(*args):
        return list((a, "s") for a in args)

    @staticmethod
    def fail(*args):
        return list((a, "f") for a in args)


er = _ExpectedResults()


class ConversationAnalyzer:
    """
    A Helper class to get info about conversation
    """
    def __init__(self, replies, ignore=None):
        self._ignore = ignore       # List of platforms to ignore
        if self._ignore is None:
            self._ignore = []
        self._participants = {}     # Dict with transaction's participants (anyone that replied at least once)
                                    # Key is participant name and value - content of last reply
        for r in replies:
            if r not in self._ignore:
                self._participants[r] = replies[r]

    @property
    def participants(self):
        """
        :return: list of transaction participants
        """
        return self._participants.keys()

    @property
    def in_progress(self):
        """
        :return: list of participants' names that not finished transaction by this moment
                 It's assumed that participant has finished transaction if it has sent reply with field "result"
        """
        return [p for p in self._participants if self._participants[p].is_notify]

    def partipiciants_by_result(self, checks, negative=False):
        """
        Returns list of participants with results that falls (or not if negated) into provided checks
        :param checks:   list or tuple of values to be checked against participants results
        :param negative: if True then list returned list of participants with results not falled into checks
        :return: list of participants' names
        """
        if checks == "s" or checks == "success":
            check_success = not negative
        elif checks == "f" or checks == "fail":
            check_success = negative
        else:
            raise ValueError("Checks can be only 'success', 's', 'fail' or 'f' but got '{}'".format(checks))
        return [p for p in self._participants
                if check_success and self._participants[p].is_success
                or (not check_success) and self._participants[p].is_failure
                ]

    def get_reply(self, source):
        """
        Returns last reply value for specified participant
        :param source: participant's name
        :return: last reply value
        """
        if source not in self._participants:
            return None
        return self._participants[source]

    @property
    def replies(self):
        return self._participants


class TestEnv(object):
    """
    Class that creates and breathes life into whole test environment
    * It loads test environment description
    * It creates all the platforms (runs his own Platforms Farm)
    * It starts/stops all the platforms
    * It performs messaging on test environment level (provides initial methods calls)
    """

    # TODO: support for model and test (specials in scheme)

    def __init__(self, description, generics=None, verbose=False):
        self.name = "__root__"
        self.farm = PlatformsFarm(self, verbose=verbose)  # Farm which manages all platform's instances and their interaction
        self._tc = None              # Topic Caster reference
        self._extrapolation_counter = 0
        self._extrapolation_chain = []
        self._extrapolated_values = {}
        self.verbose = verbose
        self._scheme = Scheme(
            description, generics=generics, root_section="test_env", specials=["model", "test", "options"],
            verbose=verbose, extrapolate=True)
        self._data = self._scheme.data
        print(self._scheme.to_uml())

    def instantiate(self):
        vprint("Test environment at instances instantination start:\n{}".format(pprint.pformat(self._data)))

        # Other entries are treated as platform's instances
        def add_instance(instance_generics, base_platform=None):
            args = copy.deepcopy(instance_generics)
            if base_platform is not None:
                args["base_platform"] = base_platform
            assert "base_platform" in args, "Not found base_platform for instance with generics {}".format(args)
            pi = PlatformFactory(farm=self.farm, **args)  # PI is for PLATFORM INSTANCE

        for p in self._data:     # P is for PLATFORM
            if p in self._scheme.specials:
                continue
            if 'condition' not in self._data[p] or self._data[p]['condition'] == True:
                ig = copy.deepcopy(self._data[p])
                if 'condition' in ig:
                    del ig['condition']
                add_instance(ig)

    def receive_message(self, context, message):
        if self._tc == (context.channel, context.thread) and PlatformMessage.message_is_reply(message):
            return True
        return False

    def transaction(self, channel, message, expected=None, ignore=None, more_info=False):
        """
        Conducts transaction on specified channel and checks platform's results against expected value
        Transaction is started from starting new thread in a specified channel and sending message into it
        Then replies are monitored. If platform has replied into channel at least once it's treated to be a participant
        After conversation on channel is finished it's ensured that:
        * there were at least single participant
        * all participants has finished transaction
        * if expected result is specified then participants's results are checked against expected value
        * if all checks were successful then transaction assumed successful to, otherwise it's failed for some reason

        :param channel: string, messaging channel's name
        :param message: PlatformMessage, to send into channel to initiate transaction
        :param expected: list with expected results. List of pairs (as lists or tuples).
                         1st value in a pair is for participant names
                         and 2nd is for expected value - "success"/"fail" or "s"/"f"
                         also special keys supported:
                         * all - all participants
                         * any - any of participants
                         * none - none of participants
                         * others - should be last in a list. corresponds to all participants that were not covered
                           by any of previous keys
                         BE WARE! Order of items in list does matters
                         if None then it's assumed that "all", "success" expected
        :param ignore: list, names of platforms that should be excluded from participants list
        :param more_info: If True then dict is returned with transaction result and all last replies,
                          otherwise - True if transaction were successful, False if not
        :return: True/False or dict depending on more_info
        """
        # TODO: Expected participants list
        if not isinstance(channel, str):
            raise ValueError("channel should be a string! got {} with value {}".format(type(channel), channel))
        if not isinstance(message, PlatformMessage):
            raise ValueError("message should be a PlatformMessage! got {} with value {}".format(type(message), message))
        message.sender = self.name

        if expected is None:
            expected = er.all_success

        if not isinstance(expected, (list, tuple)):
            raise ValueError("expected should be a list or tuple! got {} with value {}".format(type(expected), expected))
        for e in expected:
            if not isinstance(e, (list, tuple)) or len(e) < 2 or len(e) > 3:
                raise ValueError("items of expected should be a list or tuple with length 2 ot 3! "
                                 "got {} with value {}".format(type(e), e))
        if ignore is not None and not isinstance(ignore, list):
            raise ValueError(
                "ignore should be a list with length 2 ot 3! got {} with value {}".format(type(ignore), ignore))
        # TODO: check content of testing:fake_next_op

        if ignore is None:
            ignore = []  # TODO: ignore is not used yet
        if self.verbose:
            vprint("Starting transaction {}::{}".format(channel, message.serialize()))
        context = self.farm.start_thread(self, channel, message.interface)

        # NOTE: If previous transaction were interrupted due to exception (and messaging session were broken)
        # then can't proceed further
        assert self.farm.send_message_in_progress is False, "Can't start transaction" \
                                                            " if there is other messaging session is going"
        replies = self.farm.send_message(context, message)
        # NOTE: it may take some time to accomplish request (async usage for example)

        # No matter if multithreading is supported or not
        # but in the end everything should be settled down at this point

        conv_analyzer = ConversationAnalyzer(replies=replies, ignore=[self.name]+ignore)

        def check_responses(verbose=False):
            if len(conv_analyzer.in_progress) > 0:
                eprint("Some platforms ({}) are not completed transaction {}::{}!".format(
                    conv_analyzer.in_progress, channel, message.serialize()))
                return False
            elif len(conv_analyzer.participants) == 0:
                eprint("No one acknowledged transaction {}::{}!".format(channel, message.serialize()))
                return False
            elif not isinstance(expected, (list, tuple)):
                raise ValueError("'expected' argument should be a list or tuple of lists or tuples!")
            elif len(expected) == 0:
                eprint("Warning! Transaction {}::{} is without expected result! Completed but no checks made".format(
                    channel, message.serialize()))
                return True
            else:
                participants = conv_analyzer.participants
                others = conv_analyzer.participants
                total = len(others)
                result = [False]*len(expected)
                idx = 0

                for e in expected:
                    if not isinstance(e, (list, tuple)) or len(e) < 2:
                        raise ValueError("'expected' items should be list or tuple with length 2 or more")
                    negative = False
                    if len(e) >= 3:
                        negative = e[2]
                    matched = sorted(conv_analyzer.partipiciants_by_result(e[1], negative))
                    if e[0] == "all":
                        others = []
                        if len(matched) == total:
                            result[idx] = True
                        else:
                            unmatched = [p for p in participants if p not in matched]  # participants - matched
                            eprint("Platforms {} are failed to check against '{}{}' for 'all' "
                                   "on transaction {}::{}".format(unmatched, ["", "not "][negative], e[1], channel,
                                                                  message.serialize()))
                            for p in unmatched:
                                eprint("  {}: {}".format(p, conv_analyzer.replies[p].serialize()))
                    elif e[0] == "any":
                        others = []
                        if len(matched) > 0:
                            result[idx] = True
                        else:
                            unmatched = participants
                            eprint("None of platforms {} succeeded check against '{}{}' for 'any' on transaction "
                                   "{}::{}".format(unmatched, ["", "not "][negative], e[1], channel,
                                                   message.serialize()))
                            for p in unmatched:
                                eprint("  {}: {}".format(p, conv_analyzer.replies[p].serialize()))
                    elif e[0] == "others":
                        if len(others) == 0:
                            eprint("No other platforms left to check against '{}{}' on transaction {}::{}".format(
                                ["", "not "][negative], e[1], channel, message.serialize()
                            ))
                            result[idx] = True
                        else:
                            unmatched = [p for p in others if p not in matched]  # others - matched
                            others = []
                            if len(unmatched) > 0:
                                eprint("Platforms {} are failed to check against '{}{}' for 'others' on transaction"
                                       " {}::{}".format(unmatched, ["", "not "][negative], e[1], channel,
                                                        message.serialize()))
                                for p in unmatched:
                                    eprint("  {}: {}".format(p, conv_analyzer.replies[p].serialize()))
                            else:
                                result[idx] = True
                    elif e[0] == "none":
                        if len(matched) == 0:
                            result[idx] = True
                        else:
                            unmatched = matched
                            eprint("Platforms {} are failed to check against '{}{}' for 'none' "
                                   "on transaction {}::{}".format(unmatched, ["", "not "][negative], e[1], channel,
                                                                  message.serialize()))
                            for p in unmatched:
                                eprint("  {}: {}".format(p, conv_analyzer.replies[p].serialize()))
                    else:
                        if not isinstance(e[0], (list, tuple)):
                            el = [e[0]]
                        else:
                            el = e[0]
                        others = [p for p in others if p not in el]  # others - el
                        unmatched = [p for p in el if p not in matched]  # el - matched
                        if len(unmatched) == 0:
                            result[idx] = True
                        else:
                            eprint("Platforms {} are failed to check against '{}{}' on transaction {}::{}".format(
                                unmatched, ["", "not "][negative], e[1], channel, message.serialize()))
                            for p in unmatched:
                                eprint("  {}: {}".format(p, conv_analyzer.replies[p].serialize()))
                    idx += 1
            result = all(r is True for r in result)
            if result:
                if verbose:
                    vprint("Success! Transaction {}::{} completed successfully".format(channel, message.serialize()))
            else:
                if verbose:
                    eprint("Error! Transaction {}::{} failed on checks".format(channel, message.serialize()))
            return result

        result = check_responses(self.verbose)
        if more_info:
            result = {"result": result,
                      "replies": conv_analyzer.replies}
        return result

    def start_platforms(self):
        """ Starts all platforms """
        assert self.transaction("#platforms", PlatformMessage(self.name, "platformix", "start")) is True,\
            "Failed to start platforms (transaction fail)"
        assert self.farm.all_is_running, "Failed to start platforms (not all have been reacted on transaction)"

    def stop_platforms(self):
        """ Stops all platforms """
        assert self.transaction("#platforms", PlatformMessage(self.name, "platformix", "stop")) is True, \
            "Failed to stop platforms (transaction fail)"
        assert self.farm.all_is_stopped, "Failed to stop platforms (not all have been reacted on transaction)"

    def emergency_stop(self):
        return self.farm.emergency_stop()

    def check_scoreboards(self, include=None, exclude=None):
        try:
            r = self.transaction("#scoreboard",
                new_message("platformix", "get", "scoreboard"), more_info=True)    # TODO: add Scoreboard interface
        except Exception as e:
            eprint("Exception occurred on get scoreboard: {}".format(e))
            eprint()
            return False
        if r["result"] is False:
            eprint("Failed to get scoreboard")
            return False
        if len(r["replies"]) == 0:
            eprint("No scoreboards found")
            return False
        print("\n============================================================\n"
               "Scoreboards:")
        summary = {}
        errors = False
        for sname in r["replies"]:
            sdata = r["replies"][sname].reply_data["scoreboard"]
            print("  {}:\n{}".format(sname, pprint.pformat(sdata, indent=4)))
            for f in sdata:
                if f not in summary:
                    summary[f] = sdata[f]
                else:
                    try:
                        summary[f] += sdata[f]
                    except Exception as e:
                        eprint("Exception occurred on scoreboard summary update: {}".format(e))
                        exprint()
                        errors = True
        if len(r["replies"]) > 1:
            print("Summary:\n{}".format(pprint.pformat(summary)))
        print("")
        if errors or summary["errors"] > 0 or summary["unhandled"] > 0 or summary["requests"] != summary["success"]:
            return False
        return True

    def _print_device_tree(self, node, level):
        vprint("{}{}({}):".format("\t" * level, node.name, node.base_platform))
        level += 1
        farm_data = self.farm.expose_data()
        depending_nodes = [p.name for p in farm_data.platforms.values() if node in p.wait and node != p.parent]
        if node.wait is not None:
            if node.parent is None:
                waits_for = node.wait
            else:
                waits_for = [w for w in node.wait if w != node.parent.name]
            if len(waits_for) > 0:
                vprint("{}Depends on {}:".format("\t" * level, waits_for))
        if len(depending_nodes) > 0:
            vprint("{}Depending nodes {}:".format("\t" * level, depending_nodes))
        for s in node.subplatforms:
            self._print_device_tree(s, level)

    def print_device_tree(self):
        farm_data = self.farm.expose_data()
        for p in farm_data.platforms.values():
            if p.parent is None:
                self._print_device_tree(p, 1)

        # TODO: print UML for device tree
