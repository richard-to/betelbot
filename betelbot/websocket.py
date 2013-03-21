#!/usr/bin/env python

import ConfigParser
import logging
import signal
import socket

from tornado.iostream import IOStream
from tornado.ioloop import IOLoop
from tornado import web, websocket

from util import PubSubClient, signalHandler
from topic import histogramTopic


class VizualizerWebSocket(websocket.WebSocketHandler):

    def initialize(self, client):
        self.client = client

    def open(self):
        logging.info('WebSocket connected. Subscribing to histogram topic')
        self.client.subscribe(histogramTopic.id, self.callback)

    def on_message(self, message):
        self.write_message(message)

    def on_close(self):
        logging.info('WebSocket closed.')

    def callback(self, topic, data=None):
        self.write_message(" ".join(map(str, data)))


def main():
    signal.signal(signal.SIGINT, signalHandler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    client = PubSubClient('', config.getint('server', 'port'))

    application = web.Application([
        (r"/socket", VizualizerWebSocket, dict(client=client)),
    ])

    application.listen(config.getint('websocket-server', 'port'))
    IOLoop.instance().start()


if __name__ == '__main__':
    main()
