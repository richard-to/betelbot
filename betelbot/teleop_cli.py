import ConfigParser
import fcntl
import logging
import os
import select
import signal
import sys 
import termios
import threading
import time
import tty 

from tornado.ioloop import IOLoop

from topic import msgs
from util import PubSubClient, signal_handler


def threadedLoop():
    IOLoop.instance().start()
 

def callback(data=None):
    if data:
        print data.strip()


def isData():
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])


def main():
    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    client = PubSubClient('', config.getint('server', 'port'))
    client.subscribe('move', callback)
    
    validMoves = {
        '[A': '1',
        '[B': '2',
        '[C': '3',
        '[D': '4'
    }

    t = threading.Thread(target=threadedLoop)
    t.daemon = True
    t.start()

    signal.signal(signal.SIGINT, signal_handler)
    
    old_settings = termios.tcgetattr(sys.stdin)

    fd = sys.stdin.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    try:
        tty.setcbreak(sys.stdin.fileno())
        while True:
            time.sleep(.3)
            if isData():
                c = sys.stdin.read(1)
                if c == '\x1b':
                    try:
                        c = sys.stdin.read(2)
                        if c in validMoves:
                            client.publish('move', validMoves[c])
                    except: continue
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    main()