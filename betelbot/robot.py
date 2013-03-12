#!/usr/bin/env python

import ConfigParser
import logging
import os
import re
import signal
import sys
from datetime import datetime

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.netutil import TCPServer

from topic import cmdTopic
from util import PubSubClient, signal_handler


class BetelBotDriver(TCPServer):
 
    def __init__(self, client, io_loop=None, ssl_options=None, **kwargs):
        logging.info('BetelBot Driver is running')        
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)
        self.subscribers = []
        self.client = client

    def handle_stream(self, stream, address):
        BetelBotDriverConnection(stream, address, self.client)


class BetelBotDriverConnection(object):
 
    streamSet = set([])

    def __init__(self, stream, address, client):
        self._logInfo('BetelBot connected')
        self.address = address

        self.stream = stream        
        self.stream.set_close_callback(self._onClose)
        self.stream.read_until('\n', self._onReadLine)
        self.streamSet.add(self.stream)

        self.client = client
        self.client.subscribe(cmdTopic.id, self._onCmdForBot)

    def write(self, data):
        self.stream.write(data, self._onWriteComplete)

    def _onReadLine(self, data):
        self._logInfo('Received data')
        if not self.stream.reading():
            self.stream.read_until('\n', self._onReadLine)

    def _onWriteComplete(self):
        self._logInfo('Sending command')
        if not self.stream.reading():
            self.stream.read_until('\n', self._onReadLine)
    
    def _onClose(self):
        self._logInfo('BetelBot disconnected')
        self.streamSet.remove(self.stream)

    def _logInfo(self, msg):
        dt = datetime.now().strftime("%m-%d-%y %H:%M")
        logging.info('[%s, %s]%s', self.address[0], dt, msg)

    def _onCmdForBot(self, topic, data=None):
        self.write(data[0])


def main():
    signal.signal(signal.SIGINT, signal_handler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    logger = logging.getLogger('')
    logger.setLevel(config.get('general', 'log_level'))

    client = PubSubClient('', config.getint('server', 'port'))

    server = BetelBotDriver(client, msgs)
    server.listen(config.getint('robot', 'port'))

    IOLoop.instance().start()


if __name__ == '__main__':
    main()