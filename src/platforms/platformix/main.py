from core.platformix import PlatformBase
from core.simple_logging import vprint


class Platformix(PlatformBase):
    """
    Platformix platform used for self tests
    """

    def __init__(self, tag=None, **kwargs):
        super(Platformix, self).__init__(**kwargs)
        self.tag = tag  # Tag field for testing purposes. Just holds value and don't affects anything else

    def call_test(self, *args):
        """
        Method for testing purposes.
        Does nothing but prints args and returns them back
        If no args then exception is raised
        :param args:
        :return: args as list
        """
        if len(args) == 0:
            raise ValueError("At least one arg expected")
        vprint(*args)
        r = []
        for i in range(len(args)-1, -1, -1):
            r.append(args[i])
        return r


class RootClass(Platformix):
    pass
