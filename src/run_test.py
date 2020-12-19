h = """
usage: python run_test.py <environment> <tests location> <tests package> 
         [<tests module>] [<tests class>] [<test 1 name>] [<test 2 name>] ...
         [<option 1>] [<option 2>] ...

  environment   - path to file with environment description or string with 
                  description itself.
  tests location- path to test package location within framework. 
                  only 'ip_tests' and 'platforms_test' are allowed yet.
  tests package - name of package from src/tests which contains module with
                  necessary test(s).
  tests module  - name of module from test_package with necessary test(s). 
                  Optional, default value is 'main'.
  tests class   - class name from test module with necessary test(s) description
                  Optional, default value is 'RootTest'.
  test name     - name of test to run. If not specified then all tests contained
                  in test class would run.

Following one or more options could passed along:

Test environment options:

  -g=<generic name>:<generic value>   - specifies test environment generics, one
                  per each generic. Generic name should be alphanumeric value.  
                  Generic value could be a string or quoted string. 
                  See NOTE below about values types conversion.

Test options:

  -st           - if specified without value or specified with value except 
                  False or 0 then all test environment objects would be started
                  before and stopped after each test

  -a=<argument value>  - specifies positional arguments for test class 
                  constructor, one per each argument. 
                  Argument value could be a string or quoted string. 
                  See NOTE below about value types conversion
  
  -k=<argument name>:<argument value> - specifies keyworded arguments for test
                  class constructor, one per each argument.
                  Argument value could be a string or quoted string. 
                  See NOTE below about values types conversion

Result output options:

  -re   -  report elapsed time in tests results.
           Could be specified with value False or 0 to turn off.

Verbose output options:  

  -h    -  don't run test, print this usage information only

  -v    -  turn on verbose output. 
           Could be specified with value False or 0 to turn off.
  -vf   -  direct verbose output into file.
           If value is not specified then it would be file '.log' in working 
           directory. 
           If specified value is empty string ("") then STDOUT would be used.
  -ve   -  print errors output (STDERR stream) into verbose output stream.
           Could be specified with value False or 0 to turn off.
  -vt   -  turn on timestamps on verbose output
           Could be specified with value False or 0 to turn off.
  
NOTE: Values conversion. 

  Values of test environment's generics and arguments for test class 
  constructor would be converted as following:
  'True' or 'False' would be converted to boolean type,
  Values with digits only would be converted to integer number type, 
  Digits with single point would be converted to float number type. 
  
  If other type is desired then use string with following template:
  $e{<python expression>}.
  Resulting type would be return type of python expression.
  For test constructor arguments inside curly braces shall be only valid
  python expression.
  For generics values more complicated expression allowed, for more 
  information read about test environment's values extrapolation.
"""

