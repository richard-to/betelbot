#!/usr/bin/env python

import abc
import logging
import os
import re
import signal
import sys
import time
from datetime import datetime

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.netutil import TCPServer

import jsonrpc

from client import BetelbotClientConnection
from config import JsonConfig, DictConfig
from jsonrpc import JsonRpcServer, JsonRpcConnection
from pathfinder import PathfinderMethod, PathfinderSearchType
from particle import Particle, ParticleFilterMethod, convertToMotion, normalizeCmd
from topic import getTopicFactory
from util import Client, Connection, signalHandler


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
    PARAM_DRIVER = 'driver'

    def onInit(self, **kwargs):
        logging.info(RobotServer.LOG_SERVER_RUNNING)

        defaults = {
            RobotServer.PARAM_MASTER_CONN: None,
            RobotServer.PARAM_DRIVER: None
        }

        self.topics = getTopicFactory()

        self.servicesFound = False

        self.data.update(defaults, True)
        self.data.update(kwargs, False)

        self.driver = self.data.driver
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
        if self.driver.on() and self.driver.manual():
            self.driver.setCmd(cmd)
            self.driver.moveCmd(self.processRobotData)

    def onLocationPublished(self, topic, data):
        if self.driver.on() and self.driver.manual() and self.driver.location.isValid(*data):
            self.driver.setLocation(*data)

    def onWaypointPublished(self, topic, data):
        if self.driver.on() and self.driver.autonomous() and self.topics.waypoint.isValid(*data):
            self.masterConn.pathfinder_search(self.onSearchResponse,
                data[0], data[1], PathfinderSearchType.BOTH)

    def onSearchResponse(self, result):
        self.driver.setPath(*result)
        self.driver.moveAuto(self.processRobotData)

    def onUpdateParticlesResponse(self, result):
        if self.driver.on() and self.driver.autonomous():
            self.driver.moveAuto(self.processRobotData)

    def processRobotData(self, motion, measurements, reset):
        if motion is not None and measurements is not None and reset is not None:
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
        self.driver = self.data.driver

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
            status = self.driver.getStatus()
            self.logInfo(RobotConnection.LOG_STATUS.format(*status))
            self.masterConn.publish(self.topics.robot_status.id, *status)
            self.write(self.encoder.response(id, *status))

    def handleMode(self, msg):
        id = msg.get(jsonrpc.Key.ID, None)
        params = msg.get(jsonrpc.Key.PARAMS, [])
        if id and self.topics.mode.isValid(*params):
            try:
                self.driver.setMode(params[0])
                self.logInfo(RobotConnection.LOG_MODE_SET.format(self.driver.mode))
                self.masterConn.publish(self.topics.mode.id, self.driver.mode)
                self.write(self.encoder.response(id, self.driver.mode))
            except ValueError:
                pass

    def handlePower(self, msg):
        id = msg.get(jsonrpc.Key.ID, None)
        params = msg.get(jsonrpc.Key.PARAMS, [])
        if id and self.topics.power.isValid(*params):
            try:
                self.driver.setPower(params[0])
                self.logInfo(RobotConnection.LOG_POWER_SET.format(self.driver.power))
                self.masterConn.publish(self.topics.power.id, self.driver.power)
                self.write(self.encoder.response(id, self.driver.power))
            except ValueError:
                pass


class RobotDriver(object):

    __metaclass__ = abc.ABCMeta

    # Error messages
    ERROR_POWER = "Invalid power value"
    ERROR_MODE = "Invalid mode value"
    ERROR_CMD = "Invalid cmd value"
    ERROR_NO_CONNECTION = "No connection to Betelbot"

    def __init__(self, start):
        self.start = start
        self.topics = getTopicFactory()

        self.power = self.topics.power.off
        self.mode = self.topics.mode.manual

        self.delta = Particle.DELTA

        self.setLocation(*start)
        self.moveIndex = 0

    @abc.abstractmethod
    def moveCmd(self, callback):
        return

    @abc.abstractmethod
    def moveAuto(self, callback):
        return

    def getStatus(self):
        return [self.power, self.mode]

    def setPower(self, power):
        if self.topics.power.isValid(power) is False:
            raise ValueError, RobotDriverAbstract.ERROR_POWER
        self.power = power

    def setMode(self, mode):
        if self.topics.mode.isValid(mode) is False:
            raise ValueError, RobotDriverAbstract.ERROR_MODE

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
            raise ValueError, RobotDriverAbstract.ERROR_CMD
        self.resetPath()
        self.cmd = cmd

    def on(self):
        return self.power == self.topics.power.on

    def autonomous(self):
        return self.mode == self.topics.mode.autonomous

    def manual(self):
        return self.mode == self.topics.mode.manual


