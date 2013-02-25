import fcntl
import os
import select
import signal
import socket
import sys 
import termios
import time
import tty

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream


def signal_handler(signal, frame):
    sys.exit(0)


class PubSubClient:

    def __init__(self, onClose, host='', port=8888):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.stream = IOStream(sock)
        self.stream.connect((host, port))
        self.subscriptionHandlers = {}

    def publish(self, cmd, opts):
        self.stream.write("publish {} {}\n".format(cmd, opts))

    def subscribe(self, cmd, callback=None):
        self.subscriptionHandlers[cmd] = callback
        self.stream.write("subscribe {}\n".format(cmd))
        self.stream.read_until("\n", self._onReadLine)

    def _onReadLine(self, data):
        self.subscriptionHandlers['move'](data)
        self.stream.read_until("\n", self._onReadLine)

    def close():
        self.stream.close()


class NonBlockingTerm:

    def run(self, cb):
        signal.signal(signal.SIGINT, signal_handler)
        
        old_settings = termios.tcgetattr(sys.stdin)
        
        fd = sys.stdin.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        try:
            tty.setcbreak(sys.stdin.fileno())
            while True:
                time.sleep(.3)
                if self.hasData():
                    cb()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def hasData(self):
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])
