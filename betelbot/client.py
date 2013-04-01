import json
import socket

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream

from jsonrpc import JsonRpcProp, JsonRpcEncoder
from server import BetelbotMethod

class BetelbotClient:
    # Betelbot clients interact with Betelbot servers using JSON-RPC 2.0.
    #
    # Features:
    # - Publish data on topics
    # - Subscribe to topics
    # - Register a service on server
    # - Locate a service
    # - Send requests to service
    # - Receive responses from a service

    def __init__(self, host='', port=8888, terminator='\0'):
        # Initializes socket to connect with server.
        # 
        # The nullbyte is the default line terminator. Chosen because 
        # it will be least likely to interfere with JSON-RPC.

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.stream = IOStream(sock)
        self.stream.connect((host, port))
        self.subscriptionHandlers = {}
        self.serviceHandlers = {}
        self.pendingReponses = {}
        self.terminator = terminator
        self.rpc = JsonRpcEncoder()

    def publish(self, topic, *params):
        # Sends a "publish" notification to the server.
        #
        # Params are the data to be published to subscribers of topic.

        self.write(self.rpc.notification(BetelbotMethod.PUBLISH, topic, *params))

    def subscribe(self, topic, callback=None):
        # Sends a "subscribe" notification to the server.
        #
        # Anytime data gets published to the topic, client will be notified 
        # and the specified callback will be invoked.

        if topic not in self.subscriptionHandlers:
            self.subscriptionHandlers[topic] = []
        
        self.subscriptionHandlers[topic].append(callback)
        self.write(self.rpc.notification(BetelbotMethod.SUBSCRIBE, topic))

        if not self.stream.reading():
            self.stream.read_until(self.terminator, self.onReadLine)

    def register(self, method, callback=None):
        # Registers a service with the server. Currently services 
        # are just methods rather than a set of methods.
        #
        # Multiple services can be registered by the server by registering
        # a method at a time.
        #
        # The callback invoked should be capable of handling requests
        # and sending back a response.

        self.serviceHandlers[method] = callback      
        self.write(self.rpc.notification(BetelbotMethod.REGISTER, method))
        
        if not self.stream.reading():
            self.stream.read_until(self.terminator, self.onReadLine)        
    
    """
    def request(self, id, method, callback=None, *params):
        # Sends a request to a service and 
        self.pendingReponses[id] = callback
        self.write(self.rpc.request(id, BetelbotMethod.REQUEST, method, *params))
        if not self.stream.reading():
            self.stream.read_until(self.terminator, self.onReadLine)        

    def response(self, id, result, error=None):
        self.write(self.rpc.response(id, result, error))
        if not self.stream.reading():
            self.stream.read_until(self.terminator, self.onReadLine)        
    """

    def write(self, msg):
        # Lower-level method to sends msg to the server.
        #
        # Should not be called directly since this method expects 
        # message to follow JSON-RPC format.

        self.stream.write("{}{}".format(msg, self.terminator))

    def onReadLine(self, data):
        msg = json.loads(data.strip(self.terminator))
        id = msg[JsonRpcProp.ID]

        if id is None:
            self.onNotification(msg)
        elif JsonRpcProp.METHOD in msg:
            self.onRequest(msg)
        elif id in self.pendingRequests:
            self.onResponseon(msg)
            
        if not self.stream.reading():
            self.stream.read_until(self.terminator, self.onReadLine)

    def onNotification(self, msg):
        id = msg[JsonRpcProp.ID]        
        topic = msg[JsonRpcProp.METHOD]
        for subscriber in self.subscriptionHandlers[topic]:
            subscriber(topic, msg[JsonRpcProp.PARAMS])

    def onRequest(self, msg):
        id = msg[JsonRpcProp.ID]        
        method = msg[JsonRpcProp.METHOD]
        if method in self.serviceHandlers:
            self.serviceHandlers[method](id, method, msg[JsonRpcProp.PARAMS])

    def onResponse(self, msg):
        result = msg[JsonRpcProp.RESULT]
        error = msg[JsonRpcProp.ERROR]
        callback = self.pendingReponses.pop(id, None)
        callback(id, result, error)

    def close():
        # Disconnects client from server.

        self.stream.close()


if __name__ == '__main__':
    pass