from socket import socket
sock = socket()
sock.connect(("127.0.0.1", 8888))
sock.send("subscribe betelbot_move\n")
data = ''
while 1:
    data = ''
    data = sock.recv(1024)
    if data:
        print data.strip()