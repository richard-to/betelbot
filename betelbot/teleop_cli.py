import ConfigParser
import sys
import threading

from tornado.ioloop import IOLoop

from topic import msgs
from util import PubSubClient, NonBlockingTerm


def threadedLoop():
    IOLoop.instance().start()
 

def onMovePublished(data=None):
    if data:
        print data.strip()


def onInput(client, validMoves):
    c = sys.stdin.read(1)
    if c == '\x1b':
        try:
            c = sys.stdin.read(2)
            if c in validMoves:
                client.publish('move', validMoves[c])
        except: pass


def main():
    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    client = PubSubClient('', config.getint('server', 'port'))
    client.subscribe('move', onMovePublished)

    validMoves = {
        '[A': '1',
        '[B': '2',
        '[C': '3',
        '[D': '4'
    }

    thread = threading.Thread(target=threadedLoop)
    thread.daemon = True
    thread.start()

    print "Reading from keyboard";
    print "---------------------------";
    print "Use arrow keys to move.";

    term = NonBlockingTerm()
    term.run(lambda: onInput(client, validMoves))

if __name__ == "__main__":
    main()