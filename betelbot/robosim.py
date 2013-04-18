#!/usr/bin/env python

import logging
import random
import signal
import time

from math import pi

import cv2
import numpy as np

from tornado.ioloop import IOLoop

import jsonrpc

from client import BetelbotClientConnection
from config import JsonConfig, DictConfig
from jsonrpc import JsonRpcServer, JsonRpcConnection
from pathfinder import PathfinderMethod, PathfinderSearchType
from particle import Particle, ParticleFilterMethod, convertToMotion
from topic import getTopicFactory
from util import Client, signalHandler


class RoboSim(object):
    # RoboSim simulates the real robot.

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

    def moveCmd(self):

        if not self.on() or self.cmd is None:
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

        return [motion, measurements, reset]

    def moveAuto(self):

        if not self.on() or self.path is None:
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

            return [motion, measurements, reset]

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
            raise ValueError, ERROR_POWER
        self.power = power

    def setMode(self, mode):
        if self.topics.mode.isValid(mode) is False:
            raise ValueError, ERROR_MODE

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
            raise ValueError, ERROR_CMD
        self.resetPath()
        self.cmd = cmd

    def on(self):
        return self.power == self.topics.power.on

    def autonomous(self):
        return self.mode == self.topics.mode.autonomous

    def manual(self):
        return self.mode == self.topics.mode.manual


class RobotMethod(object):
    # Methods supported by Robot server
    POWER = 'robot_power'
    MODE = 'robot_mode'
    STATUS = 'robot_status'


class RobotServer(JsonRpcServer):
    # RoboSim server is a service that simulates Betelbot

    # Log messages
    LOG_SERVER_RUNNING = 'RoboSim Server is running'

    # Accepted kwargs params
    PARAM_MASTER_CONN= 'masterConn'
    PARAM_ROBOT = 'robot'

    def onInit(self, **kwargs):
        logging.info(RobotServer.LOG_SERVER_RUNNING)

        defaults = {
            RobotServer.PARAM_MASTER_CONN: None,
            RobotServer.PARAM_ROBOT: None
        }

        self.topics = getTopicFactory()

        self.servicesFound = False

        self.data.update(defaults, True)
        self.data.update(kwargs, False)

        self.robot = self.data.robot
        self.masterConn = self.data.masterConn

    def onListen(self, port):
        self.port = port
        self.masterConn.batchLocate(self.onBatchLocateResponse, [
            ParticleFilterMethod.UPDATE,
            PathfinderMethod.SEARCH
        ])

    def onBatchLocateResponse(self, found):
        if found:
            self.servicesFound = True
            self.masterConn.subscribe(self.topics.cmd.id, self.onCmdPublished)
            self.masterConn.subscribe(self.topics.location.id, self.onLocationPublished)
            self.masterConn.subscribe(self.topics.waypoint.id, self.onWaypointPublished)
            self.masterConn.register(RobotMethod.POWER, self.port)
            self.masterConn.register(RobotMethod.MODE, self.port)
            self.masterConn.register(RobotMethod.STATUS, self.port)

    def onCmdPublished(self, topic, data):
        cmd = data[0]
        if self.robot.on() and self.robot.manual():
            self.robot.setCmd(cmd)
            robotData = self.robot.moveCmd()
            if robotData is not None:
                self.processRobotData(*robotData)

    def onLocationPublished(self, topic, data):
        if self.robot.on() and self.robot.manual() and self.topics.location.isValid(*data):
            self.robot.setLocation(*data)

    def onWaypointPublished(self, topic, data):
        if self.robot.on() and self.robot.autonomous() and self.topics.waypoint.isValid(*data):
            self.masterConn.pathfinder_search(self.onSearchResponse,
                data[0], data[1], PathfinderSearchType.BOTH)

    def onSearchResponse(self, result):
        self.robot.setPath(*result)
        robotData = self.robot.moveAuto()
        if robotData is not None:
            self.processRobotData(*robotData)

    def onUpdateParticlesResponse(self, result):
        if self.robot.on() and self.robot.autonomous():
            robotData = self.robot.moveAuto()
            if robotData is not None:
                self.processRobotData(*robotData)

    def processRobotData(self, motion, measurements, reset):
        self.masterConn.publish(self.topics.sense.id, measurements)
        self.masterConn.particles_update(self.onUpdateParticlesResponse, motion, measurements, reset)


class RobotConnection(JsonRpcConnection):

    # Log messages
    LOG_NEW_CONNECTION = 'Received a new connection'
    LOG_POWER_SET = 'Power set to "{}"'
    LOG_MODE_SET = 'Mode set to "{}"'
    LOG_STATUS = "Retrieving robot status: ({} {})"

    def onInit(self):
        self.logInfo(RobotConnection.LOG_NEW_CONNECTION)
        self.masterConn = self.data.masterConn
        self.robot = self.data.robot

        self.topics = getTopicFactory()

        self.methodHandlers = {
            RobotMethod.POWER: self.handlePower,
            RobotMethod.MODE: self.handleMode,
            RobotMethod.STATUS: self.handleStatus
        }
        self.read()

    def handleStatus(self, msg):
        id = msg.get(jsonrpc.Key.ID, None)
        if id:
            status = self.robot.getStatus()
            self.logInfo(RobotConnection.LOG_STATUS.format(*status))
            self.masterConn.publish(self.topics.robot_status.id, *status)
            self.write(self.encoder.response(id, *status))

    def handleMode(self, msg):
        id = msg.get(jsonrpc.Key.ID, None)
        params = msg.get(jsonrpc.Key.PARAMS, [])
        if id and self.topics.mode.isValid(*params):
            try:
                self.robot.setMode(params[0])
                self.logInfo(RobotConnection.LOG_MODE_SET.format(self.robot.mode))
                self.masterConn.publish(self.topics.mode.id, self.robot.mode)
                self.write(self.encoder.response(id, self.robot.mode))
            except ValueError:
                pass

    def handlePower(self, msg):
        id = msg.get(jsonrpc.Key.ID, None)
        params = msg.get(jsonrpc.Key.PARAMS, [])
        if id and self.topics.power.isValid(*params):
            try:
                self.robot.setPower(params[0])
                self.logInfo(RobotConnection.LOG_POWER_SET.format(self.robot.power))
                self.masterConn.publish(self.topics.power.id, self.robot.power)
                self.write(self.encoder.response(id, self.robot.power))
            except ValueError:
                pass


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

    roboSim = RoboSim(start, grid, gridsize, lookupTable, delay)

    server = RobotServer(connection=RobotConnection, robot=roboSim, masterConn=conn)
    server.listen(serverPort)

    IOLoop.instance().start()


if __name__ == "__main__":
    main()