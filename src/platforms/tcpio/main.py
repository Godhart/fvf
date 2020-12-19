from core.platformix_core import PlatformMessage as PM
from core.platformix import PlatformBase
from core.platformix_core import new_message, proto_success, proto_failure
from ip.stream_io.definitions import StreamIOProtocol, StreamIOWrapper
from core.simple_logging import vprint, eprint, tprint, exprint
from core.eval_sandbox import evaluate
import time
import socket


class TcpIO(PlatformBase):
    """
    Platform for interaction via TCP with anything you want
    """

    def __init__(self, host=None, port=None, timeout=0.1, connect_timeout=10.0, mock=False, mock_eval=False,
                 send_on_stop=None, **kwargs):
        """
        :param host: host to connect to. If None(default) then used host of parent's platform
        :param port: host's port to connect to
        :param connect_timeout: socket connect timeout
        :param timeout: socket receive timeout
        :param mock: If True then there would be no real Send/Receive requests.
                     Receive data would be generated out of Send data
        :param mock_eval: If True then Send data would be evaluated as expression and would be used
                          for reply on Receive request.
                          Otherwise Send data itself would be used for reply on Receive request
        :param kwargs: other params supported by PlatformBase
        """
        super(TcpIO, self).__init__(**kwargs)

        self._host = host
        self._port = port
        self._sock = None
        self._timeout = timeout
        self._connect_timeout = connect_timeout
        self._close_sequence = send_on_stop

        if mock:
            self._mock = []  # Set to empty list to mock conversation (use to eval system performance w/o external io)
            self._mock_eval = mock_eval
        else:
            self._mock = None
            self._mock_eval = None

        # Register StreamIO protocol support
        self._support_protocol(StreamIOProtocol(self, StreamIOWrapper.get_wrapper(self, "_")))

        self.subscribe("#tcpio")

    def _start(self, reply_contexts):
        """
        1. Update's host from parent platform if necessary
        2. Connects to a Caller
        :return: True if started successfully, otherwise - False
        """
        if self._port is None:
            eprint("Platform {} failed to start - port should be specified".format(self.name))
            return proto_failure("Platform {} failed to start - port or service should be specified")

        if self._host is None and self.parent is not None:
            c = self.request(new_message("platformix", "get", "host"),
                             self._generic_request_handler,
                             [], {"on_success": lambda d: setattr(self, "_host", d["host"]),
                                  "on_failure": lambda d: eprint("Failed to get host due to {}:{}".format(
                                      d["errcode"], d["state"]))
                                  })

        if self._host is None:
            eprint("Platform {} failed to start - can't get host".format(self.name))
            return proto_failure("Failed to start - can't get host")
        try:
            timeout = time.time() + self._connect_timeout
            while True:
                try:
                    if self._mock is None:
                        self._sock = sock = socket.socket()
                        sock.connect((self._host, self._port))
                        sock.settimeout(self._timeout)
                        break
                except ConnectionRefusedError as e:
                    if time.time() > timeout:
                        raise e
        except Exception as e:
            self._sock = None
            eprint("Platform {} failed to start due to exception {}".format(self.name, e))
            exprint()
            return proto_failure("Failed to start due to exception {}", -2)
        return super(TcpIO, self)._start(reply_contexts)

    def _stop(self, reply_contexts):
        """
        1. Sends exit sequence to app via stdin
        2. Receives exit log if necessary
        3. Closes connection to a Caller
        :return:
        """
        try:
            if self._mock is None and self._sock is not None:
                if self._close_sequence is not None:
                    self.tcp_send(self._close_sequence)
                    time.sleep(self._timeout)
                self._sock.close()
        except Exception as e:
            eprint("Platform {} experienced exception on stop: {}".format(self.name, e))
            exprint()
            self._reply_all(reply_contexts, PM.notify("abnormal_stop: experienced exception on stop: {}".format(e)))
        self._sock = None
        return super(TcpIO, self)._stop(reply_contexts)

    def tcp_send(self, data):
        """
        Sends data to app via stdin
        :param data: Data to send over stdin. Could be an item like str, bytearray or list/tuple of items
        :return: True if data were sent successfully, otherwise - False
        """
        start_time = time.time()
        if self._mock is None and self._sock is None:
            return proto_failure("No connection. Ensure start is complete")
        try:
            if not isinstance(data, (list, tuple)):
                data = data,
            for m in data:
                if self._mock is None:
                    if not isinstance(m, bytearray):
                        if isinstance(m, str):
                            m = m.encode('UTF-8')
                        else:
                            return proto_failure("Send data is expected to be a string, bytearray or "
                                                 "list/tuple of strings and bytearrays")
                    self._sock.sendall(m)
                else:
                    try:
                        if self._mock_eval and isinstance(m, str):
                            r = evaluate(m)
                        else:
                            r = m
                    except Exception as e:
                        r = None
                    self._mock.append(str(r))
        except Exception as e:
            eprint("Platform {} failed to send due to exception {}".format(self.name, e))
            exprint()
            return proto_failure("Failed to send due to exception {}".format(e), -2)
        tprint("tcp_send elapsed {}".format(time.time() - start_time))
        return proto_success(None)

    def tcp_receive(self, count=0, timeout=None, decode='UTF-8'):
        """
        Get's data that were sent by app via stdout
        :param count: Amount of bytes to receive.
                set count to 0 to receive as much as possible, at least something
                set count to -1 to receive as much as possible, but nothing is acceptable too
        :param timeout: Time in seconds to wait for data. If None then TCP socket timeout is used
        :param deoode: If not None then received data is decoded into string using specified decoder. Default: 'UTF-8'
        :return: True if successfully received Data, otherwise - False. Data itself is contained in a reply to channel
                 and Data is list of strings
        """
        start_time = time.time()
        if not isinstance(count, int) or count < -1:
            raise ValueError("Count should be an integer in a range from -1 and up to +infinity")
        if self._mock is None and self._sock is None:
            return proto_failure("No connection. Ensure start is complete")
        try:
            if self._mock is not None:
                data = self._mock.pop(0)
            else:
                data = bytearray()
                if count < 1:
                    recv_size = 1024
                else:
                    recv_size = count
                if timeout is not None:
                    timeout = time.time() + timeout
                while len(data) < count or count == 0 or count == -1:
                    try:
                        received = self._sock.recv(recv_size)
                    except TimeoutError:
                        received = None
                    except socket.timeout:
                        received = None

                    if received is None:
                        if count < 0:
                            break
                        if count == 0 and len(data) > 0:
                            break
                    else:
                        data += received

                    if timeout is not None and time.time() > timeout:
                        break

                    if count > 0:
                        recv_size = count - len(data)

                if decode is not None:
                    data = data.decode(decode)

        except Exception as e:
            eprint("Platform {} failed to receive due to exception {}".format(self.name, e))
            exprint()
            return proto_failure("Failed to receive due to exception {}".format(e), -2)
        tprint("rpyc_receive elapsed {}".format(time.time() - start_time))
        if 0 < count != len(data):
            return proto_failure("Not all requested data were received")
            # TODO: need a way to return partially received data
        elif count == 0 and len(data) == 0:
            return proto_failure("No data were received")
        else:
            return proto_success(data)

    def _send(self, context, data):
        return self.tcp_send(data)

    def _receive(self, context, *args, **kwargs):
        return self.tcp_receive(*args, **kwargs)


class RootClass(TcpIO):
    pass
