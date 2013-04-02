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

from topic import getTopics
from util import signalHandler, Connection


class BetelbotMethod:
    # Methods supported by Betelbot server

    # - Method: publish
    # - Params: topic, data 
    # - Type: Notification    
    PUBLISH = 'publish'

    # - Type: Notification
    # - Method: subscribe
    # - Params: topic     
    SUBSCRIBE = 'subscribe'

    # - Type: Notification
    # - Method: notifysub
    # - Params: topic, data    
    NOTIFYSUB = 'notifysub'

    # Not implemented yet
    REGISTER = 'register'
    LOCATE = 'locate'


class BetelbotServer(TCPServer):
    # Master Betelbot server.
    #
    # Supported operations:
    #
    # - Manages publishers/subscribers
    # - Registers service methods
    # - Locates address of registered service methods for clients


    def __init__(self, topics, io_loop=None, ssl_options=None, **kwargs):
        logging.info('BetelBot Server is running')
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)
        self.conns = []
        self.topics = topics
        self.topicSubscribers = dict((key,[]) for key in topics.keys()) 
    
    def handle_stream(self, stream, address):
        BetelbotConnection(stream, address, self.topics, self.topicSubscribers)



class BetelbotConnection(Connection):
    # BetelbotConnection is created when a client connects to the Betelbot server.

    def __init__(self, stream, address, topics, topicSubscribers, terminator='\0', encoder=jsonrpc.Encoder()):
        super(BetelbotConnection, self).__init__(stream, address, terminator)        
        self.logInfo('Received a new connection')
        self.topics = topics
        self.topicSubscribers = topicSubscribers
        self.read()
        self.encoder = encoder
        self.methodHandlers = {
            BetelbotMethod.PUBLISH: self.handlePublish,
            BetelbotMethod.SUBSCRIBE: self.handleSubscribe
        }
 
    def onRead(self, data):
        # Overrides on onRead method to handle Betelbot server operations.

        self.logInfo('Reading a message')

        msg = json.loads(data.strip(self.terminator))
        method = msg.get(jsonrpc.Key.METHOD, None)
        if method in self.methodHandlers:
            self.methodHandlers[method](msg)
        self.read()

    def handlePublish(self, msg):
        # Handles "publish" operation.
        # 
        # Topics are validated for correct data types and then
        # data is sent to subscribers using notifySub operation.

        params = msg.get(jsonrpc.Key.PARAMS, None)
        if len(params) > 1:
            topic = params[0]
            data = params[1:]
            topicObj = self.topics.get(topic, None)        
            if topicObj and topicObj.isValid(*data):
                subscribers = self.topicSubscribers[topic]
                msg = self.encoder.notification(BetelbotMethod.NOTIFYSUB, topic, *data)
                for subscriber in subscribers:
                    subscriber.write(msg)

    def handleSubscribe(self, msg):
        # Handles "subscribe" operation.
        # 
        # Subscribers are added to topic list so they can
        # be notified later.

        params = msg.get(jsonrpc.Key.PARAMS, None)
        if len(params) == 1:
            topic = params[0]  
            if topic in self.topicSubscribers:
                self.logInfo('Subscribing to topic "{}"'.format(topic))
                self.topicSubscribers[topic].append(self)

    def onWrite(self):
        self.logInfo('Sending message')
        self.read()
 
    def onClose(self):
        # When a stream closes its connection, its subscriptions need 
        # to be removed.

        self.logInfo('Client quit')
        for topic in self.topicSubscribers:
            if self in self.topicSubscribers[topic]:
                self.logInfo('Unsubscribing client from topic "{}"'.format(topic))        
                self.topicSubscribers[topic].remove(self)

    def logInfo(self, msg):
        dt = datetime.now().strftime("%m-%d-%y %H:%M")
        logging.info('[%s, %s]%s', self.address[0], dt, msg)


def main():
    signal.signal(signal.SIGINT, signalHandler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    logger = logging.getLogger('')
    logger.setLevel(config.get('general', 'log_level'))

    server = BetelbotServer(getTopics())
    server.listen(config.getint('server', 'port'))
    
    IOLoop.instance().start()


if __name__ == '__main__':
    main()
