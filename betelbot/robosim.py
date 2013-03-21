#!/usr/bin/env python

import ConfigParser
import logging
import random
import signal

from tornado.ioloop import IOLoop

from map import simple_world
from topic import cmdTopic, moveTopic, senseTopic
from util import BetelBotClient, signalHandler


class RoboSim:

    def __init__(self, client, world):
        self.client = client
        self.world = world
        self.real_location = random.randint(0, len(world) - 1)
        self.client.subscribe(cmdTopic.id, self.onCmdPublished)

    def move(self, direction):
        self.client.publish(moveTopic.id, direction)

    def sense(self):
        self.client.publish(senseTopic.id, self.world[self.real_location])

    def onCmdPublished(self, topic, data=None):
        self.real_location = (self.real_location + 1) % len(self.world)
        self.move(moveTopic.dataType[2])
        self.sense()


def main():
    signal.signal(signal.SIGINT, signalHandler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    client = BetelBotClient('', config.getint('server', 'port'))
    roboSim = RoboSim(client, simple_world)
    IOLoop.instance().start()


if __name__ == "__main__":
    main()