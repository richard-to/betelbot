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
    # Supported operations:
    # - Publish info to topics
    # - Subscribe to topics
    # - Register a service on server
    # - Locate a registered service
    #
    # Once a service is located, those operations become supported and
    # can be invoked the same as built-in operations.

    # Log messages
    LOG_CLIENT_CONNECT = 'Client connected'
    LOG_PUBLISH = 'Publishing to topic "{}"'
    LOG_SUBSCRIBE = 'Subscribing to topic "{}"'
    LOG_SUBSCRIBE_NOTIFY = 'Received subscription notification for "{}"'
    LOG_REGISTER = 'Registering service "{}"'
    LOG_LOCATE = 'Locating service "{}"'
    LOG_ALREADY_LOCATED = 'Service "{}" already located'
    LOG_ADD_SERVICE = 'Adding service "{}"'

    def onInit(self, **kwargs):
        # - subscription handlers manage subscriber callbacks
        # - method handlers currently only handle the NotifySub method

        self.logInfo(BetelbotClientConnection.LOG_CLIENT_CONNECT)
        self.subscriptionHandlers = {}
        self.methodHandlers = {
            BetelbotMethod.NOTIFYSUB: self.handleNotifySub
        }

    def publish(self, topic, *params):
        # Sends a "publish" notification to the server.
        #
        # Params are the data to be published to subscribers of topic.

        self.logInfo(BetelbotClientConnection.LOG_PUBLISH.format(topic))
        self.write(self.encoder.notification(BetelbotMethod.PUBLISH, topic, *params))

    def subscribe(self, topic, callback=None):
        # Sends a "subscribe" notification to the server.
        #
        # Anytime data gets published to the topic, client will be notified
        # and the specified callback will be invoked.

        self.logInfo(BetelbotClientConnection.LOG_SUBSCRIBE.format(topic))
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
        # The client can subscribe to the same topic multiple times and be
        # linked to different callbacks. If the callback no longer exists,
        # then it is ignored and removed from the callback list.
        #
        # The above case is useful for websocket connections that will be
        # sharing a single client. This allows each connection to receive
        # the callback and also can handle the case if a websocket connection
        # is disconnected.

        params = msg.get(jsonrpc.Key.PARAMS, None)
        if len(params) > 1:
            topic = params[0]
            data = params[1:]
            if topic in self.subscriptionHandlers:
                self.logInfo(BetelbotClientConnection.LOG_SUBSCRIBE_NOTIFY.format(topic))
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
        # one method at a time.

        self.logInfo(BetelbotClientConnection.LOG_REGISTER.format(method))
        self.write(self.encoder.notification(BetelbotMethod.REGISTER, method, port, host))

    def locate(self, callback, method):
        # Locates the address of a service if it does not exist
        #
        # The callback will return True if found and False if not. In the case
        # that the service has already been located, the callback is called immediately.

        if self.hasService(method) is False:
            self.logInfo(BetelbotClientConnection.LOG_LOCATE.format(method))
            id = self.idincrement.id()
            self.responseHandlers[id] = lambda msg: self.handleLocateResponse(callback, method, msg)
            self.write(self.encoder.request(id, BetelbotMethod.LOCATE, method))
        else:
            self.logInfo(BetelbotClientConnection.LOG_ALREADY_LOCATED.format(method))
            callback(method, True)

    def batchLocate(self, callback, methods):
        methodsDict = {}
        def onBatchLocateResponse(methodName, found):
            if methodName in methodsDict:
                methodsDict[methodName] = found

            if all(methodsDict[method] is True for method in methodsDict):
                callback(True)

        for method in methods:
            methodsDict[method] = None
            self.locate(onBatchLocateResponse, method)

    def onBatchLocateResponse(self, callback, methodsDict, found):

        if (self.conn.hasService(PathfinderMethod.SEARCH) and
                self.conn.hasService(ParticleFilterMethod.UPDATEPARTICLES)):
            self.conn.search(self.onSearchResponse,
                self.start, self.goal, PathfinderSearchType.BOTH)
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

        result = msg.get(jsonrpc.Key.RESULT, None)
        if result and len(result) == 2:
            port, host = result
            client = Client(host, port, jsonrpc.ClientConnection)
            self.addService(method, client)
            callback(method, True)
        else:
            callback(method, False)

    def hasService(self, method):
        # Helper method to test if a service methdod exists.

        return hasattr(self.__class__, method) and callable(getattr(self.__class__, method))

    def addService(self, method, client):
        # A service is dynamically added to BetelbotClientConnection, so
        # the method can be called as a normal method.

        self.logInfo(BetelbotClientConnection.LOG_ADD_SERVICE.format(method))

        def request(self, callback, *params):
            conn = client.connect()
            conn.request(callback, method, *params)

        request.__name__ = method
        setattr(self.__class__, request.__name__, request)


def main():
    pass


if __name__ == '__main__':
    main()