#!/usr/bin/env python

import ConfigParser
import logging
import random
import signal

from tornado.ioloop import IOLoop

from client import BetelbotClientConnection
from topic.default import CmdTopic, MoveTopic
from util import Client, signalHandler


class RoboSim(object):

    def __init__(self, conn):
        self.cmdTopic = CmdTopic()
        self.moveTopic = MoveTopic()
        self.conn = conn
        self.conn.subscribe(self.cmdTopic.id, self.onCmdPublished)

    def move(self, direction):
        self.conn.publish(self.moveTopic.id, direction)

    def onCmdPublished(self, topic, data=None):
        self.move(data[0])


def main():
    signal.signal(signal.SIGINT, signalHandler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    logger = logging.getLogger('')
    logger.setLevel(config.get('general', 'log_level'))
    
    client = Client('', config.getint('server', 'port'), BetelbotClientConnection)
    conn = client.connect()

    roboSim = RoboSim(conn)
    IOLoop.instance().start()


if __name__ == "__main__":
    main()