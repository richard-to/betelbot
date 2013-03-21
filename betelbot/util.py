import fcntl
import os
import select
import signal
import socket
import sys 
import termios
import time
import tty

import numpy as np

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream


def signal_handler(signal, frame):
    sys.exit(0)


def loadGridData(filename):
    file = open(filename, 'r')
    data = file.readlines()
    return np.array(json.loads(data[0]))


class PubSubClient:

    def __init__(self, host='', port=8888):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.stream = IOStream(sock)
        self.stream.connect((host, port))
        self.subscriptionHandlers = {}

    def publish(self, topic, *args):
        self.stream.write("publish {} {}\n".format(topic, ' '.join(map(str, args))))

    def subscribe(self, topic, callback=None):
        if topic not in self.subscriptionHandlers:
            self.subscriptionHandlers[topic] = []
        self.subscriptionHandlers[topic].append(callback)
        self.stream.write("subscribe {}\n".format(topic))
        if not self.stream.reading():
            self.stream.read_until("\n", self.onReadLine)

    def onReadLine(self, data):
        tokens = data.strip().split()
        for subscriber in self.subscriptionHandlers[tokens[0]]:
            subscriber(tokens[0], tokens[1:])
        if not self.stream.reading():
            self.stream.read_until("\n", self.onReadLine)

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
