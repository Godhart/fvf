import random as _random

_generators = {}


def _check_generator(idx, seed):
    if idx not in _generators:
        _generators[idx] = _random.Random()
        if seed is None:
            seed = idx
        _generators[idx].seed(seed)


def rand(generator=0, seed=None):
    _check_generator(generator, seed)
    return _generators[generator]
