#!/usr/bin/env python

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
from config import JsonConfig
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

    # Accepted kwargs params
    PARAM_TOPICS = 'topics'
    PARAM_TOPIC_SUBSCRIBERS = 'topicSubscribers'

    # Log messages
    LOG_SERVER_RUNNING = 'BetelBot Server is running'

    def onInit(self, **kwargs):
        logging.info(BetelbotServer.LOG_SERVER_RUNNING)

        topics = kwargs.get(BetelbotServer.PARAM_TOPICS, getTopics())
        topicSubscribers = dict((key,[]) for key in topics.keys())
        defaults = {
            BetelbotServer.PARAM_TOPICS: topics,
            BetelbotServer.PARAM_TOPIC_SUBSCRIBERS: topicSubscribers
        }
        self.data.update(defaults, True)
        self.data.update(kwargs, False)


class BetelbotConnection(JsonRpcConnection):
    # BetelbotConnection is created when a client connects to the Betelbot server.

    # Log messages
    LOG_NEW_CONNECTION = 'Received a new connection'
    LOG_PUBLISH = 'Publishing to topic "{}"'
    LOG_SUBSCRIBE = 'Subscribing to topic "{}"'
    LOG_REGISTER = 'Registering service "{}"'
    LOG_LOCATE = 'Locating service "{}"'
    LOG_UNSUBSCRIBE = 'Unsubscribing client from topic "{}"'

    def onInit(self):
        # Initializes BetelbotConnection with method handlers for
        # publish, subscribe, register, locate
        #
        # Adds dictionaries for registered topics and services.

        self.logInfo(BetelbotConnection.LOG_NEW_CONNECTION)
        self.topics = self.data.topics
        self.topicSubscribers = self.data.topicSubscribers
        self.services = {}

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
                self.logInfo(BetelbotConnection.LOG_PUBLISH.format(topic))
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
                self.logInfo(BetelbotConnection.LOG_SUBSCRIBE.format(topic))
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
            method, port, host = params
            self.logInfo(BetelbotConnection.LOG_REGISTER.format(method))
            self.services[method] = (port, host)

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
            self.logInfo(BetelbotConnection.LOG_LOCATE.format(method))
            if method in self.services:
                port, host = self.services[method]
                self.write(self.encoder.response(id, port, host))
            else:
                # Send invalid request
                pass

    def onWrite(self):
        # After writing completes, need to make sure we start reading again.
        # Calls the read method to make sure.

        self.read()

    def onClose(self):
        # When a stream closes its connection, its subscriptions need
        # to be removed.

        for topic in self.topicSubscribers:
            if self in self.topicSubscribers[topic]:
                self.logInfo(BetelbotConnection.LOG_UNSUBSCRIBE.format(topic))
                self.topicSubscribers[topic].remove(self)


def main():
    signal.signal(signal.SIGINT, signalHandler)

    cfg = JsonConfig()

    logger = logging.getLogger('')
    logger.setLevel(cfg.general.logLevel)

    server = BetelbotServer(connection=BetelbotConnection, topics=getTopics())
    server.listen(cfg.server.port)

    IOLoop.instance().start()


if __name__ == '__main__':
    main()
