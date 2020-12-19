import os
import subprocess


def run(command, args, path=None, fallback_command=None, fallback_args=None):
    if path is not None:
        cwd = os.getcwd()
        try:
            os.chdir(path)
        except Exception as e:
            os.chdir(cwd)
            raise e
    else:
        cwd = None
    try:
        retry = False
        result = subprocess.run([command] + args)
    except:
        retry = True
    if retry:
        if fallback_command is not None:
            if fallback_args is None:
                fallback_args = args
            result = subprocess.run([fallback_command] + fallback_args)
    if cwd is not None:
        os.chdir(cwd)
    return result

def run_background(command, args, path=None, fallback_command=None, fallback_args=None):
    if path is not None:
        cwd = os.getcwd()
        try:
            os.chdir(path)
        except Exception as e:
            os.chdir(cwd)
            raise e
    else:
        cwd = None
    try:
        retry = False
        result = subprocess.Popen(
            [command] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except:
        result = None
        retry = True
    if retry:
        if fallback_command is not None:
            if fallback_args is None:
                fallback_args = args
            result = subprocess.Popen(
                [fallback_command] + fallback_args,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cwd is not None:
        os.chdir(cwd)
    return result
