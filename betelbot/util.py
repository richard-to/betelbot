import fcntl
import json
import os
import select
import signal
import socket
import sys 
import termios
import time
import tty


from tornado.ioloop import IOLoop
from tornado.iostream import IOStream


def signalHandler(signal, frame):
    sys.exit(0)


class BetelBotMethod:
    PUBLISH = 'publish'
    SUBSCRIBE = 'subscribe'
    SERVICE = 'service'
    REQUEST = 'request'
    RESPONSE = 'response'

class JsonRpcProp:
    ID = 'id'
    METHOD = 'method'
    PARAMS = 'params'
    RESULT = 'result'
    ERROR = 'error'


class JsonRpcEncoder:

    def request(self, id, method, *params):
        return self.encode({
            JsonRpcProp.ID: id, 
            JsonRpcProp.METHOD: method, 
            JsonRpcProp.PARAMS: params})

    def response(self, id, result, error=None):
        return self.encode({
            JsonRpcProp.ID:id, 
            JsonRpcProp.RESULT: result, 
            JsonRpcProp.ERROR: error})

    def notification(self, method, *params):
        return self.encode({
            JsonRpcProp.ID: None, 
            JsonRpcProp.METHOD: method, 
            JsonRpcProp.PARAMS: params})

    def encode(self, msg):
        return json.dumps(msg)


class BetelBotClient:

    def __init__(self, host='', port=8888, terminator='\0'):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.stream = IOStream(sock)
        self.stream.connect((host, port))
        self.subscriptionHandlers = {}
        self.serviceHandlers = {}
        self.pendingReponses = {}
        self.terminator = terminator
        self.rpc = JsonRpcEncoder()

    def publish(self, topic, *args):
        self.write(self.rpc.notification(BetelBotMethod.PUBLISH, topic, *args))

    def subscribe(self, topic, callback=None):
        if topic not in self.subscriptionHandlers:
            self.subscriptionHandlers[topic] = []
        self.subscriptionHandlers[topic].append(callback)
        self.write(self.rpc.notification(BetelBotMethod.SUBSCRIBE, topic))
        if not self.stream.reading():
            self.stream.read_until(self.terminator, self.onReadLine)

    def service(self, method, callback=None):
        self.serviceHandlers[method] = callback      
        self.write(self.rpc.notification(BetelBotMethod.SERVICE, method))

    def request(self, id, method, callback=None, *params):
        self.pendingReponses[id] = callback
        self.write(self.rpc.request(BetelBotMethod.REQUEST, id, method, *params))

    def response(self, id, result, error=None):
        self.write(self.rpc.response(BetelBotMethod.RESPONSE, id, result, error))

    def write(self, msg):
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
            self.serviceHandlers[method](id, method, msg[JsonRpcProp.params])

    def onResponse(self, msg):
        result = msg[JsonRpcProp.RESULT]
        error = msg[JsonRpcProp.ERROR]
        callback = self.pendingReponses.pop(id, None)
        callback(id, result, error)

    def close():
        self.stream.close()


class NonBlockingTerm:

    def run(self, cb):
        signal.signal(signal.SIGINT, signalHandler)
        
        old_settings = termios.tcgetattr(sys.stdin)
        
        fd = sys.stdin.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        try:
            tty.setcbreak(sys.stdin.fileno())
            while True:
                time.sleep(.3)
                if self.hasData():
                    cb()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def hasData(self):
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])
