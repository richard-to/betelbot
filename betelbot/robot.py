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

from topic import msgs
from util import PubSubClient, signal_handler

topics = msgs
topicNames = dict((key,[]) for key in msgs.keys())

subcribers = []


class BetelBotDriver(TCPServer):
 
    def __init__(self, io_loop=None, ssl_options=None, **kwargs):
        logging.info('BetelBot Driver is running')
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)
 
    def handle_stream(self, stream, address):
        BetelBotDriverConnection(stream, address)


class BetelBotDriverConnection(object):
 
    streamSet = set([])

    def __init__(self, stream, address):
        subcribers.append(self)
        self.stream = stream
        self.address = address
        self.streamSet.add(self.stream)
        self.stream.set_close_callback(self._onClose)
        self.stream.read_until('\n', self._onReadLine)
        self._logInfo('BetelBot connected')
 
    def write(self, data):
        self.stream.write(data, self._onWriteComplete);
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



def callback(topic, data=None):
    for c in subcribers:
        c.write(data[0])


config = ConfigParser.SafeConfigParser()
config.read('config/default.cfg')

logger = logging.getLogger('')
logger.setLevel(config.get('general', 'log_level'))

signal.signal(signal.SIGINT, signal_handler)

server = BetelBotDriver()
server.listen(config.getint('robot', 'port'))

client = PubSubClient('', config.getint('server', 'port'))
client.subscribe('move', callback)

IOLoop.instance().start()