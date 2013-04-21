#!/usr/bin/env python

import logging
import os
import re
import signal
import sys
from datetime import datetime

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.netutil import TCPServer

from client import BetelbotClientConnection
from config import JsonConfig, DictConfig
from topic.default import CmdTopic, MoveTopic, SenseTopic
from util import Client, Connection, signalHandler


class BetelbotDriver(TCPServer):

    # Log messages
    LOG_SERVER_RUNNING = 'BetelBot Driver is running'

    # Data params for Betelbot driver
    PARAM_CLIENT = 'client'

    def __init__(self, client, io_loop=None, ssl_options=None, **kwargs):
        logging.info(BetelbotDriver.LOG_SERVER_RUNNING)
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)
        self.data = DictConfig({BetelbotDriver.PARAM_CLIENT: client}, extend=True)

    def handle_stream(self, stream, address):
        BetelbotDriverConnection(stream, address, self.data)


class BetelbotDriverConnection(Connection):

    # Log messages
    LOG_CONNECTED = 'Betelbot connected'
    LOG_RECEIVED = 'Received data'

    def onInit(self):
        self.logInfo(BetelbotDriverConnection.LOG_CONNECTED)
        self.cmdTopic = CmdTopic()
        self.moveTopic = MoveTopic()
        self.client = data.client
        self.client.subscribe(self.cmdTopic.id, self.onCmdForBot)
        self.read()

    def onRead(self, data):
        self.logInfo(BetelbotDriverConnection.LOG_RECEIVED)
        tokens = data.strip().split(" ")
        if tokens[0] == 'm':
            self.client.publish(self.moveTopic.id, tokens[1])
        self.read()

    def onCmdForBot(self, topic, data=None):
        self.write(data[0])
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


def main():
    signal.signal(signal.SIGINT, signalHandler)

    cfg = JsonConfig()

    logger = logging.getLogger('')
    logger.setLevel(cfg.general.logLevel)

    client = Client('', cfg.server.port, BetelbotClientConnection)
    conn = client.connect()

    server = BetelbotDriver(client)
    server.listen(cfg.robot.port)

    IOLoop.instance().start()


if __name__ == '__main__':
    main()