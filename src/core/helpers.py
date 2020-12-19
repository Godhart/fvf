class _WrapperAliasProperty(object):
    """
    Helper for creating class properties in runtime
    """
    def __init__(self, host, attr):
        self._host = host
        self._attr = attr

    def __get__(self, obj, objtype):
        return getattr(self._host, self._attr)

    def __set__(self, obj, value):
        return setattr(self._host, self._attr, value)


class _WrapperAliasHostedMethod(object):
    """
    Helper for creating class methods in runtime
    """
    def __init__(self, host, method):
        self._host = host
        self._method = method

    def __get__(self, obj, objtype):
        return getattr(self._host, self._method)


class _WrapperAliasMethod(object):
    """
    Helper for creating class methods in runtime
    """
    def __init__(self, method):
        self._method = method

    def __get__(self, obj, objtype):
        return self._method


class Wrapper(object):
    """
    Creates in runtime class with specified methods and fields
    Methods and fields implementation are delegated to hosting object
    Certain fields and methods of wrapper class would be mapped to arbitrary methods and fields of hosting object
    Class is used to implement some sort of interface functionality without inheritance
    """
    _methods = ()  # List of required methods (methods names that would be mapped to some implementation)
    _fields = ()   # List of required fields (fields names that would be mapped to to real object)
    _name = "__undefined__"     # Symbolic interface name

    @staticmethod
    def _add_alias_property(cls, name, host, hosts_property):
        setattr(cls, name, _WrapperAliasProperty(host, hosts_property))

    @staticmethod
    def _add_alias_hosted_method(cls, name, host, hosts_method):
        setattr(cls, name, _WrapperAliasHostedMethod(host, hosts_method))

    @staticmethod
    def _add_alias_method(cls, name, method):
        setattr(cls, name, _WrapperAliasMethod(method))

    @classmethod
    def get_wrapper(cls, host, prefix="", mmap=None, fmap=None):
        """
        Creates wrapper class for specified methods and fields
        :param host: Object ref with actual implementation and fields objects
        :param prefix: In case if host's methods and fields are differs from interface's only by prefix then
                     prefix should be set instead of mapping
        :param mmap: Methods map. A dict with interface's method name as key and host implementation name as value
                     Required in case if host's method implementation name is not same as interface's method name
        :param fmap: Required in case if host's field name is not same as interface's field name
        """
        class Wrapped(object):
            _name = cls._name

        for v in (cls._methods, cls._fields):
            if v == cls._methods:
                should_be_callable = True
                vmap = mmap
            else:
                should_be_callable = False
                vmap = fmap
            for m in v:
                if vmap is not None and m in vmap:
                    if isinstance(vmap[m], str):
                        assert hasattr(host, vmap[m]), "Provided attribute {} for {} {} wasn't found in {}".format(
                            vmap[m], ("field", "method")[v == cls._methods],  m, host)
                        if should_be_callable:
                            assert callable(getattr(host, vmap[m])) == should_be_callable, \
                                "mmap[{}]={} of {} should be callable!".format(m, vmap[m], host)
                    else:
                        if should_be_callable:
                            assert callable(vmap[m]) == should_be_callable, \
                                "mmap[{}]={} should be callable!".format(m, vmap[m])
                        else:
                            assert False, "Only symbolic attributes names can be specified in fields map"
                    if should_be_callable:
                        if isinstance(vmap[m], str):
                            cls._add_alias_hosted_method(Wrapped, m, host, vmap[m])
                        else:
                            cls._add_alias_method(Wrapped, m, vmap[m])
                    else:
                        cls._add_alias_property(Wrapped, m, host, vmap[m])
                else:
                    assert hasattr(host, prefix+m), "Not found {} {} in {}".format(
                        ("field", "method")[v == cls._methods], prefix+m, host)
                    if should_be_callable:
                        assert callable(getattr(host, prefix + m)), \
                            "{} of {} should be callable!".format(prefix + m, host)
                        cls._add_alias_hosted_method(Wrapped, m, host, prefix+m)
                    else:
                        cls._add_alias_property(Wrapped, m, host, prefix+m)
        wrap = Wrapped()
        return wrap
