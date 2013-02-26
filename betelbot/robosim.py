import ConfigParser
import logging
import random
import signal

from tornado.ioloop import IOLoop

from map import simple_world
from topic import msgs
from util import PubSubClient, signal_handler


class RoboSim:

    def __init__(self, client, world):
        self.client = client
        self.world = world
        self.real_location = random.randint(0, len(world) - 1)
        self.client.subscribe('move', self.onMovePublished)

    def sense(self):
        self.client.publish('sense', self.world[self.real_location])

    def onMovePublished(self, topic, data=None):
        self.real_location = (self.real_location + 1) % len(self.world)
        self.sense()


def main():
    signal.signal(signal.SIGINT, signal_handler)

    config = ConfigParser.SafeConfigParser()
    config.read('config/default.cfg')

    client = PubSubClient('', config.getint('server', 'port'))
    
    roboSim = RoboSim(client, simple_world)
    roboSim.sense()

    IOLoop.instance().start()


if __name__ == "__main__":
    main()