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

    def __init__(self, conn, start, goal, delay=5):
        self.delay = delay
        self.start = start
        self.goal = goal
        self.cmdTopic = CmdTopic()
        self.moveTopic = MoveTopic()
        self.conn = conn
        self.conn.subscribe(self.cmdTopic.id, self.onCmdPublished)
        self.conn.locate(1, PathfinderMethod.SEARCH, self.onLocateResponse)

    def move(self, direction):
        self.conn.publish(self.moveTopic.id, direction)

    def onLocateResponse(self, found=False):
        if found:
            self.conn.search(self.onSearchResponse, 1, self.start, self.goal)

    def onSearchResponse(self, id, method, result):
        delta = {
            'k': [-1, 0], 
            'h': [0, -1], 
            'j': [1, 0],
            'l': [0, 1]
        }
        current = self.start
        moves = result[0][1:]
        for move in moves:
            temp = [move[0] - current[0], move[1] - current[1]]
            for key in delta:
                if delta[key] == temp:
                    self.move(key)
                    break
            current = move
            time.sleep(self.delay) 

    def onCmdPublished(self, topic, data=None):
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