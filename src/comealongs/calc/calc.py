# from core.eval_sandbox import evaluate

import sys
import socket
from threading import Thread
from time import time

# TODO: replace threads with asyncio


class Calc(object):
    """
    Main class for example Calc App
    It receives math expressions via stdin ot tcp connection,
    evaluates result and sends it back via stdout or tcp connection
    Expressions are expected to be strings containing valid python math expression
    If received expression is equals to "last" then returnes result of last math expression
    If received expression is equals to "exit" then app is stopped
    """

    def __init__(self, port=30001, stdio=False, debug=False):
        self._port = port
        self._stdio_en = stdio
        self._debug = debug
        self._stop = False
        self._last_result = None
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(('', self._port))
        self._socket.settimeout(0.1)
        self._connections = []

    def _connector(self, sock, handler):
        """
        Serves incomming TCP connections
        For each host a socket is created and then processed in separate thread
        :param sock: socket to listen for incoming connectios
        :param handler: function to handle incoming TCP stream
        :return: Nothing
        """
        while not self._stop:
            try:
                conn, addr = sock.accept()
            except TimeoutError:
                continue
            except socket.timeout:
                continue
            if self._debug:
                print("{0:.7f}:".format(time())+" Opening connection...", file=sys.stderr)
            conn.settimeout(0.1)
            t = Thread(target=handler, args=[conn])
            t.daemon = True
            t.start()
            self._connections.append((conn, addr, t))
            if self._debug:
                print("{0:.7f}:".format(time())+" ...opened", file=sys.stderr)

    def _stdio(self):
        """
        Serves requests made via stdin
        By default is disabled and should be turned on via param
        If enabled then app won't be able to stop successfully by request via TCP while there is no data on stdin
        :return: Nothing
        """
        if self._stdio_en:
            print("{0:.7f}:".format(time())+" Serving STDIO!", file=sys.stderr)
        while not self._stop and self._stdio_en:
            for line in iter(sys.stdin.readline, b''):
                self.handle_request(line)
                if self._stop or not self._stdio_en:
                    break

    def _tcpio(self, conn):
        """
        Serves requests made via stdin
        :param conn:  TCP connection to serve
        :return: Nothing
        """
        print("{0:.7f}:".format(time())+" Started tcpio thread...", file=sys.stderr)
        while not self._stop:
            try:
                buffer = conn.recv(1024)
            except TimeoutError:
                continue
            except socket.timeout:
                continue
            except Exception as e:
                print("{0:.7f}:".format(time())+" Failed to read in tcpio thread...\n{}\n...closing".format(e), file=sys.stderr)
                try:
                    conn.close()
                except:
                    pass
                break
            if len(buffer) > 0:
                if self._debug:
                    print("{0:.7f}:".format(time())+" Got request, processing", file=sys.stderr)
                try:
                    result = self.stream_handle(buffer)
                except Exception as e:
                    print("{0:.7f}:".format(time())+" Failed to process request...\n{}\n...closing".format(e), file=sys.stderr)
                    try:
                        conn.close()
                    except:
                        pass
                    break
            else:
                result = None
            try:
                if result is not None:
                    conn.sendall(result)
            except Exception as e:
                print("{0:.7f}:".format(time())+" Failed to reply in tcpio thread...\n{}\n...clossing".format(e), file=sys.stderr)
                try:
                    conn.close()
                except:
                    pass
                break

    def stream_handle(self, data):
        """
        Handles incoming requests stream
        :param data: String containing one or multiple math expressions. Multiple expressions should be delimited using \n
        :return: String with results for incoming expressions. Results for multiple expressions are separated with \n
        """
        result = []
        if len(data) > 0:
            data = data.decode('UTF-8').strip().split('\n')
            for line in data:
                result.append(self.handle_request(line, quiet=True))
                if self._stop:
                    break
        result = ('\n'.join(str(r) for r in result) + '\n').encode('UTF-8')
        return result

    def handle_request(self, request, quiet=False):
        """
        Handles single expression
        :param request: string with math expression or "last" or "exit"
        :param quiet: If True then no result is sent to stdout. Used when serving requests received by TCP
        :return: return value for request (resolution to math expression etc.)
        """
        if self._debug:
            print("Handling request {} ...".format(request), file=sys.stderr)
        self._last_result = result = self._operator(request)
        if not quiet:
            print("{}".format(result))
        if self._debug:
            print("...result: {}".format(result), file=sys.stderr)
        return result

    def _operator(self, command):
        """
        Executes single expression
        :param command: string with math expression or "last" or "exit"
        :return: value for math expression, value of last math expression if "last", None if "exit"
        """
        result = None
        if self._debug:
            print("{0:.7f}:".format(time())+" Command: {}".format(command), file=sys.stderr)
        if command.strip() == "exit":
            print("{0:.7f}:".format(time())+" Received Exit command", file=sys.stderr)
            self.stop()
            return None
        if command.strip() == "last":
            return self._last_result
        try:
            result = eval("{}".format(command))  # TODO: use evaluate for safety
        except Exception as e:
            print("{0:.7f}:".format(time())+" Exception in command {}:{}".format(command, e), file=sys.stderr)
            return None
        return result

    def run(self):
        """
        Launches requests handling
        :return:
        """
        self._socket.listen()
        t = Thread(target=self._stdio)
        t.daemon = True
        ttcp = Thread(target=self._connector, args=[self._socket, self._tcpio])
        ttcp.daemon = True
        t.start()
        ttcp.start()
        # Will exit only when received "exit" request from stdin or tcp
        if self._debug:
            print("{0:.7f}:".format(time())+" waiting ttcp to stop\n"
                  "Will exit only when received 'exit' request from stdin or tcp", file=sys.stderr)
        ttcp.join()
        for c in self._connections:
            conn, addr, thread = c
            if self._debug:
                print("{0:.7f}:".format(time()) + " waiting tcpio to stop", file=sys.stderr)
            thread.join()
        self._connections = []
        self._socket.close()
        if self._debug:
            print("{0:.7f}:".format(time())+" waiting stdio to stop", file=sys.stderr)
        t.join()
        if self._debug:
            print("{0:.7f}:".format(time())+" ...stopped sucessfully", file=sys.stderr)
            print("{0:.7f}:".format(time())+" ...exiting", file=sys.stderr)
        print("exiting...")

    def stop(self):
        """
        Stops requests handling
        :return:
        """
        self._stop = True
        for c in self._connections:
            conn, addr, thread = c
            try:
                conn.sendall("exiting...\n".encode('UTF-8'))
            except:
                pass
        if self._debug:
            print("{0:.7f}:".format(time())+" Calc started to stop...", file=sys.stderr)


if __name__ == "__main__":
    kwargs = {}
    if len(sys.argv) >= 2:
        kwargs["port"] = int(sys.argv[1])
    if len(sys.argv) >= 3:
        kwargs["stdio"] = int(sys.argv[2])
    if len(sys.argv) >= 4:
        kwargs["debug"] = int(sys.argv[3])
    c = Calc(**kwargs)
    c.run()
