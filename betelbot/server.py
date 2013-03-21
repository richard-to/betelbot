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

from topic import msgs
from util import signalHandler


class BetelBotServer(TCPServer):
 
    def __init__(self, io_loop=None, ssl_options=None, **kwargs):
        logging.info('BetelBot Server is running')
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)
 
    def handle_stream(self, stream, address):
        BetelBotConnection(stream, address)


class BetelBotConnection(object):
 
    CMD_PUBLISH = 'publish'
    CMD_SUBSCRIBE = 'subscribe'

    streamSet = set([])
    topics = msgs
    topicNames = dict((key,[]) for key in msgs.keys())

    def __init__(self, stream, address):
        self.address = address
        self._logInfo('Received a new connection')

        self.stream = stream
        self.stream.set_close_callback(self.onClose)
        self.stream.read_until('\n', self.onReadLine)
        self.streamSet.add(self.stream)
 
    def onReadLine(self, data):
        self._logInfo('Reading a message')

        tokens = data.strip().split(" ")

        if len(tokens) > 2 and tokens[0] == self.CMD_PUBLISH:
            self.publish(tokens[1], *tokens[2:])
        elif len(tokens) == 2 and tokens[0] == self.CMD_SUBSCRIBE:
            self.subscribe(tokens[1])
        
        if not self.stream.reading():
            self.stream.read_until('\n', self.onReadLine)

    def publish(self, topic, *args):
        if topic in self.topicNames and len(args) > 0:
            topicMeta = self.topics[topic]
            if topicMeta.isValid(args):
                subscribers = self.topicNames[topic]
                for subscriber in subscribers:
                    subscriber.stream.write(
                        '{} {}\n'.format(topic, ' '.join(map(str, args))), 
                        subscriber.onWriteComplete)

    def subscribe(self, topic):
        if topic in self.topicNames:
            self._logInfo('Subscribing to topic "{}"'.format(topic))
            self.topicNames[topic].append(self)
    
    def onWriteComplete(self):
        self._logInfo('Sending message')

        if not self.stream.reading():
            self.stream.read_until('\n', self.onReadLine)
 
    def onClose(self):
        self._logInfo('Client quit')

        for topic in self.topicNames:
            if self in self.topicNames[topic]:
                self._logInfo('Unsubscribing client from topic "{}"'.format(topic))        
                self.topicNames[topic].remove(self)
        self.streamSet.remove(self.stream)

    def _logInfo(self, msg):
        dt = datetime.now().strftime("%m-%d-%y %H:%M")
        logging.info('[%s, %s]%s', self.address[0], dt, msg)


def main():
    signal.signal(signal.SIGINT, signal_handler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    logger = logging.getLogger('')
    logger.setLevel(config.get('general', 'log_level'))

    server = BetelBotServer()
    server.listen(config.getint('server', 'port'))
    IOLoop.instance().start()


if __name__ == '__main__':
    main()
