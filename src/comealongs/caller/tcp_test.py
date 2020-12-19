"""
A Simple App to test interaction with app via TCP (calc.py for example)
It:
1. Connects to a app via specified TCP port
2. Get's input via stdin, sends to an app, receives and displays response and so on and so on
3. Stops if received "exiting..." message from app
"""
import socket
from threading import Thread


class TCPIO(object):
    def __init__(self, host='localhost', port=30001):
        self.sock = sock = socket.socket()
        sock.connect((host, port))
        sock.settimeout(0.1)
        self._stop = False

    def receive(self, sock):
        try:
            buffer = sock.recv(1024)
        except TimeoutError:
            buffer = bytearray()
        except socket.timeout:
            buffer = bytearray()
        return buffer

    def receive_loop(self, sock):
        while not self._stop:
            received = self.receive(sock)
            if len(received) > 0:
                received = received.decode('UTF-8').strip().split('\n')
                for r in received:
                    print("Received: {}".format(r))
                    if r == "exiting...":
                        self._stop = True
                        break

    def run(self):
        t = Thread(target=self.receive_loop, args=[self.sock])
        t.daemon = True
        t.start()

        while not self._stop:
            to_send = input("Send something:")
            if not self._stop:
                self.sock.sendall(to_send.encode('UTF-8'))

        t.join()


if __name__ == "__main__":
    TCPIO().run()
