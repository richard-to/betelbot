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

from jsonconfig import JsonConfig
from topic import cmdTopic, moveTopic, senseTopic
from util import BetelBotClient, signalHandler


class BetelBotDriver(TCPServer):

    def __init__(self, client, io_loop=None, ssl_options=None, **kwargs):
        logging.info('BetelBot Driver is running')
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)
        self.client = client

    def handle_stream(self, stream, address):
        BetelBotDriverConnection(stream, address, self.client)


class BetelBotDriverConnection(object):

    streamSet = set([])

    def __init__(self, stream, address, client, terminator='\0'):
        self.address = address
        self.logInfo('BetelBot connected')
        self.terminator = terminator
        self.stream = stream
        self.stream.set_close_callback(self.onClose)
        self.stream.read_until(self.terminator, self.onReadLine)
        self.streamSet.add(self.stream)

        self.client = client
        self.client.subscribe(cmdTopic.id, self.onCmdForBot)

    def write(self, data):
        self.stream.write(data, self.onWriteComplete)

    def onReadLine(self, data):
        self.logInfo('Received data')
        tokens = data.strip().split(" ")

        if tokens[0] == 'm':
            self.client.publish(moveTopic.id, tokens[1])
        elif tokens[0] == 's':
            color = 'green' if int(tokens[1]) > 30 else 'red'
            self.client.publish(senseTopic.id, color)

        if not self.stream.reading():
            self.stream.read_until(self.terminator, self.onReadLine)

    def onWriteComplete(self):
        self.logInfo('Sending command')
        if not self.stream.reading():
            self.stream.read_until(self.terminator, self.onReadLine)

    def onClose(self):
        self.logInfo('BetelBot disconnected')
        self.streamSet.remove(self.stream)

    def logInfo(self, msg):
        dt = datetime.now().strftime("%m-%d-%y %H:%M")
        logging.info('[%s, %s]%s', self.address[0], dt, msg)

    def onCmdForBot(self, topic, data=None):
        self.write(data[0])


def main():
    signal.signal(signal.SIGINT, signalHandler)

    cfg = JsonConfig()

    logger = logging.getLogger('')
    logger.setLevel(cfg.general.logLevel)

    client = BetelBotClient('', cfg.server.port)

    server = BetelBotDriver(client)
    server.listen(cfg.robot.port)

    IOLoop.instance().start()


if __name__ == '__main__':
    main()