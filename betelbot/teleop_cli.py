#!/usr/bin/env python

import ConfigParser
import sys
import threading

from tornado.ioloop import IOLoop

from topic.default import CmdTopic
from util import NonBlockingTerm, Client
from client import BetelbotClientConnection


def threadedLoop():
    # Need to run the Tornado IO loop in its own thread,
    # otherwise it will block terminal input.

    IOLoop.instance().start()
 

def onCmdPublished(topic, data=None):
    # Debugging callback to make test if commands are 
    # being received and published.

    if data:
        print '[{}]{}'.format(topic, ' '.join(data))


def onInput(conn, cmdTopic):
    # When terminal receives key input, this input is published 
    # if it matches the accepted values of the command topic.

    c = sys.stdin.read(1)
    if cmdTopic.isValid(c):
        conn.publish(cmdTopic.id, c)


def main():
    # Starts up a client connection to publish commands to Betelbot server.
    #
    # - Use h, j, k, and l to move left, down, up, and right respectively.
    # - Use s to stop.

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    
    cmdTopic = CmdTopic()

    client = Client('', config.getint('server', 'port'), BetelbotClientConnection)
    conn = client.connect()
    conn.subscribe(cmdTopic.id, onCmdPublished)

    thread = threading.Thread(target=threadedLoop)
    thread.daemon = True
    thread.start()

    print "Reading from keyboard"
    print "---------------------------"
    print "Use [h,j,k,l] to move and [s] to stop."

    term = NonBlockingTerm()
    term.run(lambda: onInput(conn, cmdTopic))


if __name__ == "__main__":
    main()