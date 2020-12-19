#!/bin/python
h = """
Preforms constrained random testing of calc app.
Test environment for this demo contains mocked object so no real app 
is required to run this demo.
Calc app abstraction object generates responses itself.


Any args to this script except '-h' would be used as additional options to 
'run_test.py' script.

Args without preceding '-' would specify necessary tests, args with '-' in the 
beginning would be treated as options.

Values that script sets by default would be overridden with new values if 
specified.

You may specify:
 * test name like "crt" and/or others
 * -v to print more verbose messages
 * -re to print elapsed time for tests
 * -vt to timestamp messages with real time (seconds past since 1970-01-01...)

To get info for more options run 'python ../src/run_test.py -h'
"""
import sys


from _run_helper import run

if len(sys.argv) == 2 and sys.argv[1] == '-h':
    print(h)
    exit(0)

run('python3', [
    'run_test.py',
    'envs/calc/calc_crt_mocked.yaml',        # Test Environment
    'ip_tests',                              # Tests package location (tests kind)
    'arith',                                 # Test package
    'crt',                                   # Test module
    'RootTest',                              # Test class
    ]+sys.argv[1:],
    '../src', 'python')
