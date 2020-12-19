# Here are sketches of ideas to add into platformix core
from core.platformix_core import PlatformInterfaceCore, PlatformProtocolCore

class GenericPlatformInterface(PlatformInterfaceCore):
    _base_id = "__generic__"    # NOTE: would be overridden in constructor
    """
    Provides ability to create interface on the fly. Recommended for test purposes only
    """
    def __init__(self, host, base_id, methods, worker=None, name="", mmap=None):
        self._methods = tuple(methods)
        self._base_id = base_id
        super(GenericPlatformInterface, self).__init__(host, worker, name, mmap)


class PyObjectWrapperInterface(PlatformInterfaceCore):
    """
    Automatically created interface for python object
    Would support all public methods of given python object
    _base_id of interface would be object's class name
    """
    # TODO: XXX That Interface Shouldn't be used that way. Need complete rework

    _base_id = "__pyobject__"    # NOTE: would be overridden in constructor

    def __init__(self, host, objref, name=""):
        self._methods = []
        mmap = {}
        objinfo = dir(objref)
        for oi in objinfo:
            if oi[0] == '_':
                continue
            if callable(getattr(objref, oi)):
                self._methods.append(oi)
                mmap[oi] = getattr(objref, oi)
        self._base_id = objref.__class__.__name__
        super(PyObjectWrapperInterface, self).__init__(host, objref, name, mmap)


class PyObjectWrapperProtocol(PlatformProtocolCore):
    """
    Automatically created protocol for python object
    Would support all public methods of given python object (also that object would be used worker)
    _base_id of interface would be object's class name
    """
    _default_interface = PyObjectWrapperInterface

    def __init__(self, host, objref, name):
        # NOTE: need to create instance before super's constructor call
        #  due to specific interface constructor
        # TODO: XXX That Protocol Shouldn't be used that way. Need complete rework
        interface = PyObjectWrapperInterface(host, objref, name="")

        methods = []
        fields = []
        objinfo = dir(objref)
        for oi in objinfo:
            if oi[0] == '_':
                continue
            if callable(getattr(objref, oi)):
                methods.append(oi)
            else:
                fields.append(oi)

        host_methods = ("reply_all", "reply", "register_reply_handler", "unregister_reply_handler")
        mmap = {}
        for m in host_methods:
            assert hasattr(host, m), "Host {} should have method {}".format(host, m)
            assert callable(getattr(host, m)), "Attribute {} of  {} should be callable".format(m, host)
            mmap[m] = getattr(host, m)
            if m not in methods:
                methods.append(m)

        class ObjectWrapper(Wrapper):
            _methods = tuple(methods)
            _fields = tuple(fields)
            _name = objref.__class__.__name__

        worker = ObjectWrapper.get_wrapper(objref, mmap)
        super(PyObjectWrapperProtocol, self).__init__(worker, worker, interface, name)
        # TODO: A lot of methods that would call worker's method and send reply
