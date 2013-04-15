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
from topic.default import CmdTopic, MoveTopic, SenseTopic, PowerTopic, LocationTopic
from topic.default import ModeTopic, RobotStatusTopic, WaypointTopic
from util import Client, signalHandler


class RoboSim(object):
    # RoboSim simulates the real robot.

    # Error messages
    ERROR_POWER = "Invalid power value"
    ERROR_MODE = "Invalid mode value"
    ERROR_CMD = "Invalid cmd value"

    def __init__(self, start, grid, gridsize, lookupTable, delay=1):

        self.cmdTopic = CmdTopic()
        self.powerTopic = PowerTopic()
        self.modeTopic = ModeTopic()

        self.power = self.powerTopic.off
        self.mode = self.modeTopic.manual

        self.grid = grid
        self.gridsize = gridsize
        self.lookupTable = lookupTable
        self.delay = delay
        self.delta = Particle.DELTA

        self.moveIndex = 0

        self.start = start
        self.current = self.start
        self.goal = None

        self.currentDirection = None
        self.directions = None

        self.path = None
        self.cmd = None

    def moveCmd(self):

        if not self.on():
            return

        if self.cmd is None:
            return

        pathDelta = {
            self.cmdTopic.left: [0, -1],
            self.cmdTopic.down: [1, 0],
            self.cmdTopic.up: [-1, 0],
            self.cmdTopic.right: [0, 1]
        }
        newDelta = pathDelta[self.cmd]
        y = self.current[0] + newDelta[0]
        x = self.current[1] + newDelta[1]
        measurements = self.sense(self.cmd, y, x)
        self.current = [y, x]

        if self.currentDirection is None:
            self.currentDirection = self.cmd
        motion = convertToMotion(self.cmdTopic, self.currentDirection, self.cmd, self.gridsize)
        self.currentDirection = self.cmd
        self.cmd = None

        return [motion, measurements]

    def moveAuto(self):

        if not self.on():
            return

        if self.path is None:
            return

        time.sleep(self.delay)

        if self.moveIndex < len(self.path):

            dest = self.directions[self.moveIndex]
            if self.moveIndex > 0:
                start = self.directions[self.moveIndex - 1]
            else:
                start = dest
            motion = convertToMotion(self.cmdTopic, start, dest, self.gridsize)
            self.currentDirection = dest

            y, x = self.path[self.moveIndex]
            measurements = self.sense(dest, y, x)
            self.current = (y, x)

            self.moveIndex += 1

            return [motion, measurements]

    def sense(self, direction, y, x):

        delta = self.delta
        directions = self.cmdTopic.keys
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
        if self.powerTopic.isValid(power) is False:
            raise ValueError, ERROR_POWER
        self.power = power

    def setMode(self, mode):
        if self.modeTopic.isValid(mode) is False:
            raise ValueError, ERROR_MODE
        self.mode = mode
        if self.manual():
            self.path = None
            self.directions = None
            self.moveIndex = 0

    def setLocation(self, y, x):
        self.start = [y, x]
        self.current = self.start

    def setPath(self, path, directions):
        self.moveIndex = 0
        self.start = path.pop(0)
        self.current = self.start
        self.currentDirection = None
        self.directions = directions
        self.path = path

    def setCmd(self, cmd):
        if self.cmdTopic.isValid(cmd) is False:
            raise ValueError, ERROR_CMD
        self.cmd = cmd

    def on(self):
        return self.power == self.powerTopic.on

    def autonomous(self):
        return self.mode == self.modeTopic.autonomous

    def manual(self):
        return self.mode == self.modeTopic.manual


class RobotMethod(object):
    # Methods supported by Robot server

    # - Type: Notification
    # - Method: power
    # - Params: "on", "off"
    #
    # Power should be thought of as start/pause.
    # For instance, Betelbot mode will still toggle
    # from manual to auto when power is off, but the robot will
    # not listen to commands or move using computed path.
    #
    # When power is on, Betelbot will resume current path or begin
    # listening for commands again.
    POWER = 'power'

    # - Type: Notification
    # - Method: mode
    # - Params: "autonomous", "manual"
    #
    # In autonomous mode, robot listens for waypoint topic.
    # In manual mode, robot listens for cmd topic. Also waypoints and path are cleared.
    #
    # In both cases, power must be on for messages to be processed.
    MODE = 'mode'

    # - Type: Request
    # - Method: robotstatus
    # - Params: None
    # - Response: [power, mode]
    STATUS = 'robotstatus'


