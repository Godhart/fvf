import re


def _parse_calc(expression):
    return expression, re.match(r"^\s*(-?\d+)\s*(\+|-|\*|/|\*\*)\s*(-?\d+)\s*$", expression)


def parse_message(message):
    """
    :param message: command to a platform
    :return: None for messages that should be skipped
             False for messages that can't be handled
             tupple with [0] as expression and [1] as parsed expression
             if parsing has been failed then [1] is None
    """
    if message.method == 'calc':
        expression, m = _parse_calc(*message.args, **message.kwargs)
    else:
        return None
    if m is None:
        return expression, None
    matches = m.groups()
    groups = {}
    for i in range(0, len(matches)):
        groups[r"\{}".format(i+1)] = matches[i]
    return expression, groups
