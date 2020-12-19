# from sys import stdin, stdout
from threading import Thread, RLock
import subprocess


class Caller:
    def __init__(self, cmd):
        self._cmd = cmd
        self._proc = None
        self._exit_phase = 0
        self._exiting = False
        self._stdout = []
        self._reader_lock = RLock()

    @staticmethod
    def _pipe_reader(pipe, subject):
        while not subject._exiting:
            for line in iter(pipe.readline, b''):
                line = line.decode('utf-8').strip()
                # print("read from pipe: {}".format(line))
                subject._reader_lock.acquire()
                subject._stdout.append(line)
                subject._reader_lock.release()
            subject._reader_lock.acquire()
            if subject._exit_phase == 1:
                subject._exit_phase = 2
            subject._reader_lock.release()

    def run(self):
        self._proc = proc = subprocess.Popen(
            self._cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        t = Thread(target=self._pipe_reader, args=[self._proc.stdout, self])
        t.daemon = True
        t.start()
        data = [1,2,3,4,5,"exit",6]
        iteration = 0
        while not self._exiting:
            for d in data:
                iteration += 1
                if not self._exiting and self._exit_phase == 0:
                    to_send = "{}\r\n".format(d).encode('utf-8')
                    # print("sending: {}".format(to_send))
                    try:
                        proc.stdin.write(to_send)
                        proc.stdin.flush()
                    except:  # NOTE: Most probably process has been terminated
                        self._reader_lock.acquire()
                        self._exit_phase = 1    # Initiate "soft" stop - receive and process all remaining messages before exiting
                        # NOTE: no need to release as it's RLock and it's going to be acquired in following line
                self._reader_lock.acquire()
                for line in self._stdout:
                    # print("received: {}".format(line))
                    if line[:10] == "exiting...":
                        self._exiting = True    # NOTE: no reason to process messages further
                self._stdout = []
                if self._exit_phase == 3:
                    self._exiting = True
                if self._exit_phase == 2:
                    self._exit_phase = 3    # NOTE: give a chance to receive last read values
                self._reader_lock.release()
        try:  # If process is already dead - functions ?will? rise exception
            proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=1.0)
        except:
            pass
        t.join()

if __name__ == "__main__":
    caller = Caller(["python", "stdin_to_stdout.py"])
    caller.run()
