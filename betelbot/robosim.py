#!/usr/bin/env python

import ConfigParser
import logging
import random
import signal
import time

from math import pi

import cv2
import numpy as np

from tornado.ioloop import IOLoop

from client import BetelbotClientConnection
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
        
        self.cmdTopic = CmdTopic()
        self.moveTopic = MoveTopic()
        self.senseTopic = SenseTopic()

        self.moveIndex = 0
        self.directions = None
        self.path = None

        self.conn = conn
        self.conn.subscribe(self.cmdTopic.id, self.onCmdPublished)
        self.conn.locate(self.onLocateResponse, ParticleFilterMethod.UPDATEPARTICLES)
        self.conn.locate(self.onLocateResponse, PathfinderMethod.SEARCH)

    def move(self, direction):
        # Publish move to subscribers.

        self.moveIndex += 1
        y, x = self.path[self.moveIndex]        
        measurements = self.sense(y, x)
        motion = convertToMotion(direction, self.directions[self.moveIndex], self.gridSize)

        self.conn.publish(self.moveTopic.id, direction)
        self.conn.publish(self.senseTopic.id, measurements)

        self.conn.updateparticles(self.onUpdateParticlesResponse, motion, measurements)


    def sense(self, y, x):
        delta = [[1, 0], [0, 1], [1, 0], [0, 1]]  
        Z = []
        count = len(delta) 
        index = y * self.gridSize * self.grid.shape[1] * count + x * self.gridSize * count
        for i in xrange(count):
            value = self.lookupTable[index]
            dy = value * delta[i][0]
            dx = value * delta[i][1]
            Z.append(int(dy or dx))
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

        self.path = result[0]
        self.directions = result[1]
        self.move(self.directions[self.moveIndex])

    def onUpdateParticlesResponse(self, result):

        time.sleep(self.delay)
        self.move(self.directions[self.moveIndex])

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
    grid = cv2.imread(config.get('map-data', 'map'), cv2.CV_LOAD_IMAGE_GRAYSCALE)
    lookupTable = np.load(config.get('map-data', 'dmap'))
    gridSize = config.getint('map', 'gridSize')
    delay = config.getint('robosim', 'delay')

    client = Client('', config.getint('server', 'port'), BetelbotClientConnection)
    conn = client.connect()

    roboSim = RoboSim(conn, start, goal, grid, gridSize, lookupTable, delay)
    IOLoop.instance().start()


if __name__ == "__main__":
    main()