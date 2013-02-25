import ConfigParser
import logging
import socket

from tornado.iostream import IOStream
from tornado.ioloop import IOLoop
from tornado import web, websocket

from util import PubSubClient
from topic import msgs

connections = []


class VizualizerWebSocket(websocket.WebSocketHandler):

    def open(self):
        logging.info('WebSocket connected.')
        connections.append(self)

    def on_message(self, message):
        self.write_message(u"You said: " + message)

    def on_close(self):
        logging.info('WebSocket closed.')
        connections.remove(self)


def callback(data=None):
    if data:
        print data


def main():
    application = web.Application([
        (r"/socket", VizualizerWebSocket),
    ])

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    client = PubSubClient('', config.getint('server', 'port'))
    client.subscribe('move', callback)

    application.listen(config.getint('websocket-server', 'port'))
    
    IOLoop.instance().start()


if __name__ == "__main__":
    main()
