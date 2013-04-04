import json
import socket

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream

import jsonrpc

from jsonrpc import JsonRpcConnection, JsonRpcConnection
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
    
    def onInit(self, **kwargs):
        self.logInfo('Client connected')
        self.subscriptionHandlers = {}
        self.serviceHandlers = {}
        self.methodHandlers = {
            BetelbotMethod.NOTIFYSUB: self.handleNotifySub
        }

    def publish(self, topic, *params):
        # Sends a "publish" notification to the server.
        #
        # Params are the data to be published to subscribers of topic.

        self.logInfo('Publishing to topic "{}"'.format(topic))
        self.write(self.encoder.notification(BetelbotMethod.PUBLISH, topic, *params))

    def subscribe(self, topic, callback=None):
        # Sends a "subscribe" notification to the server.
        #
        # Anytime data gets published to the topic, client will be notified 
        # and the specified callback will be invoked.

        if topic not in self.subscriptionHandlers:
            self.subscriptionHandlers[topic] = []

        self.logInfo('Subscribing to topic "{}"'.format(topic))  
        self.subscriptionHandlers[topic].append(callback)
        self.write(self.encoder.notification(BetelbotMethod.SUBSCRIBE, topic))

    def register(self, method, port, host=''):
        # Registers a service with the server. Information needed is method name,
        # host and port for the servicee.
        #
        # Currently services are just methods rather than a set of methods.
        #
        # Multiple services can be registered by the server by registering
        # a method at a time.
     
        self.logInfo('Registering service "{}"'.format(method))     
        self.write(self.encoder.notification(BetelbotMethod.REGISTER, method, port, host))

    def locate(self, id, method, callback=None):
        # Locate the address of a service

        if method not in self.serviceHandlers:
            self.logInfo('Locating to service "{}"'.format(method))
            self.responseHandlers[id] = lambda msg: self.handleLocate(method, msg, callback)
            self.write(self.encoder.request(id, BetelbotMethod.LOCATE, method))
        else:
            self.logInfo('Service "{}" already located'.format(method))

    def handleLocate(self, method, msg, callback):
        result = msg.get(jsonrpc.Key.RESULT, None)
        if result and len(result) == 2:
            port, host = result
            client = Client(host, port, jsonrpc.ClientConnection)
            self.addService(method, client)
            callback(True)
        else:
            callback(False)
     
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
            self.logInfo('Received subscription notification for "{}"'.format(topic))            
            if topic in self.subscriptionHandlers:
                for subscriber in self.subscriptionHandlers[topic]:
                    subscriber(topic, data)

    def hasService(self, method):
        return hasattr(self.__class__, method) and callable(getattr(self.__class__, method))
    
    def addService(self, methodName, client):
        
        def request(self, callback, id, *params):
            conn = client.connect()
            self.serviceHandlers[id] = (conn, methodName, callback)
            conn.request(self.handleServiceResponse, id, methodName, *params) 

        self.logInfo('Adding service "{}"'.format(methodName))
        request.__name__ = methodName
        setattr(self.__class__, request.__name__, request)

    def handleServiceResponse(self, msg):
        id = msg.get(jsonrpc.Key.ID, None)
        result = msg.get(jsonrpc.Key.RESULT, None)

        if id and id in self.serviceHandlers and result:
            conn, method, callback = self.serviceHandlers[id]
            self.logInfo('Received response from service "{}"'.format(method))
            callback(id, method, result)
            del self.serviceHandlers[id]


def main():
    pass


if __name__ == '__main__':
    main()