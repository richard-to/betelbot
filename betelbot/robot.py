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