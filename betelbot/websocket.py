 #!/usr/bin/env python

import json
import logging
import signal
import socket

from tornado.iostream import IOStream
from tornado.ioloop import IOLoop
from tornado import web, websocket

import jsonrpc

from client import BetelbotClientConnection
from config import JsonConfig
from master import BetelbotMethod
from robosim import RobotMethod
from topic import getTopicFactory
from util import Client, signalHandler


class VisualizerWebSocket(websocket.WebSocketHandler):

    # Websocket log messages
    LOG_CONNECTED = 'WebSocket connected. Subscribing to topics'
    LOG_CLOSED = 'WebSocket closed'

    state = {}

    def initialize(self, conn):
        self.conn = conn
        self.topics = getTopicFactory()
        self.encoder = jsonrpc.Encoder()

    def open(self):
        logging.info(VisualizerWebSocket.LOG_CONNECTED)

        self.conn.subscribe(self.topics.particle.id, self.onNotifySub)
        self.conn.subscribe(self.topics.path.id, self.onNotifySub)
        self.conn.subscribe(self.topics.power.id, self.onNotifySub)
        self.conn.subscribe(self.topics.mode.id, self.onNotifySub)
        self.conn.subscribe(self.topics.location.id, self.onNotifySub)
        self.conn.subscribe(self.topics.waypoint.id, self.onNotifySub)

        for key in VisualizerWebSocket.state:
            msg = self.encoder.notification(key, state[key])
            self.write(msg)

    def on_message(self, message):
        data = json.loads(message)
        method = data.get(jsonrpc.Key.METHOD, None)
        params = data.get(jsonrpc.Key.PARAMS, None)

        if method == BetelbotMethod.PUBLISH and params[0] == self.topics.cmd.id:
            self.conn.publish(*params)
        elif method == RobotMethod.POWER:
            self.conn.robot_power(self.onRequest, *params)
        elif method == RobotMethod.MODE:
            self.conn.robot_mode(self.onRequest, *params)

    def on_close(self):
        logging.info(VisualizerWebSocket.LOG_CLOSED)

    def onNotifySub(self, topic, data=None):
        if topic == self.topics.particle:
            VisualizerWebSocket.state[topic] = data

        msg = self.encoder.notification(topic, data[0])
        self.write_message(msg)

    def onRequest(self, result):
        pass


def onBatchLocateResponse(found):
    pass


def main():
    signal.signal(signal.SIGINT, signalHandler)

    cfg = JsonConfig()

    logger = logging.getLogger('')
    logger.setLevel(cfg.general.logLevel)

    client = Client('', cfg.server.port, BetelbotClientConnection)
    conn = client.connect()
    conn.batchLocate(onBatchLocateResponse,
            [RobotMethod.POWER, RobotMethod.MODE, RobotMethod.STATUS])

    application = web.Application([
        (cfg.websocketServer.socketUri, VisualizerWebSocket, dict(conn=conn)),
    ])

    application.listen(cfg.websocketServer.port)
    IOLoop.instance().start()


if __name__ == '__main__':
    main()