if __name__ == '__main__':
    from core.simple_logging import vprint, eprint, exprint
    from core.testenv import TestEnv
    from core.testrunner import TestRunner
    import core.simple_logging as simple_logging
    import re

    import sys
    import time

    import pprint

    description = None                  # Test environment description
    test_location = None                # Test kind
    permitted_test_location = ("ip_tests", "platforms_tests")
    test_package = None                 # Package with test module
    test_module = "main"                # Module with test class
    test_class = "RootTest"             # Class that should be used as TestClass
    test_name = None                    # Test Name to run (all if is None)
    generics = {}
    options = {
        'st': False,
        'v': False,
        've': False,
        'vt': False,
        're': False,
    }
    test_args = []                      # Test's positional args
    test_kwargs = {}                    # Test's keyworded args

    start_stop = False                  # Do platforms start/stop between tests # TODO: default True
    verbose = False                     # Do verbose output? Prints extended info. Otherwise only results are printed
    ve = False                          # Print errors into verbose stream
    vt = False                          # Print timestamps in verbose messages
    rel = False                         # Report elapsed time in tests results

    vf = sys.stdout                     # Stream to print verbose output to

    def print_help():
        print(h)

    def try_parse(value, is_arg=True):
        if value in ("True", "False"):
            return value == "True"
        if is_arg:
            m = re.fullmatch(r"^\$e{(.+?)}$", value)
            if m is not None:
                try:
                    retval = eval(m.groups()[0])
                    return retval
                except Exception as e:
                    if is_arg:
                        print("Failed to parse value '{}' due to exception: {}. Aborting...".format(value, e), file=sys.stderr)
                        exit(-1)
                    else:
                        return value
        if "." in value:
            try:
                return float(value)
            except Exception as e:
                pass
        else:
            try:
                return int(value)
            except Exception as e:
                pass
        return value

    is_options = False
    idx = 1

    if len(sys.argv) == 1:
        print_help()
        exit(0)

    for i in range(1, len(sys.argv)):
        value = sys.argv[i]
        if len(value) == 0:
            continue

        if value[0] == '-':
            is_options = True
        else:
            is_options = False

        if not is_options:
            if idx == 1:
                idx += 1
                description = value
                if description[0] == '"' and description[-1] == '"':
                    description = description[1:-1]
            elif idx == 2:
                idx += 1
                assert value in permitted_test_location, "Only following tests locations are permitted: {}".format(
                    ", ".join(permitted_test_location))
                test_location = value
            elif idx == 3:
                idx += 1
                test_package = value
            elif idx == 4:
                idx += 1
                test_module = value
            elif idx == 5:
                idx += 1
                test_class = value
            elif idx == 6:
                if test_name is None:
                    test_name = []
                test_name.append(value)
            else:
                print("Wrong argument '{}'!".format(value), sys.stderr)
                exit(0)
        else:
            m = re.search('^-(\w+)(?:="?(.*?)"?)?$', value)
            if m is None:
                print("Bad option format: {}".format(value))
                exit(1)
            option, oval = m.groups()
            if option == "h":
                print_help()
                exit(0)
            elif option in options:
                if oval is None:
                    oval = True
                if oval in ('False', '0'):
                    options[option] = False
                else:
                    options[option] = True
            elif option == "vf":
                if oval is None:
                    oval = ".log"
                if oval != "":
                    vf = ".log"
                else:
                    vf = sys.stdout
            elif option == "a":
                val = try_parse(oval)
                test_args.append(val)
            elif option == "k":
                key, val = oval.split(":", 1)
                val = try_parse(val)
                test_kwargs[key] = val
            elif option == "g":
                key, val = oval.split(":", 1)
                val = try_parse(val, is_arg=False)
                generics[key] = val
            else:
                print("Wrong option {}!".format(value), sys.stderr)
                print_help()
                exit(0)

    if isinstance(vf, str):
        vf = open(vf, "w")
    start_stop = options['st']
    verbose = options['v']
    ve = options['ve']
    vt = options['vt']
    rel = options['re']

    if description is None:
        print("Test environment description wasn't specified!", file=sys.stderr)
        print_help()
        exit(-1)

    if test_package is None:
        print("Test package wasn't specified!", file=sys.stderr)
        print_help()
        exit(-1)

    def do_exit(code):
        if vf != sys.stdout and vf is not None:
            vf.close()
        exit(code)

    def my_vprint(*args, **kwargs):
        kwargs["file"] = vf
        if vt:
            print("{0:7f}: ".format(time.time()), *args, **kwargs)
        else:
            print(*args, **kwargs)

    def my_vprint_no_verbose(*args, **kwargs):
        pass    # NOTE: this method just does nothing as intended

    if not verbose:
        if vf != sys.stdout:
            vf.close()
        vf = None
        simple_logging.vprint_worker = my_vprint_no_verbose
    else:
        simple_logging.vprint_worker = my_vprint
        if ve:
            simple_logging.eprint_worker = my_vprint
    simple_logging.tprint_worker = simple_logging.vprint_worker

    env = TestEnv(description=description, generics=generics, verbose=verbose)
    env.instantiate()
    farm_data = env.farm.expose_data()
    # NOTE: don't ever think about changing somethig in farm_data as it would break whole thing
    if verbose:
        vprint("Platforms: {}\nChannels: {}\nWaiting: {}".format(
            pprint.pformat(farm_data.platforms),
            pprint.pformat(farm_data.channels),
            pprint.pformat(farm_data.awaiting)))

    if len(farm_data.awaiting) > 0:
        eprint("Some items are still awaiting for creation!")
        for i in farm_data.awaiting:
            if farm_data.awaiting[i]["parent"] is not None \
                    and farm_data.awaiting[i]["parent"] not in farm_data.platforms \
                    and farm_data.awaiting[i]["parent"] not in farm_data.awaiting:
                eprint("\tNo parent with name {} is found for {}".format(
                    farm_data.awaiting[i]["parent"], i))
            else:
                eprint("{} is waiting someone: {}!".format(i, farm_data.awaiting[i]['wait']))
        exit(-1)

    # Build device tree:
    if verbose:
        vprint("Device tree:")
        env.print_device_tree()

    # TODO: print instantiated environment as uml

    # Run Test
    cl_test = None
    try:
        # TODO: is there a better way to import arbitrary class from arbitrary module?
        exec("from {}.{}.{} import {} as cl_test".format(test_location, test_package, test_module, test_class))
    except ModuleNotFoundError:
        eprint("Test module {}.{}.{} not found!".format(test_location, test_package, test_module))
        do_exit(-1)
    test = cl_test(env, *test_args, **test_kwargs)

    if start_stop:
        results = {}
        started = True
    else:
        results = {"__platforms_start__": {"status": False, "elapsed": 0}, "__platforms_stop__": None}
        started = True
        try:
            env.start_platforms()
            results["__platforms_start__"] = {"status": True, "elapsed": 0}  # TODO: start elapsed time
        except Exception as e:
            started = False
            results["__platforms_start__"] = {"status": e, "elapsed": 0}
            eprint("Exception occurred while starting platforms!")
            exprint()
            try:
                env.stop_platforms()
                results["__platforms_stop__"] = {"status": True, "elapsed": 0}    # TODO: stop elapsed time
            except Exception as e:
                results["__platforms_stop__"] = {"status": e, "elapsed": 0}
                eprint("Exception occurred while stopping platforms!")
                exprint()
                env.farm.emergency_stop()

        if started:
            # TODO: load stored coverage and scoreboard data if necessary
            pass

    tests = test.tests
    if "#scoreboard" in env.farm.channels:
        tests += \
            [
                {"name": "_scoreboards_", "f": env.check_scoreboards, "args": [], "kwargs": {}},
            ]
    for dry_run in True, False:  # NOTE: do a dry_run to fill results with tests list even if not started properly
        if dry_run or started:
            if test_name is not None:
                tresults = TestRunner.run_tests(env, tests, start_stop, include=test_name + ["_scoreboards_"],
                                                dry_run=dry_run)
            else:
                tresults = TestRunner.run_tests(env, tests, start_stop, dry_run=dry_run)
            for r in tresults:
                results[r] = tresults[r]

    if started and not start_stop:
        # TODO: save stored coverage and scoreboard data if necessary
        del results["__platforms_stop__"]   # Delete record to print report data in proper order
        results["__platforms_stop__"] = {"status": False, "elapsed": 0}
        try:
            env.stop_platforms()
            results["__platforms_stop__"] = {"status": True, "elapsed": 0}    # TODO: stop elapsed time
        except Exception as e:
            results["__platforms_stop__"] = {"status": e, "elapsed": 0}
            eprint("Exception occurred while stopping platforms!")
            exprint()
            env.farm.emergency_stop()

    vprint("\n============================================================\n"
           "Tests results:")

    passed = 0
    failed = 0
    exceptions = 0
    others = 0
    total = 0
    for test, result in results.items():
        total += 1
        if result is None:
            message = "Wasn't started"
            elapsed = 0
            others += 1
        else:
            stat = result["status"]
            elapsed = result["elapsed"]
            if stat is False:
                message = "Failed"
                failed += 1
            elif stat is True:
                message = "Passed"
                passed += 1
            elif stat is None:
                message = "N/A"
                others += 1
            else:
                message = "Ex.: {}".format(stat)
                exceptions += 1
        print("{}{} - {}{}{}".format(["", "  "][verbose],
                                     ["{}:{}:{}:{}".format(test_package, test_module, test_class, test),
                                      test[2:-2]][test[:2]=="__"],
                                     ["", float(elapsed)][rel], ["", ":"][rel], message))

    vprint("\n============================================================\n"
           "Summary:")
    vprint("  Total: {}\n  Passed: {}\n  Failed: {}\n  Exceptions: {}\n  Unknown: {}\n".format(
        total, passed, failed, exceptions, others
    ))
    if total != passed:
        vprint("Errors were detected!")

    # TODO: print accumulated coverage and scoreboard results

    do_exit(0)
