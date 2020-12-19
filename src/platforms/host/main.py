from core.platformix import PlatformBase


class Host(PlatformBase):
    """
    An Abstraction (Wrapper) of Network Host
    Just few more properties to PlatformBase, no Interface/Protocol is required
    """

    def __init__(self, host="localhost", **kwargs):
        super(Host, self).__init__(**kwargs)
        self._host = host

    @property
    def host(self):
        """
        :return: Host's address
        """
        return self._host

    def _start(self, reply_contexts):
        # TODO: ping host on start. Fail if no response
        return super(Host, self)._start(reply_contexts)


class RootClass(Host):
    pass
