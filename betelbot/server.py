#!/usr/bin/env python

import ConfigParser
import json
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
from util import JsonRpcEncoder, JsonRpcProp, PubSubMethod, signalHandler


class BetelBotServer(TCPServer):
 
    def __init__(self, io_loop=None, ssl_options=None, **kwargs):
        logging.info('BetelBot Server is running')
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)
 
    def handle_stream(self, stream, address):
        BetelBotConnection(stream, address)


class BetelBotConnection(object):
 
    streamSet = set([])
    topics = msgs
    topicNames = dict((key,[]) for key in msgs.keys())

    def __init__(self, stream, address, terminator='\0'):
        self.address = address
        self._logInfo('Received a new connection')
        self.terminator = terminator
        self.stream = stream
        self.stream.set_close_callback(self.onClose)
        self.stream.read_until(self.terminator, self.onReadLine)
        self.streamSet.add(self.stream)
        self.rpc = JsonRpcEncoder()
 
    def onReadLine(self, data):
        self._logInfo('Reading a message')
        msg = json.loads(data.strip(self.terminator))
        method = msg[JsonRpcProp.METHOD]
        params = msg[JsonRpcProp.PARAMS]
        numParams = len(params)
        if numParams > 1 and method == PubSubMethod.PUBLISH:
            self.publish(params[0], *params[1:])
        elif numParams == 1 and method == PubSubMethod.SUBSCRIBE:
            self.subscribe(params[0])      
        if not self.stream.reading():
            self.stream.read_until(self.terminator, self.onReadLine)

    def publish(self, topic, *args):
        if topic in self.topicNames and len(args) > 0:
            topicMeta = self.topics[topic]
            if topicMeta.isValid(args):
                subscribers = self.topicNames[topic]
                msg = '{}{}'.format(self.rpc.notification(topic, *args), self.terminator)
                for subscriber in subscribers:
                    subscriber.stream.write(msg, subscriber.onWriteComplete)

    def subscribe(self, topic):
        if topic in self.topicNames:
            self._logInfo('Subscribing to topic "{}"'.format(topic))
            self.topicNames[topic].append(self)
    
    def onWriteComplete(self):
        self._logInfo('Sending message')
        if not self.stream.reading():
            self.stream.read_until(self.terminator, self.onReadLine)
 
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
    signal.signal(signal.SIGINT, signalHandler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    logger = logging.getLogger('')
    logger.setLevel(config.get('general', 'log_level'))

    server = BetelBotServer()
    server.listen(config.getint('server', 'port'))
    IOLoop.instance().start()


if __name__ == '__main__':
    main()
