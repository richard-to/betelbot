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

from jsonrpc import JsonRpcConnection, JsonRpcServer
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

    # - Type: Notification
    # - Method: register
    # - Params: method, host, port 
    REGISTER = 'register'

    # - Type: Request
    # - Method: locate
    # - Params method
    # - Response: host, port
    LOCATE = 'locate'


class BetelbotServer(JsonRpcServer):
    # Master Betelbot server.
    #
    # Supported operations:
    #
    # - Manages publishers/subscribers
    # - Registers service methods
    # - Locates address of registered service methods for clients

    def onInit(self, **kwargs):
        logging.info('BetelBot Server is running')

        topics = kwargs.get('topics', getTopics())
        self.data['topics'] = topics
        self.data['topicSubscribers'] = dict((key,[]) for key in topics.keys())
        self.data['services'] = {}


class BetelbotConnection(JsonRpcConnection):
    # BetelbotConnection is created when a client connects to the Betelbot server.

    def onInit(self, **kwargs):
        self.logInfo('Received a new connection')
        
        self.topics = kwargs.get('topics', [])
        self.topicSubscribers = kwargs.get('topicSubscribers', {})
        self.services = kwargs.get('services', {})

        self.methodHandlers = {
            BetelbotMethod.PUBLISH: self.handlePublish,
            BetelbotMethod.SUBSCRIBE: self.handleSubscribe,
            BetelbotMethod.REGISTER: self.handleRegister,
            BetelbotMethod.LOCATE: self.handleLocate
        }
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

    def handleRegister(self, msg):
        # Handles "register" operation
        #
        # Registers a service method. If another client registers an existing 
        # method, then the host and port will be overwritten.
        #
        # Currently services can't be unregistered, even if the service disconnects

        params = msg.get(jsonrpc.Key.PARAMS, None)
        if len(params) == 3:
            method, host, port = params            
            self.logInfo('Registering service "{}"'.format(method))            
            self.services[method] = (host, port)

    def handleLocate(self, msg):
        # Handles "locate" operation
        #
        # The locate operation returns the address of service
        
        id = msg.get(jsonrpc.Key.ID, None)
        params = msg.get(jsonrpc.Key.PARAMS, None)
        
        if not id:
            # Send invalid params
            pass
        elif not len(params) == 1:
            # Send invalid params
            pass
        else:
            method = params[0]            
            self.logInfo('Locating service "{}"'.format(method))
            if method in self.services:          
                host, port = self.services[method]
                self.write(self.encoder.response(id, host, port))
            else:
                # Send invalid request
                pass    

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

    server = BetelbotServer(connection=BetelbotConnection, topics=getTopics())
    server.listen(config.getint('server', 'port'))
    
    IOLoop.instance().start()


if __name__ == '__main__':
    main()
