from core.platformix_core import PlatformMessage as PM
from core.platformix import PlatformBase
from core.platformix_core import new_message, proto_success, proto_failure
from ip.software_runner.definitions import SoftwareRunnerProtocol, SoftwareRunnerWrapper
from core.eval_sandbox import evaluate
from core.simple_logging import vprint, eprint, tprint, exprint

import rpyc
import time
import copy


class SoftwareRunner(PlatformBase):
    """
    Platform for interaction via RPyC with app hosted by Caller (caller.py)
    """

    def __init__(self, host=None, port=None, service=None, args=None, cmd_on_start=None, cmd_on_stop=None,
                 stop_timeout=5, display_log_on_stop=False, mock=False, mock_eval=False, **kwargs):
        """
        :param host: host on which Caller runs. If None(default) then used host of parent's platform
        :param port: for connection to a Caller
        :param service: service name that can be used instead of port
        :param args: additional args to started app
        # TODO: condition to make sure app started
        # TODO: rules to extract params from app's stdout on start
        :param cmd_on_start: list with commands to send to app via stdin on start
        :param cmd_on_stop: list with commands to send to app via stdin on stop
        :param stop_timeout: timeout to wait while app successfully stops
        :param display_log_on_stop: True to get and display app's log on stop
        :param mock: If True then there would be no real Send/Receive requests.
                     Receive data would be generated out of Send data
        :param mock_eval: If True then Send data would be evaluated as expression and would be used
                          for reply on Receive request.
                          Otherwise Send data itself would be used for reply on Receive request
        :param kwargs: other params supported by PlatformBase
        """
        super(SoftwareRunner, self).__init__(**kwargs)

        self._host = host
        self._port = port
        self._service = service
        self._args = args
        self._start_sequence = cmd_on_start
        self._exit_sequence = cmd_on_stop
        self._stop_timeout = stop_timeout
        self._display_log_on_stop = display_log_on_stop
        self._connection = None

        if mock:
            self._mock = []  # Set to empty list to mock conversation (use to eval system performance w/o external io)
            self._mock_eval = mock_eval
        else:
            self._mock = None
            self._mock_eval = None

        # Register SoftwareRunner protocol support
        self._support_protocol(SoftwareRunnerProtocol(self, SoftwareRunnerWrapper.get_wrapper(self, "_")))

        self.subscribe("#softwarerunner")

    def _start(self, reply_contexts):
        """
        1. Update's host from parent platform if necessary
        2. Connects to a Caller
        :return: True if started successfully, otherwise - False
        """
        if self._port is None and self._service is None:
            eprint("Platform {} failed to start - port or service should be specified".format(self.name))
            return proto_failure("Platform {} failed to start - port or service should be specified")

        if self._port is not None and self._service is not None:
            eprint("Platform {} failed to start - specify only port or service, but not both".format(self.name))
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
            self._connection = rpyc.connect(self._host, self._port)
            # TODO: use service instead of port if it's specified
            if self._args is not None:
                self._connection.root.set_args(copy.copy(self._args))
            result = self._connection.root.run()
        except Exception as e:
            self._connection = None
            eprint("Platform {} failed to start due to exception {}".format(self.name, e))
            exprint()
            return proto_failure("Failed to start due to exception {}", -2)
        if result is False:
            self._connection = None
            eprint("Platform {} failed to start: rpyc server returned False".format(self.name))
            return proto_failure("RPYC server returned False")
        if result and not self._mock:
            if self._start_sequence is not None and len(self._start_sequence) > 0:
                self.rpyc_send(self._start_sequence)
        return super(SoftwareRunner, self)._start(reply_contexts)

    def _stop(self, reply_contexts):
        """
        1. Sends exit sequence to app via stdin
        2. Receives exit log if necessary
        3. Closes connection to a Caller
        :return:
        """
        stop_failed = None
        try:
            if self._connection is not None:    # Check before proceeding as it can be emergency stop
                if self._exit_sequence is not None and len(self._exit_sequence) > 0:
                    self.rpyc_send(self._exit_sequence)
                    exit_time = time.time() + self._stop_timeout
                    forced_stop = False
                else:
                    self._connection.root.stop("Stopped by intent of SoftwareRunner (_stop)", force=True)
                    exit_time = time.time() + self._stop_timeout
                    forced_stop = True
                while self._connection.root.running and (not forced_stop or time.time() < exit_time):
                    if not self._connection.root.running:
                        break
                    if time.time() >= exit_time and (not forced_stop):
                        self._connection.root.stop("Forced to stop by intent of SoftwareRunner (_stop)", force=True)
                        exit_time = time.time() + self._stop_timeout
                        forced_stop = True
                        stop_failed = "Not stopped by stop sequence"
                if self._connection.root.running:
                    if stop_failed is not None:
                        stop_failed += ", "
                    else:
                        stop_failed = ""
                    stop_failed += "App not stopped"

                # TODO: check whether isntance is running and call stop explicitly
                if self._display_log_on_stop:
                    data = list(self._connection.root.log)
                    vprint("Platform {}. Exit log: {}".format(self.name, '\n'.join(data)))
                self._connection.close()
        except Exception as e:
            eprint("Platform {} experienced exception on stop: {}".format(self.name, e))
            exprint()
            self._reply_all(reply_contexts, PM.notify("abnormal_stop: experienced exception on stop: {}".format(e)))
            if stop_failed is not None:
                stop_failed += ", "
            else:
                stop_failed = ""
            stop_failed += "Experienced exception: {}".format(e)

        if stop_failed is not None:
            eprint("Software runner {} failed to stop app properly: {}".format(self.name, stop_failed))
            self._reply_all(reply_contexts, PM.notify("Software runner {} failed to stop app properly: {}".format(self.name, stop_failed)))

        self._connection = None
        super_result = super(SoftwareRunner, self)._stop(reply_contexts)
        if stop_failed:
            return proto_failure(stop_failed)
        else:
            return super_result

    def rpyc_send(self, data):
        """
        Sends data to app via stdin
        :param data: Data to send over stdin. Could be an item like str, bytearray or list/tuple of items
        :return: True if data were sent successfully, otherwise - False
        """
        start_time = time.time()
        if (self._mock is None or data == 'exit') and self._connection is None:
            return proto_failure("No connection. Ensure start is complete")
        try:
            if not isinstance(data, (list, tuple)):
                data = data,
            for m in data:
                if self._mock is None or data == 'exit':    # TODO: why data=='exit' overrides self._mock?
                    self._connection.root.send(m)
                else:
                    try:
                        if self._mock_eval:
                            r = evaluate(m)
                        else:
                            r = m
                    except Exception as e:
                        r = None
                    self._mock.append(str(r))
            if self._mock is None or data == 'exit':        # TODO: why data=='exit' overrides self._mock?
                self._connection.root.flush()
        except Exception as e:
            eprint("Platform {}: exception occurred during send: {}".format(self.name, e))
            exprint()
            return proto_failure("Failed to send due to exception {}".format(e), -2)
        tprint("rpyc_send elapsed {}".format(time.time() - start_time))
        return proto_success(None)

    def rpyc_receive(self, count=1, timeout=1.0):
        """
        Get's data that were sent by app via stdout
        :param count: Amount of lines to receive.
                set count to 0 to receive as much as possible, and at least one message
                set count to -1 to receive as much as possible, but nothing is acceptable too
        :param timeout: Time in seconds to wait for data
        :return: True if successfully received Data, otherwise - False. Data itself is contained in a reply to channel
                 and Data is list of strings
        """
        start_time = time.time()
        if not isinstance(count, int) or count < -1:
            raise ValueError("Count should be an integer in a range from -1 and up to +infinity")
        if self._mock is None and self._connection is None:
            return proto_failure("No connection. Ensure start is complete")
        try:
            data = []
            if self._mock is not None:
                data = self._mock[:count]
                self._mock = self._mock[count:]
            else:
                while len(data) < count or count == 0 or count == -1:
                    received = self._connection.root.receive(timeout)
                    if received is None or len(received) == 0:
                        break
                    if isinstance(received, (list, tuple)):
                        data += received
                    else:
                        data.append(received)
        except Exception as e:
            eprint("Platform {}: exception occurred during receive: {}".format(self.name, e))
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

    def rpyc_log(self):
        if self._connection is None:
            return proto_failure("No connection. Ensure start is complete")
        try:
            data = self._connection.root.log
        except Exception as e:
            eprint("Platform {}: exception occurred while getting log: {}".format(self.name, e))
            exprint()
            return proto_failure("Failed to get log due to exception {}".format(e), -2)
        return proto_success(data)

    def _send(self, context, data):
        return self.rpyc_send(data)

    def _receive(self, context, *args, **kwargs):
        return self.rpyc_receive(*args, **kwargs)

    def _log(self, context):
        return self.rpyc_log()

    # TODO: REMOVE
    # NOTE: was replaced with generic_request_handler with lambda function
    # NOTE2: wasn't checked before replacement
    # def _get_host_handler(self, context, message, dry_run, timeouted):
    #     if not self._request_handler_common(context, message, dry_run, timeouted):
    #         return False
    #     if dry_run:
    #         return True
    #     if message.is_success:
    #         self._host = message.reply_data("host")
    #     self._unregister_reply_handler(context, message.is_success, {})
    #     return True


class RootClass(SoftwareRunner):
    pass
