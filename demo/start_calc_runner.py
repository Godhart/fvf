#!/bin/python
h = """
Starts app runner server for running calc app.

Usage: python ./00-run_calc_caller.py [<port>]

 * <port> - Listening port for app runner server
"""
import sys
from _run_helper import run, run_background


if len(sys.argv) == 2 and sys.argv[1] == '-h':
    print(h)
    exit(0)

if len(sys.argv) >= 2:
    port = sys.argv[1]
else:
    port = '53575'

run('python3', ['caller.py', 'calc', port, 'python3', '../calc/calc.py'],
    '../src/comealongs/caller',
    'python', ['caller.py', 'calc', port, 'python', '../calc/calc.py'])
