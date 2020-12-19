#!/bin/python
h = """
Runs hardcoded tests to check a calc app (located in /src/comealong/calc).

App runner server for for this demo starts along with this test 
(app runner is located in /src/comealongs/caller).

You may try to run test with external server by specifying server parameters
with command line options -host and -port like this:
 -host=127.0.0.1 -port=53575

NOTE: To run app server you may use script 'start_calc_runner.py'.

Demo script wouldn't start app runner server if host or port is specified.
But it would set test environment's generics to use specified server.

Any args to this script except '-h' would be used as additional options to 
'run_test.py' script.

Args without preceding '-' would specify necessary tests, args with '-' in the 
beginning would be treated as options.

Values that script sets by default would be overridden with new values if 
specified.

You may specify:
 * test name like "test_sum" and/or others
 * -v to print more verbose messages
 * -re to print elapsed time for tests
 * -vt to timestamp messages with real time (seconds past since 1970-01-01...)

To get info for more options run 'python ../src/run_test.py -h'
"""
import sys
import time
import re
from _run_helper import run, run_background


if len(sys.argv) == 2 and sys.argv[1] == '-h':
    print(h)
    exit(0)

args = []
host = None
port = None

for a in sys.argv[1:]:
    m = re.match("^-(host|port)(?:=(.+))?$", a)
    if m is not None:
        option, value = m.groups()
        if option == 'host':
            host = value
        else:
            port = value
    else:
        args.append(a)

generics = []
if host is None and port is None:
    caller = run_background(
        'python3', ['caller.py', 'calc', '53575', 'python3', '../calc/calc.py'],
        '../src/comealongs/caller',
        'python', ['caller.py', 'calc', '53575', 'python', '../calc/calc.py'])
    time.sleep(1)
else:
    if host is not None:
        generics += ["-g=calc_host:{}".format(host)]
    if port is not None:
        generics += ["-g=app_runner_port:{}".format(port)]
    caller = None
    print("Ensure you had started app runner server on host {} listening port {}".format(
        [host, "127.0.0.1"][host is None], [port, 53575][port is None]))
    print(
"""
To start server clone this repo to desired host and start app runner server
by running script from demo folder like this:

  python ./start_calc_runner.py [<listening_port>]
  
  Default listening port value is 53575

""")

run('python3', [
    'run_test.py',
    'envs/calc/calc_test.yaml',              # Test Environment
    'ip_tests',                              # Tests package location (tests kind)
    'arith',                                 # Test package
    'main',                                  # Test module
    'RootTest',                              # Test class
    ]+args+generics,
    '../src', 'python')

if caller is not None:
    caller = None
