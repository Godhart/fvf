from core.platformix import PlatformBase
from core.simple_logging import eprint


class Coverage(PlatformBase):
    """
    Class for functional coverage gathering
    Implements core of coverage class and provides strictly defined interface
    All specifics are covered with worker instance (created on core start)
    """

    def __init__(self, channel, interface, rules, rules_kwargs=None, **kwargs):
        super(Coverage, self).__init__(**kwargs)

        self._channel = channel
        self._interface = interface
        if rules_kwargs is None:
            rules_kwargs = {}

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

        self.subscribe("#coverage")
        self.subscribe(self._channel)

    @property
    def coverage(self):
        """
        Coverage summary - tupple with amount of cases and covered cases
        May be used to determine coverage percentage
        :return: tuple
        """
        return self._rules.coverage()

    @property
    def coverage_data(self):
        """
        Full coverage information
        :return: dict
        """
        return self._rules.coverage_data()

    def receive_message(self, context, message):
        if not super(Coverage, self).receive_message(context, message):
            if context.channel == self._channel and context.interface == self._interface:
                return self._rules.receive_message(context, message)
            else:
                return False

    # TODO: method to store/load statistics


class RootClass(Coverage):
    pass
