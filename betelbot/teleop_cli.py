#!/usr/bin/env python

import sys
import threading

from tornado.ioloop import IOLoop

import jsonrpc

from client import BetelbotClientConnection
from config import JsonConfig
from topic.default import CmdTopic
from util import NonBlockingTerm, Client


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
    elif c == 'p':
        conn.power(None, 'on')
    elif c == 'm':
        conn.mode(None, 'manual')
    elif c == 'a':
        conn.mode(None, 'autonomous')
    elif c == 'r':
        conn.publish("location", 0, 14)
    elif c == 'w':
        conn.publish("waypoint", [0, 14], [15, 2])

def printInstructions(cmdTopic):
    # Prints Betelbot control instructions to console

    print "Reading from keyboard"
    print "---------------------------"
    print "Use [{}, {}, {}, {}] to move and [{}] to stop.".format(
            cmdTopic.left, cmdTopic.down, cmdTopic.up,
            cmdTopic.right, cmdTopic.stop)

def onBatchLocateResponse(found):
    if found:
        print "Services located"

def main():
    # Starts up a client connection to publish commands to Betelbot server.
    #
    # - Use h, j, k, and l to move left, down, up, and right respectively.
    # - Use s to stop.

    cfg = JsonConfig()

    cmdTopic = CmdTopic()

    client = Client('', cfg.server.port, BetelbotClientConnection)
    conn = client.connect()
    conn.subscribe(cmdTopic.id, onCmdPublished)
    conn.batchLocate(onBatchLocateResponse, ["power", "mode", "robotstatus"])
    thread = threading.Thread(target=threadedLoop)
    thread.daemon = True
    thread.start()

    printInstructions(cmdTopic)

    term = NonBlockingTerm()
    term.run(lambda: onInput(conn, cmdTopic))


if __name__ == "__main__":
    main()