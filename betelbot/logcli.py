#!/usr/bin/env python

import logging
import signal

from tornado.ioloop import IOLoop

from client import BetelbotClientConnection
from jsonconfig import JsonConfig
from topic import getTopics
from util import Client, signalHandler


def onTopicPublished(topic, data=None):
    # Callback function that prints the name of topic and associated data to
    # console.
    #
    # This function is designed to be executed by Betelbot client whenever a
    # subscription receives new data from a publisher.

    if data:
        print '[{}]{}'.format(topic, ' '.join(map(str, data)))


def main():
    # Start up a Betelbot client and subscribe to all topics. When data is
    # received, print to console.
    #
    # The main purpose of this script is for logging messages.

    signal.signal(signal.SIGINT, signalHandler)

    cfg = JsonConfig()

    logger = logging.getLogger('')
    logger.setLevel(cfg.general.logLevel)

    client = Client('', cfg.server.port, BetelbotClientConnection)
    conn = client.connect()

    topics = getTopics()
    for topic in topics:
        conn.subscribe(topic, onTopicPublished)

    IOLoop.instance().start()


if __name__ == "__main__":
    main()