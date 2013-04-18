 #!/usr/bin/env python

import logging
import signal
import socket

from tornado.iostream import IOStream
from tornado.ioloop import IOLoop
from tornado import web, websocket

import jsonrpc

from client import BetelbotClientConnection
from config import JsonConfig
from util import Client, signalHandler
from topic import getTopicFactory


class VizualizerWebSocket(websocket.WebSocketHandler):

    # Websocket log messages
    LOG_CONNECTED = 'WebSocket connected. Subscribing to topics'
    LOG_CLOSED = 'WebSocket closed'

    def initialize(self, conn):
        self.conn = conn
        self.topics = getTopicFactory()
        self.encoder = jsonrpc.Encoder()

    def open(self):
        logging.info(VizualizerWebSocket.LOG_CONNECTED)
        self.conn.subscribe(self.topics.particle.id, self.onNotifySub)
        self.conn.subscribe(self.topics.path.id, self.onNotifySub)
        self.conn.subscribe(self.topics.power.id, self.onNotifySub)
        self.conn.subscribe(self.topics.mode.id, self.onNotifySub)
        self.conn.subscribe(self.topics.location.id, self.onNotifySub)
        self.conn.subscribe(self.topics.waypoint.id, self.onNotifySub)

    def on_message(self, message):
        self.write_message(message)

    def on_close(self):
        logging.info(VizualizerWebSocket.LOG_CLOSED)

    def onNotifySub(self, topic, data=None):
        msg = self.encoder.notification(topic, data[0])
        self.write_message(msg)


def main():
    signal.signal(signal.SIGINT, signalHandler)

    cfg = JsonConfig()

    logger = logging.getLogger('')
    logger.setLevel(cfg.general.logLevel)

    client = Client('', cfg.server.port, BetelbotClientConnection)
    conn = client.connect()

    application = web.Application([
        (cfg.websocketServer.socketUri, VizualizerWebSocket, dict(conn=conn)),
    ])

    application.listen(cfg.websocketServer.port)
    IOLoop.instance().start()


if __name__ == '__main__':
    main()
