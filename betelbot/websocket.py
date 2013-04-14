 #!/usr/bin/env python

import logging
import signal
import socket

from tornado.iostream import IOStream
from tornado.ioloop import IOLoop
from tornado import web, websocket

import jsonrpc

from client import BetelbotClientConnection
from jsonconfig import JsonConfig
from util import Client, signalHandler
from topic.default import ParticleTopic, PathTopic


class VizualizerWebSocket(websocket.WebSocketHandler):

    def initialize(self, conn):
        self.conn = conn
        self.particleTopic = ParticleTopic()
        self.pathTopic = PathTopic()
        self.encoder = jsonrpc.Encoder()

    def open(self):
        logging.info('WebSocket connected. Subscribing to particle topic')
        self.conn.subscribe(self.particleTopic.id, self.onNotifySub)
        self.conn.subscribe(self.pathTopic.id, self.onNotifySub)

    def on_message(self, message):
        self.write_message(message)

    def on_close(self):
        logging.info('WebSocket closed.')

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
