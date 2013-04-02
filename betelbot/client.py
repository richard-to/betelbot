import json
import socket

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream

import jsonrpc

from jsonrpc import JsonRpcConnection
from master import BetelbotMethod
from util import Client


class BetelbotClientConnection(JsonRpcConnection):
    # Betelbot client connections are persistent tcp connections
    # that send/receive messages from Betelbot server using JSON-RPC 2.0.
    #
    # In other words is a peer-to-peer connection, which may not be part of 
    # the JSON-RPC 2.0 protocol.
    #
    # Supported operations:
    # - Publish info to topics
    # - Subscribe to topics
    # - Register a service on server
    # - Locate a registered service
    #
    # If service requests/notifications are required, use the connection class
    # in jsonrpc module.

    def __init__(self, stream, address):
        super(BetelbotClientConnection, self).__init__(stream, address)
        self.subscriptionHandlers = {}
        self.methodHandlers = {
            BetelbotMethod.NOTIFYSUB: self.handleNotifySub
        }

    def publish(self, topic, *params):
        # Sends a "publish" notification to the server.
        #
        # Params are the data to be published to subscribers of topic.

        self.write(self.encoder.notification(BetelbotMethod.PUBLISH, topic, *params))

    def subscribe(self, topic, callback=None):
        # Sends a "subscribe" notification to the server.
        #
        # Anytime data gets published to the topic, client will be notified 
        # and the specified callback will be invoked.

        if topic not in self.subscriptionHandlers:
            self.subscriptionHandlers[topic] = []
        
        self.subscriptionHandlers[topic].append(callback)
        self.write(self.encoder.notification(BetelbotMethod.SUBSCRIBE, topic))

    def register(self, method, host, port):
        # Registers a service with the server. Information needed is method name,
        # host and port for the servicee.
        #
        # Currently services are just methods rather than a set of methods.
        #
        # Multiple services can be registered by the server by registering
        # a method at a time.
     
        self.write(self.encoder.notification(BetelbotMethod.REGISTER, method, host, port))

    def locate(self, id, method, callback=None):
        # Locate the address of a service

        self.responseHandlers[id] = callback
        self.write(self.encoder.request(id, BetelbotMethod.LOCATE, method))

    def handleNotifySub(self, msg):
        # Handles subscription notifcation.
        #
        # The subscription handler will send this data along to local
        # subscribers.
        #
        # The reason that there can be multiple subscribers to the same 
        # message is in the case of a web server that has multiple websocket
        # connections.

        params = msg.get(jsonrpc.Key.PARAMS, None)
        if len(params) > 1:
            topic = params[0]
            data = params[1:]
            if topic in self.subscriptionHandlers:
                for subscriber in self.subscriptionHandlers[topic]:
                    subscriber(topic, data)


if __name__ == '__main__':
    pass