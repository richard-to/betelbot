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
from particle import Particle, convertToMotion
from robot import RobotConnection, RobotMethod, RobotServer
from topic import getTopicFactory
from util import Client, signalHandler


class BetelbotSimDriver(object):
    # BetelbotSimDriver simulates the real robot.

    # Error messages
    ERROR_POWER = "Invalid power value"
    ERROR_MODE = "Invalid mode value"
    ERROR_CMD = "Invalid cmd value"

    def __init__(self, start, grid, gridsize, lookupTable, delay=1):

        self.topics = getTopicFactory()

        self.power = self.topics.power.off
        self.mode = self.topics.mode.manual

        self.grid = grid
        self.gridsize = gridsize
        self.lookupTable = lookupTable
        self.delay = delay
        self.delta = Particle.DELTA

        self.setLocation(*start)
        self.moveIndex = 0

    def moveCmd(self, callback):

        if not self.on() or self.cmd is None:
            callback(None, None, None)
            return

        cmdTopic = self.topics.cmd
        pathDelta = {
            cmdTopic.left: [0, -1],
            cmdTopic.down: [1, 0],
            cmdTopic.up: [-1, 0],
            cmdTopic.right: [0, 1]
        }
        newDelta = pathDelta[self.cmd]
        y = self.current[0] + newDelta[0]
        x = self.current[1] + newDelta[1]
        measurements = self.sense(self.cmd, y, x)
        self.current = [y, x]

        reset = False
        if self.currentDirection is None:
            self.currentDirection = self.cmd
            reset = True
        motion = convertToMotion(cmdTopic, self.currentDirection, self.cmd, self.gridsize)
        self.currentDirection = self.cmd
        self.cmd = None

        callback(motion, measurements, reset)

    def moveAuto(self, callback):

        if not self.on() or self.path is None:
            callback(None, None, None)
            return

        time.sleep(self.delay)

        if self.moveIndex < len(self.path):
            reset = False
            dest = self.directions[self.moveIndex]
            if self.moveIndex > 0:
                start = self.directions[self.moveIndex - 1]
            else:
                start = dest
                reset = True
            motion = convertToMotion(self.topics.cmd, start, dest, self.gridsize)
            self.currentDirection = dest

            y, x = self.path[self.moveIndex]
            measurements = self.sense(dest, y, x)
            self.current = (y, x)

            self.moveIndex += 1
            callback(motion, measurements, reset)

    def sense(self, direction, y, x):

        delta = self.delta
        directions = self.topics.cmd.keys
        Z = []
        count = len(delta)
        midpoint = self.gridsize/2
        y = y * self.gridsize + midpoint
        x = x * self.gridsize + midpoint
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

    def getStatus(self):
        return [self.power, self.mode]

    def setPower(self, power):
        if self.topics.power.isValid(power) is False:
            raise ValueError, BetelbotSimDriver.ERROR_POWER
        self.power = power

    def setMode(self, mode):
        if self.topics.mode.isValid(mode) is False:
            raise ValueError, BetelbotSimDriver.ERROR_MODE

        if self.mode != mode:
            self.mode = mode
            self.resetPath()

    def setLocation(self, y, x):
        self.resetPath()
        self.start = [y, x]
        self.current = self.start
        self.currentDirection = None
        self.goal = None

    def setPath(self, path, directions):
        self.setLocation(*path.pop(0))
        self.goal = path[-1]
        self.path = path
        self.directions = directions

    def resetPath(self):
        self.cmd = None
        self.path = None
        self.directions = None
        self.moveIndex = 0

    def setCmd(self, cmd):
        if self.topics.cmd.isValid(cmd) is False:
            raise ValueError, BetelbotSimDriver.ERROR_CMD
        self.resetPath()
        self.cmd = cmd

    def on(self):
        return self.power == self.topics.power.on

    def autonomous(self):
        return self.mode == self.topics.mode.autonomous

    def manual(self):
        return self.mode == self.topics.mode.manual


def main():
    signal.signal(signal.SIGINT, signalHandler)

    cfg = JsonConfig()

    logger = logging.getLogger('')
    logger.setLevel(cfg.general.logLevel)

    grid = cv2.imread(cfg.mapData.map, cv2.CV_LOAD_IMAGE_GRAYSCALE)
    lookupTable = np.load(cfg.mapData.dmap)
    gridsize = cfg.map.gridsize
    start =  cfg.robosim.start
    delay = cfg.robosim.delay

    serverPort = cfg.robosim.port

    client = Client('', cfg.server.port, BetelbotClientConnection)
    conn = client.connect()

    driver = BetelbotSimDriver(start, grid, gridsize, lookupTable, delay)

    server = RobotServer(connection=RobotConnection, driver=driver, masterConn=conn)
    server.listen(serverPort)

    IOLoop.instance().start()


if __name__ == "__main__":
    main()