#!/usr/bin/env python

import ConfigParser
import logging
import signal

from tornado.ioloop import IOLoop

from util import BetelBotClient, signalHandler
from topic import msgs


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

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')
    client = BetelBotClient('', config.getint('server', 'port'))
    for msg in msgs:
        client.subscribe(msg, onTopicPublished)
    IOLoop.instance().start()


if __name__ == "__main__":
    main()