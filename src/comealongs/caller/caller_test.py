"""
A Simple App to test interaction with Caller (caller.py) via RPyC
It:
1. Connects to a caller (and starts remote app with this / connects to shared app instance)
2. Get's input via stdin, sends to caller, receives and displays response and so on and so on
   If "log" is entered then displays stderr output of remote app that is running by caller
3. Stops if connection if caller is closed
"""
import rpyc


c = rpyc.connect("localhost", 53575)
io = c.root
a = io.run()
while True:
    received = io.receive()
    if received is not None:
        for r in received:
            print("Received: {}".format(r))
    else:
        break
    to_send = input("Send something:")
    if to_send == "log":
        log = io.log
        for l in log:
            print("Log: {}".format(l))
        log = []
    elif not io.send(to_send):
        break
