 #!/usr/bin/env python

import ConfigParser
import logging
import signal
import socket

from tornado.iostream import IOStream
from tornado.ioloop import IOLoop
from tornado import web, websocket

import jsonrpc

from client import BetelbotClientConnection
from util import Client, signalHandler
from topic.default import ParticleTopic


class VizualizerWebSocket(websocket.WebSocketHandler):

    def initialize(self, conn):
        self.conn = conn
        self.particleTopic = ParticleTopic()
        self.encoder = jsonrpc.Encoder()

    def open(self):
        logging.info('WebSocket connected. Subscribing to particle topic')
        self.conn.subscribe(self.particleTopic.id, self.onNotifySub)

    def on_message(self, message):
        self.write_message(message)

    def on_close(self):
        logging.info('WebSocket closed.')

    def onNotifySub(self, topic, data=None):
        msg = self.encoder.notification(topic, data[0])
        self.write_message(msg)


def main():
    signal.signal(signal.SIGINT, signalHandler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    logger = logging.getLogger('')
    logger.setLevel(config.get('general', 'log_level'))

    client = Client('', config.getint('server', 'port'), BetelbotClientConnection)
    conn = client.connect()

    application = web.Application([
        (r"/socket", VizualizerWebSocket, dict(conn=conn)),
    ])

    application.listen(config.getint('websocket-server', 'port'))
    IOLoop.instance().start()


if __name__ == '__main__':
    main()
