#!/usr/bin/env python

import logging
import random
import signal
import time

from math import pi

import cv2
import numpy as np

from tornado.ioloop import IOLoop

from client import BetelbotClientConnection
from config import JsonConfig
from pathfinder import PathfinderMethod, PathfinderSearchType
from particle import ParticleFilterMethod, convertToMotion
from topic.default import CmdTopic, MoveTopic, SenseTopic
from util import Client, signalHandler


class RoboSim(object):
    # RoboSim simulates the real robot.

    def __init__(self, conn, start, goal, grid, gridSize, lookupTable, delay=1):
        # Initializes RoboSim with certain parameters.
        #
        # - Conn is the connection with master Betelbot server.
        # - Start is an x,y coordinate that represents robot start position
        # - Goal is an x,y coordinate that represents robot destination
        # - Delay is the number of seconds before publishing a move
        #
        # Need to add a flag for manual control?

        self.start = start
        self.goal = goal
        self.grid = grid
        self.gridSize = gridSize
        self.lookupTable = lookupTable
        self.delay = delay

        self.moveTopic = MoveTopic()
        self.senseTopic = SenseTopic()

        self.moveIndex = 0
        self.directions = None
        self.path = None

        self.conn = conn

        self.conn.locate(self.onLocateResponse, ParticleFilterMethod.UPDATEPARTICLES)
        self.conn.locate(self.onLocateResponse, PathfinderMethod.SEARCH)

    def move(self):
        # Publish move to subscribers.

        if self.path and self.moveIndex < len(self.path):

            dest = self.directions[self.moveIndex]
            if self.moveIndex > 0:
                start = self.directions[self.moveIndex - 1]
            else:
                start = dest
            motion = convertToMotion(start, dest, self.gridSize)

            y, x = self.path[self.moveIndex]
            measurements = self.sense(dest, y, x)

            self.moveIndex += 1

            self.conn.publish(self.moveTopic.id, dest)
            self.conn.publish(self.senseTopic.id, measurements)

            self.conn.updateparticles(self.onUpdateParticlesResponse, motion, measurements)

    def sense(self, direction, y, x):
        delta = [[1, 0], [0, 1], [1, 0], [0, 1]]
        directions = ['k', 'h', 'j', 'l']
        Z = []
        count = len(delta)
        y = y * self.gridSize + self.gridSize/2
        x = x * self.gridSize + self.gridSize/2
        index = y * self.grid.shape[1] * count + x * count
        for i in xrange(count):
            if direction != directions[i]:
                value = self.lookupTable[index]
                dy = value * delta[i][0]
                dx = value * delta[i][1]
                Z.append(int(dy or dx))
            else:
                Z.append(None)
            index += 1
        return Z

    def onLocateResponse(self, found=False):
        # If the getdirections method is found, then call service method.

        if (self.conn.hasService(PathfinderMethod.SEARCH) and
                self.conn.hasService(ParticleFilterMethod.UPDATEPARTICLES)):
            self.conn.search(self.onSearchResponse,
                self.start, self.goal, PathfinderSearchType.BOTH)

    def onSearchResponse(self, result):
        # Need to make this callback work asynchronously?
        # Sleep method blocks everything.

        self.directions = result[1]
        self.path = result[0]
        self.path.pop(0)
        self.move()

    def onUpdateParticlesResponse(self, result):

        time.sleep(self.delay)
        self.move()


def main():
    signal.signal(signal.SIGINT, signalHandler)

    cfg = JsonConfig()

    logger = logging.getLogger('')
    logger.setLevel(cfg.general.logLevel)

    start =  cfg.map.start
    goal = cfg.map.goal
    grid = cv2.imread(cfg.mapData.map, cv2.CV_LOAD_IMAGE_GRAYSCALE)
    lookupTable = np.load(cfg.mapData.dmap)
    gridSize = cfg.map.gridsize
    delay = cfg.robosim.delay

    client = Client('', cfg.server.port, BetelbotClientConnection)
    conn = client.connect()

    roboSim = RoboSim(conn, start, goal, grid, gridSize, lookupTable, delay)
    IOLoop.instance().start()


if __name__ == "__main__":
    main()