from core.helpers import Wrapper


class IWTestInterface(Wrapper):
    _methods = ("start", "stop")
    _fields = ("running",)
    _name = "IWTestInterface"


class IWTestImplementation(object):

    def __init__(self):
        self._running = False
        self.iw = IWTestInterface.get_wrapper(self, prefix="_")

    def _start(self):
        self._running = True

    def _stop(self):
        self._running = False


if __name__ == "__main__":

    o = IWTestImplementation()
    iw = o.iw

    print("{}:{}".format(o._running, iw.running))
    assert o._running == iw.running, "Values should be the same"
    iw.start()
    print("{}:{}".format(o._running, iw.running))
    assert o._running == iw.running, "Values should be the same"
    iw.stop()
    print("{}:{}".format(o._running, iw.running))
    assert o._running == iw.running, "Values should be the same"

    o._start()
    print("{}:{}".format(o._running, iw.running))
    assert o._running == iw.running, "Values should be the same"
    o._stop()
    print("{}:{}".format(o._running, iw.running))
    assert o._running == iw.running, "Values should be the same"

    iw.running = True
    print("{}:{}".format(o._running, iw.running))
    assert o._running == iw.running, "Values should be the same"
