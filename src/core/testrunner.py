from core.simple_logging import vprint, eprint, exprint

import time


class TestRunner(object):
    """
    Runs tests in specified test environment
    """

    @staticmethod
    def run_tests(env, tests, start_stop=True, include=None, exclude=None, dry_run=False):
        """
        A General Routine to run all Tests
        Returns dict with test name and it's results.
        True if test passed, False if test failed, None if test wasn't executed at all
        If exception is occurred on test then it's stored as a test's result
        :param env: Test environment in which test would run
        :param tests: List with tests descriptions to run. Each item exected to be a dict
        :param start_stop: If start_stop is True (default) then all platforms are stared before executing test
        and the all platforms are stopped after test has been executed
        :param include: List of test's names to be executed. Other test would be ignored. Set to None to include all
        :param exclude: List of test's names to be excluded from execution. Set to None to avoid exclusion.
        Exclude list takes priority over include
        :param dry_run: Don't run test actually. Just that tests would run
        :return: a dict with test name as key and test result (see run_test description) as value
                 if dry_run specified then test result would be None
        """
        result = {}
        if include is not None:
            includes_not_found = []
            tests_names = [t['name'] for t in tests]
            for test in include:
                if test not in tests_names and test != "_scoreboards_":
                    includes_not_found.append(test)
            if len(includes_not_found) != 0:
                raise ValueError("Tests {} were not found in:\n {}".format(', '.join(includes_not_found),
                                                                           ' \n '.join([t["name"] for t in tests])))
                # raise ValueError("Tests {} were not found".format(', '.join(includes_not_found)))

        for test in tests:
            k = test["name"]
            if exclude is not None and k in exclude:
                continue
            if include is not None and k not in include:
                continue
            result[k] = None
        for test in tests:
            k = test["name"]
            if exclude is not None and k in exclude:
                continue
            if include is not None and k not in include:
                continue
            try:
                if not dry_run:
                    result[k] = TestRunner.run_test(env, test, start_stop, start_stop)
                else:
                    result[k] = None
            except Exception as e:
                # TODO: make sure transaction ended (force it to end if necessary)
                result[k] = {"status": e, "elapsed": 0}
                eprint("Exception occurred on test '{}': {}".format(k, e))
                exprint()
                if start_stop:  # Make sure platforms are stopped
                    try:
                        env.stop_platforms()
                    except Exception as e:  # If it's impossible to stop platforms - break check
                        result["stop_platforms"] = {"status": e, "elapsed": 0}
                        eprint("Unrecoverable exception occurred during test calc::{}!\n"
                               "Aborting run_tests routine!\n"
                               "Exception: {}".format(k, e))
                        exprint()
                        env.emergency_stop()
                break
        return result

    @staticmethod
    def run_test(env, test, start, stop):
        """
        A General Routine to run single Tests
        Returns dict with test status and time elapsed
        :param env: Test environment in which test would run
        :param test: A Test to run. Should be a dict with following structure
          "name" - Test's name
          "f" - A function to call
          "args" - Args to a function, list expected
          "kwargs" - Keywords args to a function, dict expected
        :param start: Boolean. Set to True to start all platforms before conducting a Test
        :param stop: Boolean. Set to True to stop all platforms after test has been conducted
        :return: a dict with fields "status" and "elapsed"
        """
        vprint("\n\n===================================\nStarting test {}...\n".format(test["name"]))
        elapsed = time.time()
        if start:
            env.start_platforms()
        stat = test["f"](*test["args"], **test["kwargs"])
        if stop:
            env.stop_platforms()
        elapsed = time.time() - elapsed
        return {"status": stat, "elapsed": elapsed}
