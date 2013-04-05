#!/usr/bin/env python

import ConfigParser
import logging
import random
import signal
import time

from tornado.ioloop import IOLoop

from client import BetelbotClientConnection
from pathfinder import PathfinderMethod
from topic.default import CmdTopic, MoveTopic
from util import Client, signalHandler


class RoboSim(object):
    # RoboSim simulates the real robot.

    def __init__(self, conn, start, goal, delay=1):
        # Initializes RoboSim with certain parameters.
        # 
        # - Conn is the connection with master Betelbot server.
        # - Start is an x,y coordinate that represents robot start position
        # - Goal is an x,y coordinate that represents robot destination
        # - Delay is the number of seconds before publishing a move
        #
        # Need to add a flag for manual control?

        self.delay = delay
        self.start = start
        self.goal = goal
        self.cmdTopic = CmdTopic()
        self.moveTopic = MoveTopic()
        self.conn = conn
        self.conn.subscribe(self.cmdTopic.id, self.onCmdPublished)
        self.conn.locate(self.onLocateResponse, PathfinderMethod.GETDIRECTIONS)

    def move(self, direction):
        # Publish move to subscribers.
        
        self.conn.publish(self.moveTopic.id, direction)

    def onLocateResponse(self, found=False):
        # If the getdirections method is found, then call service method.
        
        if found:
            self.conn.getdirections(self.onGetDirectionsResponse, self.start, self.goal)

    def onGetDirectionsResponse(self, result):
        # Need to make this callback work asynchronously? 
        # Sleep method blocks everything.

        directions = result[0]
        for cmd in directions:
            self.move(cmd)
            time.sleep(self.delay)

    def onCmdPublished(self, topic, data=None):
        # If simulator receives a command, wait x seconds before 
        # publishing the move to subscribers.
        
        time.sleep(self.delay)        
        self.move(data[0])


def main():
    signal.signal(signal.SIGINT, signalHandler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    logger = logging.getLogger('')
    logger.setLevel(config.get('general', 'log_level'))

    start = [int(num) for num in config.get('map', 'start').split(',')]
    goal = [int(num) for num in config.get('map', 'goal').split(',')]

    client = Client('', config.getint('server', 'port'), BetelbotClientConnection)
    conn = client.connect()

    roboSim = RoboSim(conn, start, goal)
    IOLoop.instance().start()


if __name__ == "__main__":
    main()