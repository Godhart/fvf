import inspect
import time
from core.simple_logging import eprint, exprint
from core.platformix_core import new_message, fake_op_message, proto_failure
from core.testenv import er


class PlatformixTest(object):

    def __init__(self, env):
        """
        :param env: Environment class which hosts all the test infrastructure. Should be a TestEnv class instance
        """
        self._env = env

    @property
    def tests(self):
        """
        Returns list of available tests in TestEnv test description format
        Order of items defines order of execution in run_all
        :return a list of tests
        """
        result = [
            #  NOTE: uncomment string below if want to do all smoke tests at once
            # {"name": "[smoke_test]", "f": self.smoke_test, "args": [], "kwargs": {}},
            {"name": "[sanity check]", "f": self.smoke_test, "args": [["[sanity check]"]], "kwargs": {}},
            {"name": "[single fail] success check", "f": self.smoke_test, "args": [["[single fail] success check"]], "kwargs": {}},
            {"name": "[any success] fail check", "f": self.smoke_test, "args": [["[any success] fail check"]], "kwargs": {}},
            {"name": "[not(any success)] fail check", "f": self.smoke_test, "args": [["[not(any success)] fail check"]], "kwargs": {}},
            {"name": "[any fail] success check", "f": self.smoke_test, "args": [["[any fail] success check"]], "kwargs": {}},
            {"name": "[no response] fail check", "f": self.smoke_test, "args": [["[no response] fail check"]], "kwargs": {}},
            {"name": "[set/get] complex check", "f": self.getset_test, "args": [], "kwargs": {}},
            {"name": "[call] check", "f": self.call_test, "args": [], "kwargs": {}},
            {"name": "[exception_test]", "f": self.exception_test, "args": [], "kwargs": {}},
            {"name": "[shouldn't be started]", "f": self.call_test, "args": [], "kwargs": {}},
        ]
        return result

    def _platformix_smoke_test(self, tests_list=None):
        env = self._env
        # Accepts following values in tests_list:
        # "success, fake, report"
        # "no fail check"

        # TODO: check if there is required amount of responses

        # Start  # NOTE: startup is made by testenv itself now
        # assert env.transaction("#platforms", new_message("platformix", "start")) is True, "Failed to start platforms"

        # Test errors control
        if tests_list is not None:
            tests_list = list(tests_list)
        if tests_list is None or "[sanity check]" in tests_list:
            if tests_list is not None:
                del tests_list[tests_list.index("[sanity check]")]
            if env.transaction(
                    "@platform_b",
                    fake_op_message("platformix",
                                    proto_failure("Failed by intent (fake_next_op, "
                                                  "Single unit error in [all success] condition)"),
                                    on_channel="#platforms",
                                    on_message=new_message("platformix", "report", "is_running")
                                    ),
                    er.all_success + er.none_fail) is False:
                eprint("Failed to set fake_next_op on [sanity check]")
                return False
            # NOTE: both all and none in condition above are for testing purpose

            # No fail since it's another channel
            if env.transaction("@platform_b", new_message("platformix", "report", "is_running"), er.none_fail) is False:
                # NOTE: none in condition above is testing purpose
                eprint("Failed to pass [report is_running] or avoid faking on [sanity check]")
                return False

            # No fail since it's another command
            if env.transaction("#platforms", new_message("platformix", "report", "running")) is False:
                eprint("Failed to pass [report running] or avoid faking on [sanity check]")
                return False

            # Fail as we told platform_b to do so
            if env.transaction("#platforms", new_message("platformix", "report", "is_running")) is True:
                eprint("Failed to pass faking or [all success] fail check on [sanity check]")
                return False

        if tests_list is None or "[single fail] success check" in tests_list:
            if tests_list is not None:
                del tests_list[tests_list.index("[single fail] success check")]
            if env.transaction(
                    "@platform_b",
                    fake_op_message("platformix",
                                    proto_failure("Failed by intent (fake_next_op, Single unit error "
                                                  "in [single fail] condition)"),
                                    on_channel="#platforms",
                                    execute=True
                                    )) is False:
                eprint("Failed to set fake_next_op on [single fail] success check")
                return False

            # No fail as we expecting that platform_b about to fail (NOTE: - no message filtering here)
            if env.transaction("#platforms", new_message("platformix", "report", "running"),
                               er.fail("platform_b") + er.others_success) is False:
                eprint("Failed to pass [single fail] success check")
                return False

        if tests_list is None or "[any success] fail check" in tests_list:
            if tests_list is not None:
                del tests_list[tests_list.index("[any success] fail check")]
            if env.transaction(
                    "#platforms",
                    fake_op_message("platformix",
                                    proto_failure("Failed by intent (fake_next_op, All fail "
                                                  "on [any success] condition)"),
                                    on_channel="#platforms"
                                    )) is False:
                eprint("Failed to set fake_next_op on [any success] fail check")
                return False

            # Should fail
            if env.transaction("#platforms", new_message("platformix", "report", "running"), er.any_success) is True:
                eprint("Failed to pass [any success] fail check")
                return False

        if tests_list is None or "[not(any success)] fail check" in tests_list:
            if tests_list is not None:
                del tests_list[tests_list.index("[not(any success)] fail check")]
            # Should pass as condition is negated
            if env.transaction("#platforms", new_message("platformix", "report", "running"),
                               [("any", "success", True)]) is True:
                eprint("Failed to pass [not(any success)] fail check")
                return False

        if tests_list is None or "[any fail] success check" in tests_list:
            if tests_list is not None:
                del tests_list[tests_list.index("[any fail] success check")]
            if env.transaction(
                    "@platform_b",
                    fake_op_message("platformix",
                                    proto_failure("Failed by intent (fake_next_op, Should pass "
                                                  "as condition is negated)"),
                                    on_channel="#platforms"
                                    )) is False:
                eprint("Failed to set fake_next_op on [any fail] success check")
                return False

            # Should pass as one item failed, as expected
            if env.transaction("#platforms", new_message("platformix", "report", "running"), er.any_fail) is False:
                eprint("Failed to pass [any fail] success check")
                return False

        # Check request without response (should fail)
        if tests_list is None or "[no response] fail check" in tests_list:
            if tests_list is not None:
                del tests_list[tests_list.index("[no response] fail check")]
            if env.transaction("__void__", new_message(None, "platformix", "report", "running"), er.all_fail) is True:
                eprint("Failed to pass [no response] fail check")
                return False

        # Stop  # NOTE: stop is made by testenv itself now
        # assert env.transaction("#platforms", new_message("platformix", "stop")) is True, "Failed to stop platforms"

        if tests_list is not None and len(tests_list) > 0:
            eprint("There is unknown tests left in a list: {}".format(tests_list))
            return False

        return True

    def _platformix_getset_test(self):
        env = self._env
        value = time.time()
        if env.transaction("@platform_b", new_message("platformix", "set", "tag", value), er.all_success) is False:
            eprint("Failed to set property")
            return False

        r = env.transaction("@platform_b", new_message("platformix", "get", "tag"), er.all_success, more_info=True)
        if r["result"] is False:
            eprint("Failed to get property")
            return False
        r = r["replies"]["platform_b"]
        if r.reply_data["tag"] != value:
            eprint("Value of property: {} is not that expected: {}!".format(r.reply_data["tag"], value))
            return False

        if env.transaction("@platform_b", new_message("platformix", "set", "__shouldnt_exists__", value),
                           er.all_fail) is False:
            eprint("Failed check of setting wrong property (expected to fail, but succeed)")
            return False

        return True
        # TODO: enable code below
        # NOTE: code below is unreachable yet since exception during transaction now breaks whole process
        try:
            if env.transaction("@platform_b", new_message("platformix", "set", "__shouldnt_exists__"),
                               er.all_fail) is False:
                eprint("Failed check set without necessary arguments (expected exception, but succeed)")
                return False
            eprint("Failed check set without necessary arguments (expected exception, but failed)")
            return False
        except TypeError as e:
            pass

        try:
            if env.transaction("@platform_b", new_message("platformix", "get"),
                               er.all_fail) is False:
                eprint("Failed check get without necessary arguments (expected exception, but succeed)")
                return False
            eprint("Failed check get without necessary arguments (expected exception, but failed)")
            return False
        except TypeError as e:
            pass

        return True

    def _platformix_call_test(self):
        env = self._env
        value = [0, 101, 202]
        expected = [value[2], value[1], value[0]]
        r = env.transaction("@platform_b", new_message("platformix", "call", "call_test", *value), er.all_success,
                            more_info=True)
        if r["result"] is False:
            eprint("Failed call_test transaction")
            return False
        r = r["replies"]["platform_b"]
        r_data = r.reply_data["value"]
        compare_failed = False
        if not isinstance(r_data, list):
            compare_failed = True
        elif len(r_data) != len(expected):
            compare_failed = True
        else:
            for i in range(0, len(expected)):
                if r_data[i] != expected[i]:
                    compare_failed = True
                    break
        if compare_failed:
            eprint("Reply of call_test: {} is not that expected: {}!".format(r.reply_data["value"], expected))
            return False
        return True

    def smoke_test(self, *args, **kwargs):
        """ Shallow checks for core functions of platformix protocol, platform_base component and testenv itself
        """

        try:
            if not self._platformix_smoke_test(*args, **kwargs):
                return False

        except Exception as e:
            eprint("Exception occurred during test platformix::{}({},{})!".format(
                inspect.currentframe().f_code.co_name, args, kwargs))
            exprint()
            raise e

        return True

    def exception_test(self, *args, **kwargs):
        """ Checks testenv reaction to exception during test
        """
        eprint("Exception is provoked as a part of test. Further testing should break and platforms shall be stopped")
        assert False, "Assertion error occurred AS EXPECTED. Ensure platforms are stopped correctly"

    def getset_test(self, *args, **kwargs):
        """ Checks get method of platformix protocol
        """
        try:
            if not self._platformix_getset_test(*args, **kwargs):
                return False

        except Exception as e:
            eprint("Exception occurred during test platformix::{}({},{})!".format(
                inspect.currentframe().f_code.co_name, args, kwargs))
            exprint()
            raise e

        return True

    def call_test(self, *args, **kwargs):
        """ Checks get method of platformix protocol
        """
        try:
            if not self._platformix_call_test(*args, **kwargs):
                return False

        except Exception as e:
            eprint("Exception occurred during test platformix::{}({},{})!".format(
                inspect.currentframe().f_code.co_name, args, kwargs))
            exprint()
            raise e

        return True


class RootTest(PlatformixTest):
    pass
