from sys import stdin, stdout

while True:
    line = stdin.readline()
    line.strip()
    if line == "exit":
        print("exiting...")
        break
    if line == "raise":
        raise EOFError("Raised error by intention")
    if len(line) > 0:
        print(line)
