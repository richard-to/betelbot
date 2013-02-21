from socket import socket
sock = socket()
sock.connect(("127.0.0.1", 8888))
while 1:
    data = raw_input("Enter move: ")
    if data:
        sock.send("publish betelbot_move {}\n".format(data))
    else:
        break