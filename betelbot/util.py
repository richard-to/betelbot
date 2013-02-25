import socket
import sys

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream


def signal_handler(signal, frame):
    sys.exit(0)


class PubSubClient:

    def __init__(self, host='', port=8888):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.stream = IOStream(sock)
        self.stream.connect((host, port))
        self.sub_cb = {}

    def publish(self, cmd, opts):
        self.stream.write("publish {} {}\n".format(cmd, opts))

    def subscribe(self, cmd, callback=None):
        self.sub_cb[cmd] = callback
        self.stream.write("subscribe {}\n".format(cmd))
        self.stream.read_until("\n", self._on_read_line)

    def _on_read_line(self, data):
        self.sub_cb['move'](data)
        self.stream.read_until("\n", self._on_read_line)

    def close():
        self.stream.close()