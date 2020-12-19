from core.platformix import PlatformBase
from core.platformix_core import PlatformMessage as PM
from core.simple_logging import eprint
import copy


class Scoreboard(PlatformBase):
    """
    Implements core of scoreboard and provides strictly defined interface
    All specifics are covered with worker instance (specified as rules and created on core start)
    """

    def __init__(self, cmd, res, rules, rules_kwargs=None, clean_completed=False, **kwargs):
        """
        :param cmd: dict with 'channel' and 'interface' to specify where commands are coming from
        :param res: dict with 'channel' and 'interface' to specify where responses are coming from
        :param rules: string with path to python's class which would actually handle cmmands and responses
        :param rules_kwargs: dict with keyworded args for rules instantiation
        :param clean_completed: cleanup completed commands data to free up memory
        :param kwargs: kwargs to PlatformBase
        """
        super(Scoreboard, self).__init__(**kwargs)
        assert isinstance(cmd, dict) and "channel" in cmd and "interface" in cmd, "cmd should be a dict with" \
                                                                                  "records 'channel' and 'interface'"
        assert isinstance(res, dict) and "channel" in res and "interface" in res, "cmd should be a dict with" \
                                                                                  "records 'channel' and 'interface'"
        self._clean_completed = clean_completed
        self._cmd = cmd
        self._res = res
        if rules_kwargs is None:
            rules_kwargs = {}

        # Common Metrics
        self.commands = 0    # Total amount of received commands
        self.responses = 0   # Total amount of received responses
        self.success = 0     # Total amount of successfully passed responses (received expected result)
        self.errors = []     # List with errors
        self.unhandled = []  # List of unhandled commands
        self.expected = {}   # Dict with expected values without received response. Key is messaging context

        lcls = {}
        try:
            exec("from {} import Scoreboard as sb; cl = sb".format(rules), globals(), lcls)
        except ModuleNotFoundError as e:
            eprint("Rules module '{}' wasn't found for scoreboard {}!".format(rules, self.name))
            raise e
        except ImportError as e:
            eprint("Scoreboard unit wasn't found in rules module '{}' for scoreboard {}!".format(rules, self.name))
            raise e

        self._rules = lcls["cl"](host=self, **rules_kwargs)

        self.subscribe("#scoreboard")
        self.subscribe(self._cmd["channel"])
        if self._cmd["channel"] != self._res["channel"]:
            self.subscribe(self._res["channel"])

    @property
    def clean_completed(self):
        return self._clean_completed

    @property
    def scoreboard(self):
        """
        Scoreboard accumulated (summary) statistics including rules's specific data (rules_stats)
        :return: dict
        """
        stats = {
            "requests": self.commands,
            "responses": self.responses,
            "success": self.success,
            "errors": len(self.errors),
            "unhandled": len(self.unhandled),
            "queued_requests": len(self.expected)
        }
        if hasattr(self._rules, "stats"):
            rules_stats = self._rules.stats
            for stat in rules_stats:
                stats[stat] = rules_stats[stat]
        return stats

    @property
    def rules_stats(self):
        """
        Rules specific dict with accumulated (summary) statistics
        :return: dict
        """
        if hasattr(self._rules, "stats"):
            return self._rules.stats
        else:
            return None

    @property
    def scoreboard_data(self):
        """
        Full scoreboard information
        Like: which commands were observed / not observed, on which there were errors, which are still in progress
        :return: dict
        """
        data = {
            "errors": copy.deepcopy(self.errors),
            "unhandled": copy.deepcopy(self.unhandled),
            "queued_requests": copy.deepcopy(self.expected)
        }
        if hasattr(self._rules, "details"):
            details = self._rules.details
            for record in details:
                data[record] = details[record]
        return data

    def receive_message(self, context, message):
        if not super(Scoreboard, self).receive_message(context, message):
            message = PM.parse(message)
            if context.channel == self._cmd["channel"] and context.interface == self._cmd["interface"]\
                    and not message.is_reply:
                return self._rules.cmd(context, message)
            elif context.channel == self._res["channel"] and context.interface == self._res["interface"]\
                    and message.is_reply:
                return self._rules.response(context, message)
            else:
                return False
        else:
            return True

    # TODO: method to store/load statistics


class RootClass(Scoreboard):
    pass
