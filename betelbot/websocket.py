import ConfigParser
import logging
import socket

from tornado.iostream import IOStream
from tornado.ioloop import IOLoop
from tornado import web, websocket

from util import PubSubClient
from topic import msgs

connections = []


subscribers = []

class VizualizerWebSocket(websocket.WebSocketHandler):

    def open(self):
        logging.info('WebSocket connected.')
        connections.append(self)

    def on_message(self, message):
        self.write_message(message)
        if message == 'subscribe histogram':
            subscribers.append(self)

    def on_close(self):
        logging.info('WebSocket closed.')
        connections.remove(self)


def callback(topic, data=None):
    print data
    for s in subscribers:
        s.write_message(" ".join(map(str, data)))


config = ConfigParser.SafeConfigParser()
config.read('config/default.cfg')

client = PubSubClient('', config.getint('server', 'port'))
client.subscribe('histogram', callback)

application = web.Application([
    (r"/socket", VizualizerWebSocket),
])

application.listen(config.getint('websocket-server', 'port'))

IOLoop.instance().start()