class BetelbotDriver(RobotDriver):

    def __init__(self, start, dist, server):
        super(BetelbotDriver, self).__init__(start)
        self.server = server
        self.dist = dist

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
        self.current = [y, x]

        reset = False
        if self.currentDirection is None:
            self.currentDirection = self.cmd
            reset = True
        motion = convertToMotion(cmdTopic, self.currentDirection, self.cmd, self.dist)
        self.currentDirection = self.cmd

        cmd = self.cmd
        self.cmd = None

        formatMeasurements = self.formatMeasurements
        self.server.connection.sense(
            lambda Z: callback(motion, formatMeasurements(cmd, Z), reset),
            normalizeCmd(self.topics.cmd, motion[0]))


    def moveAuto(self, callback):

        if not self.on() or self.path is None:
            callback(None, None, None)
            return

        if self.moveIndex < len(self.path):

            time.sleep(3)

            reset = False
            dest = self.directions[self.moveIndex]
            if self.moveIndex > 0:
                start = self.directions[self.moveIndex - 1]
            else:
                start = dest
                reset = True
            motion = convertToMotion(self.topics.cmd, start, dest, self.dist)
            self.currentDirection = dest

            y, x = self.path[self.moveIndex]
            self.current = (y, x)
            self.moveIndex += 1

            formatMeasurements = self.formatMeasurements
            self.server.connection.sense(
                lambda Z: callback(motion, formatMeasurements(dest, Z), reset),
                normalizeCmd(self.topics.cmd, motion[0]))

    def formatMeasurements(self, cmd, Z):
        cmdTopic = self.topics.cmd
        if cmd == cmdTopic.left:
            measurements = [Z[1], Z[2], Z[0], None]
        elif cmd == cmdTopic.down:
            measurements = [Z[2], None, Z[1], Z[0]]
        elif cmd == cmdTopic.up:
            measurements = [Z[0], Z[1], None, Z[2]]
        elif cmd == cmdTopic.right:
            measurements = [None, Z[0], Z[2], Z[1]]
        return measurements

    def setPower(self, power):
        if self.server.connection is None:
            raise ValueError, BetelbotDriver.ERROR_NO_CONNECTION

        if self.topics.power.isValid(power) is False:
            raise ValueError, BetelbotDriver.ERROR_POWER

        self.power = power


class BetelbotDriverServer(TCPServer):

    # Log messages
    LOG_SERVER_RUNNING = 'BetelBot Driver is running'
    LOG_CONNECTION_REFUSED = 'Only one connection is allowed at a time'

    def __init__(self, io_loop=None, ssl_options=None, **kwargs):
        logging.info(BetelbotDriverServer.LOG_SERVER_RUNNING)
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)
        self.connection = None

    def handle_stream(self, stream, address):
        if self.connection is None:
            self.connection = BetelbotDriverConnection(stream, address, None)
        else:
            logging.info(BetelbotDriverServer.LOG_CONNECTION_REFUSED)
            stream.close()


class BetelbotDriverConnection(Connection):

    # Log messages
    LOG_CONNECTED = 'Betelbot connected'
    LOG_RECEIVED = 'Received data'

    SENSOR_READINGS = 3

    MSG_STRIP = " \x00"
    MSG_SPLIT = " "

    def onInit(self):
        self.logInfo(BetelbotDriverConnection.LOG_CONNECTED)
        self.callback = None
        self.read()

    def onRead(self, data):
        self.logInfo(BetelbotDriverConnection.LOG_RECEIVED)
        data = data.strip(BetelbotDriverConnection.MSG_STRIP)
        tokens = data.split(BetelbotDriverConnection.MSG_SPLIT)
        tokens = [int(token) for token in tokens]
        if len(tokens) == BetelbotDriverConnection.SENSOR_READINGS and self.callback is not None:
            self.callback(tokens)
        self.read()

    def sense(self, callback, cmd):
        self.callback = callback
        print cmd
        self.write(cmd)


def main():
    signal.signal(signal.SIGINT, signalHandler)

    cfg = JsonConfig()

    logger = logging.getLogger('')
    logger.setLevel(cfg.general.logLevel)

    client = Client('', cfg.server.port, BetelbotClientConnection)
    conn = client.connect()

    driverServer = BetelbotDriverServer()
    driverServer.listen(cfg.robot.driverPort)
    driver = BetelbotDriver(cfg.robot.start, cfg.robot.dist, driverServer)

    server = RobotServer(connection=RobotConnection, driver=driver, masterConn=conn)
    server.listen(cfg.robot.port)

    IOLoop.instance().start()


if __name__ == '__main__':
    main()