class RoboSimServer(JsonRpcServer):
    # RoboSim server is a service that simulates Betelbot

    # Log messages
    LOG_SERVER_RUNNING = 'RoboSim Server is running'

    # Accepted kwargs params
    PARAM_MASTER_CONN= 'masterConn'
    PARAM_ROBOT = 'robot'

    def onInit(self, **kwargs):
        logging.info(RoboSimServer.LOG_SERVER_RUNNING)

        defaults = {
            RoboSimServer.PARAM_MASTER_CONN: None,
            RoboSimServer.PARAM_ROBOT: None
        }

        self.cmdTopic = CmdTopic()
        self.powerTopic = PowerTopic()
        self.modeTopic = ModeTopic()
        self.senseTopic = SenseTopic()
        self.waypointTopic = WaypointTopic()
        self.locationTopic = LocationTopic()
        self.robotTopic = RobotStatusTopic()

        self.servicesFound = False

        self.data.update(defaults, True)
        self.data.update(kwargs, False)

        self.robot = self.data.robot
        self.masterConn = self.data.masterConn

    def onListen(self, port):
        self.port = port
        self.masterConn.batchLocate(self.onBatchLocateResponse, [
            ParticleFilterMethod.UPDATEPARTICLES,
            PathfinderMethod.SEARCH
        ])

    def onBatchLocateResponse(self, found):
        if found:
            self.servicesFound = True
            self.masterConn.subscribe(self.cmdTopic.id, self.onCmdPublished)
            self.masterConn.subscribe(self.locationTopic.id, self.onLocationPublished)
            self.masterConn.subscribe(self.waypointTopic.id, self.onWaypointPublished)
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
        if self.robot.on() and self.robot.manual():
            self.robot.setLocation(*data)

    def onWaypointPublished(self, topic, data):
        if self.robot.on() and self.robot.autonomous():
            self.masterConn.search(self.onSearchResponse,
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

    def processRobotData(self, motion, measurements):
        self.masterConn.publish(self.senseTopic.id, measurements)
        self.masterConn.updateparticles(self.onUpdateParticlesResponse, motion, measurements)


class RoboSimConnection(JsonRpcConnection):

    # Log messages
    LOG_NEW_CONNECTION = 'Received a new connection'
    LOG_POWER_SET = 'Power set to "{}"'
    LOG_MODE_SET = 'Mode set to "{}"'
    LOG_STATUS = "Retrieving robot status: ({} {})"

    def onInit(self):
        self.logInfo(RoboSimConnection.LOG_NEW_CONNECTION)

        self.masterConn = self.data.masterConn
        self.robot = self.data.robot

        self.powerTopic = PowerTopic()
        self.modeTopic = ModeTopic()
        self.robotTopic = RobotStatusTopic()

        self.methodHandlers = {
            RobotMethod.POWER: self.handlePower,
            RobotMethod.MODE: self.handleMode,
            RobotMethod.STATUS: self.handleStatus
        }
        self.read()

    def handleStatus(self, msg):
        status = self.robot.getStatus()
        self.logInfo(RoboSimConnection.LOG_STATUS.format(status))
        self.masterConn.publish(self.robotStatusTopic.id, status)

    def handleMode(self, msg):
        params = msg.get(jsonrpc.Key.PARAMS, None)
        if len(params) == 1:
            try:
                self.robot.setMode(params[0])
                self.logInfo(RoboSimConnection.LOG_MODE_SET.format(self.robot.mode))
                self.masterConn.publish(self.modeTopic.id, self.robot.mode)
            except ValueError:
                pass

    def handlePower(self, msg):
        params = msg.get(jsonrpc.Key.PARAMS, None)
        if len(params) == 1:
            try:
                self.robot.setPower(params[0])
                self.logInfo(RoboSimConnection.LOG_POWER_SET.format(self.robot.power))
                self.masterConn.publish(self.powerTopic.id, self.robot.power)
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

    server = RoboSimServer(connection=RoboSimConnection, robot=roboSim, masterConn=conn)
    server.listen(serverPort)

    IOLoop.instance().start()


if __name__ == "__main__":
    main()