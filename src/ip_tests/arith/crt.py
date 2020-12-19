import inspect
from core.simple_logging import eprint, exprint
from core.platformix_core import new_message


class ArithTest(object):

    def __init__(self, env, crt=False):
        """
        :param env: Environment class which hosts all the test infrastructure. Should be a TestEnv class instance
        """
        self._env = env
        self._crt = crt

    @property
    def tests(self):
        """
        Returns list of available tests in TestEnv test description format
        Order of items defines order of execution in run_all
        :return a list of tests
        """
        result = [
            {"name": "crt", "f": self._test_arith_crt, "args": [], "kwargs": {}},
            {"name": "crt_long", "f": self._test_arith_crt, "args": [1000], "kwargs": {}},
        ]
        return result

    def _test_arith_crt(self, runs=None):
        # TODO: tell scoreboards about new test beginning (to be available get isolated test results)
        if runs is not None:
            args = [runs]
        else:
            args = []
        r = self._env.transaction("#sequencer", new_message("sequencer", "run", *args), more_info=True)
        assert r["result"] is True, "Failed on sequence running for arith".format()
        # TODO: get scoreboards results and judge failed it or not
        return True


class RootTest(ArithTest):

    def __init__(self, env, crt=False):
        super(RootTest, self).__init__(env, crt=crt)
