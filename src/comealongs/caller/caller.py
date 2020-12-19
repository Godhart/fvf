# from sys import stdin, stdout
from threading import Thread, RLock
import subprocess
import rpyc
import sys
import copy
import time

default_encoding = 'cp866'

# TODO: replace threads with asyncio

class Logger(object):
    def __init__(self):
        self._log = []
        self.print_by_default = True
        self.timestamp = True

    def log(self, msg, do_print=None):
        if self.timestamp:
            msg = "{0:.7f}: ".format(time.time()) + msg
        self._log.append(msg)
        if self.print_by_default is True and do_print is not False:
            print(msg)

    @property
    def logged(self):
        return copy.copy(self._log)


logger = Logger()
log = logger.log


class VerbalLock(object):

    def __init__(self, name, print_log=False, factory=RLock, *args, **kwargs):
        self.name = name
        self.print_log = print_log
        self._lock = factory(*args, **kwargs)

    def acquire(self):
        result = self._lock.acquire()
        if self.print_log:
            print(self.name + " locked", file=sys.stderr)
        return result

    def release(self):
        result = self._lock.release()
        if self.print_log:
            print(self.name + " released", file=sys.stderr)
        return result


class RCMDService(rpyc.Service):
    ALIASES = ["RCMD"]

    def __init__(self, *args, **kwargs):
        self.dbg_print = False
        log("Starting new instance {}...".format(self))
        if rpyc.version.version[0] >= 4:
            startup_args = {"cmd": kwargs.get('cmd', None)}
            if "cmd" in kwargs:
                del kwargs["cmd"]
            if "alias" in kwargs:
                startup_args["alias"] = kwargs["alias"]
                del kwargs["alias"]
        elif __name__ == "__main__":
            startup_args = {"cmd": sys.argv[3:], "alias": sys.argv[1]}
        else:
            startup_args = {}
        cmd = startup_args['cmd']
        if cmd is None:
            log("...Failed! No command were specified!")
            raise ValueError("cmd should be specified")
        elif not isinstance(cmd, (list, tuple)) or not (all(isinstance(c, str) for c in cmd)):
            log("...Failed! Unexpected command format ({})!")
            raise ValueError("command should be a list of string or a tuple of strings")
        self._cmd = cmd
        if "alias" in startup_args:
            alias = startup_args["alias"]
            if isinstance(alias, (list, tuple)):
                if all(isinstance(a, str) for a in alias):
                    self.ALIASES = [] + alias
                else:
                    log("...Failed! Unexpected alias format ({})!".format(alias))
                    raise ValueError("alias should be a string, a list of string or a tuple of strings")
            elif isinstance(alias, str):
                self.ALIASES = [alias]
            else:
                log("...Failed! Unexpected alias format ({})!".format(alias))
                raise ValueError("alias should be a string, list of string or tuple of strings")
            log("...service is now known as {}...".format(self.ALIASES))
        super(RCMDService, self).__init__(*args, **kwargs)
        self.exposed_encoding = default_encoding
        self._args = []
        self._proc = None
        self._exit_phase = 0
        self._exiting = False
        self._stopping = False
        self._stop_reason = "Not started yet"
        self._received = []
        self._errors = []
        self._to_send = []
        self._reader = None
        self._writer = None
        self._errors_reader = None
        self._reader_lock = VerbalLock("reader", False)  # RLock()
        self._errors_lock = VerbalLock("errors", False)  # RLock()
        self._writer_lock = VerbalLock("writer", False)  # RLock()
        self._exit_lock = RLock()
        self._stop_lock = RLock()

    def __del__(self):
        log("{}:  Instance just died".format(self))

    # def on_connect(self):
    #     # code that runs when a connection is created
    #     # (to init the service, if needed)
    #     pass
    #
    # def on_disconnect(self):
    #     # code that runs after the connection has already closed
    #     # (to finalize the service, if needed)
    #     pass

    @property
    def exposed_args(self):
        return copy.copy(self._args)

    # TODO: setter not works for some reason
    # @exposed_args.setter
    # def exposed_args(self, value):
    #     self._args = value

    def exposed_set_args(self, value):
        self._args = [str(v) for v in list(value)]

    @property
    def exposed_ready_to_start(self):
        return self._proc is None and not self._stopping

    @property
    def exposed_running(self):
        return not self._stopping and self._proc is not None

    @property
    def exposed_stopping(self):
        return self._stopping

    @property
    def exposed_stop_reason(self):
        return self._stop_reason

    @property
    def exposed_log(self):
        result = logger.logged
        return result

    def exposed_run(self):
        if self.exposed_running:
            return True
        if not self.exposed_ready_to_start:  # Is not running but not stopped yet
            log("Not started command because not ready!")
            return False
        log("{}:  Running command {}...".format(self, self._cmd + self._args))
        try:
            self._proc = subprocess.Popen(
                self._cmd + self._args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            self._proc = None
            log("...Failed by reason: {}".format(e))
            return False

        self._errors_reader = Thread(
            target=self._pipe_reader,
            args=[self._proc.stderr, self._errors, self._errors_lock, self._exit_lock, 2, self])
        self._errors_reader.daemon = True

        self._reader = Thread(
            target=self._pipe_reader,
            args=[self._proc.stdout, self._received, self._reader_lock, self._exit_lock, 1, self])
        self._reader.daemon = True

        self._writer = Thread(
            target=self._pipe_writer,
            args=[self._proc.stdin, self._to_send, self._writer_lock, self._exit_lock, self])
        self._writer.daemon = True

        stopper = Thread(target=self._stopper, args=[self])
        stopper.daemon = True

        try:
            self._errors_reader.start()
            self._reader.start()
            self._writer.start()
        except Exception as e:
            log("...Failed start io threads: {}".format(e))
            self.exposed_stop("Failed to start io threads: {}".format(e))
            self._stopper(self)
            return False

        # TODO: stop app when connection is broken

        if self.dbg_print:
            log("{}:  Starting stopper. Will proceed only when app stops".format(self))
        stopper.start()
        log("{}:  ...Successfully!".format(self))
        return True

    def exposed_stop(self, reason="Normal stop", force=False):
        if not self.exposed_running:
            return True
        return self._stop(self, reason, force=force)

    @staticmethod
    def _stop(subject, reason, soft_exit=None, force=False):
        if subject._proc is None:
            return True

        # => Lock
        subject._stop_lock.acquire()
        if subject._stopping:
            subject._stop_lock.release()
            return False
        subject._stopping = True
        subject._stop_lock.release()
        # <= Unock
        subject._stop_reason = reason
        if soft_exit is not None:
            subject._exit_phase = soft_exit
        else:
            subject._exiting = True
        log("{}:  Stop! Reason: {}, soft_exit: {}".format(subject, reason, soft_exit))
        if force:
            subject.forced_stop()

    def forced_stop(self):
        pass    # NOTE: nothing to do yet

    @staticmethod
    def _stopper(subject):
        if subject.dbg_print:
            log("{}:  STDIO  Waiting sender to stop".format(subject))
        subject._writer.join()
        if subject.dbg_print:
            log("{}:  STDIO  Sender stopped".format(subject))

        if subject.dbg_print:
            log("{}:  STDIO  Waiting receiver to stop".format(subject))
        subject._reader.join()
        if subject.dbg_print:
            log("{}:  STDIO  Receiver stopped".format(subject))

        if subject.dbg_print:
            log("{}:  STDERR Waiting receiver to stop".format(subject))
        subject._errors_reader.join()
        if subject.dbg_print:
            log("{}:  STDERR Receiver stopped".format(subject))

        try:  # If process is already dead - functions ?will? raise exception
            subject._proc.stdin.close()
            subject._proc.terminate()
            subject._proc.wait(timeout=1.0)
        except:
            pass
        subject._proc = None
        subject._exiting = False
        subject._exit_phase = 0
        subject._stopping = False
        log("{}:  Instance successfully stopped".format(subject))
        return True

    @staticmethod
    def _pipe_reader(pipe, buffer, reader_lock, exit_lock, exit_phase, subject):
        dbg_print = False

        # TODO: # BUG#00001 - when running via caller from command line (Windows at least) messages from past instance
        # run are received (even if it's clean start %) )
        # When caller is started via PyCharm there is no such thing

        while not subject._exiting and subject._exit_phase <= exit_phase:
            if subject._exit_phase > 0 and subject._exit_phase < exit_phase:
                continue
            try:
                for line in iter(pipe.readline, b''):
                    line = line.decode(subject.exposed_encoding).strip()
                    if dbg_print:
                        print("{}:{} Reader received '{}'".format(subject, exit_phase, line))
                    if exit_phase == 1 and line[:10] == "exiting...":
                        if dbg_print:
                            print("{}:{} Stopping...".format(subject, exit_phase))
                        subject._stop(subject, "App stopped")
                    if exit_phase == 2:
                        log("{}:e {} ".format(subject, line))
                    # => Locked
                    reader_lock.acquire()
                    buffer.append(line)
                    if dbg_print:
                        print("{}:{}  Reader managed to put line into buffer".format(subject, exit_phase))
                    reader_lock.release()
                    if dbg_print:
                        print("{}:{}  Received '{}' at pipe {}".format(subject, exit_phase, line, pipe))
                        print("  subject._received: {}".format(subject._received))
                    # <= Unlocked
                # => Locked
                exit_lock.acquire()
                if subject._exit_phase == exit_phase:
                    subject._exit_phase += 1
                exit_lock.release()
                # <= Unlocked
            except Exception as e:
                subject._stop(subject, "{}:{} Reader failed: {}".format(subject, exit_phase, e), soft_exit=exit_phase+1)

    @staticmethod
    def _pipe_writer(pipe, buffer, writer_lock, exit_lock, subject):
        dbg_print = False
        iteration = 0
        while not subject._exiting and subject._exit_phase == 0:
            if len(buffer) > 0:
                # => Locked
                writer_lock.acquire()
                to_send = copy.copy(buffer)
                buffer.clear()
                writer_lock.release()
                # <= Unlocked
            else:
                continue

            for d in to_send:
                iteration += 1
                if not subject._exiting and subject._exit_phase == 0:
                    to_send = "{}\r\n".format(d).encode(subject.exposed_encoding)
                    # TODO: remove \r, check if \n already on the end
                    if dbg_print:
                        print("{}:  Sending: {}".format(subject, to_send))
                    try:
                        pipe.write(to_send)
                        pipe.flush()
                    except Exception as e:  # NOTE: Most probably process has been terminated
                        # Initiate "soft" stop - receive and process all remaining messages before exiting
                        subject._stop(subject, "Writer failed: {}".format(e), soft_exit=1)
                        break
            to_send = []

    def exposed_receive(self, wait=True, timeout=1.0):
        dbg_print = False
        if not self.exposed_running and len(self._received) == 0:
            return None

        if wait and len(self._received) == 0:
            start = time.time()
            elapsed = 0
            while len(self._received) == 0 and elapsed < timeout:
                elapsed = time.time() - start
                time.sleep(0.001)

        # => Locked
        self._reader_lock.acquire()
        if dbg_print:
            print("Receive - self._received: {}".format(self._received))
        result = copy.deepcopy(self._received)
        if dbg_print:
            print("Receive - sending back: {}".format(result))
        self._received.clear()
        self._reader_lock.release()
        # <= Unlocked
        return result

    def exposed_errors(self):
        if not self.exposed_running and len(self._errors) == 0:
            return None

        # => Locked
        self._errors_lock.acquire()
        result = copy.deepcopy(self._errors)
        self._errors.clear()
        self._errors_lock.release()
        # <= Unlocked
        return result

    def exposed_send(self, data):
        if not self.exposed_running or self.exposed_stopping:
            return False

        send_data = []
        if isinstance(data, (list, tuple)):
            send_data += data
        elif not isinstance(data, str):
            send_data.append("{}".format(data))
        else:
            send_data.append(data)

        # => Locked
        self._writer_lock.acquire()
        self._to_send += send_data
        self._writer_lock.release()
        # <= Unlocked
        return True

    def exposed_flush(self, timeout=1.0):
        if not self.exposed_running or self.exposed_stopping:
            return False

        start = time.time()
        elapsed = 0
        while len(self._to_send) > 0 and elapsed < timeout:
            elapsed = time.time() - start
            time.sleep(0.001)

        return len(self._to_send) == 0


def rcmd_start(alias, port, cmd):
    from rpyc.utils.server import ThreadedServer
    if rpyc.version.version[0] >= 4:
        from rpyc.utils.helpers import classpartial
        service = classpartial(RCMDService, alias=alias, cmd=cmd)
        log("Stating threaded service named {} on port {} with command {}".format(alias, port, cmd))
        ThreadedServer(service, port=port).start()
    else:
        ThreadedServer(RCMDService, port=port).start()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: {} <alias> <port> <command>".format(sys.argv[0]))
    log("Serving app runner on port {} with command '{}'".format(sys.argv[2], ' '.join(sys.argv[3:])))
    rcmd_start(sys.argv[1], int(sys.argv[2]), sys.argv[3:])
