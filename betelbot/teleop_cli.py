#!/usr/bin/env python

import ConfigParser
import sys
import threading

from tornado.ioloop import IOLoop

from topic import cmdTopic
from util import NonBlockingTerm
from client import BetelbotClient


def threadedLoop():
    IOLoop.instance().start()
 

def onCmdPublished(topic, data=None):
    if data:
        print '[{}]{}'.format(topic, ' '.join(data))


def onInput(client):
    c = sys.stdin.read(1)
    if c in cmdTopic.dataType:
        client.publish(cmdTopic.id, c)


def main():
    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    client = BetelbotClient('', config.getint('server', 'port'))
    client.subscribe(cmdTopic.id, onCmdPublished)

    thread = threading.Thread(target=threadedLoop)
    thread.daemon = True
    thread.start()

    print "Reading from keyboard"
    print "---------------------------"
    print "Use [h,j,k,l] to move and [s] to stop."

    term = NonBlockingTerm()
    term.run(lambda: onInput(client))


if __name__ == "__main__":
    main()