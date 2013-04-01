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

import jsonrpc

from topic import msgs
from util import signalHandler



class BetelbotMethod:
    # Methods supported by Betelbot server

    PUBLISH = 'publish'
    SUBSCRIBE = 'subscribe'
    REGISTER = 'register'
    LOCATE = 'locate'
    ONSUBSCRIBE = 'onsubscribe'


class BetelbotServer(TCPServer):
 
    def __init__(self, io_loop=None, ssl_options=None, **kwargs):
        logging.info('BetelBot Server is running')
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)
 
    def handle_stream(self, stream, address):
        BetelbotConnection(stream, address)


class BetelbotConnection(object):
 
    streamSet = set([])
    topics = msgs
    topicNames = dict((key,[]) for key in msgs.keys())
    services = {}
    pendingResponses = {}

    def __init__(self, stream, address, terminator='\0'):
        self.address = address
        self._logInfo('Received a new connection')
        self.terminator = terminator
        self.stream = stream
        self.stream.set_close_callback(self.onClose)
        self.stream.read_until(self.terminator, self.onReadLine)
        self.streamSet.add(self.stream)
        self.rpc = jsonrpc.Encoder()
 
    def onReadLine(self, data):
        self._logInfo('Reading a message')
        msg = json.loads(data.strip(self.terminator))
        method = msg[jsonrpc.Key.METHOD]
        params = msg[jsonrpc.Key.PARAMS]
        numParams = len(params)
        print msg
        if method == BetelbotMethod.PUBLISH and numParams > 1:
            self.publish(params[0], *params[1:])
        elif method == BetelbotMethod.SUBSCRIBE and numParams == 1:
            self.subscribe(params[0])
        elif method == BetelbotMethod.SERVICE and numParams == 1:
            self.service(params[0])
        elif method == BetelbotMethod.REQUEST and numParams > 1:
            id = msg[jsonrpc.Key.ID]
            self.request(id, params[0], *params[1:])
        elif method == BetelbotMethod.RESPONSE and numParams == 2:
            id = msg[jsonrpc.Key.ID]
            self.response(id, params[0], params[1]) 

        if not self.stream.reading():
            self.stream.read_until(self.terminator, self.onReadLine)

    def publish(self, topic, *args):
        if topic in self.topicNames and len(args) > 0:
            topicMeta = self.topics[topic]
            if topicMeta.isValid(args):
                subscribers = self.topicNames[topic]
                msg = '{}{}'.format(self.rpc.notification(
                    BetelbotMethod.ONSUBSCRIBE, topic, *args), self.terminator)
                for subscriber in subscribers:
                    subscriber.stream.write(msg, subscriber.onWriteComplete)

    def subscribe(self, topic):
        if topic in self.topicNames:
            self._logInfo('Subscribing to topic "{}"'.format(topic))
            self.topicNames[topic].append(self)

    def service(self, method):
        if method not in self.services:
            self._logInfo('Registering service "{}"'.format(method))
            self.services[method] = self

    def request(self, id, method, *params):
        print method
        if method in self.services:
            self.pendingResponses[id] = self
            service = self.services[method]
            msg = '{}{}'.format(self.rpc.request(id, method, *params), self.terminator)
            service.stream.write(msg, service.onWriteComplete)

    def response(self, id, result, error=None):
        if id in self.pendingResponses:
            client = self.pendingReponses.pop(id, None)
            msg = '{}{}'.format(self.rpc.response(id, result, error), self.terminator)
            service.stream.write(msg, service.onWriteComplete)

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
        
        for method in self.services:
            if self.services[method] == self:
                self._logInfo('Deregistering service "{}"'.format(method))        
                del self.services[method]

        for id in self.pendingResponses:
            if self.pendingResponses[id] == self:
                self._logInfo("Removing client's pending responses")        
                del self.pendingResponses[id] 

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

    server = BetelbotServer()
    server.listen(config.getint('server', 'port'))
    IOLoop.instance().start()


if __name__ == '__main__':
    main()
