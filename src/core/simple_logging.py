import sys
import traceback


def _default_vprint_worker(*args, **kwargs):
    """
    Default worker function for vprint and tprint
    :param args: args to print command
    :param kwargs: kwargs to print command
    :return: None
    """
    print(*args, **kwargs)


def _default_eprint_worker(*args, **kwargs):
    """
    Default worker function for eprint
    :param args: args to print command
    :param kwargs: kwargs to print command
    :return: None
    """
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)


vprint_worker = _default_vprint_worker
eprint_worker = _default_eprint_worker
tprint_worker = _default_vprint_worker


def vprint(*args, **kwargs):
    """
    Use to print extended verbose information
    :param args: args to print command
    :param kwargs: kwargs to print command
    :return: None
    """
    vprint_worker(*args, **kwargs)


def eprint(*args, **kwargs):
    """
    Use to print information about errors
    :param args: args to print command
    :param kwargs: kwargs to print command
    :return: None
    """
    eprint_worker(*args, **kwargs)


def tprint(*args, **kwargs):
    """
    Use to print timing information
    :param args: args to print command
    :param kwargs: kwargs to print command
    :return: None
    """
    tprint_worker(*args, **kwargs)


def exprint():
    traceback.print_exc()
