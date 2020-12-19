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
        if not self._crt:
            result = [
                {"name": "test_sum", "f": self.test_arith, "args": [["sum", 1, 1]], "kwargs": {"expected": 1 + 1}},
                {"name": "test_sub", "f": self.test_arith, "args": [["sub", 5, 2]], "kwargs": {"expected": 5 - 2}},
                {"name": "test_mult", "f": self.test_arith, "args": [["mult", 2, 2]], "kwargs": {"expected": 2 * 2}},
                {"name": "test_div", "f": self.test_arith,
                 "args": [["div", 5, 3]], "kwargs": {"expected": 5/3}},
                {"name": "test_power", "f": self.test_arith, "args": [["power", 2, 9]], "kwargs": {"expected": 512}},

                {"name": "test_div0", "f": self.test_arith, "args": [["div", 5, 0]], "kwargs": {"expected": None}},
                # NOTE: This should provoke exception in tested app

                {"name": "should_fail", "f": self.test_arith, "args": [["sum", 2, 3]],
                 "kwargs": {"expected": 2 + 3 + 1}},
                # NOTE: A special test to check that fail checking is work
            ]
        else:
            result = [
                {"name": "crt", "f": self._test_arith_crt, "args": [], "kwargs": {}},
                {"name": "crt_long", "f": self._test_arith_crt, "args": [1000], "kwargs": {}},
            ]

        return result

    def _test_arith(self, op, expected):
        """ Issues operation to a arith component and checks result against expected value """
        r = self._env.transaction("@calc_if",  # TODO: specify channel via arg
            new_message("arith", *op), more_info=True)
        assert r["result"] is True, "Failed to complete transaction {}".format(' '.join(str(o) for o in op))
        if r["replies"]["calc_if"].reply_data["value"] != expected:  # TODO: specify responder's name via arg
            return False
        return True

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

    def test_arith(self, *args, **kwargs):
        """ Checks how arith functions works
        """

        try:
            if not self._test_arith(*args, **kwargs):
                return False

        except Exception as e:
            eprint("Exception occurred during test arith::{}!".format(
                inspect.currentframe().f_code.co_name, e))
            exprint()
            raise e

        return True


class RootTest(ArithTest):

    def __init__(self, env, crt=False):
        super(RootTest, self).__init__(env, crt=crt)
