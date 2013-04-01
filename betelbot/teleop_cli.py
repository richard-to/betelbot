#!/usr/bin/env python

import ConfigParser
import sys
import threading

from tornado.ioloop import IOLoop

from topic import cmdTopic
from util import NonBlockingTerm, Client
from client import BetelbotConnection


def threadedLoop():
    # Need to run the Tornado IO loop in its own thread,
    # otherwise it will block terminal input.

    IOLoop.instance().start()
 

def onCmdPublished(topic, data=None):
    # Debugging callback to make test if commands are 
    # being received and published.

    if data:
        print '[{}]{}'.format(topic, ' '.join(data))


def onInput(client):
    # When terminal receives key input, this input is published 
    # if it matches the accepted values of the command topic.

    c = sys.stdin.read(1)
    if c in cmdTopic.dataType:
        client.publish(cmdTopic.id, c)


def main():
    # Starts up a client connection to publish commands to Betelbot server.
    #
    # - Use h, j, k, and l to move left, down, up, and right respectively.
    # - Use s to stop.

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    client = Client('', config.getint('server', 'port'), BetelbotConnection)
    conn = client.connect()
    conn.subscribe(cmdTopic.id, onCmdPublished)

    thread = threading.Thread(target=threadedLoop)
    thread.daemon = True
    thread.start()

    print "Reading from keyboard"
    print "---------------------------"
    print "Use [h,j,k,l] to move and [s] to stop."

    term = NonBlockingTerm()
    term.run(lambda: onInput(conn))


if __name__ == "__main__":
    main()