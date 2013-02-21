from socket import socket
sock = socket()
sock.connect(("127.0.0.1", 8888))
sock.send("SDF\r\n")
while 1:
    data = raw_input("Enter data: ")
    if (data):
        sock.send(data + "\r\n")
    else:
        break