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
        # For the BetelbotClientConnections, a few handlers need to be initialized.
        #
        # - subscription handlers are manage subscriber callbacks
        # - method handlers currently only handle the NotifySub method

        self.logInfo('Client connected')
        self.subscriptionHandlers = {}
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
        self.logInfo('Subscribing to topic "{}"'.format(topic)) 
        if topic not in self.subscriptionHandlers:
            self.subscriptionHandlers[topic] = []
            self.write(self.encoder.notification(BetelbotMethod.SUBSCRIBE, topic))
        self.subscriptionHandlers[topic].append(callback)

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
                self.logInfo('Received subscription notification for "{}"'.format(topic))
                disconnected = []
                for subscriber in self.subscriptionHandlers[topic]:
                    try:
                        subscriber(topic, data)
                    except AttributeError:
                        disconnected.append(subscriber)

                for subscriber in disconnected:
                    self.subscriptionHandlers[topic].remove(subscriber)

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

    def locate(self, callback, method):
        # Locates the address of a service if it does not exist
        #
        # The callback will return True if found and False if not. In the case
        # that the service has been located, the callback is called immediately.

        if self.hasService(method) is False:
            self.logInfo('Locating to service "{}"'.format(method))            
            id = self.idincrement.id()
            self.responseHandlers[id] = lambda msg: self.handleLocateResponse(callback, method, msg)
            self.write(self.encoder.request(id, BetelbotMethod.LOCATE, method))
        else:
            self.logInfo('Service "{}" already located'.format(method))            
            callback(True)

    def handleLocateResponse(self, callback, method, msg):
        # When the locate method receives a response, this callback will be
        # invoked so that we can add the service to the client.
        #
        # Services are individual clients that create their own connections.
        # These connections send a request and then close the connection once a 
        # response is received.
        #
        # Service methods are dynamically added to BetelbotClientConnection 
        # and can be called like a regular method.
        #
        # Example: conn.search(callback, [1,2], [2,3])
        #
        # Afterwards the user callback will be invoked with True/False.

        result = msg.get(jsonrpc.Key.RESULT, None)
        if result and len(result) == 2:
            port, host = result
            client = Client(host, port, jsonrpc.ClientConnection)
            self.addService(method, client)
            callback(True)
        else:
            callback(False)

    def hasService(self, method):
        # Helper method to test if a 
        
        return hasattr(self.__class__, method) and callable(getattr(self.__class__, method))
    
    def addService(self, method, client):
        # A service is dynamically added to BetelbotClientConnection, so
        # the method can be called naturally.

        self.logInfo('Adding service "{}"'.format(method))

        def request(self, callback, *params):
            conn = client.connect()
            conn.request(callback, method, *params) 

        request.__name__ = method
        setattr(self.__class__, request.__name__, request)          


def main():
    pass


if __name__ == '__main__':
    main()