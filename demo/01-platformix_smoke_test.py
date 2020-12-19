#!/bin/python
h = """
Runs smoke test for platformix protocol and platformix base class itself.
Following generics for test_env are set by script:
 * enable_generate: True
 * generate_range1_end: 2
 * tag_default: "a tag"

Any args to this script except '-h' would be used as additional options to 
'run_test.py' script.

Args without preceding '-' would specify necessary tests, args with '-' in the 
beginning would be treated as options.

Values that script sets by default would be overridden with new values if 
specified.

You may specify:
 * test name like "[sanity check]" and/or others
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
    'envs/platformix/test_platformix.yaml',  # Test Environment
    'ip_tests',                              # Tests package location (tests kind)
    'platformix',                            # Test package
    'main',                                  # Test module
    'RootTest',                              # Test class
    '-g=enable_generate:True', '-g=generate_range1_end:2', '-g=tag_default:"a tag"']+sys.argv[1:],
    '../src', 'python')
